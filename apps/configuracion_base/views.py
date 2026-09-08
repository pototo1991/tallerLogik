import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from celery.result import AsyncResult

from .models import Cliente, Material, MaterialGlobal, MovimientoInventario, Proveedor
from .forms import ClienteForm, MaterialForm, OperarioForm, OperarioEditForm, ReestablecerPasswordForm, AjusteStockForm, ProveedorForm
from .services import importar_material_a_taller
from .services_inventario import registrar_movimiento_inventario
from .tasks import tarea_scraping_manual_async
from apps.core_auth.models import Usuario, AuditoriaLog


logger = logging.getLogger('saas_taller')




# -------------------------------------------------------------
# 1. GESTIÓN DE CLIENTES
# -------------------------------------------------------------

class ClienteListView(LoginRequiredMixin, View):
    """Lista de clientes del taller activo."""
    def get(self, request):
        clientes = Cliente.objects.filter(id_empresa=request.tenant)
        return render(request, 'configuracion_base/clientes_list.html', {'clientes': clientes})


class ClienteCreateView(LoginRequiredMixin, View):
    """Creación de nuevo cliente con soporte para HTMX modal/fragmento."""
    def get(self, request):
        if not request.tenant:
            messages.warning(request, "Como Superadministrador Global del SaaS, debes registrar o seleccionar primero una Empresa/Taller (Nivel 2) para gestionar sus clientes.")
            return redirect('core_auth:dashboard')
        form = ClienteForm()
        return render(request, 'configuracion_base/cliente_form.html', {'form': form, 'titulo': 'Nuevo Cliente'})

    def post(self, request):
        if not request.tenant:
            messages.error(request, "No se puede crear un cliente sin una Empresa/Taller activa asociadas.")
            return redirect('core_auth:dashboard')
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.id_empresa = request.tenant
            cliente.save()

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='CREAR_CLIENTE',
                detalles=f'Cliente {cliente.razon_social} creado.',
                direccion_ip=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Cliente '{cliente.razon_social}' creado con éxito.")
            return redirect('configuracion_base:clientes_list')
        return render(request, 'configuracion_base/cliente_form.html', {'form': form, 'titulo': 'Nuevo Cliente'})


class ClienteUpdateView(LoginRequiredMixin, View):
    """Edición de cliente existente."""
    def get(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk, id_empresa=request.tenant)
        form = ClienteForm(instance=cliente)
        return render(request, 'configuracion_base/cliente_form.html', {'form': form, 'titulo': 'Editar Cliente', 'cliente': cliente})

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk, id_empresa=request.tenant)
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cliente '{cliente.razon_social}' actualizado.")
            return redirect('configuracion_base:clientes_list')
        return render(request, 'configuracion_base/cliente_form.html', {'form': form, 'titulo': 'Editar Cliente', 'cliente': cliente})


class ClienteDeleteView(LoginRequiredMixin, View):
    """Borrado lógico de cliente."""
    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk, id_empresa=request.tenant)
        razon_social = cliente.razon_social
        cliente.delete()

        AuditoriaLog.objects.create(
            id_empresa=request.tenant,
            id_usuario=request.user,
            accion='BORRAR_CLIENTE',
            detalles=f'Cliente {razon_social} eliminado lógicamente.',
            direccion_ip=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Cliente '{razon_social}' eliminado.")
        return redirect('configuracion_base:clientes_list')


# -------------------------------------------------------------
# 1.1 GESTIÓN DE PROVEEDORES
# -------------------------------------------------------------

class ProveedorListView(LoginRequiredMixin, View):
    """Lista de proveedores del taller activo."""
    def get(self, request):
        proveedores = Proveedor.objects.filter(id_empresa=request.tenant)
        return render(request, 'configuracion_base/proveedores_list.html', {'proveedores': proveedores})


class ProveedorCreateView(LoginRequiredMixin, View):
    """Creación de nuevo proveedor."""
    def get(self, request):
        if not request.tenant:
            messages.warning(request, "Debes seleccionar primero una Empresa/Taller activa.")
            return redirect('core_auth:dashboard')
        form = ProveedorForm()
        return render(request, 'configuracion_base/proveedor_form.html', {'form': form, 'titulo': 'Nuevo Proveedor'})

    def post(self, request):
        if not request.tenant:
            messages.error(request, "No se puede crear un proveedor sin una Empresa/Taller activa.")
            return redirect('core_auth:dashboard')
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.id_empresa = request.tenant
            proveedor.save()

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='CREAR_PROVEEDOR',
                detalles=f'Proveedor {proveedor.razon_social} creado.',
                direccion_ip=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Proveedor '{proveedor.razon_social}' creado con éxito.")
            return redirect('configuracion_base:proveedores_list')
        return render(request, 'configuracion_base/proveedor_form.html', {'form': form, 'titulo': 'Nuevo Proveedor'})


class ProveedorUpdateView(LoginRequiredMixin, View):
    """Edición de proveedor existente."""
    def get(self, request, pk):
        proveedor = get_object_or_404(Proveedor, pk=pk, id_empresa=request.tenant)
        form = ProveedorForm(instance=proveedor)
        return render(request, 'configuracion_base/proveedor_form.html', {'form': form, 'titulo': 'Editar Proveedor', 'proveedor': proveedor})

    def post(self, request, pk):
        proveedor = get_object_or_404(Proveedor, pk=pk, id_empresa=request.tenant)
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, f"Proveedor '{proveedor.razon_social}' actualizado.")
            return redirect('configuracion_base:proveedores_list')
        return render(request, 'configuracion_base/proveedor_form.html', {'form': form, 'titulo': 'Editar Proveedor', 'proveedor': proveedor})


