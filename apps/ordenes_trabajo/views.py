import json
import logging
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Sum

from .models import Proyecto, ItemProyecto
from .forms import ProyectoForm, ItemProyectoRectificacionForm, AsignarMaterialBodegaForm
from .services import aprobar_cotizacion_y_generar_ot
from apps.core_auth.models import AuditoriaLog
from apps.configuracion_base.models import Material
from apps.configuracion_base.services_inventario import registrar_movimiento_inventario

logger = logging.getLogger('saas_taller')


class AsignarBodegaItemProyectoView(LoginRequiredMixin, View):
    """Permite seleccionar un material específico de bodega y descontar el stock para un ítem de la OT."""
    def get(self, request, item_pk):
        item = get_object_or_404(ItemProyecto, pk=item_pk, id_empresa=request.tenant)
        initial_data = {'cantidad': item.cantidad}
        if item.id_material:
            initial_data['id_material'] = item.id_material.pk

        form = AsignarMaterialBodegaForm(empresa=request.tenant, initial=initial_data)
        context = {
            'item': item,
            'proyecto': item.id_proyecto,
            'form': form
        }
        return render(request, 'ordenes_trabajo/partials/modal_asignar_stock_item.html', context)

    def post(self, request, item_pk):
        item = get_object_or_404(ItemProyecto, pk=item_pk, id_empresa=request.tenant)
        form = AsignarMaterialBodegaForm(request.POST, empresa=request.tenant)

        if form.is_valid():
            mat = form.cleaned_data['id_material']
            cant = form.cleaned_data['cantidad']

            # Verificar disponibilidad
            if mat.stock_actual < cant:
                messages.error(
                    request,
                    f"No hay suficiente stock en bodega para '{mat.nombre}'. Stock disponible: {mat.stock_actual} {mat.unidad_medida}."
                )
                return redirect('ordenes_trabajo:proyecto_detail', pk=item.id_proyecto.pk)

            # Ejecutar descuento en bodega
            mov = registrar_movimiento_inventario(
                material=mat,
                cantidad=-cant,
                tipo_movimiento='DESCUENTO_OT',
                usuario=request.user,
                proyecto=item.id_proyecto,
                observaciones=f"Asignación de insumo a OT {item.id_proyecto.codigo_ot}: {item.descripcion}"
            )

            # Actualizar el ítem de la OT
            item.id_material = mat
            item.cantidad_descontada_stock += cant
            item.stock_descontado = True
            item.save()

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='ASIGNAR_MATERIAL_BODEGA_OT',
                detalles=f"Descontadas {cant} {mat.unidad_medida} de '{mat.nombre}' para la OT {item.id_proyecto.codigo_ot}."
            )

            messages.success(request, f"¡Exitoso! Se asignaron y descontaron {cant} {mat.unidad_medida} de '{mat.nombre}' de la bodega.")
            return redirect('ordenes_trabajo:proyecto_detail', pk=item.id_proyecto.pk)

        context = {
            'item': item,
            'proyecto': item.id_proyecto,
            'form': form
        }
        return render(request, 'ordenes_trabajo/partials/modal_asignar_stock_item.html', context)



class AprobarCotizacionView(LoginRequiredMixin, View):
    """Vista de acción para convertir una cotización comercial aprobada en Orden de Trabajo."""
    def post(self, request, cotizacion_pk):
        proyecto = aprobar_cotizacion_y_generar_ot(cotizacion_pk, request.user)
        messages.success(request, f"¡Cotización aprobada! Se ha generado exitosamente la Orden de Trabajo '{proyecto.codigo_ot}'.")
        return redirect('ordenes_trabajo:proyecto_detail', pk=proyecto.pk)


class ProyectoListView(LoginRequiredMixin, View):
    """Lista y Tablero Kanban de Órdenes de Trabajo en taller."""
    def get(self, request):
        proyectos = Proyecto.objects.filter(id_empresa=request.tenant).select_related('id_cliente', 'id_cotizacion_origen')

        # Agrupar proyectos por estado para vista Kanban
        kanban = {
            'planificado': proyectos.filter(estado='planificado'),
            'corte': proyectos.filter(estado='corte'),
            'armado': proyectos.filter(estado='armado'),
            'laca_pintura': proyectos.filter(estado='laca_pintura'),
            'montaje': proyectos.filter(estado='montaje'),
            'entregado': proyectos.filter(estado='entregado'),
        }

        context = {
            'proyectos': proyectos,
            'kanban': kanban,
        }
        return render(request, 'ordenes_trabajo/proyectos_list.html', context)


