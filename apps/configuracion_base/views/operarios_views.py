from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from ..forms import OperarioForm, OperarioEditForm, ReestablecerPasswordForm
from apps.core_auth.models import Usuario, AuditoriaLog


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