class ProveedorDeleteView(LoginRequiredMixin, View):
    """Borrado de proveedor."""
    def post(self, request, pk):
        proveedor = get_object_or_404(Proveedor, pk=pk, id_empresa=request.tenant)
        razon_social = proveedor.razon_social
        proveedor.delete()

        AuditoriaLog.objects.create(
            id_empresa=request.tenant,
            id_usuario=request.user,
            accion='BORRAR_PROVEEDOR',
            detalles=f'Proveedor {razon_social} eliminado.',
            direccion_ip=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Proveedor '{razon_social}' eliminado.")
        return redirect('configuracion_base:proveedores_list')


# -------------------------------------------------------------
# 2. CATÁLOGO DE MATERIALES E INSUMOS
# -------------------------------------------------------------

class MaterialListView(LoginRequiredMixin, View):
    """Catálogo de materiales del taller."""
    def get(self, request):
        materiales = Material.objects.filter(id_empresa=request.tenant)
        return render(request, 'configuracion_base/materiales_list.html', {'materiales': materiales})


class MaterialCreateView(LoginRequiredMixin, View):
    """Crear nuevo material."""
    def get(self, request):
        if not request.tenant:
            messages.warning(request, "Como Superadministrador Global del SaaS, debes registrar o seleccionar primero una Empresa/Taller (Nivel 2) para gestionar materiales.")
            return redirect('core_auth:dashboard')
        form = MaterialForm()
        return render(request, 'configuracion_base/material_form.html', {'form': form, 'titulo': 'Nuevo Material'})

    def post(self, request):
        if not request.tenant:
            messages.error(request, "No se puede crear un material sin una Empresa/Taller activa.")
            return redirect('core_auth:dashboard')
        form = MaterialForm(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            material.id_empresa = request.tenant
            material.save()
            messages.success(request, f"Material '{material.nombre}' añadido al catálogo.")
            return redirect('configuracion_base:materiales_list')
        return render(request, 'configuracion_base/material_form.html', {'form': form, 'titulo': 'Nuevo Material'})


class MaterialUpdateView(LoginRequiredMixin, View):
    """Editar material existente."""
    def get(self, request, pk):
        material = get_object_or_404(Material, pk=pk, id_empresa=request.tenant)
        form = MaterialForm(instance=material)
        return render(request, 'configuracion_base/material_form.html', {'form': form, 'titulo': 'Editar Material', 'material': material})

    def post(self, request, pk):
        material = get_object_or_404(Material, pk=pk, id_empresa=request.tenant)
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, f"Material '{material.nombre}' actualizado.")
            return redirect('configuracion_base:materiales_list')
        return render(request, 'configuracion_base/material_form.html', {'form': form, 'titulo': 'Editar Material', 'material': material})


class MaterialDeleteView(LoginRequiredMixin, View):
    """Borrado lógico de material."""
    def post(self, request, pk):
        material = get_object_or_404(Material, pk=pk, id_empresa=request.tenant)
        nombre = material.nombre
        material.delete()
        messages.success(request, f"Material '{nombre}' eliminado.")
        return redirect('configuracion_base:materiales_list')


class MaterialAjustarStockView(LoginRequiredMixin, View):
    """Modal/Formulario para registrar entradas, compras o ajustes manuales de stock."""
    def get(self, request, pk):
        material = get_object_or_404(Material, pk=pk, id_empresa=request.tenant)
        form = AjusteStockForm()
        context = {
            'material': material,
            'form': form
        }
        return render(request, 'configuracion_base/partials/modal_ajuste_stock.html', context)

    def post(self, request, pk):
        material = get_object_or_404(Material, pk=pk, id_empresa=request.tenant)
        form = AjusteStockForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data['tipo_operacion']
            cant = form.cleaned_data['cantidad']
            obs = form.cleaned_data['observaciones']

            # Si es ajuste por corrección/pérdida, se registra como salida (-)
            if tipo == 'AJUSTE_MANUAL':
                cant = -cant

            movimiento = registrar_movimiento_inventario(
                material=material,
                cantidad=cant,
                tipo_movimiento=tipo,
                usuario=request.user,
                observaciones=obs
            )

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='AJUSTAR_STOCK_BODEGA',
                detalles=f"Stock de '{material.nombre}' ajustado en {cant} unidades. Nuevo stock: {movimiento.stock_resultante}",
                direccion_ip=request.META.get('REMOTE_ADDR')
            )

            messages.success(request, f"Stock de '{material.nombre}' actualizado correctamente a {movimiento.stock_resultante} {material.unidad_medida}.")
            return redirect('configuracion_base:materiales_list')

        context = {
            'material': material,
            'form': form
        }
        return render(request, 'configuracion_base/partials/modal_ajuste_stock.html', context)


