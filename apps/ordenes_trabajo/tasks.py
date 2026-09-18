import logging
from celery import shared_task
from django.conf import settings
from apps.core_auth.models import Empresa, Usuario
from apps.ordenes_trabajo.services_excel_ot import procesar_directorio_nocturno

logger = logging.getLogger(__name__)


@shared_task(name="ordenes_trabajo.tarea_proceso_nocturno_excel")
def tarea_proceso_nocturno_excel(directorio_path=None, empresa_id=None):
    """
    Tarea programada (Celery Beat) para la ingesta nocturna desatendida de planillas Excel de OT.
    Se ejecuta automáticamente cada noche.
    """
    logger.info("Iniciando tarea nocturna Celery: tarea_proceso_nocturno_excel")
    
    dir_ingesta = directorio_path or getattr(settings, 'EXCEL_IMPORT_DIR', '/home/whsg27/proyectos/tallerLogik')
    
    if empresa_id:
        empresa = Empresa.objects.filter(id=empresa_id).first()
    else:
        empresa = Empresa.objects.first()
        
    if not empresa:
        logger.error("No se encontró ninguna empresa en la base de datos para ejecutar la ingesta nocturna.")
        return {'exito': False, 'error': 'Empresa no encontrada'}
        
    usuario = Usuario.objects.filter(id_empresa=empresa).first()
    if not usuario:
        usuario = Usuario.objects.create_user(
            correo_electronico='batch_nocturno@taller.cl',
            password='Password123!',
            nombre_completo='Proceso Nocturno Batch',
            id_empresa=empresa
        )

    try:
        resultados = procesar_directorio_nocturno(dir_ingesta, empresa, usuario)
        logger.info(f"Tarea nocturna completada. Resultados: {resultados}")
        return {'exito': True, 'resultados': resultados}
    except Exception as e:
        logger.error(f"Error fatal en la tarea nocturna de Excel: {e}")
        return {'exito': False, 'error': str(e)}
