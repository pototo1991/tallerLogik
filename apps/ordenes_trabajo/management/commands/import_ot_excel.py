import os
from django.core.management.base import BaseCommand, CommandError
from apps.core_auth.models import Empresa, Usuario
from apps.ordenes_trabajo.services_excel_ot import procesar_excel_ot, procesar_directorio_nocturno


class Command(BaseCommand):
    help = "Ingesta planillas Excel (.xlsx) de Órdenes de Trabajo individuales o procesa un directorio en modo batch nocturno."

    def add_arguments(self, parser):
        parser.add_argument(
            '--path',
            type=str,
            help="Ruta absoluta o relativa de la planilla Excel (.xlsx) a importar (ej: /path/to/COSTEO.xlsx)."
        )
        parser.add_argument(
            '--batch',
            action='store_true',
            help="Ejecuta la ingesta nocturna desatendida sobre todos los archivos .xlsx de un directorio."
        )
        parser.add_argument(
            '--dir',
            type=str,
            default='/home/whsg27/proyectos/tallerLogik',
            help="Directorio de entrada para el proceso batch nocturno (por defecto: /home/whsg27/proyectos/tallerLogik)."
        )
        parser.add_argument(
            '--empresa_id',
            type=str,
            help="UUID de la Empresa / Tenant a la que pertenecen las OTs."
        )
        parser.add_argument(
            '--estado',
            type=str,
            choices=['planificado', 'corte', 'armado', 'laca_pintura', 'montaje', 'entregado'],
            help="Estado opcional para forzar en la OT (ej: entregado o en_curso)."
        )
        parser.add_argument(
            '--ver_ot',
            type=str,
            help="Código de la OT a consultar (ej: OT-1069) para ver sus KPIs y detalle financiero."
        )

    def handle(self, *args, **options):
        # Resolver Empresa / Tenant
        empresa_id = options.get('empresa_id')
        if empresa_id:
            empresa = Empresa.objects.filter(id=empresa_id).first()
            if not empresa:
                raise CommandError(f"Empresa con UUID {empresa_id} no encontrada.")
        else:
            empresa = Empresa.objects.first()
            if not empresa:
                empresa = Empresa.objects.create(
                    nombre_empresa='Taller Pruebas',
                    rut_o_identificacion='76.543.210-K'
                )

        # Resolver Usuario ejecutor
        usuario = Usuario.objects.filter(id_empresa=empresa).first()
        if not usuario:
            usuario = Usuario.objects.create_user(
                correo_electronico='admin@taller.cl',
                password='Password123!',
                nombre_completo='Admin Sistema',
                id_empresa=empresa
            )

        ver_ot_code = options.get('ver_ot')
        is_batch = options.get('batch')
        file_path = options.get('path')
        dir_path = options.get('dir')
        estado_override = options.get('estado')

        if ver_ot_code:
            from apps.ordenes_trabajo.models import Proyecto
            from apps.rentabilidad_cobranzas.services import calcular_rentabilidad_proyecto

            proyecto = Proyecto.objects.filter(id_empresa=empresa, codigo_ot__icontains=ver_ot_code).first()
            if not proyecto:
                raise CommandError(f"No se encontró la OT con el código '{ver_ot_code}'.")

            m = calcular_rentabilidad_proyecto(proyecto)
            self.stdout.write(self.style.SUCCESS(
                f"\n=== DETALLE Y KPIS FINANCIEROS DE LA OT {proyecto.codigo_ot} ===\n"
                f"  - Proyecto: {proyecto.nombre_proyecto}\n"
                f"  - Cliente: {proyecto.id_cliente.razon_social}\n"
                f"  - Estado: {proyecto.get_estado_display()}\n"
                f"  - Total Cobrado / Precio Cotizado: ${m['precio_cotizado']:,.2f}\n"
                f"  - Costo Presupuestado (PC): ${m['costo_presupuestado']:,.2f}\n"
                f"  - Costo Real Total: ${m['costo_real_total']:,.2f}\n"
                f"      * Materiales & Subcontratos: ${m['gastos_materiales_reales']:,.2f}\n"
                f"      * Mano de Obra Directa (MOD): ${m['costo_mod_real']:,.2f}\n"
                f"  - Desviación de Costo: ${m['desviacion_costo']:,.2f} ({m['desviacion_pct']}%)\n"
                f"  - Sobrecosto Detectado: {'SÍ' if m['sobrecosto_detectado'] else 'NO'}\n"
                f"  - Utilidad Real Obtenida: ${m['margen_real_monto']:,.2f}\n"
                f"  - Margen Real %: {m['margen_real_pct']}%\n"
                f"  - Cobranzas (Abonados): ${m['total_pagado_cliente']:,.2f}\n"
                f"  - Saldo Pendiente de Cobro: ${m['saldo_pendiente_cobro']:,.2f}\n"
            ))
            return

        if is_batch:
            self.stdout.write(self.style.NOTICE(f"Iniciando proceso nocturno batch en directorio: {dir_path}..."))
            resultados = procesar_directorio_nocturno(dir_path, empresa, usuario)
            
            exitos = sum(1 for r in resultados if r['exito'])
            errores = sum(1 for r in resultados if not r['exito'])
            
            for r in resultados:
                if r['exito']:
                    res = r['resumen']
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[OK] Archivo: {r['archivo']} -> OT {res['codigo_ot']} ({res['nombre_proyecto']}) - "
                            f"Gastos: {res['gastos_creados']}, Tiempos: {res['tiempos_creados']}"
                        )
                    )
                else:
                    self.stdout.write(self.style.ERROR(f"[ERROR] Archivo: {r['archivo']} -> {r['error']}"))
                    
            self.stdout.write(
                self.style.SUCCESS(f"Proceso nocturno completado. Procesados con éxito: {exitos}, Errores: {errores}.")
            )

        elif file_path:
            self.stdout.write(self.style.NOTICE(f"Procesando planilla Excel individual: {file_path}..."))
            try:
                res = procesar_excel_ot(file_path, empresa, usuario, estado_override=estado_override)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"¡Ingesta Exitosa!\n"
                        f"  - OT: {res['codigo_ot']}\n"
                        f"  - Proyecto: {res['nombre_proyecto']}\n"
                        f"  - Cliente: {res['cliente']}\n"
                        f"  - Total Cobrado: ${res['total_cobrado']:,.2f}\n"
                        f"  - Total Costo PC: ${res['pc_total']:,.2f}\n"
                        f"  - Nuevos Gastos Registrados: {res['gastos_creados']}\n"
                        f"  - Nuevos Tiempos MOD Registrados: {res['tiempos_creados']}\n"
                        f"  - Estado de OT: {res['estado_ot']}"
                    )
                )
            except Exception as e:
                raise CommandError(f"Error procesando la planilla Excel: {e}")
        else:
            # Si no se especifica --path ni --batch, procesar por defecto el COSTEO.xlsx en la raíz
            default_path = '/home/whsg27/proyectos/tallerLogik/COSTEO.xlsx'
            if os.path.exists(default_path):
                self.stdout.write(self.style.NOTICE(f"Usando ruta por defecto: {default_path}"))
                res = procesar_excel_ot(default_path, empresa, usuario, estado_override=estado_override)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"¡Ingesta Exitosa!\n"
                        f"  - OT: {res['codigo_ot']}\n"
                        f"  - Proyecto: {res['nombre_proyecto']}\n"
                        f"  - Cliente: {res['cliente']}\n"
                        f"  - Total Cobrado: ${res['total_cobrado']:,.2f}\n"
                        f"  - Total Costo PC: ${res['pc_total']:,.2f}\n"
                        f"  - Estado OT: {res['estado_ot']}"
                    )
                )
            else:
                raise CommandError("Debe especificar --path=/ruta/al/archivo.xlsx o --batch --dir=/ruta/directorio.")
