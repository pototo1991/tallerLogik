from decimal import Decimal
from django.db.models import Sum, Max
from .models import Cotizacion, ItemCotizacion
from apps.core_auth.models import AuditoriaLog


def recalcular_cotizacion(cotizacion):
    """
    Agrupa y suma los subtotales de los ítems de la cotización por su tipo
    y recalcula los totales y el precio de venta.
    """
    items = cotizacion.items.all()

    costo_mat = items.filter(tipo_item__in=['Material', 'Insumo']).aggregate(total=Sum('subtotal_costo'))['total'] or Decimal('0.00')
    costo_mo = items.filter(tipo_item='Mano_Obra').aggregate(total=Sum('subtotal_costo'))['total'] or Decimal('0.00')
    costo_serv = items.filter(tipo_item='Servicio_Tercero').aggregate(total=Sum('subtotal_costo'))['total'] or Decimal('0.00')

    cotizacion.costo_materiales_estimado = costo_mat
    cotizacion.costo_mano_obra_estimado = costo_mo
    cotizacion.costo_servicios_estimado = costo_serv
    cotizacion.calcular_totales()
    return cotizacion


def clonar_version_cotizacion(cotizacion_id, usuario):
    """
    Clona una cotización existente para crear una nueva versión (v1 -> v2),
    duplicando la cabecera y todos sus ítems en estado borrador.
    """
    cotizacion_original = Cotizacion.objects.get(id=cotizacion_id, id_empresa=usuario.id_empresa)

    # Determinar siguiente versión correlativa
    max_version = Cotizacion.objects.filter(
        id_empresa=usuario.id_empresa,
        numero_cotizacion=cotizacion_original.numero_cotizacion
    ).aggregate(max_v=Max('version'))['max_v'] or 1

    nueva_version_num = max_version + 1

    # Crear nueva versión
    nueva_cotizacion = Cotizacion.objects.create(
        id_empresa=cotizacion_original.id_empresa,
        id_cliente=cotizacion_original.id_cliente,
        numero_cotizacion=cotizacion_original.numero_cotizacion,
        version=nueva_version_num,
        titulo_propuesta=f"{cotizacion_original.titulo_propuesta} (v{nueva_version_num})",
        costo_materiales_estimado=cotizacion_original.costo_materiales_estimado,
        costo_mano_obra_estimado=cotizacion_original.costo_mano_obra_estimado,
        costo_servicios_estimado=cotizacion_original.costo_servicios_estimado,
        costo_indirecto_cif_estimado=cotizacion_original.costo_indirecto_cif_estimado,
        costo_total_estimado=cotizacion_original.costo_total_estimado,
        margen_objetivo_pct=cotizacion_original.margen_objetivo_pct,
        precio_venta_neto=cotizacion_original.precio_venta_neto,
        estado='borrador',
        dias_validez=cotizacion_original.dias_validez,
        fecha_inicio_estimada=cotizacion_original.fecha_inicio_estimada,
        fecha_entrega_manual=cotizacion_original.fecha_entrega_manual,
        notas_condiciones=cotizacion_original.notas_condiciones
    )

    # Duplicar ítems
    items_clonados = []
    for item in cotizacion_original.items.all():
        items_clonados.append(ItemCotizacion(
            id_empresa=cotizacion_original.id_empresa,
            id_cotizacion=nueva_cotizacion,
            id_material=item.id_material,
            descripcion=item.descripcion,
            tipo_item=item.tipo_item,
            cantidad=item.cantidad,
            costo_unitario=item.costo_unitario,
            porcentaje_merma_aplicado=item.porcentaje_merma_aplicado,
            subtotal_costo=item.subtotal_costo
        ))

    ItemCotizacion.objects.bulk_create(items_clonados)

    # Registrar en Auditoría
    AuditoriaLog.objects.create(
        id_empresa=usuario.id_empresa,
        id_usuario=usuario,
        accion='CLONAR_VERSION_COTIZACION',
        detalles=f'Creada versión v{nueva_version_num} para cotización {cotizacion_original.numero_cotizacion}'
    )

    return nueva_cotizacion
