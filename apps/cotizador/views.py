import json
import logging
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Max
from weasyprint import HTML

from .models import Cotizacion, ItemCotizacion
from .forms import CotizacionForm, ItemCotizacionForm
from .services import recalcular_cotizacion, clonar_version_cotizacion
from apps.core_auth.models import AuditoriaLog, Usuario
from apps.configuracion_base.models import Material

logger = logging.getLogger('saas_taller')


class CotizacionListView(LoginRequiredMixin, View):
    """Lista de cotizaciones comerciales del taller."""
    def get(self, request):
        cotizaciones = Cotizacion.objects.filter(id_empresa=request.tenant).select_related('id_cliente')
        return render(request, 'cotizador/cotizaciones_list.html', {'cotizaciones': cotizaciones})


class CotizacionCreateView(LoginRequiredMixin, View):
    """Crear cabecera de nueva cotización."""
    def get(self, request):
        form = CotizacionForm(empresa=request.tenant)
        return render(request, 'cotizador/cotizacion_form.html', {'form': form, 'titulo': 'Nueva Cotización Comercial'})

    def post(self, request):
        form = CotizacionForm(request.POST, empresa=request.tenant)
        if form.is_valid():
            cotizacion = form.save(commit=False)
            cotizacion.id_empresa = request.tenant

            # Generar correlativo automático COT-2026-001
            ultimo_num = Cotizacion.objects.filter(id_empresa=request.tenant).count() + 1
            cotizacion.numero_cotizacion = f"COT-2026-{ultimo_num:03d}"
            cotizacion.version = 1
            cotizacion.save()

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='CREAR_COTIZACION',
                detalles=f'Cotización {cotizacion.numero_cotizacion} v1 creada para {cotizacion.id_cliente.razon_social}'
            )
            messages.success(request, f"Cotización '{cotizacion.numero_cotizacion}' creada con éxito. Agrega los insumos y mano de obra.")
            return redirect('cotizador:cotizacion_detail', pk=cotizacion.pk)

        return render(request, 'cotizador/cotizacion_form.html', {'form': form, 'titulo': 'Nueva Cotización Comercial'})


class CotizacionDetailView(LoginRequiredMixin, View):
    """Editor interactivo de cotización (Detalle, formulario de ítems y vista HTMX)."""
    def get(self, request, pk):
        cotizacion = get_object_or_404(Cotizacion, pk=pk, id_empresa=request.tenant)
        items = cotizacion.items.all().select_related('id_material')
        item_form = ItemCotizacionForm(empresa=request.tenant)
        header_form = CotizacionForm(instance=cotizacion, empresa=request.tenant)

        materiales = Material.objects.filter(id_empresa=request.tenant)
        materiales_dict = {
            str(m.id): {
                'costo': float(m.costo_unitario),
                'nombre': m.nombre
            }
            for m in materiales
        }

        # Cargar usuarios/operarios de la empresa creados en el aplicativo para la estimación de MOD
        usuarios_empresa = Usuario.objects.filter(id_empresa=request.tenant, activo=True)
        operarios_dict = {
            str(u.id): {
                'nombre': u.nombre_completo,
                'rol': u.get_rol_display(),
                'costo_hora': float(u.costo_hora)
            }
            for u in usuarios_empresa
        }

        context = {
            'cotizacion': cotizacion,
            'items': items,
            'item_form': item_form,
            'header_form': header_form,
            'materiales_json': json.dumps(materiales_dict),
            'operarios_json': json.dumps(operarios_dict),
            'operarios_lista': usuarios_empresa,
        }
        return render(request, 'cotizador/cotizacion_detail.html', context)

    def post(self, request, pk):
        """Actualizar parámetros de la cabecera (Margen %, CIF, Notas)."""
        cotizacion = get_object_or_404(Cotizacion, pk=pk, id_empresa=request.tenant)
        form = CotizacionForm(request.POST, instance=cotizacion, empresa=request.tenant)
        if form.is_valid():
            form.save()
            recalcular_cotizacion(cotizacion)
            messages.success(request, "Valores de la cotización actualizados.")

        return redirect('cotizador:cotizacion_detail', pk=cotizacion.pk)


