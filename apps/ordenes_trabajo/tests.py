from decimal import Decimal
from django.test import TestCase
from apps.core_auth.models import Empresa, Usuario
from apps.configuracion_base.models import Cliente
from apps.cotizador.models import Cotizacion, ItemCotizacion
from apps.cotizador.services import recalcular_cotizacion
from apps.ordenes_trabajo.models import Proyecto, ItemProyecto
from apps.ordenes_trabajo.services import aprobar_cotizacion_y_generar_ot


class OrdenesTrabajoTestCase(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre_empresa="Taller Muebles", rut_o_identificacion="77.777.777-7")
        self.jefe_taller = Usuario.objects.create_user(
            correo_electronico="jefe@taller.cl",
            password="Password123!",
            nombre_completo="Jefe Taller",
            rol="jefe_taller",
            id_empresa=self.empresa
        )
        self.cliente = Cliente.objects.create(
            id_empresa=self.empresa,
            razon_social="Cliente OT",
            nombre_contacto="Carlos Soto"
        )
        self.cotizacion = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-010",
            version=1,
            titulo_propuesta="Rack de TV Flotante",
            margen_objetivo_pct=Decimal("40.00")
        )
        ItemCotizacion.objects.create(
            id_empresa=self.empresa,
            id_cotizacion=self.cotizacion,
            descripcion="Plancha MDF Enchapada Encinado",
            tipo_item="Material",
            cantidad=Decimal("3.00"),
            costo_unitario=Decimal("45000.00")
        )
        recalcular_cotizacion(self.cotizacion)

    def test_aprobar_cotizacion_y_generar_ot(self):
        """Verifica que aprobar la cotización cree la OT con código correlativo y clone el BOM."""
        proyecto = aprobar_cotizacion_y_generar_ot(self.cotizacion.id, self.jefe_taller)

        self.cotizacion.refresh_from_db()
        self.assertEqual(self.cotizacion.estado, 'aprobada')
        self.assertEqual(proyecto.codigo_ot, "OT-2026-010")
        self.assertEqual(proyecto.estado, 'planificado')
        self.assertEqual(proyecto.items_produccion.count(), 1)

        item_bom = proyecto.items_produccion.first()
        self.assertEqual(item_bom.descripcion, "Plancha MDF Enchapada Encinado")
        self.assertFalse(item_bom.agregado_rectificacion)

    def test_rectificacion_en_obra(self):
        """Verifica el marcado de ítems agregados tras medir en terreno."""
        proyecto = aprobar_cotizacion_y_generar_ot(self.cotizacion.id, self.jefe_taller)

        item_rectificacion = ItemProyecto.objects.create(
            id_empresa=self.empresa,
            id_proyecto=proyecto,
            descripcion="Tapacantos PVC Extra por desnivel muro",
            tipo_item="Insumo",
            cantidad=Decimal("5.00"),
            costo_unitario=Decimal("2000.00"),
            subtotal_costo=Decimal("10000.00"),
            agregado_rectificacion=True
        )

        self.assertTrue(item_rectificacion.agregado_rectificacion)
        self.assertEqual(proyecto.items_produccion.count(), 2)

    def test_proyectos_views_formato_moneda(self):
        """Verifica que en las vistas de OTs /proyectos/ los valores se muestren como $xxx.xxx sin decimales."""
        from django.urls import reverse

        proyecto = aprobar_cotizacion_y_generar_ot(self.cotizacion.id, self.jefe_taller)
        self.client.login(correo_electronico="jefe@taller.cl", password="Password123!")

        # 1. Test Lista / Kanban /proyectos/
        res_list = self.client.get(reverse('ordenes_trabajo:proyectos_list'))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, "$225.000")
        self.assertNotContains(res_list, "$225000.00")

        # 2. Test Detalle OT /proyectos/<pk>/
        res_detail = self.client.get(reverse('ordenes_trabajo:proyecto_detail', args=[proyecto.pk]))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "$225.000")
        self.assertNotContains(res_detail, "$225000.00")

    def test_asignacion_manual_stock_item_ot(self):
        """Verifica que al aprobar una cotización NO se descuente stock automáticamente, sino mediante la asignación manual por ítem."""
        from django.urls import reverse
        from apps.configuracion_base.models import Material

        mat = Material.objects.create(
            id_empresa=self.empresa,
            nombre="Plancha MDF Enchapada Encinado Blanco",
            categoria="Tableros",
            unidad_medida="Plancha",
            costo_unitario=Decimal("45000.00"),
            stock_actual=Decimal("5.00")
        )

        cot = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-099",
            version=1,
            titulo_propuesta="Mueble de Cocina",
            margen_objetivo_pct=Decimal("35.00")
        )
        ItemCotizacion.objects.create(
            id_empresa=self.empresa,
            id_cotizacion=cot,
            descripcion="Plancha MDF 18mm",
            tipo_item="Material",
            cantidad=Decimal("3.00"),
            costo_unitario=Decimal("45000.00")
        )

        # 1. Aprobar cotización: NO debe descontar stock automáticamente
        proyecto = aprobar_cotizacion_y_generar_ot(cot.id, self.jefe_taller)
        mat.refresh_from_db()
        self.assertEqual(mat.stock_actual, Decimal("5.00")) # Stock intacto

        item_bom = proyecto.items_produccion.first()
        self.assertFalse(item_bom.stock_descontado)

        # 2. Asignación manual de material de bodega al ítem de la OT
        self.client.login(correo_electronico="jefe@taller.cl", password="Password123!")
        url_asignar = reverse('ordenes_trabajo:item_asignar_bodega', args=[item_bom.id])

        response = self.client.post(url_asignar, {
            'id_material': mat.id,
            'cantidad': '3.00'
        })
        self.assertEqual(response.status_code, 302)

        # 3. Verificar que el stock de bodega se haya descontado correctamente (5 - 3 = 2)
        mat.refresh_from_db()
        item_bom.refresh_from_db()
        self.assertEqual(mat.stock_actual, Decimal("2.00"))
        self.assertTrue(item_bom.stock_descontado)
        self.assertEqual(item_bom.cantidad_descontada_stock, Decimal("3.00"))
        self.assertEqual(item_bom.id_material, mat)