class MaterialHistorialMovimientosView(LoginRequiredMixin, View):
    """Muestra el historial/Kardex de entradas y salidas de bodega para un material."""
    def get(self, request, pk):
        material = get_object_or_404(Material, pk=pk, id_empresa=request.tenant)
        movimientos = MovimientoInventario.objects.filter(
            id_empresa=request.tenant,
            id_material=material
        ).select_related('id_usuario', 'id_proyecto')

        context = {
            'material': material,
            'movimientos': movimientos
        }
        return render(request, 'configuracion_base/partials/modal_historial_stock.html', context)



# -------------------------------------------------------------
# 3. GESTIÓN DE OPERARIOS Y TARIFAS HORA (Solo Dueño de Taller)
# -------------------------------------------------------------

class OperarioListView(LoginRequiredMixin, View):
    """Lista de personal del taller."""
    def get(self, request):
        if request.user.rol not in ['superadmin_saas', 'dueno_taller', 'jefe_taller']:
            messages.error(request, "No tienes permisos para acceder a la gestión de operarios.")
            return redirect('core_auth:dashboard')

        operarios = Usuario.objects.filter(id_empresa=request.tenant)
        return render(request, 'configuracion_base/operarios_list.html', {'operarios': operarios})


class OperarioCreateView(LoginRequiredMixin, View):
    """Crear nuevo usuario/operario en el taller."""
    def get(self, request):
        if request.user.rol not in ['superadmin_saas', 'dueno_taller']:
            messages.error(request, "Solo el Dueño del Taller puede registrar nuevo personal.")
            return redirect('configuracion_base:operarios_list')

        form = OperarioForm()
        return render(request, 'configuracion_base/operario_form.html', {'form': form, 'titulo': 'Nuevo Miembro del Equipo'})

    def post(self, request):
        if request.user.rol not in ['superadmin_saas', 'dueno_taller']:
            return redirect('configuracion_base:operarios_list')

        form = OperarioForm(request.POST)
        if form.is_valid():
            operario = Usuario.objects.create_user(
                correo_electronico=form.cleaned_data['correo_electronico'],
                password=form.cleaned_data['password'],
                nombre_completo=form.cleaned_data['nombre_completo'],
                rol=form.cleaned_data['rol'],
                costo_hora=form.cleaned_data['costo_hora'],
                id_empresa=request.tenant
            )
            messages.success(request, f"Usuario '{operario.nombre_completo}' registrado exitosamente.")
            return redirect('configuracion_base:operarios_list')
        return render(request, 'configuracion_base/operario_form.html', {'form': form, 'titulo': 'Nuevo Miembro del Equipo'})


