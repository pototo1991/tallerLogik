from django.test import TestCase
from apps.core_auth.models import Empresa, Usuario, AuditoriaLog


class MultiTenantAuthTestCase(TestCase):
    def setUp(self):
        # Crear dos empresas/tenants
        self.empresa_a = Empresa.objects.create(nombre_empresa="Taller A Muebles", rut_o_identificacion="76.111.111-1")
        self.empresa_b = Empresa.objects.create(nombre_empresa="Taller B Carpinteria", rut_o_identificacion="76.222.222-2")

        # Crear usuarios para cada taller
        self.dueno_a = Usuario.objects.create_user(
            correo_electronico="dueno@tallera.cl",
            password="PasswordSecure123!",
            nombre_completo="Juan Taller A",
            rol="dueno_taller",
            id_empresa=self.empresa_a
        )

        self.dueno_b = Usuario.objects.create_user(
            correo_electronico="dueno@tallerb.cl",
            password="PasswordSecure123!",
            nombre_completo="Pedro Taller B",
            rol="dueno_taller",
            id_empresa=self.empresa_b
        )

    def test_creacion_usuarios(self):
        """Verifica la asignación de roles y empresas."""
        self.assertEqual(self.dueno_a.id_empresa, self.empresa_a)
        self.assertEqual(self.dueno_b.id_empresa, self.empresa_b)
        self.assertTrue(self.dueno_a.check_password("PasswordSecure123!"))

    def test_soft_delete(self):
        """Verifica que el método delete() realice un borrado lógico."""
        self.empresa_b.delete()
        self.assertIsNotNone(self.empresa_b.eliminado_en)
        # objetos activos no incluyen la empresa_b
        self.assertFalse(Empresa.objects.filter(id=self.empresa_b.id).exists())
        # all_objects sí incluye el registro eliminado
        self.assertTrue(Empresa.all_objects.filter(id=self.empresa_b.id).exists())

    def test_auditoria_log(self):
        """Verifica creación de registros de auditoría."""
        log = AuditoriaLog.objects.create(
            id_empresa=self.empresa_a,
            id_usuario=self.dueno_a,
            accion="TEST_ACCION",
            detalles="Prueba de auditoría"
        )
        self.assertEqual(log.id_empresa, self.empresa_a)
        self.assertEqual(log.id_usuario, self.dueno_a)

    def test_onboarding_taller_acceso_anonimo(self):
        """Verifica que usuarios anónimos no puedan acceder ni registrar talleres."""
        response = self.client.get('/auth/onboarding/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

        response_post = self.client.post('/auth/onboarding/', {
            'nombre_empresa': 'Muebles Hack',
            'nombre_dueno': 'Hacker',
            'correo_electronico': 'hacker@test.cl',
            'password': 'Password123!'
        })
        self.assertEqual(response_post.status_code, 302)
        self.assertFalse(Empresa.objects.filter(nombre_empresa='Muebles Hack').exists())

    def test_onboarding_taller_acceso_dueno_denegado(self):
        """Verifica que dueños de taller u otros roles no superadmin no puedan registrar talleres."""
        self.client.force_login(self.dueno_a)
        response = self.client.get('/auth/onboarding/')
        self.assertRedirects(response, '/auth/dashboard/')

    def test_onboarding_taller_acceso_superadmin_exitoso(self):
        """Verifica que solo el Superadministrador SaaS puede crear un nuevo taller."""
        superadmin = Usuario.objects.create_user(
            correo_electronico="admin@saas.com",
            password="AdminPassword123!",
            nombre_completo="Super Admin Global",
            rol="superadmin_saas"
        )
        self.client.force_login(superadmin)

        response = self.client.get('/auth/onboarding/')
        self.assertEqual(response.status_code, 200)

        response_post = self.client.post('/auth/onboarding/', {
            'nombre_empresa': 'Mueblería Elite',
            'rut_o_identificacion': '14138344-2',
            'nombre_dueno': 'Carlos Dueño',
            'correo_electronico': 'carlos@muebleriaelite.cl',
            'password': 'PasswordSecure123!'
        })
        self.assertRedirects(response_post, '/auth/dashboard/')
        self.assertTrue(Empresa.objects.filter(nombre_empresa='Mueblería Elite').exists())
        self.assertTrue(Usuario.objects.filter(correo_electronico='carlos@muebleriaelite.cl').exists())

    def test_validacion_rut_modulo11_funcion(self):
        """Verifica la lógica del algoritmo de Módulo 11 para RUTs chilenos."""
        from apps.core_auth.forms import validar_rut_chileno_modulo11
        
        # RUT válido de ejemplo
        es_valido, rut_fmt = validar_rut_chileno_modulo11('14138344-2')
        self.assertTrue(es_valido)
        self.assertEqual(rut_fmt, '14138344-2')

        # RUT válido con puntos
        es_valido_pts, rut_fmt_pts = validar_rut_chileno_modulo11('14.138.344-2')
        self.assertTrue(es_valido_pts)
        self.assertEqual(rut_fmt_pts, '14138344-2')

        # RUT con DV erróneo
        es_valido_bad, _ = validar_rut_chileno_modulo11('14138344-9')
        self.assertFalse(es_valido_bad)

    def test_form_onboarding_validaciones_estrictas(self):
        """Verifica que el formulario rechace RUTs con DV inválido y correos mal formateados."""
        from apps.core_auth.forms import OnboardingTallerForm

        # 1. Formulario con RUT con DV incorrecto
        form_bad_rut = OnboardingTallerForm(data={
            'nombre_empresa': 'Taller Test',
            'rut_o_identificacion': '14138344-9', # DV debería ser 2
            'nombre_dueno': 'Admin Test',
            'correo_electronico': 'admin@test.cl',
            'password': 'PasswordSecure123!'
        })
        self.assertFalse(form_bad_rut.is_valid())
        self.assertIn('rut_o_identificacion', form_bad_rut.errors)

        # 2. Formulario con Correo electrónico inválido
        form_bad_email = OnboardingTallerForm(data={
            'nombre_empresa': 'Taller Test',
            'rut_o_identificacion': '14138344-2',
            'nombre_dueno': 'Admin Test',
            'correo_electronico': 'correo_invalido_sin_arriba.com',
            'password': 'PasswordSecure123!'
        })
        self.assertFalse(form_bad_email.is_valid())
        self.assertIn('correo_electronico', form_bad_email.errors)

    def test_visor_logs_acceso_anonimo_denegado(self):
        """Verifica que usuarios no autenticados sean redirigidos al login al intentar ver los logs."""
        response = self.client.get('/auth/logs/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

    def test_visor_logs_acceso_usuario_normal_denegado(self):
        """Verifica que usuarios con rol distinto a superadmin_saas no puedan acceder a los logs."""
        self.client.force_login(self.dueno_a)
        response = self.client.get('/auth/logs/')
        self.assertRedirects(response, '/auth/dashboard/')

    def test_visor_logs_acceso_superadmin_exitoso(self):
        """Verifica que el Superadministrador SaaS pueda acceder al visor de logs de actividad y errores."""
        superadmin = Usuario.objects.create_user(
            correo_electronico="adminlogs@saas.com",
            password="AdminPassword123!",
            nombre_completo="Super Admin Logs",
            rol="superadmin_saas"
        )
        self.client.force_login(superadmin)

        # Probar log de actividad
        response_act = self.client.get('/auth/logs/?tipo=actividad')
        self.assertEqual(response_act.status_code, 200)
        self.assertContains(response_act, "Logs del Sistema")
        self.assertContains(response_act, "Log de Actividad")

        # Probar log de errores
        response_err = self.client.get('/auth/logs/?tipo=errores')
        self.assertEqual(response_err.status_code, 200)
        self.assertContains(response_err, "Log de Errores")

    def test_custom_filters(self):
        """Verifica los filtros personalizados de formateo de moneda CLP y cantidades."""
        from apps.core_auth.templatetags.custom_filters import clp, clp_raw, cantidad_format
        from decimal import Decimal

        # Prueba filtro CLP con signo de peso
        self.assertEqual(clp(Decimal('92620.00')), '$92.620')
        self.assertEqual(clp(Decimal('45600.00')), '$45.600')
        self.assertEqual(clp(Decimal('25000')), '$25.000')
        self.assertEqual(clp(Decimal('163220.00')), '$163.220')
        self.assertEqual(clp(Decimal('251107.69')), '$251.108')
        self.assertEqual(clp(1500.00), '$1.500')
        self.assertEqual(clp(0), '$0')
        self.assertEqual(clp(None), '$0')

        # Prueba filtro CLP sin signo de peso
        self.assertEqual(clp_raw(Decimal('92620.00')), '92.620')
        self.assertEqual(clp_raw(251107.69), '251.108')

        # Prueba filtro cantidad sin decimales
        self.assertEqual(cantidad_format(Decimal('3.00')), '3')
        self.assertEqual(cantidad_format(Decimal('4.00')), '4')
        self.assertEqual(cantidad_format(Decimal('40.00')), '40')
        self.assertEqual(cantidad_format(Decimal('16.00')), '16')
        self.assertEqual(cantidad_format(3.50), '3,5')
        self.assertEqual(cantidad_format(None), '0')

    def test_dashboard_dueno_formato_moneda(self):
        """Verifica que en /auth/dashboard/ para un dueño de taller los valores de las tarjetas KPI se muestren como $xxx.xxx sin decimales."""
        from apps.ordenes_trabajo.models import Proyecto
        from apps.configuracion_base.models import Cliente
        from apps.cotizador.models import Cotizacion
        from decimal import Decimal

        cliente = Cliente.objects.create(
            id_empresa=self.empresa_a,
            razon_social="Cliente Test",
            rut_o_identificacion="12.345.678-9"
        )
        cotizacion = Cotizacion.objects.create(
            id_empresa=self.empresa_a,
            id_cliente=cliente,
            numero_cotizacion="COT-1001",
            titulo_propuesta="Mueble Oficina",
            precio_venta_neto=Decimal("1500000.00")
        )
        Proyecto.objects.create(
            id_empresa=self.empresa_a,
            id_cliente=cliente,
            id_cotizacion_origen=cotizacion,
            codigo_ot="OT-1001",
            nombre_proyecto="Mueble Oficina",
            precio_cotizado=Decimal("1500000.00"),
            costo_presupuestado_total=Decimal("800000.00")
        )

        self.client.force_login(self.dueno_a)
        response = self.client.get('/auth/dashboard/')
        self.assertEqual(response.status_code, 200)

        # Debe mostrar $1.500.000 en lugar de $1500000.00
        self.assertContains(response, "$1.500.000")
        self.assertNotContains(response, "$1500000.00")





