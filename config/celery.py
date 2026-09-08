import os
from celery import Celery

# Establecer el módulo de configuración predeterminado de Django para el programa 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('tallerLogik')

# Usar una cadena aquí significa que el worker no tiene que serializar
# el objeto de configuración a objetos de configuración secundarios.
# - namespace='CELERY' significa que todas las claves de configuración de celery
#   deben tener un prefijo 'CELERY_'.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Cargar módulos de tareas de todas las aplicaciones de Django registradas.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
