from django.apps import AppConfig


class CoreAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core_auth'
    verbose_name = 'Autenticación & Tenants'
