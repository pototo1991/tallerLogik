from django.db import models
from django.contrib.auth.models import BaseUserManager


class SoftDeleteManager(models.Manager):
    """Manager que excluye automáticamente los registros marcados como eliminados."""
    def get_queryset(self):
        return super().get_queryset().filter(eliminado_en__isnull=True)


class TenantManager(SoftDeleteManager):
    """
    Manager Multi-Tenant que aplica filtrado por tenant e inscribe aislamiento.
    """
    def for_tenant(self, empresa):
        """Filtra explícitamente por el objeto Empresa o UUID entregado."""
        if empresa is None:
            return self.get_queryset()
        return self.get_queryset().filter(id_empresa=empresa)


class UsuarioManager(BaseUserManager):
    """Manager para la creación de usuarios estándar y superadministradores SaaS."""
    def create_user(self, correo_electronico, password=None, **extra_fields):
        if not correo_electronico:
            raise ValueError('El correo electrónico es obligatorio')
        correo = self.normalize_email(correo_electronico)
        user = self.model(correo_electronico=correo, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo_electronico, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', 'superadmin_saas')
        return self.create_user(correo_electronico, password, **extra_fields)