class ProyectoDetailView(LoginRequiredMixin, View):
    """Vista detallada de la Orden de Trabajo y su BOM de producción."""
    def get(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk, id_empresa=request.tenant)
        items_bom = proyecto.items_produccion.all().select_related('id_material')
        rectificacion_form = ItemProyectoRectificacionForm(empresa=request.tenant)
        proyecto_form = ProyectoForm(instance=proyecto)

        materiales = Material.objects.filter(id_empresa=request.tenant)
        materiales_dict = {
            str(m.id): {
                'id': str(m.id),
                'costo': float(m.costo_unitario),
                'nombre': m.nombre
            } for m in materiales
        }

        context = {
            'proyecto': proyecto,
            'items_bom': items_bom,
            'rectificacion_form': rectificacion_form,
            'proyecto_form': proyecto_form,
            'materiales_json': json.dumps(materiales_dict),
        }
        return render(request, 'ordenes_trabajo/proyecto_detail.html', context)

    def post(self, request, pk):
        """Actualizar estado o fechas de la OT."""
        proyecto = get_object_or_404(Proyecto, pk=pk, id_empresa=request.tenant)
        form = ProyectoForm(request.POST, instance=proyecto)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos de la Orden de Trabajo actualizados.")
        return redirect('ordenes_trabajo:proyecto_detail', pk=proyecto.pk)


class ItemProyectoRectificacionCreateView(LoginRequiredMixin, View):
    """Agregar un ítem de rectificación en terreno (agregado_rectificacion = True)."""
    def post(self, request, proyecto_pk):
        proyecto = get_object_or_404(Proyecto, pk=proyecto_pk, id_empresa=request.tenant)
        form = ItemProyectoRectificacionForm(request.POST, empresa=request.tenant)

        if form.is_valid():
            item = form.save(commit=False)
            item.id_empresa = request.tenant
            item.id_proyecto = proyecto
            item.agregado_rectificacion = True

            if item.id_material and not item.descripcion:
                item.descripcion = f"[Rectificación] {item.id_material.nombre}"

            item.save()

            # Recalcular costo presupuestado total del proyecto
            total_bom = proyecto.items_produccion.aggregate(total=Sum('subtotal_costo'))['total'] or Decimal('0.00')
            proyecto.costo_presupuestado_total = total_bom
            proyecto.save(update_fields=['costo_presupuestado_total'])

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='AGREGAR_RECTIFICACION_OBRA',
                detalles=f'Insumo de rectificación "{item.descripcion}" añadido a la OT {proyecto.codigo_ot}'
            )

            messages.success(request, f"Ítem de rectificación '{item.descripcion}' registrado en el BOM.")
            return redirect('ordenes_trabajo:proyecto_detail', pk=proyecto.pk)

        messages.error(request, "Error al registrar el ítem por rectificación. Revisa los campos.")
        return redirect('ordenes_trabajo:proyecto_detail', pk=proyecto.pk)


class ProyectoCambiarEstadoView(LoginRequiredMixin, View):
    """Cambiar la etapa productiva de la OT vía HTMX o POST."""
    def post(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk, id_empresa=request.tenant)
        nuevo_estado = request.POST.get('nuevo_estado')

        if nuevo_estado in dict(Proyecto.ESTADOS).keys():
            proyecto.estado = nuevo_estado
            proyecto.save(update_fields=['estado'])

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='CAMBIAR_ETAPA_OT',
                detalles=f'OT {proyecto.codigo_ot} movida a etapa "{proyecto.get_estado_display()}"'
            )
            messages.success(request, f"Etapa de la OT {proyecto.codigo_ot} actualizada a '{proyecto.get_estado_display()}'.")

        return redirect('ordenes_trabajo:proyectos_list')


class ProyectoItemsAPIView(LoginRequiredMixin, View):
    """API interna para retornar los ítems del BOM de un proyecto (excluyendo mano de obra) en formato JSON."""
    def get(self, request, proyecto_id):
        from django.http import JsonResponse
        proyecto = get_object_or_404(Proyecto, id=proyecto_id, id_empresa=request.tenant)
        items_qs = proyecto.items_produccion.exclude(tipo_item='Mano_Obra').select_related('id_material')
        
        items_list = list(items_qs)
        if not items_list and proyecto.id_cotizacion_origen:
            items_list = list(proyecto.id_cotizacion_origen.items.exclude(tipo_item='Mano_Obra').select_related('id_material'))
        
        data = {
            'items': [
                {
                    'id': str(item.id),
                    'descripcion': item.descripcion,
                    'tipo_item': getattr(item, 'tipo_item', 'Material'),
                    'costo_unitario': float(item.costo_unitario),
                    'cantidad': float(item.cantidad),
                    'subtotal_costo': float(item.subtotal_costo),
                }
                for item in items_list
            ]
        }
        return JsonResponse(data)
