from decimal import Decimal
from django.db.models import Sum
from apps.ordenes_trabajo.models import Proyecto
from apps.compras_gastos.models import GastoProyecto, RegistroTiempo
from .models import PagoProyecto


def calcular_rentabilidad_proyecto(proyecto):
    """
    Calcula en tiempo real los indicadores de rentabilidad, sobrecostos y cobranzas
    de una Orden de Trabajo individual.
    """
    costo_presupuestado = proyecto.costo_presupuestado_total or Decimal('0.00')

    # Suma de Compras/Facturas asignadas a este proyecto
    gastos_materiales_reales = GastoProyecto.objects.filter(
        id_proyecto=proyecto,
        id_empresa=proyecto.id_empresa
    ).aggregate(total=Sum('monto_neto_asignado'))['total'] or Decimal('0.00')

    # Suma de Mano de Obra Directa (MOD) imputada a este proyecto
    costo_mod_real = RegistroTiempo.objects.filter(
        id_proyecto=proyecto,
        id_empresa=proyecto.id_empresa
    ).aggregate(total=Sum('costo_mano_obra_calculado'))['total'] or Decimal('0.00')

    # Costo Real Total Incurrido
    costo_real_total = gastos_materiales_reales + costo_mod_real

    # Desviación de Costo (Sobrecosto)
    desviacion_costo = costo_real_total - costo_presupuestado
    if costo_presupuestado > Decimal('0.00'):
        desviacion_pct = ((desviacion_costo / costo_presupuestado) * Decimal('100.00')).quantize(Decimal('0.01'))
    else:
        desviacion_pct = Decimal('0.00')

    sobrecosto_detectado = costo_real_total > costo_presupuestado

    # Margen sobre venta Real vs. Objetivo
    precio_cotizado = proyecto.precio_cotizado or Decimal('0.00')
    margen_real_monto = precio_cotizado - costo_real_total

    if precio_cotizado > Decimal('0.00'):
        margen_real_pct = ((margen_real_monto / precio_cotizado) * Decimal('100.00')).quantize(Decimal('0.01'))
    else:
        margen_real_pct = Decimal('0.00')

    # Gestión de Cobranza (Abonos)
    total_pagado_cliente = PagoProyecto.objects.filter(
        id_proyecto=proyecto,
        id_empresa=proyecto.id_empresa
    ).aggregate(total=Sum('monto_pago'))['total'] or Decimal('0.00')

    saldo_pendiente_cobro = precio_cotizado - total_pagado_cliente
    pct_cobrado = ((total_pagado_cliente / precio_cotizado) * Decimal('100.00')).quantize(Decimal('0.01')) if precio_cotizado > Decimal('0.00') else Decimal('0.00')

    return {
        'proyecto': proyecto,
        'precio_cotizado': precio_cotizado,
        'costo_presupuestado': costo_presupuestado,
        'gastos_materiales_reales': gastos_materiales_reales,
        'costo_mod_real': costo_mod_real,
        'costo_real_total': costo_real_total,
        'desviacion_costo': desviacion_costo,
        'desviacion_pct': desviacion_pct,
        'sobrecosto_detectado': sobrecosto_detectado,
        'margen_objetivo_pct': proyecto.margen_objetivo_pct,
        'margen_real_monto': margen_real_monto,
        'margen_real_pct': margen_real_pct,
        'total_pagado_cliente': total_pagado_cliente,
        'saldo_pendiente_cobro': saldo_pendiente_cobro,
        'pct_cobrado': pct_cobrado,
    }


def obtener_metricas_globales_taller(tenant):
    """
    Consolida las métricas financieras globales para el Dashboard del Taller.
    """
    proyectos = Proyecto.objects.filter(id_empresa=tenant)

    total_proyectos = proyectos.count()
    total_facturado_neto = proyectos.aggregate(total=Sum('precio_cotizado'))['total'] or Decimal('0.00')
    costo_presupuestado_global = proyectos.aggregate(total=Sum('costo_presupuestado_total'))['total'] or Decimal('0.00')

    # Gastos reales de materiales + mano de obra
    total_gastos_materiales = GastoProyecto.objects.filter(id_empresa=tenant).aggregate(total=Sum('monto_neto_asignado'))['total'] or Decimal('0.00')
    total_costo_mod = RegistroTiempo.objects.filter(id_empresa=tenant).aggregate(total=Sum('costo_mano_obra_calculado'))['total'] or Decimal('0.00')
    costo_real_global = total_gastos_materiales + total_costo_mod

    # Cobranzas
    total_cobrado = PagoProyecto.objects.filter(id_empresa=tenant).aggregate(total=Sum('monto_pago'))['total'] or Decimal('0.00')
    total_saldo_pendiente = total_facturado_neto - total_cobrado

    # Margen global acumulado
    utilidad_neta_global = total_facturado_neto - costo_real_global
    margen_global_pct = ((utilidad_neta_global / total_facturado_neto) * Decimal('100.00')).quantize(Decimal('0.01')) if total_facturado_neto > Decimal('0.00') else Decimal('0.00')

    # Proyectos con sobrecosto
    proyectos_sobrecosto = 0
    proyectos_metricas = []
    for p in proyectos:
        m = calcular_rentabilidad_proyecto(p)
        proyectos_metricas.append(m)
        if m['sobrecosto_detectado']:
            proyectos_sobrecosto += 1

    return {
        'total_proyectos': total_proyectos,
        'total_facturado_neto': total_facturado_neto,
        'costo_presupuestado_global': costo_presupuestado_global,
        'costo_real_global': costo_real_global,
        'utilidad_neta_global': utilidad_neta_global,
        'margen_global_pct': margen_global_pct,
        'total_cobrado': total_cobrado,
        'total_saldo_pendiente': total_saldo_pendiente,
        'proyectos_sobrecosto': proyectos_sobrecosto,
        'proyectos_metricas': proyectos_metricas,
    }
