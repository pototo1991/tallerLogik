from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Material, MovimientoInventario


@transaction.atomic
def registrar_movimiento_inventario(material, cantidad, tipo_movimiento, usuario, proyecto=None, observaciones=""):
    """
    Servicio centralizado y atómico para gestionar movimientos de bodega:
    - Actualiza 'stock_actual' del modelo Material.
    - Genera la bitácora inmutable en MovimientoInventario.
    
    :param material: Instancia de Material
    :param cantidad: Decimal (Positivo para entradas/ingresos, Negativo para salidas/descuentos)
    :param tipo_movimiento: String en TIPOS_MOVIMIENTO ('INGRESO_INICIAL', 'COMPRA_BODEGA', 'DESCUENTO_OT', 'AJUSTE_MANUAL', 'DEVOLUCION')
    :param usuario: Usuario que ejecuta el movimiento
    :param proyecto: Proyecto/OT opcional asociado a la salida o devolución
    :param observaciones: String descriptivo de la transacción
    """
    cant_decimal = Decimal(str(cantidad)).quantize(Decimal('0.01'))

    # Bloquear registro para evitar condiciones de carrera (Race Condition)
    material_db = Material.objects.select_for_update().get(id=material.id, id_empresa=usuario.id_empresa)

    nuevo_stock = material_db.stock_actual + cant_decimal
    if nuevo_stock < Decimal('0.00'):
        # Evitar stock negativo si no está permitido
        nuevo_stock = Decimal('0.00')

    material_db.stock_actual = nuevo_stock
    material_db.save(update_fields=['stock_actual'])

    movimiento = MovimientoInventario.objects.create(
        id_empresa=usuario.id_empresa,
        id_material=material_db,
        tipo_movimiento=tipo_movimiento,
        cantidad=cant_decimal,
        stock_resultante=nuevo_stock,
        id_proyecto=proyecto,
        observaciones=observaciones,
        id_usuario=usuario
    )

    return movimiento
