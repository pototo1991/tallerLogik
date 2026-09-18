from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.core_auth.models import Empresa, Usuario
from apps.configuracion_base.models import Cliente
from apps.cotizador.models import Cotizacion
from apps.ordenes_trabajo.models import Proyecto
from apps.compras_gastos.models import FacturaCompra, GastoProyecto, RegistroTiempo
from apps.compras_gastos.services import registrar_factura_y_distribuir_gastos


class ComprasGastosTestCase(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre_empresa="Taller Muebles", rut_o_identificacion="77.777.777-7")
        self.jefe_taller = Usuario.objects.create_user(
            correo_electronico="jefe@taller.cl",
            password="Password123!",
            nombre_completo="Jefe Taller",
            rol="jefe_taller",
            id_empresa=self.empresa
        )
        self.operario = Usuario.objects.create_user(
            correo_electronico="operario1@taller.cl",
            password="Password123!",
            nombre_completo="Juan Operario",
            rol="operario",
            costo_hora=Decimal("5000.00"),
            id_empresa=self.empresa
        )
        self.cliente = Cliente.objects.create(
            id_empresa=self.empresa,
            razon_social="Cliente Compras",
            nombre_contacto="Contacto Compras"
        )
        self.cotizacion = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-050",
            version=1,
            titulo_propuesta="Proyecto Compras"
        )
        self.proyecto1 = Proyecto.objects.create(
            id_empresa=self.empresa,
            id_cotizacion_origen=self.cotizacion,
            id_cliente=self.cliente,
            codigo_ot="OT-2026-001",
            nombre_proyecto="Proyecto 1",
            precio_cotizado=Decimal("500000.00"),
            costo_presupuestado_total=Decimal("300000.00")
        )
        self.proyecto2 = Proyecto.objects.create(
            id_empresa=self.empresa,
            id_cotizacion_origen=self.cotizacion,
            id_cliente=self.cliente,
            codigo_ot="OT-2026-002",
            nombre_proyecto="Proyecto 2",
            precio_cotizado=Decimal("400000.00"),
            costo_presupuestado_total=Decimal("200000.00")
        )

    def test_cuadratura_factura_exitosa(self):
        """Verifica que la compra se registre si la suma de desgloses cuadra con el total neto."""
        factura_data = {
            'numero_factura': 'F-1234',
            'proveedor': 'Sodimac',
            'monto_total_neto': Decimal('100000.00')
        }
        desgloses = [
            {'proyecto': self.proyecto1, 'tipo_gasto': 'Material', 'monto_neto_asignado': Decimal('60000.00')},
            {'proyecto': self.proyecto2, 'tipo_gasto': 'Material', 'monto_neto_asignado': Decimal('40000.00')},
        ]

        factura = registrar_factura_y_distribuir_gastos(factura_data, desgloses, self.jefe_taller)

        self.assertEqual(factura.numero_factura, 'F-1234')
        self.assertEqual(factura.gastos_distribuidos.count(), 2)
        self.assertEqual(GastoProyecto.objects.filter(id_proyecto=self.proyecto1).first().monto_neto_asignado, Decimal('60000.00'))

    def test_cuadratura_factura_fallida(self):
        """Verifica que falle con ValidationError si la suma desglosada no cuadra con el total neto."""
        factura_data = {
            'numero_factura': 'F-9999',
            'proveedor': 'Imperial',
            'monto_total_neto': Decimal('100000.00')
        }
        desgloses = [
            {'proyecto': self.proyecto1, 'tipo_gasto': 'Material', 'monto_neto_asignado': Decimal('50000.00')},
            {'proyecto': self.proyecto2, 'tipo_gasto': 'Material', 'monto_neto_asignado': Decimal('40000.00')},
        ]

        with self.assertRaises(ValidationError):
            registrar_factura_y_distribuir_gastos(factura_data, desgloses, self.jefe_taller)

    def test_imputacion_tiempos_mod(self):
        """Verifica el cálculo inmutable de costo MOD = horas * costo_hora."""
        registro = RegistroTiempo.objects.create(
            id_empresa=self.empresa,
            id_proyecto=self.proyecto1,
            id_usuario=self.operario,
            etapa='Corte',
            horas_trabajadas=Decimal('4.50'),
            registrado_por=self.jefe_taller
        )

        # 4.5 * 5000 = 22500.00
        self.assertEqual(registro.costo_mano_obra_calculado, Decimal('22500.00'))

    def test_distribucion_gasto_con_item_preexistente(self):
        """Verifica que el gasto de compra se pueda asociar a un ItemProyecto ya existente."""
        from apps.ordenes_trabajo.models import ItemProyecto
        
        item_existente = ItemProyecto.objects.create(
            id_empresa=self.empresa,
            id_proyecto=self.proyecto1,
            descripcion="Tornillos Soberbios 2 pulgadas",
            tipo_item="Insumo",
            cantidad=Decimal("100.00"),
            costo_unitario=Decimal("20.00"),
            subtotal_costo=Decimal("2000.00")
        )
        
        factura_data = {
            'numero_factura': 'F-5555',
            'proveedor': 'Imperial',
            'monto_total_neto': Decimal('2000.00')
        }
        
        desgloses = [
            {
                'proyecto': self.proyecto1,
                'item_id': str(item_existente.id),
                'tipo_gasto': 'Material',
                'monto_neto_asignado': Decimal('2000.00')
            }
        ]
        
        factura = registrar_factura_y_distribuir_gastos(factura_data, desgloses, self.jefe_taller)
        
        gasto = GastoProyecto.objects.get(id_factura_compra=factura)
        self.assertEqual(gasto.id_item_proyecto, item_existente)
        self.assertEqual(gasto.monto_neto_asignado, Decimal('2000.00'))
        
    def test_distribucion_gasto_crea_item_nuevo(self):
        """Verifica que si no se provee item_id, se cree un ItemProyecto de rectificación dinámicamente."""
        from apps.ordenes_trabajo.models import ItemProyecto
        
        factura_data = {
            'numero_factura': 'F-7777',
            'proveedor': 'Easy',
            'monto_total_neto': Decimal('15000.00')
        }
        
        desgloses = [
            {
                'proyecto': self.proyecto1,
                'item_id': None,
                'descripcion': 'Material Extra - Bisagras Especiales',
                'tipo_gasto': 'Insumo',
                'monto_neto_asignado': Decimal('15000.00')
            }
        ]
        
        self.proyecto1.costo_presupuestado_total = Decimal('0.00')
        self.proyecto1.save()
        
        factura = registrar_factura_y_distribuir_gastos(factura_data, desgloses, self.jefe_taller)
        
        gasto = GastoProyecto.objects.get(id_factura_compra=factura)
        self.assertIsNotNone(gasto.id_item_proyecto)
        
        item_creado = gasto.id_item_proyecto
        self.assertEqual(item_creado.descripcion, 'Material Extra - Bisagras Especiales')
        self.assertEqual(item_creado.tipo_item, 'Insumo')
        self.assertTrue(item_creado.agregado_rectificacion)
        
        # Verificar que el costo del proyecto se haya actualizado
        self.proyecto1.refresh_from_db()
        self.assertEqual(self.proyecto1.costo_presupuestado_total, Decimal('15000.00'))

    def test_compras_views_formato_moneda(self):
        """Verifica que en las vistas de compras (/compras/ y /compras/<id>/) los valores se muestren como $xxx.xxx sin decimales."""
        from django.urls import reverse

        factura_data = {
            'numero_factura': 'F-8888',
            'proveedor': 'Imperial',
            'monto_total_neto': Decimal('150000.00')
        }
        desgloses = [
            {'proyecto': self.proyecto1, 'tipo_gasto': 'Material', 'monto_neto_asignado': Decimal('150000.00')},
        ]
        factura = registrar_factura_y_distribuir_gastos(factura_data, desgloses, self.jefe_taller)

        self.client.login(correo_electronico="jefe@taller.cl", password="Password123!")

        # 1. Test Lista de Facturas /compras/
        res_list = self.client.get(reverse('compras_gastos:facturas_list'))
        self.assertEqual(res_list.status_code, 200)
        self.assertContains(res_list, "$150.000")
        self.assertNotContains(res_list, "$150000.00")

        # 2. Test Detalle de Factura /compras/<pk>/
        res_detail = self.client.get(reverse('compras_gastos:factura_detail', args=[factura.pk]))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, "$150.000")
        self.assertNotContains(res_detail, "$150000.00")

    def test_desglose_sub_items_con_barra(self):
        """Verifica que items_desglosados separe descripciones compuestas por '/' y extraiga las cantidades de cada sub-ítem."""
        gasto = GastoProyecto.objects.create(
            id_empresa=self.empresa,
            id_factura_compra=FacturaCompra.objects.create(
                id_empresa=self.empresa,
                numero_factura="F-SUBITEMS",
                proveedor="Proveedor Insumos",
                monto_total_neto=Decimal("120000.00"),
                id_usuario_registro=self.jefe_taller
            ),
            id_proyecto=self.proyecto1,
            descripcion="FUENTE DE PODER 23W 12V INTERIOR (CANT.01)/FUENTE DE PODER 50W 12V INTERIOR (CANT.01)/FUENTE DE PODER 75W 12V INTERIOR (CANT.01)/CINTA LED 2835 BCO CALIDO 9.6W 12V (CANT.15MTS)",
            tipo_gasto="Material",
            monto_neto_asignado=Decimal("120000.00"),
            id_usuario_registro=self.jefe_taller
        )

        items = gasto.items_desglosados
        self.assertEqual(len(items), 4)

        self.assertEqual(items[0]['descripcion'], "FUENTE DE PODER 23W 12V INTERIOR (CANT.01)")
        self.assertEqual(items[0]['cantidad'], "01")

        self.assertEqual(items[1]['descripcion'], "FUENTE DE PODER 50W 12V INTERIOR (CANT.01)")
        self.assertEqual(items[1]['cantidad'], "01")

        self.assertEqual(items[2]['descripcion'], "FUENTE DE PODER 75W 12V INTERIOR (CANT.01)")
        self.assertEqual(items[2]['cantidad'], "01")

        self.assertEqual(items[3]['descripcion'], "CINTA LED 2835 BCO CALIDO 9.6W 12V (CANT.15MTS)")
        self.assertEqual(items[3]['cantidad'], "15MTS")

        self.assertEqual(gasto.cantidad_extraida, "01, 01, 01, 15MTS")