class OperarioUpdateView(LoginRequiredMixin, View):
    """Editar datos de un miembro del equipo existente (sin modificar su contraseña)."""
    def get(self, request, pk):
        if request.user.rol not in ['superadmin_saas', 'dueno_taller']:
            messages.error(request, "Solo el Dueño del Taller puede editar datos del personal.")
            return redirect('configuracion_base:operarios_list')

        operario = get_object_or_404(Usuario, pk=pk, id_empresa=request.tenant)
        form = OperarioEditForm(instance=operario)
        return render(request, 'configuracion_base/operario_form.html', {
            'form': form,
            'titulo': f"Editar Miembro - {operario.nombre_completo}",
            'operario': operario
        })

    def post(self, request, pk):
        if request.user.rol not in ['superadmin_saas', 'dueno_taller']:
            messages.error(request, "Solo el Dueño del Taller puede editar datos del personal.")
            return redirect('configuracion_base:operarios_list')

        operario = get_object_or_404(Usuario, pk=pk, id_empresa=request.tenant)
        form = OperarioEditForm(request.POST, instance=operario)
        if form.is_valid():
            form.save()
            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='EDITAR_OPERARIO',
                detalles=f'Datos del usuario {operario.correo_electronico} ({operario.nombre_completo}) actualizados.',
                direccion_ip=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Datos de '{operario.nombre_completo}' actualizados con éxito.")
            return redirect('configuracion_base:operarios_list')

        return render(request, 'configuracion_base/operario_form.html', {
            'form': form,
            'titulo': f"Editar Miembro - {operario.nombre_completo}",
            'operario': operario
        })


class OperarioResetPasswordView(LoginRequiredMixin, View):
    """Permite al Dueño o Jefe de Taller restablecer la contraseña de un miembro del equipo."""
    def get(self, request, pk):
        if request.user.rol not in ['superadmin_saas', 'dueno_taller', 'jefe_taller']:
            messages.error(request, "No tienes permisos para restablecer contraseñas.")
            return redirect('configuracion_base:operarios_list')

        operario = get_object_or_404(Usuario, pk=pk, id_empresa=request.tenant)
        form = ReestablecerPasswordForm()
        return render(request, 'configuracion_base/operario_reset_password.html', {
            'form': form,
            'operario': operario,
            'titulo': f"Restablecer Contraseña - {operario.nombre_completo}"
        })

    def post(self, request, pk):
        if request.user.rol not in ['superadmin_saas', 'dueno_taller', 'jefe_taller']:
            messages.error(request, "No tienes permisos para restablecer contraseñas.")
            return redirect('configuracion_base:operarios_list')

        operario = get_object_or_404(Usuario, pk=pk, id_empresa=request.tenant)
        form = ReestablecerPasswordForm(request.POST)

        if form.is_valid():
            nueva_clave = form.cleaned_data['password']
            operario.set_password(nueva_clave)
            operario.save()

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='RESTABLECER_PASSWORD_OPERARIO',
                detalles=f'Contraseña restablecida para {operario.correo_electronico} por {request.user.nombre_completo}.',
                direccion_ip=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Contraseña del usuario '{operario.nombre_completo}' restablecida con éxito.")
            return redirect('configuracion_base:operarios_list')

        return render(request, 'configuracion_base/operario_reset_password.html', {
            'form': form,
            'operario': operario,
            'titulo': f"Restablecer Contraseña - {operario.nombre_completo}"
        })


class OperarioToggleActivoView(LoginRequiredMixin, View):
    """Permite EXCLUSIVAMENTE al Dueño del Taller (o Superadmin SaaS) activar o desactivar miembros del equipo de cualquier rol."""
    def post(self, request, pk):
        if request.user.rol not in ['superadmin_saas', 'dueno_taller']:
            messages.error(request, "Solo el Dueño del Taller tiene permisos para activar o desactivar miembros del equipo.")
            return redirect('configuracion_base:operarios_list')

        operario = get_object_or_404(Usuario, pk=pk, id_empresa=request.tenant)

        # Prevenir que el usuario desactive su propia cuenta activa
        if operario.id == request.user.id:
            messages.error(request, "No puedes desactivar tu propia cuenta de usuario.")
            return redirect('configuracion_base:operarios_list')

        operario.activo = not operario.activo
        operario.save()

        estado_txt = "activado" if operario.activo else "desactivado"
        AuditoriaLog.objects.create(
            id_empresa=request.tenant,
            id_usuario=request.user,
            accion='CAMBIAR_ESTADO_USUARIO',
            detalles=f'El usuario {operario.correo_electronico} ({operario.get_rol_display()}) fue {estado_txt}.',
            direccion_ip=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f"El usuario '{operario.nombre_completo}' ha sido {estado_txt} con éxito.")
        return redirect('configuracion_base:operarios_list')