class ItemCotizacionCreateView(LoginRequiredMixin, View):
    """Agregar un ítem a la cotización vía HTMX (Material, Mano de Obra o Servicio Tercero)."""
    def post(self, request, cotizacion_pk):
        cotizacion = get_object_or_404(Cotizacion, pk=cotizacion_pk, id_empresa=request.tenant)
        form = ItemCotizacionForm(request.POST, empresa=request.tenant)

        if form.is_valid():
            item = form.save(commit=False)
            item.id_empresa = request.tenant
            item.id_cotizacion = cotizacion
            
            tipo_item_post = request.POST.get('tipo_item', 'Material')
            item.tipo_item = tipo_item_post
            item.porcentaje_merma_aplicado = Decimal('0.00')

            if item.tipo_item == 'Material':
                if item.id_material:
                    if not item.descripcion:
                        item.descripcion = item.id_material.nombre
                    if not item.costo_unitario or item.costo_unitario == Decimal('0.00'):
                        item.costo_unitario = item.id_material.costo_unitario
            else:
                # Mano_Obra o Servicio_Tercero
                item.id_material = None

            item.save()
            recalcular_cotizacion(cotizacion)

            if request.headers.get('HX-Request'):
                items = cotizacion.items.all().select_related('id_material')
                context = {'cotizacion': cotizacion, 'items': items, 'item_form': ItemCotizacionForm(empresa=request.tenant)}
                return render(request, 'cotizador/partials/items_table.html', context)

            messages.success(request, f"Ítem '{item.descripcion}' agregado.")
            return redirect('cotizador:cotizacion_detail', pk=cotizacion.pk)

        if request.headers.get('HX-Request'):
            items = cotizacion.items.all()
            return render(request, 'cotizador/partials/items_table.html', {'cotizacion': cotizacion, 'items': items, 'item_form': form})

        return redirect('cotizador:cotizacion_detail', pk=cotizacion.pk)



class ItemCotizacionDeleteView(LoginRequiredMixin, View):
    """Eliminar un ítem de la cotización vía HTMX."""
    def post(self, request, cotizacion_pk, item_pk):
        cotizacion = get_object_or_404(Cotizacion, pk=cotizacion_pk, id_empresa=request.tenant)
        item = get_object_or_404(ItemCotizacion, pk=item_pk, id_cotizacion=cotizacion, id_empresa=request.tenant)
        item.delete()

        recalcular_cotizacion(cotizacion)

        if request.headers.get('HX-Request'):
            items = cotizacion.items.all().select_related('id_material')
            context = {'cotizacion': cotizacion, 'items': items, 'item_form': ItemCotizacionForm(empresa=request.tenant)}
            return render(request, 'cotizador/partials/items_table.html', context)

        messages.success(request, "Ítem eliminado.")
        return redirect('cotizador:cotizacion_detail', pk=cotizacion.pk)


class CotizacionClonarVersionView(LoginRequiredMixin, View):
    """Acción para clonar una versión (v1 -> v2)."""
    def post(self, request, pk):
        cotizacion_nueva = clonar_version_cotizacion(pk, request.user)
        messages.success(request, f"Se ha creado la versión v{cotizacion_nueva.version} de la cotización '{cotizacion_nueva.numero_cotizacion}'.")
        return redirect('cotizador:cotizacion_detail', pk=cotizacion_nueva.pk)


class CotizacionPDFView(LoginRequiredMixin, View):
    """Generación de propuesta comercial en PDF profesional usando WeasyPrint."""
    def get(self, request, pk):
        cotizacion = get_object_or_404(Cotizacion, pk=pk, id_empresa=request.tenant)
        items = cotizacion.items.all().select_related('id_material')

        context = {
            'cotizacion': cotizacion,
            'items': items,
            'empresa': request.tenant,
            'cliente': cotizacion.id_cliente,
        }

        # Renderizar plantilla HTML limpia para WeasyPrint
        html_content = render_to_string('cotizador/cotizacion_pdf.html', context)
        pdf_bytes = HTML(string=html_content, base_url=request.build_absolute_uri('/')).write_pdf()

        filename = f"Cotizacion_{cotizacion.numero_cotizacion}_v{cotizacion.version}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
