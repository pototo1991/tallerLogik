from decimal import Decimal
from django.test import TestCase
from apps.core_auth.models import Empresa, Usuario
from apps.configuracion_base.models import Cliente, Material
from apps.cotizador.models import Cotizacion, ItemCotizacion
from apps.cotizador.services import recalcular_cotizacion, clonar_version_cotizacion


class CotizadorTestCase(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre_empresa="Taller Muebles", rut_o_identificacion="77.777.777-7")
        self.usuario = Usuario.objects.create_user(
            correo_electronico="vendedor@taller.cl",
            password="Password123!",
            nombre_completo="Vendedor Taller",
            rol="vendedor",
            id_empresa=self.empresa
        )
        self.cliente = Cliente.objects.create(
            id_empresa=self.empresa,
            razon_social="Cliente Prueba",
            nombre_contacto="Juan Dueño"
        )
        self.material = Material.objects.create(
            id_empresa=self.empresa,
            nombre="Plancha Terciado 18mm",
            categoria="Tableros",
            unidad_medida="Plancha",
            costo_unitario=Decimal("30000.00"),
            porcentaje_merma_defecto=Decimal("10.00")
        )

    def test_calculo_subtotal_item_con_merma(self):
        """Verifica que el subtotal incorpore el porcentaje de merma."""
        cotizacion = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-001",
            version=1,
            titulo_propuesta="Mueble TV",
            margen_objetivo_pct=Decimal("35.00")
        )

        item = ItemCotizacion.objects.create(
            id_empresa=self.empresa,
            id_cotizacion=cotizacion,
            id_material=self.material,
            descripcion="Plancha Terciado 18mm",
            tipo_item="Material",
            cantidad=Decimal("2.00"),
            costo_unitario=Decimal("30000.00"),
            porcentaje_merma_aplicado=Decimal("10.00")
        )

        # 2 * 30,000 * 1.10 = 66,000.00
        self.assertEqual(item.subtotal_costo, Decimal("66000.00"))

    def test_margen_sobre_venta(self):
        """Verifica la fórmula de margen sobre venta P = C / (1 - M)."""
        cotizacion = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-002",
            version=1,
            titulo_propuesta="Mueble Barra",
            costo_materiales_estimado=Decimal("650000.00"),
            margen_objetivo_pct=Decimal("35.00")
        )
        cotizacion.calcular_totales()

        # 650000 / (1 - 0.35) = 650000 / 0.65 = 1,000,000.00
        self.assertEqual(cotizacion.precio_venta_neto, Decimal("1000000.00"))

    def test_clonar_version_cotizacion(self):
        """Verifica que el versionamiento cree v2 manteniendo la numeración y clonando ítems."""
        cotizacion_v1 = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-003",
            version=1,
            titulo_propuesta="Mueble Cocina Base",
            margen_objetivo_pct=Decimal("30.00")
        )
        ItemCotizacion.objects.create(
            id_empresa=self.empresa,
            id_cotizacion=cotizacion_v1,
            descripcion="Mano de obra armado",
            tipo_item="Mano_Obra",
            cantidad=Decimal("10.00"),
            costo_unitario=Decimal("15000.00")
        )
        recalcular_cotizacion(cotizacion_v1)

        # Clonar a v2
        cotizacion_v2 = clonar_version_cotizacion(cotizacion_v1.id, self.usuario)

        self.assertEqual(cotizacion_v2.numero_cotizacion, "COT-2026-003")
        self.assertEqual(cotizacion_v2.version, 2)
        self.assertEqual(cotizacion_v2.items.count(), 1)
        self.assertEqual(cotizacion_v2.costo_mano_obra_estimado, Decimal("150000.00"))

    def test_crear_item_cotizacion_flujo_nuevo(self):
        """Verifica la creación de ítem en el nuevo flujo (sin tipo_item ni merma en payload)."""
        cotizacion = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-004",
            version=1,
            titulo_propuesta="Mueble Repisa",
            margen_objetivo_pct=Decimal("30.00")
        )

        self.client.force_login(self.usuario)
        from django.urls import reverse
        url = reverse('cotizador:item_create', kwargs={'cotizacion_pk': cotizacion.pk})
        response = self.client.post(
            url,
            data={
                'id_material': str(self.material.id),
                'costo_unitario': '25000.00',  # Valor unitario modificado
                'cantidad': '3.00',
                'descripcion': 'Plancha Especial Modificada'
            },
            HTTP_HX_REQUEST='true'
        )

        self.assertEqual(response.status_code, 200)
        item = cotizacion.items.first()
        self.assertIsNotNone(item)
        self.assertEqual(item.tipo_item, 'Material')
        self.assertEqual(item.porcentaje_merma_aplicado, Decimal('0.00'))
        self.assertEqual(item.costo_unitario, Decimal('25000.00'))
        self.assertEqual(item.cantidad, Decimal('3.00'))
        self.assertEqual(item.subtotal_costo, Decimal('75000.00'))  # 25,000 * 3 = 75,000
        self.assertEqual(item.descripcion, 'Plancha Especial Modificada')

    def test_crear_item_mano_de_obra(self):
        """Verifica la creación de ítem de Mano de Obra y actualización del costo_mano_obra_estimado."""
        cotizacion = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-005",
            version=1,
            titulo_propuesta="Mueble Closet",
            margen_objetivo_pct=Decimal("35.00")
        )

        self.client.force_login(self.usuario)
        from django.urls import reverse
        url = reverse('cotizador:item_create', kwargs={'cotizacion_pk': cotizacion.pk})
        response = self.client.post(
            url,
            data={
                'tipo_item': 'Mano_Obra',
                'costo_unitario': '6500.00',  # Costo por hora
                'cantidad': '48.00',          # 3 días * 2 personas * 8 hrs
                'descripcion': 'Operario de Taller (2 personas × 3 días hábiles)'
            },
            HTTP_HX_REQUEST='true'
        )

        self.assertEqual(response.status_code, 200)
        cotizacion.refresh_from_db()
        item = cotizacion.items.first()
        self.assertIsNotNone(item)
        self.assertEqual(item.tipo_item, 'Mano_Obra')
        self.assertEqual(item.subtotal_costo, Decimal('312000.00'))  # 48 * 6500 = 312,000
        self.assertEqual(cotizacion.costo_mano_obra_estimado, Decimal('312000.00'))

    def test_render_cotizacion_form_view(self):
        """Verifica que la plantilla de creación de cotizaciones se renderice sin errores de sintaxis y que el campo cif no use decimales."""
        self.client.force_login(self.usuario)
        from django.urls import reverse
        response = self.client.get(reverse('cotizador:cotizacion_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nueva Cotización Comercial")

        # Verificar que el input de costo_indirecto_cif_estimado se renderice con step="1" y sin decimales
        self.assertContains(response, 'name="costo_indirecto_cif_estimado"')
        self.assertContains(response, 'step="1"')

    def test_fecha_entrega_sugerida_y_manual(self):
        """Verifica el cálculo de fecha de entrega sugerida por mano de obra y la prevalencia de fecha fija manual."""
        from datetime import date, timedelta
        fecha_inicio = date(2026, 9, 1)
        cotizacion = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-006",
            version=1,
            titulo_propuesta="Mueble Escritorio",
            fecha_inicio_estimada=fecha_inicio
        )

        # 1. Sin ítems de mano de obra: días laborables = 0, fecha sugerida = fecha inicio
        self.assertEqual(cotizacion.dias_mano_obra_estimados, 0)
        self.assertEqual(cotizacion.fecha_entrega_sugerida, fecha_inicio)

        # 2. Agregar ítem de mano de obra con 48 hrs (48 / 8 = 6 días laborables)
        ItemCotizacion.objects.create(
            id_empresa=self.empresa,
            id_cotizacion=cotizacion,
            descripcion="Armado Taller",
            tipo_item="Mano_Obra",
            cantidad=Decimal("48.00"),
            costo_unitario=Decimal("5000.00")
        )
        self.assertEqual(cotizacion.dias_mano_obra_estimados, 6)
        self.assertEqual(cotizacion.fecha_entrega_sugerida, fecha_inicio + timedelta(days=6))

        # 3. Establecer fecha fija manual (override)
        fecha_fija = date(2026, 9, 20)
        cotizacion.fecha_entrega_manual = fecha_fija
        cotizacion.save()

        self.assertEqual(cotizacion.fecha_entrega_sugerida, fecha_fija)

    def test_editar_precio_venta_neto_recalcula_margen(self):
        """Verifica que al editar el precio de venta neto, se recalculen el porcentaje y monto de margen."""
        cotizacion = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-007",
            version=1,
            titulo_propuesta="Mueble Recepción",
            costo_materiales_estimado=Decimal("650000.00"),
            margen_objetivo_pct=Decimal("35.00")
        )
        cotizacion.calcular_totales()
        # Inicialmente 650.000 / (1 - 0.35) = 1.000.000.00
        self.assertEqual(cotizacion.precio_venta_neto, Decimal("1000000.00"))
        self.assertEqual(cotizacion.monto_margen_estimado, Decimal("350000.00"))

        # Editar precio de venta neto a 1.200.000 via POST
        self.client.force_login(self.usuario)
        from django.urls import reverse
        url = reverse('cotizador:cotizacion_detail', kwargs={'pk': cotizacion.pk})
        response = self.client.post(
            url,
            data={
                'origen_cambio': 'precio',
                'precio_venta_neto_clean': '1200000.00',
                'precio_venta_neto': '1.200.000',
                'margen_objetivo_pct': '35.00',
                'dias_validez': '15',
                'costo_indirecto_cif_estimado': '0'
            }
        )
        self.assertEqual(response.status_code, 302)
        cotizacion.refresh_from_db()
        # Nuevo precio = 1.200.000.00
        self.assertEqual(cotizacion.precio_venta_neto, Decimal("1200000.00"))
        # Margen = (1200000 - 650000) / 1200000 * 100 = 45.83%
        self.assertEqual(cotizacion.margen_objetivo_pct, Decimal("45.83"))
        # Monto margen = 1200000 - 650000 = 550.000.00
        self.assertEqual(cotizacion.monto_margen_estimado, Decimal("550000.00"))



