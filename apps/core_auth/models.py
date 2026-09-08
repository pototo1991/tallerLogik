import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import SoftDeleteManager, TenantManager, UsuarioManager


class SoftDeleteModel(models.Model):
    """Modelo base abstracto para borrado lógico (Soft Delete)."""
    eliminado_en = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Sobrescribe el borrado físico por un borrado lógico marcando la fecha actual."""
        self.eliminado_en = timezone.now()
        self.save(update_fields=['eliminado_en'])


class Empresa(SoftDeleteModel):
    """Entidad Tenant / Empresa que representa un Taller o Mueblería a medida."""
    PLANES = (
        ('basico', 'Plan Básico Taller'),
        ('pro', 'Plan Pro Taller'),
        ('enterprise', 'Plan Enterprise'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_empresa = models.CharField(max_length=255)
    rut_o_identificacion = models.CharField(max_length=50, blank=True, null=True)
    plan_suscripcion = models.CharField(max_length=50, choices=PLANES, default='basico')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'empresas'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nombre_empresa


class TenantAwareModel(SoftDeleteModel):
    """Modelo base abstracto para aislamiento multi-tenant estricto."""
    id_empresa = models.ForeignKey(
        Empresa,
        on_delete=models.RESTRICT,
        related_name="%(class)s_set"
    )

    objects = TenantManager()

    class Meta:
        abstract = True


class Usuario(AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    """Modelo de Usuario personalizado con roles de taller y superadministración SaaS."""
    ROLES = (
        ('superadmin_saas', 'Administrador SaaS Global'),
        ('dueno_taller', 'Dueño / Admin del Taller'),
        ('jefe_taller', 'Jefe de Taller'),
        ('operario', 'Operario'),
        ('montador', 'Montador'),
        ('compras', 'Compras'),
        ('disenador', 'Diseñador'),
        ('vendedor', 'Vendedor'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_empresa = models.ForeignKey(
        Empresa,
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name='usuarios'
    )
    correo_electronico = models.EmailField(max_length=255, unique=True)
    nombre_completo = models.CharField(max_length=255)
    rol = models.CharField(max_length=50, choices=ROLES, default='operario')
    costo_hora = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    activo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo_electronico'
    REQUIRED_FIELDS = ['nombre_completo']

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.nombre_completo} ({self.get_rol_display()})"

    @property
    def iniciales(self):
        """Retorna las iniciales del usuario para avatares (ej: Leonor Silva -> LS)."""
        if not self.nombre_completo:
            return "U"
        partes = self.nombre_completo.strip().split()
        if len(partes) >= 2:
            return f"{partes[0][0]}{partes[-1][0]}".upper()
        elif partes:
            return partes[0][:2].upper()
        return "U"



class AuditoriaLog(models.Model):
    """Tabla de auditoría para trazabilidad de eventos de negocio en base de datos."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_empresa = models.ForeignKey(
        Empresa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs_auditoria'
    )
    id_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acciones_auditadas'
    )
    accion = models.CharField(max_length=100)
    detalles = models.TextField(blank=True, null=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auditoria_logs'
        ordering = ['-fecha_registro']
        verbose_name = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'

    def __str__(self):
        usuario_str = self.id_usuario.nombre_completo if self.id_usuario else 'ANON'
        return f"[{self.fecha_registro.strftime('%Y-%m-%d %H:%M')}] {self.accion} por {usuario_str}"