# -------------------------------------------------------------
# 4. CATÁLOGO GLOBAL & SCRAPING (Imperial)
# -------------------------------------------------------------


class MaterialGlobalBuscarView(LoginRequiredMixin, View):
    """Buscador y visor del catálogo global de materiales de Imperial."""
    def get(self, request):
        query = request.GET.get('q', '').strip()
        categoria = request.GET.get('categoria', '').strip()

        materiales = MaterialGlobal.objects.all()

        if query:
            materiales = materiales.filter(nombre__icontains=query) | materiales.filter(sku_proveedor__icontains=query)
        if categoria:
            materiales = materiales.filter(categoria=categoria)

        # Determinar qué materiales ya han sido importados por este taller
        imported_skus = set(
            Material.objects.filter(
                id_empresa=request.tenant,
                sku_proveedor__isnull=False
            ).values_list('sku_proveedor', flat=True)
        )

        for mg in materiales:
            mg.ya_importado = mg.sku_proveedor in imported_skus

        categorias_choices = MaterialGlobal.CATEGORIAS
        total_imperial = MaterialGlobal.objects.filter(proveedor='Imperial').count()

        context = {
            'materiales': materiales,
            'query': query,
            'categoria_filtro': categoria,
            'categorias': categorias_choices,
            'total_imperial': total_imperial,
        }
        return render(request, 'configuracion_base/materiales_global_buscar.html', context)


class MaterialImportarActionView(LoginRequiredMixin, View):
    """Acción que importa un material global al catálogo privado del taller."""
    def post(self, request, global_id):
        if not request.tenant:
            return JsonResponse({'error': 'No hay un taller activo configurado.'}, status=400)

        try:
            importar_material_a_taller(global_id, request.tenant, request.user)
            # Retornar un fragmento HTML para HTMX que reemplace el botón por una insignia de éxito
            return render(request, 'configuracion_base/partials/badge_importado.html')
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.exception("Error al importar material global")
            return JsonResponse({'error': 'Error interno del servidor.'}, status=500)


class EjecutarScrapingManualView(LoginRequiredMixin, View):
    """Acción que inicia el scraping de Imperial en segundo plano."""
    def post(self, request):
        if request.user.rol not in ['superadmin_saas']:
            return JsonResponse({'error': 'No tienes permisos para ejecutar la sincronización.'}, status=403)

        # Disparar tarea en segundo plano
        task = tarea_scraping_manual_async.delay(request.user.id)

        # Retornar el fragmento que inicia el polling de HTMX
        context = {
            'task_id': task.id,
            'message': 'Iniciando conexión con Imperial...'
        }
        return render(request, 'configuracion_base/partials/scraping_progress.html', context)


class ScrapingTaskStatusView(LoginRequiredMixin, View):
    """Consulta el estado actual de la tarea de scraping y retorna fragmentos HTMX."""
    def get(self, request, task_id):
        res = AsyncResult(task_id)
        
        if res.state == 'PROGRESS':
            info = res.info or {}
            context = {
                'task_id': task_id,
                'current': info.get('current', 10),
                'message': info.get('message', 'Procesando...')
            }
            return render(request, 'configuracion_base/partials/scraping_progress.html', context)
            
        elif res.state == 'SUCCESS':
            result = res.result or {}
            context = {
                'creados': result.get('creados', 0),
                'actualizados': result.get('actualizados', 0),
                'completado': True
            }
            return render(request, 'configuracion_base/partials/scraping_success.html', context)
            
        elif res.state == 'FAILURE':
            context = {
                'error': 'La tarea de sincronización falló o fue cancelada.',
                'fallado': True
            }
            return render(request, 'configuracion_base/partials/scraping_error.html', context)
            
        else:
            # Estado pendiente o desconocido
            context = {
                'task_id': task_id,
                'current': 5,
                'message': 'En cola de espera...'
            }
            return render(request, 'configuracion_base/partials/scraping_progress.html', context)

