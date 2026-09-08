from django.db import transaction
from django.db.models import Max
from .models import Proyecto, ItemProyecto
from apps.cotizador.models import Cotizacion
from apps.core_auth.models import AuditoriaLog


@transaction.atomic
def aprobar_cotizacion_y_generar_ot(cotizacion_id, usuario):
    """
    Servicio de conversión Comercial -> Operativa:
    1. Marca la Cotización como 'aprobada'.
    2. Crea el Proyecto / Orden de Trabajo (OT) con código correlativo único.
    3. Clona todos los ítems comerciales a la lista de producción (BOM de la OT).
    4. Genera log de auditoría.
    """
    cotizacion = Cotizacion.objects.select_for_update().get(id=cotizacion_id, id_empresa=usuario.id_empresa)

    if cotizacion.estado == 'aprobada':
        # Si ya fue aprobada anteriormente, retornar el proyecto existente
        proyecto_existente = Proyecto.objects.filter(id_empresa=usuario.id_empresa, id_cotizacion_origen=cotizacion).first()
        if proyecto_existente:
            return proyecto_existente

    # 1. Marcar cotización como aprobada
    cotizacion.estado = 'aprobada'
    cotizacion.save(update_fields=['estado'])

    # 2. Generar código de OT único derivado del número de la cotización comercial
    if cotizacion.numero_cotizacion.startswith("COT-"):
        codigo_ot = cotizacion.numero_cotizacion.replace("COT-", "OT-", 1)
    else:
        codigo_ot = f"OT-{cotizacion.numero_cotizacion}"

    # 3. Crear Proyecto / OT
    proyecto = Proyecto.objects.create(
        id_empresa=usuario.id_empresa,
        id_cotizacion_origen=cotizacion,
        id_cliente=cotizacion.id_cliente,
        codigo_ot=codigo_ot,
        nombre_proyecto=cotizacion.titulo_propuesta,
        estado='planificado',
        precio_cotizado=cotizacion.precio_venta_neto,
        costo_presupuestado_total=cotizacion.costo_total_estimado,
        margen_objetivo_pct=cotizacion.margen_objetivo_pct
    )

    # 4. Clonar ítems comerciales al BOM de producción
    items_produccion = []
    for item in cotizacion.items.all():
        items_produccion.append(ItemProyecto(
            id_empresa=usuario.id_empresa,
            id_proyecto=proyecto,
            id_material=item.id_material,
            descripcion=item.descripcion,
            tipo_item=item.tipo_item,
            cantidad=item.cantidad,
            costo_unitario=item.costo_unitario,
            subtotal_costo=item.subtotal_costo,
            agregado_rectificacion=False
        ))

    ItemProyecto.objects.bulk_create(items_produccion)

    # 5. Auditoría
    AuditoriaLog.objects.create(
        id_empresa=usuario.id_empresa,
        id_usuario=usuario,
        accion='APROBAR_COTIZACION_GENERAR_OT',
        detalles=f'Cotización {cotizacion.numero_cotizacion} v{cotizacion.version} aprobada. Generada OT {codigo_ot}'
    )

    return proyecto


