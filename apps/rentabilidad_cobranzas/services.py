from decimal import Decimal
from django.db.models import Sum
from apps.ordenes_trabajo.models import Proyecto
from apps.compras_gastos.models import GastoProyecto, RegistroTiempo
from .models import PagoProyecto


def calcular_rentabilidad_proyecto(proyecto):
    """
    Calcula en tiempo real los indicadores de rentabilidad, sobrecostos, cobranzas
    y desgloses por categoría (PC vs Real) para una Orden de Trabajo individual.
    """
    costo_presupuestado = proyecto.costo_presupuestado_total or Decimal('0.00')
    precio_cotizado = proyecto.precio_cotizado or Decimal('0.00')
    cotizacion = getattr(proyecto, 'id_cotizacion_origen', None)

    # 1. Desglose de Gastos Reales por Categoría
    gastos_qs = GastoProyecto.objects.filter(id_proyecto=proyecto, id_empresa=proyecto.id_empresa)
    tiempos_qs = RegistroTiempo.objects.filter(id_proyecto=proyecto, id_empresa=proyecto.id_empresa)

    real_mat = gastos_qs.filter(tipo_gasto__in=['Material', 'Ferreteria_Imprevista']).aggregate(total=Sum('monto_neto_asignado'))['total'] or Decimal('0.00')
    real_mo_externa = gastos_qs.filter(tipo_gasto='Subcontrato').aggregate(total=Sum('monto_neto_asignado'))['total'] or Decimal('0.00')

    real_mo_fab = tiempos_qs.filter(etapa__in=['Corte', 'Armado', 'Laca_Pintura']).aggregate(total=Sum('costo_mano_obra_calculado'))['total'] or Decimal('0.00')
    real_mo_inst = tiempos_qs.filter(etapa='Montaje').aggregate(total=Sum('costo_mano_obra_calculado'))['total'] or Decimal('0.00')

    costos_directos_reales = real_mat + real_mo_externa + real_mo_fab + real_mo_inst
    real_admin = (costos_directos_reales * Decimal('0.10')).quantize(Decimal('0.01'))

    costo_real_total = costos_directos_reales + real_admin

    # 2. Desglose de Presupuesto Comercial (PC) por Categoría
    pc_mat = getattr(cotizacion, 'costo_materiales_estimado', Decimal('0.00')) or Decimal('0.00')
    pc_mo_fab = getattr(cotizacion, 'costo_mano_obra_estimado', Decimal('0.00')) or Decimal('0.00')
    pc_mo_inst = getattr(cotizacion, 'costo_servicios_estimado', Decimal('0.00')) or Decimal('0.00')
    pc_mo_externa = Decimal('0.00')
    pc_admin = getattr(cotizacion, 'costo_indirecto_cif_estimado', Decimal('0.00')) or Decimal('0.00')

    # Si PC no viene desglosado en cotización, calcular estimado proporcional
    if pc_mat == Decimal('0.00') and costo_presupuestado > Decimal('0.00'):
        pc_mat = (costo_presupuestado * Decimal('0.45')).quantize(Decimal('0.01'))
        pc_mo_fab = (costo_presupuestado * Decimal('0.20')).quantize(Decimal('0.01'))
        pc_mo_inst = (costo_presupuestado * Decimal('0.10')).quantize(Decimal('0.01'))
        pc_mo_externa = (costo_presupuestado * Decimal('0.20')).quantize(Decimal('0.01'))
        pc_admin = (costo_presupuestado * Decimal('0.05')).quantize(Decimal('0.01'))

    # 3. Construir Tabla Comparativa por Categoría (PC vs Real vs Variaciones)
    def _armar_cat(nombre, pc, real):
        var_monto = pc - real
        var_pct = ((var_monto / pc) * Decimal('100.00')).quantize(Decimal('0.01')) if pc > Decimal('0.00') else Decimal('0.00')
        estado = "Favorable" if var_monto >= Decimal('0.00') else "Sobrecosto"
        return {
            'categoria': nombre,
            'pc': pc,
            'real': real,
            'variacion_monto': var_monto,
            'variacion_pct': var_pct,
            'estado': estado
        }

    categorias_desempeno = [
        _armar_cat('Materiales e Insumos', pc_mat, real_mat),
        _armar_cat('Mano de Obra Directa (Fab)', pc_mo_fab, real_mo_fab),
        _armar_cat('Gastos Instalación', pc_mo_inst, real_mo_inst),
        _armar_cat('Mano de Obra Externa (Subcontratos)', pc_mo_externa, real_mo_externa),
        _armar_cat('Gastos Administrativos / CIF', pc_admin, real_admin),
    ]

    total_pc_cat = sum(c['pc'] for c in categorias_desempeno)
    total_real_cat = sum(c['real'] for c in categorias_desempeno)
    total_var_monto = total_pc_cat - total_real_cat
    total_var_pct = ((total_var_monto / total_pc_cat) * Decimal('100.00')).quantize(Decimal('0.01')) if total_pc_cat > Decimal('0.00') else Decimal('0.00')

    categoria_total = {
        'categoria': 'TOTAL',
        'pc': total_pc_cat,
        'real': total_real_cat,
        'variacion_monto': total_var_monto,
        'variacion_pct': total_var_pct,
        'estado': "Favorable" if total_var_monto >= Decimal('0.00') else "Sobrecosto"
    }

    # Desviación General & Sobrecosto
    desviacion_costo = costo_real_total - costo_presupuestado
    desviacion_pct = ((desviacion_costo / costo_presupuestado) * Decimal('100.00')).quantize(Decimal('0.01')) if costo_presupuestado > Decimal('0.00') else Decimal('0.00')
    sobrecosto_detectado = costo_real_total > costo_presupuestado

    # Margen sobre venta Real vs. Objetivo
    margen_real_monto = precio_cotizado - costo_real_total
    margen_real_pct = ((margen_real_monto / precio_cotizado) * Decimal('100.00')).quantize(Decimal('0.01')) if precio_cotizado > Decimal('0.00') else Decimal('0.00')

    # Gestión de Cobranza (Abonos)
    total_pagado_cliente = PagoProyecto.objects.filter(
        id_proyecto=proyecto,
        id_empresa=proyecto.id_empresa
    ).aggregate(total=Sum('monto_pago'))['total'] or Decimal('0.00')

    saldo_pendiente_cobro = precio_cotizado - total_pagado_cliente
    pct_cobrado = ((total_pagado_cliente / precio_cotizado) * Decimal('100.00')).quantize(Decimal('0.01')) if precio_cotizado > Decimal('0.00') else Decimal('0.00')

    # Indicadores de Control Documental
    total_movimientos = gastos_qs.count()
    movimientos_con_factura = gastos_qs.exclude(id_factura_compra__numero_factura__in=['S/N', '']).count()
    cobertura_factura_pct = round((movimientos_con_factura / total_movimientos * 100), 1) if total_movimientos > 0 else 100.0

    return {
        'proyecto': proyecto,
        'precio_cotizado': precio_cotizado,
        'costo_presupuestado': costo_presupuestado,
        'gastos_materiales_reales': real_mat,
        'costo_mod_real': real_mo_fab + real_mo_inst,
        'costo_subcontratos_real': real_mo_externa,
        'costo_admin_real': real_admin,
        'costo_real_total': costo_real_total,
        'desviacion_costo': desviacion_costo,
        'desviacion_pct': desviacion_pct,
        'ahorro_vs_pc': total_var_monto if total_var_monto > Decimal('0.00') else Decimal('0.00'),
        'sobrecosto_detectado': sobrecosto_detectado,
        'margen_objetivo_pct': proyecto.margen_objetivo_pct,
        'margen_real_monto': margen_real_monto,
        'margen_real_pct': margen_real_pct,
        'total_pagado_cliente': total_pagado_cliente,
        'saldo_pendiente_cobro': saldo_pendiente_cobro,
        'pct_cobrado': pct_cobrado,
        'categorias_desempeno': categorias_desempeno,
        'categoria_total': categoria_total,
        'total_movimientos': total_movimientos,
        'cobertura_factura_pct': cobertura_factura_pct,
    }