class ImportarExcelOTTestCase(TestCase):
    def setUp(self):
        import os
        self.empresa = Empresa.objects.create(
            nombre_empresa="Mueblería Test",
            rut_o_identificacion="76.111.222-3"
        )
        self.usuario = Usuario.objects.create_user(
            correo_electronico="test@taller.cl",
            password="Password123!",
            nombre_completo="Juan Perez",
            id_empresa=self.empresa
        )
        self.excel_path = "/home/whsg27/proyectos/tallerLogik/COSTEO.xlsx"

    def test_ingesta_limpia_costeo_excel(self):
        """Verifica la primera ingesta atómica de COSTEO.xlsx."""
        import os
        from apps.ordenes_trabajo.services_excel_ot import procesar_excel_ot
        from apps.compras_gastos.models import GastoProyecto, RegistroTiempo
        from apps.rentabilidad_cobranzas.services import calcular_rentabilidad_proyecto

        self.assertTrue(os.path.exists(self.excel_path))
        
        res = procesar_excel_ot(self.excel_path, self.empresa, self.usuario)
        
        self.assertEqual(res['codigo_ot'], 'OT-1069')
        self.assertEqual(res['cliente'], 'FERNANDA KRAUSS')
        self.assertEqual(res['total_cobrado'], 29869454.0)
        self.assertEqual(res['pc_total'], 20521040.0)
        
        # Verificar permanencia en base de datos
        proyecto = Proyecto.objects.get(id_empresa=self.empresa, codigo_ot='OT-1069')
        self.assertEqual(proyecto.precio_cotizado, Decimal('29869454.00'))
        self.assertEqual(proyecto.costo_presupuestado_total, Decimal('20521040.00'))
        
        # Verificar total de gastos y registros MOD
        gastos_count = GastoProyecto.objects.filter(id_empresa=self.empresa, id_proyecto=proyecto).count()
        tiempos_count = RegistroTiempo.objects.filter(id_empresa=self.empresa, id_proyecto=proyecto).count()
        self.assertGreater(gastos_count, 0)
        self.assertGreater(tiempos_count, 0)
        
        # Verificar cuadratura exacta de rentabilidad ($11.537.115,70 de costo real con CIF)
        metricas = calcular_rentabilidad_proyecto(proyecto)
        self.assertEqual(metricas['costo_real_total'], Decimal('11537115.70'))
        self.assertEqual(metricas['margen_real_monto'], Decimal('18332338.30'))

    def test_idempotencia_relectura_excel(self):
        """Verifica que re-ejecutar la ingesta sobre el mismo archivo no duplique compras ni tiempos."""
        from apps.ordenes_trabajo.services_excel_ot import procesar_excel_ot
        from apps.compras_gastos.models import GastoProyecto, RegistroTiempo

        procesar_excel_ot(self.excel_path, self.empresa, self.usuario)
        gastos_iniciales = GastoProyecto.objects.filter(id_empresa=self.empresa).count()
        tiempos_iniciales = RegistroTiempo.objects.filter(id_empresa=self.empresa).count()
        
        # Segunda ejecución
        res2 = procesar_excel_ot(self.excel_path, self.empresa, self.usuario)
        self.assertFalse(res2['creado_nuevo'])
        self.assertEqual(res2['gastos_creados'], 0)
        self.assertEqual(res2['tiempos_creados'], 0)
        
        gastos_finales = GastoProyecto.objects.filter(id_empresa=self.empresa).count()
        tiempos_finales = RegistroTiempo.objects.filter(id_empresa=self.empresa).count()
        
        self.assertEqual(gastos_iniciales, gastos_finales)
        self.assertEqual(tiempos_iniciales, tiempos_finales)

    def test_proceso_nocturno_batch(self):
        """Verifica el escaneo y procesamiento batch de directorio."""
        from apps.ordenes_trabajo.services_excel_ot import procesar_directorio_nocturno
        resultados = procesar_directorio_nocturno("/home/whsg27/proyectos/tallerLogik", self.empresa, self.usuario)
        self.assertGreater(len(resultados), 0)
        self.assertTrue(any(r['archivo'] == 'COSTEO.xlsx' and r['exito'] for r in resultados))

    def test_filtro_dashboard_por_estado(self):
        """Verifica que obtener_metricas_globales_taller permita filtrar OTs en curso vs terminadas."""
        from apps.ordenes_trabajo.services_excel_ot import procesar_excel_ot
        from apps.rentabilidad_cobranzas.services import obtener_metricas_globales_taller

        procesar_excel_ot(self.excel_path, self.empresa, self.usuario, estado_override='entregado')
        
        metricas_terminadas = obtener_metricas_globales_taller(self.empresa, estado_filtro='terminado')
        metricas_en_curso = obtener_metricas_globales_taller(self.empresa, estado_filtro='en_curso')
        
    def test_omite_ingesta_ot_terminada(self):
        """Verifica que si una OT ya está terminada ('entregado'), re-ejecutar la ingesta no modifique ni intervenga sus datos históricos."""
        from apps.ordenes_trabajo.services_excel_ot import procesar_excel_ot

        # 1. Primera ingesta marcándola como terminada
        res1 = procesar_excel_ot(self.excel_path, self.empresa, self.usuario, estado_override='entregado')
        self.assertFalse(res1.get('ya_terminado', False))

        # 2. Segunda ingesta incluso intentando forzar estado (debe detectar que está entregada en BD y omitir)
        res2 = procesar_excel_ot(self.excel_path, self.empresa, self.usuario, estado_override='armado')
        self.assertTrue(res2.get('ya_terminado', False))
        self.assertEqual(res2['gastos_creados'], 0)
        self.assertEqual(res2['tiempos_creados'], 0)
        self.assertIn("TERMINADA", res2['mensaje'])




