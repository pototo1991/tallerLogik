from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from ..models import Material, MovimientoInventario
from ..forms import MaterialForm, AjusteStockForm
from ..services_inventario import registrar_movimiento_inventario
from apps.core_auth.models import AuditoriaLog


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
        form = MaterialForm(empresa=request.tenant)
        return render(request, 'configuracion_base/material_form.html', {'form': form, 'titulo': 'Nuevo Material'})

    def post(self, request):
        if not request.tenant:
            messages.error(request, "No se puede crear un material sin una Empresa/Taller activa.")
            return redirect('core_auth:dashboard')
        form = MaterialForm(request.POST, empresa=request.tenant)
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
        form = MaterialForm(instance=material, empresa=request.tenant)
        return render(request, 'configuracion_base/material_form.html', {'form': form, 'titulo': 'Editar Material', 'material': material})

    def post(self, request, pk):
        material = get_object_or_404(Material, pk=pk, id_empresa=request.tenant)
        form = MaterialForm(request.POST, instance=material, empresa=request.tenant)
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
