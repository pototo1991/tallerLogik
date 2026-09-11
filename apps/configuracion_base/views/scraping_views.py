import logging
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from celery.result import AsyncResult

from ..models import Material, MaterialGlobal
from ..services import importar_material_a_taller
from ..tasks import tarea_scraping_manual_async

logger = logging.getLogger('saas_taller')


class MaterialGlobalBuscarView(LoginRequiredMixin, View):
    """Buscador y visor del catálogo global de materiales de Imperial."""
    def get(self, request):
        query = request.GET.get('q', '').strip()
        categoria = request.GET.get('categoria', '').strip()

        materiales = MaterialGlobal.objects.all()

        if query:
            materiales = materiales.filter(nombre__icontains=query) | materiales.filter(sku_proveedor__icontains=query)
        if categoria:
            materiales = materiales.filter(categoria=categoria)

        # Determinar qué materiales ya han sido importados por este taller
        imported_skus = set(
            Material.objects.filter(
                id_empresa=request.tenant,
                sku_proveedor__isnull=False
            ).values_list('sku_proveedor', flat=True)
        )

        for mg in materiales:
            mg.ya_importado = mg.sku_proveedor in imported_skus

        categorias_choices = MaterialGlobal.CATEGORIAS
        total_imperial = MaterialGlobal.objects.filter(proveedor='Imperial').count()

        context = {
            'materiales': materiales,
            'query': query,
            'categoria_filtro': categoria,
            'categorias': categorias_choices,
            'total_imperial': total_imperial,
        }
        return render(request, 'configuracion_base/materiales_global_buscar.html', context)


class MaterialImportarActionView(LoginRequiredMixin, View):
    """Acción que importa un material global al catálogo privado del taller."""
    def post(self, request, global_id):
        if not request.tenant:
            return JsonResponse({'error': 'No hay un taller activo configurado.'}, status=400)

        try:
            importar_material_a_taller(global_id, request.tenant, request.user)
            # Retornar un fragmento HTML para HTMX que reemplace el botón por una insignia de éxito
            return render(request, 'configuracion_base/partials/badge_importado.html')
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception:
            logger.exception("Error al importar material global")
            return JsonResponse({'error': 'Error interno del servidor.'}, status=500)


class EjecutarScrapingManualView(LoginRequiredMixin, View):
    """Acción que inicia el scraping de Imperial en segundo plano."""
    def post(self, request):
        if request.user.rol not in ['superadmin_saas']:
            return JsonResponse({'error': 'No tienes permisos para ejecutar la sincronización.'}, status=403)

        # Disparar tarea en segundo plano
        task = tarea_scraping_manual_async.delay(request.user.id)

        # Retornar el fragmento que inicia el polling de HTMX
        context = {
            'task_id': task.id,
            'message': 'Iniciando conexión con Imperial...'
        }
        return render(request, 'configuracion_base/partials/scraping_progress.html', context)


class ScrapingTaskStatusView(LoginRequiredMixin, View):
    """Consulta el estado actual de la tarea de scraping y retorna fragmentos HTMX."""
    def get(self, request, task_id):
        res = AsyncResult(task_id)

        if res.state == 'PROGRESS':
            info = res.info or {}
            context = {
                'task_id': task_id,
                'current': info.get('current', 10),
                'message': info.get('message', 'Procesando...')
            }
            return render(request, 'configuracion_base/partials/scraping_progress.html', context)

        elif res.state == 'SUCCESS':
            result = res.result or {}
            context = {
                'creados': result.get('creados', 0),
                'actualizados': result.get('actualizados', 0),
                'completado': True
            }
            return render(request, 'configuracion_base/partials/scraping_success.html', context)

        elif res.state == 'FAILURE':
            context = {
                'error': 'La tarea de sincronización falló o fue cancelada.',
                'fallado': True
            }
            return render(request, 'configuracion_base/partials/scraping_error.html', context)

        else:
            # Estado pendiente o desconocido
            context = {
                'task_id': task_id,
                'current': 5,
                'message': 'En cola de espera...'
            }
            return render(request, 'configuracion_base/partials/scraping_error.html', context)
