import os
import re
import logging
from decimal import Decimal
from datetime import datetime
import openpyxl
from django.db import transaction
from django.utils import timezone
from apps.core_auth.models import Usuario, Empresa
from apps.configuracion_base.models import Cliente, Proveedor
from apps.cotizador.models import Cotizacion
from apps.ordenes_trabajo.models import Proyecto, ItemProyecto
from apps.compras_gastos.models import FacturaCompra, GastoProyecto, RegistroTiempo

logger = logging.getLogger(__name__)


def _sanitize_path(filepath: str) -> str:
    """Sanitiza y resuelve la ruta del archivo de forma segura."""
    resolved = os.path.realpath(filepath)
    if not os.path.exists(resolved):
        raise FileNotFoundError(f"El archivo especificado no existe: {resolved}")
    if not resolved.endswith('.xlsx'):
        raise ValueError("El archivo debe ser una planilla de Excel válida (.xlsx).")
    return resolved


def _to_decimal(val) -> Decimal:
    """Convierte un valor de celda a Decimal seguro sin None."""
    if val is None:
        return Decimal('0.00')
    try:
        return Decimal(str(val)).quantize(Decimal('0.01'))
    except (ValueError, TypeError, ArithmeticError):
        return Decimal('0.00')


def procesar_excel_ot(filepath: str, empresa: Empresa, usuario: Usuario, estado_override: str = None) -> dict:
    """
    Ingesta una planilla Excel de costeo de una OT individual de forma atómica e idempotente.
    Retorna un diccionario con el resumen de los datos importados/actualizados.
    """
    clean_path = _sanitize_path(filepath)
    
    wb = openpyxl.load_workbook(clean_path, data_only=True)
    if 'Hoja1' not in wb.sheetnames:
        raise ValueError("El archivo Excel no contiene la hoja obligatoria 'Hoja1'.")
    
    sheet = wb['Hoja1']
    
    # 1. Extraer cabecera de la OT
    ot_header = str(sheet.cell(2, 4).value or '').strip()
    if not ot_header:
        # Fallback a nombre de archivo si la celda C4 está vacía
        ot_header = os.path.splitext(os.path.basename(clean_path))[0]
        
    ot_match = re.search(r'OT\s*(\d+)', ot_header, re.IGNORECASE)
    codigo_ot = f"OT-{ot_match.group(1)}" if ot_match else "OT-1000"
    
    match_header = re.match(r'OT\s*\d+\s+(.*?)\s*-\s*(.*)', ot_header, re.IGNORECASE)
    if match_header:
        cliente_str = match_header.group(1).strip()
        nombre_proyecto = match_header.group(2).strip()
    else:
        cliente_str = "CLIENTE EXCEL"
        nombre_proyecto = ot_header

    # 2. Extraer Totales Financieros de Control
    total_cobrado = Decimal('0.00')
    for r in range(75, min(90, sheet.max_row + 1)):
        c2 = str(sheet.cell(r, 2).value or '')
        c3 = sheet.cell(r, 3).value
        if 'TOTAL COBRADO' in c2.upper() and c3 is not None:
            total_cobrado = _to_decimal(c3)
            break
            
    # Extraer Presupuesto Comercial (PC)
    pc_materiales = Decimal('0.00')
    pc_mo = Decimal('0.00')
    pc_instalacion = Decimal('0.00')
    pc_mo_externa = Decimal('0.00')
    pc_gastos_admin = Decimal('0.00')
    
    for r in range(84, min(95, sheet.max_row + 1)):
        c2 = str(sheet.cell(r, 2).value or '').upper()
        c3 = sheet.cell(r, 3).value
        if 'COSTO MAT.PC' in c2:
            pc_materiales = _to_decimal(c3)
        elif 'MANO DE OBRA PC' in c2 and 'EXTERNA' not in c2:
            pc_mo = _to_decimal(c3)
        elif 'GASTOS INSTALACION' in c2:
            pc_instalacion = _to_decimal(c3)
        elif 'MANO DE OBRA EXTERNA' in c2:
            pc_mo_externa = _to_decimal(c3)
        elif 'GASTOS ADMINISTRATIVOS' in c2:
            pc_gastos_admin = _to_decimal(c3)

    pc_total = pc_materiales + pc_mo + pc_instalacion + pc_mo_externa + pc_gastos_admin

    # 3. Iniciar Transacción Atómica en Base de Datos
    with transaction.atomic():
        # Get or Create Cliente (Tenant Scoped)
        cliente_obj, _ = Cliente.objects.get_or_create(
            id_empresa=empresa,
            razon_social=cliente_str,
            defaults={
                'rut_o_identificacion': '11.111.111-1',
                'nombre_contacto': cliente_str,
                'correo_general': 'contacto@cliente.cl'
            }
        )
        
        # Get or Create Cotizacion origen
        cotizacion_obj, _ = Cotizacion.objects.get_or_create(
            id_empresa=empresa,
            numero_cotizacion=f"COT-{codigo_ot.replace('OT-', '')}",
            version=1,
            defaults={
                'id_cliente': cliente_obj,
                'titulo_propuesta': nombre_proyecto,
                'costo_total_estimado': pc_total,
                'precio_venta_neto': total_cobrado if total_cobrado > 0 else pc_total,
                'estado': 'aprobada'
            }
        )
        
        # Determinar estado de la OT
        estado_ot = estado_override or ('entregado' if total_cobrado > 0 else 'armado')
        
        # Get or Create Proyecto (OT)
        proyecto_obj, creado_proyecto = Proyecto.objects.get_or_create(
            id_empresa=empresa,
            codigo_ot=codigo_ot,
            defaults={
                'id_cotizacion_origen': cotizacion_obj,
                'id_cliente': cliente_obj,
                'nombre_proyecto': nombre_proyecto,
                'estado': estado_ot,
                'precio_cotizado': total_cobrado if total_cobrado > 0 else pc_total,
                'costo_presupuestado_total': pc_total,
                'margen_objetivo_pct': Decimal('35.00')
            }
        )
        
        if not creado_proyecto:
            # Regla Estricta: Si la OT ya existe en BD y está TERMINADA ('entregado'),
            # NUNCA se permite actualizar ni modificar sus datos históricos.
            if proyecto_obj.estado == 'entregado':
                summary = {
                    'codigo_ot': codigo_ot,
                    'nombre_proyecto': proyecto_obj.nombre_proyecto,
                    'cliente': cliente_str,
                    'creado_nuevo': False,
                    'ya_terminado': True,
                    'total_cobrado': float(proyecto_obj.precio_cotizado),
                    'pc_total': float(proyecto_obj.costo_presupuestado_total),
                    'gastos_creados': 0,
                    'tiempos_creados': 0,
                    'estado_ot': 'entregado',
                    'mensaje': f"La OT {codigo_ot} ya se encuentra TERMINADA (Entregado Conforme) en el sistema. No se realizaron modificaciones a sus datos históricos."
                }
                logger.info(f"Ingesta omitida para OT terminada {codigo_ot}: {summary}")
                return summary

            # Si la OT está EN CURSO: Actualizar montos e incorporar compras / MOD
            proyecto_obj.nombre_proyecto = nombre_proyecto
            if total_cobrado > 0:
                proyecto_obj.precio_cotizado = total_cobrado
            if pc_total > 0:
                proyecto_obj.costo_presupuestado_total = pc_total
            if estado_override:
                proyecto_obj.estado = estado_override
            proyecto_obj.save()

        # 4. Ingerir Movimientos de Compras y Subcontratos
        gastos_creados = 0
        current_cat = 'Material'
        
        for r in range(5, min(75, sheet.max_row + 1)):
            c2 = sheet.cell(r, 2).value
            c3 = sheet.cell(r, 3).value
            c4 = sheet.cell(r, 4).value
            c5 = sheet.cell(r, 5).value
            c6 = sheet.cell(r, 6).value
            c9 = sheet.cell(r, 9).value
            
            c2_str = str(c2 or '').strip()
            if c2 and not isinstance(c3, (int, str)) and c6 is not None:
                if any(kw in c2_str for kw in ['Material', 'Pintura', 'Planchas', 'Fierro', 'Taller', 'Mano de obra externa', 'Iluminación', 'Colaciones']):
                    current_cat = c2_str

            if (c3 is not None or c4 is not None) and c6 is not None:
                try:
                    monto_neto = Decimal(str(c6)).quantize(Decimal('0.01'))
                    if monto_neto > Decimal('0.00'):
                        n_factura = str(c3).strip() if c3 else 'S/N'
                        prov_nombre = str(c4).strip() if c4 else 'PROVEEDOR VARIOS'
                        detalle = str(c5).strip() if c5 else current_cat
                        status_str = str(c9).strip() if c9 else ''
                        
                        # Parse fecha
                        fecha_emision = timezone.now().date()
                        if isinstance(c2, datetime):
                            fecha_emision = c2.date()
                        elif isinstance(c2, str) and len(c2) >= 10:
                            try:
                                fecha_emision = datetime.strptime(c2[:10], '%Y-%m-%d').date()
                            except ValueError:
                                pass

                        # Get or Create Proveedor
                        prov_obj, _ = Proveedor.objects.get_or_create(
                            id_empresa=empresa,
                            razon_social=prov_nombre,
                            defaults={'rut_o_identificacion': '77.777.777-7'}
                        )

                        # Get or Create FacturaCompra
                        factura_obj, _ = FacturaCompra.objects.get_or_create(
                            id_empresa=empresa,
                            numero_factura=n_factura,
                            proveedor=prov_nombre,
                            defaults={
                                'id_proveedor': prov_obj,
                                'fecha_emision': fecha_emision,
                                'monto_total_neto': monto_neto,
                                'id_usuario_registro': usuario,
                                'observaciones': f"Estado Excel: {status_str}" if status_str else None
                            }
                        )

                        # Determine tipo_gasto
                        tipo_gasto = 'Subcontrato' if 'Mano de obra externa' in current_cat else 'Material'

                        # Deduplicar GastoProyecto
                        gasto_obj, creado_gasto = GastoProyecto.objects.get_or_create(
                            id_empresa=empresa,
                            id_factura_compra=factura_obj,
                            id_proyecto=proyecto_obj,
                            monto_neto_asignado=monto_neto,
                            descripcion=detalle[:255],
                            defaults={
                                'tipo_gasto': tipo_gasto,
                                'id_usuario_registro': usuario
                            }
                        )
                        if creado_gasto:
                            gastos_creados += 1
                except (ValueError, TypeError, ArithmeticError):
                    continue

        # 5. Ingerir Tiempos MOD (Mano de Obra Directa)
        tiempos_creados = 0
        
        # Mapeo de operarios en Excel a Usuarios del sistema (o usuario por defecto)
        def _get_usuario_operario(nombre_operario: str) -> Usuario:
            first_name = nombre_operario.split()[0].title()
            u = Usuario.objects.filter(id_empresa=empresa, nombre_completo__icontains=first_name).first()
            if not u:
                # Usar el usuario actual que está realizando la importación
                u = usuario
            return u

        # Parse Fabricación (R95-R108) e Instalación (R112-R125)
        secciones_mo = [
            (95, 108, 'Armado'),
            (112, 125, 'Montaje')
        ]
        
        for start_r, end_r, etapa_str in secciones_mo:
            for r in range(start_r, min(end_r + 1, sheet.max_row + 1)):
                c2_op = sheet.cell(r, 2).value
                c3_monto = sheet.cell(r, 3).value
                c4_detalle = sheet.cell(r, 4).value
                
                if c2_op and c3_monto is not None:
                    try:
                        monto_mo = Decimal(str(c3_monto)).quantize(Decimal('0.01'))
                        if monto_mo > Decimal('0.00'):
                            op_nombre = str(c2_op).strip()
                            u_op = _get_usuario_operario(op_nombre)
                            
                            # Estimar horas basándose en costo por hora del usuario o 8 hrs por día
                            costo_hr = getattr(u_op, 'costo_hora', Decimal('5000.00')) or Decimal('5000.00')
                            hrs_estimadas = (monto_mo / costo_hr).quantize(Decimal('0.01'))
                            
                            reg_tiempo, creado_tiempo = RegistroTiempo.objects.get_or_create(
                                id_empresa=empresa,
                                id_proyecto=proyecto_obj,
                                id_usuario=u_op,
                                etapa=etapa_str,
                                horas_trabajadas=hrs_estimadas,
                                defaults={
                                    'costo_mano_obra_calculado': monto_mo,
                                    'registrado_por': usuario
                                }
                            )
                            if creado_tiempo:
                                tiempos_creados += 1
                    except (ValueError, TypeError, ArithmeticError):
                        continue

    summary = {
        'codigo_ot': codigo_ot,
        'nombre_proyecto': nombre_proyecto,
        'cliente': cliente_str,
        'creado_nuevo': creado_proyecto,
        'total_cobrado': float(total_cobrado),
        'pc_total': float(pc_total),
        'gastos_creados': gastos_creados,
        'tiempos_creados': tiempos_creados,
        'estado_ot': proyecto_obj.estado
    }
    
    logger.info(f"Ingesta finalizada para OT {codigo_ot}: {summary}")
    return summary


def procesar_directorio_nocturno(directorio_path: str, empresa: Empresa, usuario: Usuario) -> list:
    """
    Escanea la carpeta de OTs e ingesta incrementalmente todas las planillas Excel (.xlsx).
    """
    real_dir = os.path.realpath(directorio_path)
    if not os.path.exists(real_dir) or not os.path.isdir(real_dir):
        raise FileNotFoundError(f"Directorio de ingesta nocturna no existe: {real_dir}")
        
    resultados = []
    for filename in os.listdir(real_dir):
        if filename.endswith('.xlsx') and not filename.startswith('~$'):
            filepath = os.path.join(real_dir, filename)
            try:
                res = procesar_excel_ot(filepath, empresa, usuario)
                resultados.append({'archivo': filename, 'exito': True, 'resumen': res})
            except Exception as e:
                logger.error(f"Error procesando {filename} en proceso nocturno: {e}")
                resultados.append({'archivo': filename, 'exito': False, 'error': str(e)})
                
    return resultados
