import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from .services import ejecutar_scraping_imperial
from apps.core_auth.models import AuditoriaLog

logger = logging.getLogger('saas_taller')
Usuario = get_user_model()


@shared_task
def tarea_scraping_imperial_programada():
    """
    Tarea programada para Celery Beat que se ejecuta domingos y jueves.
    Utiliza el scraping en vivo (con fallback automático).
    """
    logger.info("Iniciando tarea programada automática de scraping...")
    creados, actualizados = ejecutar_scraping_imperial(use_mock=False)
    logger.info(f"Tarea programada automática completada. Creados: {creados}, Actualizados: {actualizados}")
    return {'creados': creados, 'actualizados': actualizados}


@shared_task(bind=True)
def tarea_scraping_manual_async(self, usuario_id):
    """
    Tarea disparada manualmente desde el botón de la UI.
    """
    logger.info(f"Iniciando scraping manual solicitado por el usuario {usuario_id}...")
    
    # Simular avance para feedback en UI (HTMX Polling)
    self.update_state(state='PROGRESS', meta={'current': 10, 'total': 100, 'message': 'Conectando con distribuidor...'})
    
    try:
        user = Usuario.objects.get(id=usuario_id)
        empresa = user.id_empresa
    except Usuario.DoesNotExist:
        user = None
        empresa = None
        
    self.update_state(state='PROGRESS', meta={'current': 50, 'total': 100, 'message': 'Ejecutando scraping de materiales...'})
    
    creados, actualizados = ejecutar_scraping_imperial(use_mock=False)
    
    self.update_state(state='PROGRESS', meta={'current': 90, 'total': 100, 'message': 'Actualizando precios de los talleres...'})

    if empresa:
        AuditoriaLog.objects.create(
            id_empresa=empresa,
            id_usuario=user,
            accion='EJECUTAR_SCRAPING_MANUAL',
            detalles=f"Scraping de Imperial ejecutado manualmente. Creados: {creados}, Actualizados: {actualizados}."
        )

    logger.info(f"Scraping manual completado. Creados: {creados}, Actualizados: {actualizados}")
    return {'creados': creados, 'actualizados': actualizados}
