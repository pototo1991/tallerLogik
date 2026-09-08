import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .forms import LoginForm, OnboardingTallerForm
from .models import Empresa, Usuario, AuditoriaLog

logger = logging.getLogger('saas_taller')


class CustomLoginView(View):
    """Vista de Inicio de Sesión."""
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core_auth:dashboard')
        form = LoginForm()
        return render(request, 'core_auth/login.html', {'form': form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            
            # Registrar log de auditoría en BD
            AuditoriaLog.objects.create(
                id_empresa=user.id_empresa,
                id_usuario=user,
                accion='INICIO_SESION',
                detalles=f'Inicio de sesión exitoso para {user.correo_electronico}',
                direccion_ip=request.META.get('REMOTE_ADDR')
            )
            logger.info(f"Inicio de sesión exitoso para el usuario {user.correo_electronico}")
            return redirect('core_auth:dashboard')
        
        return render(request, 'core_auth/login.html', {'form': form})


class CustomLogoutView(View):
    """Vista de Cierre de Sesión."""
    def get(self, request):
        if request.user.is_authenticated:
            logger.info(f"Cierre de sesión del usuario {request.user.correo_electronico}")
            logout(request)
        return redirect('core_auth:login')


class OnboardingTallerView(LoginRequiredMixin, View):
    """Vista para el Onboarding / Alta de un nuevo Taller y su Dueño (restringido a Superadmin SaaS)."""
    login_url = '/auth/login/'

    def get(self, request):
        if getattr(request.user, 'rol', None) != 'superadmin_saas':
            messages.error(request, "Acceso denegado: Solo el Superadministrador SaaS puede registrar nuevos talleres.")
            return redirect('core_auth:dashboard')
        form = OnboardingTallerForm()
        return render(request, 'core_auth/onboarding_taller.html', {'form': form})

    def post(self, request):
        if getattr(request.user, 'rol', None) != 'superadmin_saas':
            messages.error(request, "Acceso denegado: Solo el Superadministrador SaaS puede registrar nuevos talleres.")
            return redirect('core_auth:dashboard')

        form = OnboardingTallerForm(request.POST)
        if form.is_valid():
            # 1. Crear Empresa / Tenant
            empresa = Empresa.objects.create(
                nombre_empresa=form.cleaned_data['nombre_empresa'],
                rut_o_identificacion=form.cleaned_data.get('rut_o_identificacion')
            )
            
            # 2. Crear Usuario Dueño de Taller
            usuario = Usuario.objects.create_user(
                correo_electronico=form.cleaned_data['correo_electronico'],
                password=form.cleaned_data['password'],
                nombre_completo=form.cleaned_data['nombre_dueno'],
                rol='dueno_taller',
                id_empresa=empresa,
                is_staff=False
            )

            # 3. Registrar Log de Auditoría
            AuditoriaLog.objects.create(
                id_empresa=empresa,
                id_usuario=request.user,
                accion='REGISTRO_TALLER',
                detalles=f'Registro de nuevo taller {empresa.nombre_empresa} con dueño {usuario.correo_electronico}',
                direccion_ip=request.META.get('REMOTE_ADDR')
            )
            logger.info(f"Nuevo taller registrado por Superadmin {request.user.correo_electronico}: {empresa.nombre_empresa} ({empresa.id})")

            messages.success(request, f"¡Taller '{empresa.nombre_empresa}' y su Usuario Dueño '{usuario.correo_electronico}' registrados exitosamente!")
            return redirect('core_auth:dashboard')

        return render(request, 'core_auth/onboarding_taller.html', {'form': form})


from django.utils import timezone

class ToggleEmpresaEstadoView(LoginRequiredMixin, View):
    """Permite al Superadmin cambiar el estado (Habilitado / Deshabilitado) de un Taller/Empresa cliente."""
    def post(self, request, pk):
        if request.user.rol != 'superadmin_saas':
            messages.error(request, "No tienes permisos para cambiar el estado de las empresas.")
            return redirect('core_auth:dashboard')

        empresa = get_object_or_404(Empresa.all_objects, pk=pk)
        if empresa.eliminado_en:
            empresa.eliminado_en = None
            estado_str = "Habilitada"
        else:
            empresa.eliminado_en = timezone.now()
            estado_str = "Deshabilitada"
        
        empresa.save()

        # Actualizar el campo 'activo' de los usuarios asociados
        Usuario.all_objects.filter(id_empresa=empresa).update(activo=(empresa.eliminado_en is None))

        AuditoriaLog.objects.create(
            id_empresa=empresa,
            id_usuario=request.user,
            accion='CAMBIAR_ESTADO_EMPRESA',
            detalles=f'Empresa {empresa.nombre_empresa} fue {estado_str}.',
            direccion_ip=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f"La empresa '{empresa.nombre_empresa}' ahora está {estado_str}.")
        return redirect('core_auth:dashboard')


from apps.rentabilidad_cobranzas.services import obtener_metricas_globales_taller


class DashboardView(LoginRequiredMixin, View):
    """Dashboard principal del usuario con vista diferenciada según su rol."""
    login_url = '/auth/login/'

    def get(self, request):
        user = request.user
        empresa = request.tenant
        metricas = obtener_metricas_globales_taller(empresa) if empresa else None

        empresas_saas = []
        usuarios_saas = []

        if user.rol == 'superadmin_saas':
            empresas_saas = list(Empresa.all_objects.all().order_by('-fecha_registro'))
            for emp in empresas_saas:
                emp.dueno = Usuario.all_objects.filter(id_empresa=emp, rol='dueno_taller').first()
            usuarios_saas = list(Usuario.all_objects.select_related('id_empresa').all().order_by('-fecha_creacion'))

        context = {
            'usuario': user,
            'empresa': empresa,
            'rol_nombre': user.get_rol_display(),
            'metricas': metricas,
            'total_empresas': len(empresas_saas) if user.rol == 'superadmin_saas' else 0,
            'total_usuarios': len(usuarios_saas) if user.rol == 'superadmin_saas' else 0,
            'empresas_saas': empresas_saas,
            'usuarios_saas': usuarios_saas,
        }
        return render(request, 'core_auth/dashboard.html', context)


import os
from django.conf import settings

class VerLogsView(LoginRequiredMixin, View):
    """Vista para visualizar los logs del sistema (sistema_actividad.log y sistema_errores.log).
    Restringida exclusivamente a usuarios con rol superadmin_saas.
    """
    login_url = '/auth/login/'

    def get(self, request):
        if getattr(request.user, 'rol', None) != 'superadmin_saas':
            messages.error(request, "Acceso denegado: Solo el Superadministrador SaaS puede ver los logs del sistema.")
            return redirect('core_auth:dashboard')

        tipo = request.GET.get('tipo', 'actividad')
        if tipo not in ['actividad', 'errores']:
            tipo = 'actividad'

        nombre_archivo = 'sistema_actividad.log' if tipo == 'actividad' else 'sistema_errores.log'
        log_filepath = settings.LOGS_DIR / nombre_archivo

        lineas = []
        tamano_kb = 0
        existe = False

        if os.path.exists(log_filepath):
            existe = True
            tamano_kb = round(os.path.getsize(log_filepath) / 1024, 2)
            try:
                with open(log_filepath, 'r', encoding='utf-8', errors='replace') as f:
                    todas = f.readlines()
                    lineas = todas[-500:] if len(todas) > 500 else todas
            except Exception as e:
                logger.error(f"Error al leer archivo de log {nombre_archivo}: {str(e)}")
                messages.error(request, f"Error al abrir el archivo de log: {str(e)}")

        context = {
            'tipo': tipo,
            'nombre_archivo': nombre_archivo,
            'lineas': lineas,
            'total_lineas': len(lineas),
            'tamano_kb': tamano_kb,
            'existe': existe,
        }

        if request.headers.get('HX-Request') and request.GET.get('partial') == '1':
            return render(request, 'core_auth/partials/log_content.html', context)

        return render(request, 'core_auth/logs_viewer.html', context)

