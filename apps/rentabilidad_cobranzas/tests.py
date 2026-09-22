from decimal import Decimal
from django.test import TestCase
from apps.core_auth.models import Empresa, Usuario
from apps.configuracion_base.models import Cliente
from apps.cotizador.models import Cotizacion
from apps.ordenes_trabajo.models import Proyecto
from apps.compras_gastos.models import FacturaCompra, GastoProyecto, RegistroTiempo
from apps.rentabilidad_cobranzas.models import PagoProyecto
from apps.rentabilidad_cobranzas.services import calcular_rentabilidad_proyecto, obtener_metricas_globales_taller


class RentabilidadCobranzasTestCase(TestCase):
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
            correo_electronico="operario@taller.cl",
            password="Password123!",
            nombre_completo="Pedro Operario",
            rol="operario",
            costo_hora=Decimal("5000.00"),
            id_empresa=self.empresa
        )
        self.cliente = Cliente.objects.create(
            id_empresa=self.empresa,
            razon_social="Cliente Rentabilidad",
            nombre_contacto="Contacto Rentabilidad"
        )
        self.cotizacion = Cotizacion.objects.create(
            id_empresa=self.empresa,
            id_cliente=self.cliente,
            numero_cotizacion="COT-2026-100",
            version=1,
            titulo_propuesta="Cocina Premium Encinado"
        )
        self.proyecto = Proyecto.objects.create(
            id_empresa=self.empresa,
            id_cotizacion_origen=self.cotizacion,
            id_cliente=self.cliente,
            codigo_ot="OT-2026-099",
            nombre_proyecto="Cocina Premium",
            precio_cotizado=Decimal("1000000.00"),
            costo_presupuestado_total=Decimal("650000.00"),
            margen_objetivo_pct=Decimal("35.00")
        )

    def test_calculo_sobrecosto_y_desviacion(self):
        """Verifica la detección de sobrecosto cuando el costo real supera el presupuestado."""
        factura = FacturaCompra.objects.create(
            id_empresa=self.empresa,
            numero_factura="F-100",
            proveedor="Madera Co.",
            monto_total_neto=Decimal("500000.00"),
            id_usuario_registro=self.jefe_taller
        )
        GastoProyecto.objects.create(
            id_empresa=self.empresa,
            id_factura_compra=factura,
            id_proyecto=self.proyecto,
            tipo_gasto="Material",
            monto_neto_asignado=Decimal("500000.00"),
            id_usuario_registro=self.jefe_taller
        )
        # 40 hrs @ 5,000 = 200,000 MOD (Total real = 700,000 vs Presupuestado = 650,000)
        RegistroTiempo.objects.create(
            id_empresa=self.empresa,
            id_proyecto=self.proyecto,
            id_usuario=self.operario,
            etapa="Armado",
            horas_trabajadas=Decimal("40.00"),
            registrado_por=self.jefe_taller
        )

        m = calcular_rentabilidad_proyecto(self.proyecto)

        self.assertEqual(m['costo_real_total'], Decimal("770000.00"))
        self.assertEqual(m['desviacion_costo'], Decimal("120000.00"))
        self.assertTrue(m['sobrecosto_detectado'])
        # Margen real: (1,000,000 - 770,000) / 1,000,000 = 23.00%
        self.assertEqual(m['margen_real_pct'], Decimal("23.00"))


    def test_gestion_cobranzas_saldo_pendiente(self):
        """Verifica la disminución del saldo pendiente al registrar abonos del cliente."""
        PagoProyecto.objects.create(
            id_empresa=self.empresa,
            id_proyecto=self.proyecto,
            concepto_hito="Anticipo_50",
            monto_pago=Decimal("500000.00"),
            medio_pago="Transferencia",
            id_usuario_registro=self.jefe_taller
        )

        m = calcular_rentabilidad_proyecto(self.proyecto)

        self.assertEqual(m['total_pagado_cliente'], Decimal("500000.00"))
        self.assertEqual(m['saldo_pendiente_cobro'], Decimal("500000.00"))
        self.assertEqual(m['pct_cobrado'], Decimal("50.00"))

    def test_rentabilidad_views_formato_moneda(self):
        """Verifica que en el dashboard de rentabilidad y cobranzas los valores se muestren como $xxx.xxx sin decimales."""
        from django.urls import reverse

        self.client.login(correo_electronico="jefe@taller.cl", password="Password123!")

        # 1. Test Dashboard Rentabilidad /rentabilidad/
        res_dash = self.client.get(reverse('rentabilidad_cobranzas:dashboard_rentabilidad'))
        self.assertEqual(res_dash.status_code, 200)
        self.assertContains(res_dash, "$1.000.000")
        self.assertNotContains(res_dash, "$1000000.00")

        # 2. Test Lista Cobranzas /rentabilidad/cobranzas/
        res_cob = self.client.get(reverse('rentabilidad_cobranzas:cobranzas_list'))
        self.assertEqual(res_cob.status_code, 200)
        self.assertContains(res_cob, "$1.000.000")
        self.assertNotContains(res_cob, "$1000000.00")