def obtener_metricas_globales_taller(tenant, estado_filtro='todos'):
    """
    Consolida las métricas financieras globales para el Dashboard del Taller,
    filtrando opcionalmente por estado ('en_curso', 'terminado' o 'todos').
    """
    proyectos = Proyecto.objects.filter(id_empresa=tenant)

    if estado_filtro == 'en_curso':
        proyectos = proyectos.exclude(estado='entregado')
    elif estado_filtro == 'terminado':
        proyectos = proyectos.filter(estado='entregado')

    total_proyectos = proyectos.count()
    total_facturado_neto = proyectos.aggregate(total=Sum('precio_cotizado'))['total'] or Decimal('0.00')
    costo_presupuestado_global = proyectos.aggregate(total=Sum('costo_presupuestado_total'))['total'] or Decimal('0.00')

    # Gastos reales de materiales + mano de obra para los proyectos filtrados
    proyectos_ids = proyectos.values_list('id', flat=True)
    total_gastos_materiales = GastoProyecto.objects.filter(
        id_empresa=tenant,
        id_proyecto__in=proyectos_ids
    ).aggregate(total=Sum('monto_neto_asignado'))['total'] or Decimal('0.00')

    total_costo_mod = RegistroTiempo.objects.filter(
        id_empresa=tenant,
        id_proyecto__in=proyectos_ids
    ).aggregate(total=Sum('costo_mano_obra_calculado'))['total'] or Decimal('0.00')

    # Proyectos con sobrecosto, conteo por estado y desglose global por categoría
    proyectos_sobrecosto = 0
    proyectos_metricas = []

    conteo_estados = {
        'planificado': 0,
        'corte': 0,
        'armado': 0,
        'laca_pintura': 0,
        'montaje': 0,
        'entregado': 0,
    }

    desglose_costos_global = {
        'materiales': Decimal('0.00'),
        'mod': Decimal('0.00'),
        'subcontratos': Decimal('0.00'),
        'admin_cif': Decimal('0.00'),
    }

    for p in proyectos:
        m = calcular_rentabilidad_proyecto(p)
        proyectos_metricas.append(m)
        if m['sobrecosto_detectado']:
            proyectos_sobrecosto += 1

        if p.estado in conteo_estados:
            conteo_estados[p.estado] += 1

        desglose_costos_global['materiales'] += m['gastos_materiales_reales']
        desglose_costos_global['mod'] += m['costo_mod_real']
        desglose_costos_global['subcontratos'] += m['costo_subcontratos_real']
        desglose_costos_global['admin_cif'] += m['costo_admin_real']

    costo_real_global = sum((m['costo_real_total'] for m in proyectos_metricas), Decimal('0.00'))

    # Cobranzas
    total_cobrado = PagoProyecto.objects.filter(
        id_empresa=tenant,
        id_proyecto__in=proyectos_ids
    ).aggregate(total=Sum('monto_pago'))['total'] or Decimal('0.00')

    total_saldo_pendiente = total_facturado_neto - total_cobrado

    # Margen global acumulado
    utilidad_neta_global = total_facturado_neto - costo_real_global
    margen_global_pct = ((utilidad_neta_global / total_facturado_neto) * Decimal('100.00')).quantize(Decimal('0.01')) if total_facturado_neto > Decimal('0.00') else Decimal('0.00')

    return {
        'estado_filtro': estado_filtro,
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
        'conteo_estados': conteo_estados,
        'desglose_costos_global': desglose_costos_global,
    }

