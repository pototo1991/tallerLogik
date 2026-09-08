from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Empresa, Usuario, AuditoriaLog


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'rut_o_identificacion', 'plan_suscripcion', 'fecha_registro', 'eliminado_en')
    search_fields = ('nombre_empresa', 'rut_o_identificacion')
    list_filter = ('plan_suscripcion', 'fecha_registro')


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('correo_electronico', 'nombre_completo', 'rol', 'id_empresa', 'activo', 'is_staff')
    list_filter = ('rol', 'activo', 'is_staff', 'id_empresa')
    search_fields = ('correo_electronico', 'nombre_completo')
    ordering = ('correo_electronico',)

    fieldsets = (
        (None, {'fields': ('correo_electronico', 'password')}),
        ('Información Personal', {'fields': ('nombre_completo', 'id_empresa', 'rol', 'costo_hora')}),
        ('Permisos', {'fields': ('activo', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('correo_electronico', 'nombre_completo', 'password', 'rol', 'id_empresa'),
        }),
    )


@admin.register(AuditoriaLog)
class AuditoriaLogAdmin(admin.ModelAdmin):
    list_display = ('fecha_registro', 'accion', 'id_usuario', 'id_empresa', 'direccion_ip')
    list_filter = ('accion', 'fecha_registro', 'id_empresa')
    search_fields = ('accion', 'detalles', 'id_usuario__correo_electronico')
    readonly_fields = ('id', 'id_empresa', 'id_usuario', 'accion', 'detalles', 'direccion_ip', 'fecha_registro')
