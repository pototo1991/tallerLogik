from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import FacturaCompra, GastoProyecto
from apps.core_auth.models import AuditoriaLog


@transaction.atomic
def registrar_factura_y_distribuir_gastos(factura_data, desgloses_list, usuario):
    """
    Servicio de Registro de Facturas con Cuadratura Estricta:
    - Valida que la suma de los montos desglosados a proyectos coincida exactamente
      con el monto_total_neto de la factura de compra.
    - Persiste FacturaCompra y GastoProyecto en base de datos.
    """
    if not desgloses_list:
        raise ValidationError("Debes asignar el monto neto de la compra a al menos un proyecto activo.")

    monto_total_neto = Decimal(str(factura_data['monto_total_neto'])).quantize(Decimal('0.01'))
    suma_desgloses = Decimal('0.00')

    for d in desgloses_list:
        monto_asig = Decimal(str(d['monto_neto_asignado'])).quantize(Decimal('0.01'))
        suma_desgloses += monto_asig

    if suma_desgloses != monto_total_neto:
        diferencia = monto_total_neto - suma_desgloses
        raise ValidationError(
            f"Cuadratura incorrecta: La suma distribuida por proyectos (${suma_desgloses}) "
            f"no coincide con el total neto de la factura (${monto_total_neto}). "
            f"Diferencia: ${diferencia}"
        )

    # 1. Crear Cabecera de Factura
    factura = FacturaCompra.objects.create(
        id_empresa=usuario.id_empresa,
        numero_factura=factura_data['numero_factura'],
        id_proveedor=factura_data.get('id_proveedor'),
        proveedor=factura_data.get('proveedor') or (factura_data['id_proveedor'].razon_social if factura_data.get('id_proveedor') else ''),
        fecha_emision=factura_data.get('fecha_emision') or timezone.now(),
        monto_total_neto=monto_total_neto,
        forma_pago=factura_data.get('forma_pago', 'TRANSFERENCIA'),
        banco_origen=factura_data.get('banco_origen', ''),
        observaciones=factura_data.get('observaciones', ''),
        id_usuario_registro=usuario
    )

    # 2. Crear Desgloses por Proyecto
    from apps.ordenes_trabajo.models import ItemProyecto
    from django.db.models import Sum

    gastos_objs = []
    for d in desgloses_list:
        proyecto = d['proyecto']
        item_id = d.get('item_id')
        monto_asig = Decimal(str(d['monto_neto_asignado'])).quantize(Decimal('0.01'))
        
        item_proyecto_obj = None
        if item_id:
            try:
                item_proyecto_obj = ItemProyecto.objects.get(id=item_id, id_proyecto=proyecto, id_empresa=usuario.id_empresa)
            except (ItemProyecto.DoesNotExist, ValueError):
                pass
                
        if not item_proyecto_obj:
            # Crear un ítem de producción dinámicamente (rectificación) si no existía
            desc_item = d.get('descripcion') or f"Ítem extra - Compra {factura.proveedor}"
            tipo_item_val = d.get('tipo_gasto', 'Material')
            if tipo_item_val not in ['Material', 'Insumo', 'Servicio_Tercero']:
                tipo_item_val = 'Material'
                
            item_proyecto_obj = ItemProyecto.objects.create(
                id_empresa=usuario.id_empresa,
                id_proyecto=proyecto,
                descripcion=desc_item,
                tipo_item=tipo_item_val,
                cantidad=Decimal('1.00'),
                costo_unitario=monto_asig,
                subtotal_costo=monto_asig,
                agregado_rectificacion=True
            )
            
            # Recalcular el costo total de la OT (BOM)
            total_bom = proyecto.items_produccion.aggregate(total=Sum('subtotal_costo'))['total'] or Decimal('0.00')
            proyecto.costo_presupuestado_total = total_bom
            proyecto.save(update_fields=['costo_presupuestado_total'])

        desc_gasto = d.get('descripcion') or item_proyecto_obj.descripcion
        gastos_objs.append(GastoProyecto(
            id_empresa=usuario.id_empresa,
            id_factura_compra=factura,
            id_proyecto=proyecto,
            id_item_proyecto=item_proyecto_obj,
            descripcion=desc_gasto,
            tipo_gasto=d.get('tipo_gasto', 'Material'),
            monto_neto_asignado=monto_asig,
            id_usuario_registro=usuario
        ))

    GastoProyecto.objects.bulk_create(gastos_objs)

    # 3. Registro de Auditoría
    AuditoriaLog.objects.create(
        id_empresa=usuario.id_empresa,
        id_usuario=usuario,
        accion='REGISTRAR_FACTURA_COMPRA',
        detalles=f'Registrada Factura {factura.numero_factura} ({factura.proveedor}) por ${monto_total_neto} distribuida en {len(gastos_objs)} proyectos.'
    )

    return factura
