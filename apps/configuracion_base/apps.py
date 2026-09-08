from django.apps import AppConfig


class ConfiguracionBaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.configuracion_base'
    verbose_name = 'Configuración Base & Clientes'
