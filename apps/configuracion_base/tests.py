from django.test import TestCase
from apps.core_auth.models import Empresa
from apps.configuracion_base.models import Cliente, Material
from decimal import Decimal


class ConfiguracionBaseTestCase(TestCase):
    def setUp(self):
        self.empresa_a = Empresa.objects.create(nombre_empresa="Taller A", rut_o_identificacion="11111111-1")
        self.empresa_b = Empresa.objects.create(nombre_empresa="Taller B", rut_o_identificacion="22222222-2")

        # Cliente y Material en Taller A
        self.cliente_a = Cliente.objects.create(
            id_empresa=self.empresa_a,
            razon_social="Cliente Taller A",
            nombre_contacto="Contacto A"
        )
        self.material_a = Material.objects.create(
            id_empresa=self.empresa_a,
            nombre="Plancha MDF 18mm",
            categoria="Tableros",
            unidad_medida="Plancha",
            costo_unitario=Decimal("25000.00")
        )

        # Cliente y Material en Taller B
        self.cliente_b = Cliente.objects.create(
            id_empresa=self.empresa_b,
            razon_social="Cliente Taller B",
            nombre_contacto="Contacto B"
        )
        self.material_b = Material.objects.create(
            id_empresa=self.empresa_b,
            nombre="Madera Pino 2x4",
            categoria="Maderas",
            unidad_medida="ML",
            costo_unitario=Decimal("3500.00")
        )

    def test_aislamiento_clientes(self):
        """Verifica que el Taller A solo vea sus propios clientes."""
        clientes_taller_a = Cliente.objects.filter(id_empresa=self.empresa_a)
        self.assertEqual(clientes_taller_a.count(), 1)
        self.assertEqual(clientes_taller_a.first(), self.cliente_a)

    def test_aislamiento_materiales(self):
        """Verifica que el Taller B solo vea sus propios materiales."""
        materiales_taller_b = Material.objects.filter(id_empresa=self.empresa_b)
        self.assertEqual(materiales_taller_b.count(), 1)
        self.assertEqual(materiales_taller_b.first(), self.material_b)

    def test_importar_material_global(self):
        """Verifica la clonación de un material global al inventario del taller."""
        from apps.configuracion_base.models import MaterialGlobal
        from apps.configuracion_base.services import importar_material_a_taller
        from django.core.exceptions import ValidationError

        mg = MaterialGlobal.objects.create(
            sku_proveedor="TEST-IMP-001",
            nombre="Tablero Terciado MOCK",
            categoria="Tableros",
            unidad_medida="Plancha",
            costo_unitario=Decimal("20000.00")
        )

        # Importar a Taller A
        mat_taller = importar_material_a_taller(mg.id, self.empresa_a)
        self.assertEqual(mat_taller.nombre, mg.nombre)
        self.assertEqual(mat_taller.costo_unitario, mg.costo_unitario)
        self.assertEqual(mat_taller.material_global, mg)
        self.assertEqual(mat_taller.sku_proveedor, mg.sku_proveedor)
        self.assertEqual(mat_taller.id_empresa, self.empresa_a)
        self.assertTrue(mat_taller.actualizacion_automatica)

        # Intentar importar duplicado debe lanzar ValidationError
        with self.assertRaises(ValidationError):
            importar_material_a_taller(mg.id, self.empresa_a)

    def test_unique_sku_per_tenant(self):
        """Valida la restricción de base de datos de un único SKU por taller."""
        from django.db import IntegrityError, transaction
        
        # Taller A ya tiene TEST-SKU
        Material.objects.create(
            id_empresa=self.empresa_a,
            nombre="Madera Test 1",
            categoria="Maderas",
            unidad_medida="ML",
            costo_unitario=Decimal("1500.00"),
            sku_proveedor="TEST-SKU"
        )

        # Taller A intenta agregar otro con el mismo SKU -> Debe fallar por restricción UniqueConstraint
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Material.objects.create(
                    id_empresa=self.empresa_a,
                    nombre="Madera Test 2",
                    categoria="Maderas",
                    unidad_medida="ML",
                    costo_unitario=Decimal("1800.00"),
                    sku_proveedor="TEST-SKU"
                )

        # Taller B sí puede agregar el mismo SKU (Aislamiento de catálogo por Tenant)
        mat_taller_b = Material.objects.create(
            id_empresa=self.empresa_b,
            nombre="Madera Test B",
            categoria="Maderas",
            unidad_medida="ML",
            costo_unitario=Decimal("1500.00"),
            sku_proveedor="TEST-SKU"
        )
        self.assertEqual(mat_taller_b.sku_proveedor, "TEST-SKU")

    def test_propagacion_precios(self):
        """Prueba que los cambios de precios en catálogo global se propaguen solo a talleres con auto-sync."""
        from apps.configuracion_base.models import MaterialGlobal
        from apps.configuracion_base.services import importar_material_a_taller, ejecutar_scraping_imperial
        # Crear un material global vinculado a un SKU del mock fallback
        mg = MaterialGlobal.objects.create(
            sku_proveedor="115846",
            nombre="Melamina blanca 15mm 1,83x2,50mt",
            categoria="Tableros",
            unidad_medida="Plancha",
            costo_unitario=Decimal("10000.00"),
            proveedor="Imperial"
        )

        # Taller A importa el material (con actualización automática)
        mat_taller_a = importar_material_a_taller(mg.id, self.empresa_a)
        
        # Taller B importa pero apaga la sincronización automática
        mat_taller_b = importar_material_a_taller(mg.id, self.empresa_b)
        mat_taller_b.actualizacion_automatica = False
        mat_taller_b.save()

        # Ejecutamos el scraper con mock fallback (que tiene el SKU 115846 a $37,900.00)
        ejecutar_scraping_imperial(use_mock=True)

        # Verificar
        mat_taller_a.refresh_from_db()
        mat_taller_b.refresh_from_db()

        # Taller A debe actualizarse al nuevo precio del mock (37900.00)
        self.assertEqual(mat_taller_a.costo_unitario, Decimal("37900.00"))
        
        # Taller B debe retener su costo unitario viejo de 10000.00
        self.assertEqual(mat_taller_b.costo_unitario, Decimal("10000.00"))

    from django.test import override_settings

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_views_catalogo_global_and_import(self):
        """Prueba de integración para las vistas de búsqueda, importación y estado del scraper."""
        from django.contrib.auth import get_user_model
        from apps.configuracion_base.models import MaterialGlobal
        from django.urls import reverse

        Usuario = get_user_model()
        user = Usuario.objects.create_user(
            correo_electronico="superadmin@saas.com",
            password="testpassword123",
            nombre_completo="Superadmin SaaS",
            rol="superadmin_saas",
            id_empresa=self.empresa_a
        )

        # Login
        self.client.login(correo_electronico="superadmin@saas.com", password="testpassword123")

        # Crear un material global de prueba
        mg = MaterialGlobal.objects.create(
            sku_proveedor="VIEW-TEST-SKU",
            nombre="Tablero MDF View Test",
            categoria="Tableros",
            unidad_medida="Plancha",
            costo_unitario=Decimal("25000.00")
        )

        # 1. Test Buscador Global
        url_buscar = reverse('configuracion_base:materiales_global_buscar')
        response = self.client.get(url_buscar, {'q': 'MDF'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tablero MDF View Test")
        self.assertContains(response, "$25.000")
        self.assertEqual(response.context['total_imperial'], 1)
        self.assertContains(response, "1 productos extraídos")

        # 2. Test Importar Material Global
        url_importar = reverse('configuracion_base:material_importar', args=[mg.id])
        response = self.client.post(url_importar)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Importado") # Debe renderizar el badge de éxito

        # Verificar que el material ahora existe en el taller
        self.assertTrue(
            Material.objects.filter(id_empresa=self.empresa_a, sku_proveedor="VIEW-TEST-SKU").exists()
        )

        # 3. Test Ejecutar Scraping Manual (restringido a superadmin_saas)
        from unittest.mock import patch, MagicMock
        with patch('apps.configuracion_base.views.scraping_views.tarea_scraping_manual_async.delay') as mock_delay:
            mock_delay.return_value = MagicMock(id='dummy-task-id')
            url_scraping = reverse('configuracion_base:materiales_ejecutar_scraping')
            response = self.client.post(url_scraping)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "status/")

        # 4. Test Scraping Task Status (con mock de AsyncResult)
        with patch('apps.configuracion_base.views.scraping_views.AsyncResult') as mock_async_result:
            mock_res = MagicMock()
            mock_res.state = 'SUCCESS'
            mock_res.result = {'creados': 5, 'actualizados': 0}
            mock_async_result.return_value = mock_res
            
            url_status = reverse('configuracion_base:scraping_task_status', args=['dummy-task-id'])
            response = self.client.get(url_status)
            self.assertEqual(response.status_code, 200)



class ClienteFormValidationTestCase(TestCase):

    """Pruebas unitarias para las validaciones de RUT (Módulo 11 y formato 12345678-9) y correos en ClienteForm."""

    def test_cliente_form_rut_valido(self):
        from apps.configuracion_base.forms import ClienteForm

        form = ClienteForm(data={
            'razon_social': 'Muebles SA',
            'nombre_contacto': 'Juan Perez',
            'rut_o_identificacion': '14138344-2',
            'correo_contacto': 'contacto@muebles.cl',
            'correo_general': 'facturacion@muebles.cl',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['rut_o_identificacion'], '14138344-2')
        self.assertEqual(form.cleaned_data['correo_contacto'], 'contacto@muebles.cl')

    def test_cliente_form_rut_formato_invalido_con_puntos(self):
        from apps.configuracion_base.forms import ClienteForm

        form = ClienteForm(data={
            'razon_social': 'Muebles SA',
            'nombre_contacto': 'Juan Perez',
            'rut_o_identificacion': '14.138.344-2',  # Con puntos -> debe fallar formato
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rut_o_identificacion', form.errors)
        self.assertIn('formato 12345678-9', form.errors['rut_o_identificacion'][0])

    def test_cliente_form_rut_dv_incorrecto_modulo11(self):
        from apps.configuracion_base.forms import ClienteForm

        form = ClienteForm(data={
            'razon_social': 'Muebles SA',
            'nombre_contacto': 'Juan Perez',
            'rut_o_identificacion': '14138344-9',  # DV debería ser 2 -> debe fallar Módulo 11
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rut_o_identificacion', form.errors)
        self.assertIn('Módulo 11', form.errors['rut_o_identificacion'][0])

    def test_cliente_form_correo_invalido(self):
        from apps.configuracion_base.forms import ClienteForm

        form = ClienteForm(data={
            'razon_social': 'Muebles SA',
            'nombre_contacto': 'Juan Perez',
            'correo_contacto': 'correo_invalido_sin_arriba.com',
            'correo_general': 'facturacion@',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('correo_contacto', form.errors)
        self.assertIn('correo_general', form.errors)


class MaterialFormTestCase(TestCase):
    """Pruebas unitarias para campos proveedor y observaciones en MaterialForm y Material."""

    def test_material_form_proveedor_y_observaciones(self):
        from apps.configuracion_base.forms import MaterialForm

        form = MaterialForm(data={
            'nombre': 'Tapacanto PVC 22x0.4mm',
            'categoria': 'Insumos',
            'unidad_medida': 'ML',
            'costo_unitario': '450.00',
            'porcentaje_merma_defecto': '5.00',
            'proveedor': 'Placacentro',
            'observaciones': 'Contacto: Pedro +56911223344, Sucursal San Bernardo'
        })
        self.assertTrue(form.is_valid(), form.errors)
        material = form.save(commit=False)
        self.assertEqual(material.proveedor, 'Placacentro')
        self.assertEqual(material.observaciones, 'Contacto: Pedro +56911223344, Sucursal San Bernardo')

    def test_material_form_proveedores_desplegables(self):
        """Verifica que al instanciar MaterialForm con empresa, el campo proveedor despliegue los proveedores del taller."""
        from apps.core_auth.models import Empresa
        from apps.configuracion_base.models import Proveedor
        from apps.configuracion_base.forms import MaterialForm

        empresa = Empresa.objects.create(nombre_empresa="Taller Proveedores Test", rut_o_identificacion="55555555-5")
        Proveedor.objects.create(id_empresa=empresa, razon_social="Imperial S.A.")
        Proveedor.objects.create(id_empresa=empresa, razon_social="Dap Ducasse")

        form = MaterialForm(empresa=empresa)
        choices_values = [c[0] for c in form.fields['proveedor'].choices]
        self.assertIn('Imperial S.A.', choices_values)
        self.assertIn('Dap Ducasse', choices_values)


class OperarioFormTestCase(TestCase):
    """Pruebas unitarias para validación de correo electrónico en OperarioForm."""

    def test_operario_form_correo_valido(self):
        from apps.configuracion_base.forms import OperarioForm

        form = OperarioForm(data={
            'nombre_completo': 'Carlos Operario',
            'correo_electronico': 'CARLOS.OPERARIO@TALLER.CL ',
            'password': 'passwordseguro123',
            'rol': 'operario',
            'costo_hora': '6500.00'
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['correo_electronico'], 'carlos.operario@taller.cl')

    def test_operario_form_correo_formato_invalido(self):
        from apps.configuracion_base.forms import OperarioForm

        form = OperarioForm(data={
            'nombre_completo': 'Carlos Operario',
            'correo_electronico': 'carlos_sin_dominio_valido',
            'password': 'passwordseguro123',
            'rol': 'operario',
            'costo_hora': '6500.00'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('correo_electronico', form.errors)
        self.assertIn('correo electrónico válido', form.errors['correo_electronico'][0])

    def test_operario_form_roles_choices(self):
        from apps.configuracion_base.forms import OperarioForm
        form = OperarioForm()
        choices_labels = [c[1] for c in form.fields['rol'].choices]
        self.assertEqual(choices_labels, sorted(choices_labels))
        choices_keys = [c[0] for c in form.fields['rol'].choices]
        self.assertNotIn('superadmin_saas', choices_keys)
        self.assertIn('administrativo', choices_keys)

    def test_operario_form_costo_hora_formateado(self):
        from apps.configuracion_base.forms import OperarioForm
        from decimal import Decimal
        form = OperarioForm(data={
            'nombre_completo': 'Juan Perez',
            'correo_electronico': 'juan.perez@taller.cl',
            'password': 'password123',
            'rol': 'operario',
            'costo_hora': '$12.500'
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['costo_hora'], Decimal('12500.00'))

    def test_operario_form_correo_duplicado(self):
        from apps.configuracion_base.forms import OperarioForm
        from apps.core_auth.models import Usuario

        Usuario.objects.create_user(
            correo_electronico='existente@taller.cl',
            password='password123',
            nombre_completo='Usuario Existente',
            rol='operario'
        )

        form = OperarioForm(data={
            'nombre_completo': 'Otro Operario',
            'correo_electronico': 'EXISTENTE@TALLER.CL',
            'password': 'passwordseguro123',
            'rol': 'operario',
            'costo_hora': '6500.00'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('correo_electronico', form.errors)
        self.assertIn('ya se encuentra registrado', form.errors['correo_electronico'][0])


class ReestablecerPasswordAndToggleActivoTestCase(TestCase):
    """Pruebas unitarias para restablecimiento de contraseña y activación/desactivación de usuarios."""

    def setUp(self):
        from apps.core_auth.models import Empresa, Usuario

        self.empresa = Empresa.objects.create(nombre_empresa="Taller Test", rut_o_identificacion="11111111-1")
        
        self.dueno = Usuario.objects.create_user(
            correo_electronico="dueno@taller.cl",
            password="oldpassword123",
            nombre_completo="Pedro Dueño",
            rol="dueno_taller",
            id_empresa=self.empresa
        )

        self.jefe = Usuario.objects.create_user(
            correo_electronico="jefe@taller.cl",
            password="oldpassword123",
            nombre_completo="Juan Jefe",
            rol="jefe_taller",
            id_empresa=self.empresa
        )

        self.operario = Usuario.objects.create_user(
            correo_electronico="op@taller.cl",
            password="oldpassword123",
            nombre_completo="Mario Operario",
            rol="operario",
            id_empresa=self.empresa
        )

    def test_form_password_vacia_rechazada(self):
        from apps.configuracion_base.forms import ReestablecerPasswordForm

        form = ReestablecerPasswordForm(data={'password': '   '})
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

    def test_dueño_y_jefe_pueden_resetear_password(self):
        from django.urls import reverse

        # Login como Jefe de Taller
        self.client.login(correo_electronico="jefe@taller.cl", password="oldpassword123")
        url_reset = reverse('configuracion_base:operario_reset_password', args=[self.operario.id])

        # Enviar nueva contraseña válida
        response = self.client.post(url_reset, {'password': 'newpassword123'})
        self.assertEqual(response.status_code, 302)

        # Verificar que la contraseña cambió
        self.operario.refresh_from_db()
        self.assertTrue(self.operario.check_password('newpassword123'))

    def test_solo_dueno_puede_toggle_activo(self):
        from django.urls import reverse

        url_toggle = reverse('configuracion_base:operario_toggle_activo', args=[self.operario.id])

        # 1. Intentar con Jefe de Taller -> Debe denegar (restringido solo a dueño)
        self.client.login(correo_electronico="jefe@taller.cl", password="oldpassword123")
        response = self.client.post(url_toggle)
        self.assertEqual(response.status_code, 302)
        self.operario.refresh_from_db()
        self.assertTrue(self.operario.activo)  # Permanece activo

        # 2. Intentar con Dueño de Taller -> Debe permitir desactivar
        self.client.login(correo_electronico="dueno@taller.cl", password="oldpassword123")
        response = self.client.post(url_toggle)
        self.assertEqual(response.status_code, 302)
        self.operario.refresh_from_db()
        self.assertFalse(self.operario.activo)  # Ahora está inactivo

    def test_dueno_no_puede_desactivarse_a_si_mismo(self):
        from django.urls import reverse

        self.client.login(correo_electronico="dueno@taller.cl", password="oldpassword123")
        url_toggle = reverse('configuracion_base:operario_toggle_activo', args=[self.dueno.id])

        response = self.client.post(url_toggle)
        self.assertEqual(response.status_code, 302)
        self.dueno.refresh_from_db()
        self.assertTrue(self.dueno.activo)  # No cambia de estado

    def test_dueno_puede_editar_operario(self):
        from django.urls import reverse

        self.client.login(correo_electronico="dueno@taller.cl", password="oldpassword123")
        url_edit = reverse('configuracion_base:operario_update', args=[self.operario.id])

        # GET vista de edición
        res_get = self.client.get(url_edit)
        self.assertEqual(res_get.status_code, 200)

        # POST actualización de datos
        res_post = self.client.post(url_edit, {
            'nombre_completo': 'Mario Operario Modificado',
            'correo_electronico': 'mario.nuevo@taller.cl',
            'rol': 'jefe_taller',
            'costo_hora': '12500.00'
        })
        self.assertEqual(res_post.status_code, 302)

        self.operario.refresh_from_db()
        self.assertEqual(self.operario.nombre_completo, 'Mario Operario Modificado')
        self.assertEqual(self.operario.correo_electronico, 'mario.nuevo@taller.cl')
        self.assertEqual(self.operario.rol, 'jefe_taller')
        self.assertEqual(self.operario.costo_hora, Decimal('12500.00'))

    def test_operario_edit_form_initial_costo_hora_formateado(self):
        """Verifica que al instanciar OperarioEditForm con un costo de $40.000 se inicialice como '40.000' y no '40000.00'."""
        from apps.configuracion_base.forms import OperarioEditForm
        from django.urls import reverse

        self.operario.costo_hora = Decimal("40000.00")
        self.operario.save()

        form = OperarioEditForm(instance=self.operario)
        self.assertEqual(form.initial.get('costo_hora'), "40.000")

        self.client.login(correo_electronico="dueno@taller.cl", password="oldpassword123")
        url_edit = reverse('configuracion_base:operario_update', args=[self.operario.id])
        response = self.client.get(url_edit)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="40.000"')

    def test_operarios_list_formato_moneda(self):
        """Verifica que en /configuracion/operarios/ la tarifa costo/hora se muestre con el formato $xxx.xxx sin decimales."""
        from django.urls import reverse

        self.operario.costo_hora = Decimal("6500.00")
        self.operario.save()

        self.client.login(correo_electronico="dueno@taller.cl", password="oldpassword123")
        url_list = reverse('configuracion_base:operarios_list')
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, 200)

        # Debe contener $6.500 / hr y no $6500.00 / hr
        self.assertContains(response, "$6.500 / hr")
        self.assertNotContains(response, "$6500.00 / hr")


class InventarioTestCase(TestCase):
    """Pruebas unitarias para movimientos de bodega y ajuste de stock."""

    def setUp(self):
        from apps.core_auth.models import Empresa, Usuario

        self.empresa = Empresa.objects.create(nombre_empresa="Taller Bodega", rut_o_identificacion="33333333-3")
        self.usuario = Usuario.objects.create_user(
            correo_electronico="bodega@taller.cl",
            password="password123",
            nombre_completo="Juan Bodeguero",
            rol="dueno_taller",
            id_empresa=self.empresa
        )
        self.material = Material.objects.create(
            id_empresa=self.empresa,
            nombre="Plancha Terciado 18mm",
            categoria="Tableros",
            unidad_medida="Plancha",
            costo_unitario=Decimal("30000.00"),
            stock_actual=Decimal("10.00"),
            stock_minimo=Decimal("2.00")
        )

    def test_registrar_movimiento_inventario_ingreso(self):
        from apps.configuracion_base.services_inventario import registrar_movimiento_inventario

        mov = registrar_movimiento_inventario(
            material=self.material,
            cantidad=Decimal("5.00"),
            tipo_movimiento='INGRESO_INICIAL',
            usuario=self.usuario,
            observaciones="Carga inicial de bodega"
        )
        self.material.refresh_from_db()
        self.assertEqual(self.material.stock_actual, Decimal("15.00"))
        self.assertEqual(mov.stock_resultante, Decimal("15.00"))

    def test_registrar_movimiento_inventario_descuento(self):
        from apps.configuracion_base.services_inventario import registrar_movimiento_inventario

        mov = registrar_movimiento_inventario(
            material=self.material,
            cantidad=Decimal("-4.00"),
            tipo_movimiento='AJUSTE_MANUAL',
            usuario=self.usuario,
            observaciones="Ajuste por merma"
        )
        self.material.refresh_from_db()
        self.assertEqual(self.material.stock_actual, Decimal("6.00"))
        self.assertEqual(mov.stock_resultante, Decimal("6.00"))


class BancoFormTestCase(TestCase):
    """Pruebas unitarias para desplegables de tipo de cuenta en BancoForm y modelo Banco."""

    def test_banco_form_tipos_cuenta_validos(self):
        from apps.configuracion_base.forms import BancoForm
        from apps.configuracion_base.models import Banco

        tipos_esperados = ['Cuenta Corriente', 'Cuenta Vista', 'Cuenta Ahorro', 'Cuenta Nómina']
        for tipo in tipos_esperados:
            form = BancoForm(data={
                'nombre_banco': 'Banco de Chile',
                'codigo_sbif': '001',
                'numero_cuenta': '123456789',
                'tipo_cuenta': tipo,
                'activo': True
            })
            self.assertTrue(form.is_valid(), f"El tipo de cuenta '{tipo}' debería ser válido. Errores: {form.errors}")

    def test_banco_form_tipo_cuenta_invalido(self):
        from apps.configuracion_base.forms import BancoForm

        form = BancoForm(data={
            'nombre_banco': 'Banco de Chile',
            'codigo_sbif': '001',
            'numero_cuenta': '123456789',
            'tipo_cuenta': 'Tipo Invalido Desconocido',
            'activo': True
        })
        self.assertFalse(form.is_valid())
        self.assertIn('tipo_cuenta', form.errors)

    def test_banco_form_numero_cuenta_duplicado_mismo_taller(self):
        """Valida que no se pueda registrar un número de cuenta ya existente en el mismo taller."""
        from apps.core_auth.models import Empresa
        from apps.configuracion_base.models import Banco
        from apps.configuracion_base.forms import BancoForm

        empresa = Empresa.objects.create(nombre_empresa="Taller Banco 1", rut_o_identificacion="77777777-7")
        Banco.objects.create(
            id_empresa=empresa,
            nombre_banco="BancoEstado",
            numero_cuenta="9988776655",
            tipo_cuenta="Cuenta Vista"
        )

        form = BancoForm(
            data={
                'nombre_banco': 'Banco BCI',
                'codigo_sbif': '016',
                'numero_cuenta': ' 9988776655 ',  # Mismo número con espacios alrededor
                'tipo_cuenta': 'Cuenta Corriente',
                'activo': True
            },
            empresa=empresa
        )
        self.assertFalse(form.is_valid())
        self.assertIn('numero_cuenta', form.errors)
        self.assertIn('ya se encuentra registrado', form.errors['numero_cuenta'][0])

    def test_banco_form_numero_cuenta_mismo_numero_distinto_taller(self):
        """Valida que dos talleres diferentes sí puedan registrar el mismo número de cuenta."""
        from apps.core_auth.models import Empresa
        from apps.configuracion_base.models import Banco
        from apps.configuracion_base.forms import BancoForm

        empresa1 = Empresa.objects.create(nombre_empresa="Taller 1", rut_o_identificacion="88888888-8")
        empresa2 = Empresa.objects.create(nombre_empresa="Taller 2", rut_o_identificacion="99999999-9")

        Banco.objects.create(
            id_empresa=empresa1,
            nombre_banco="Banco de Chile",
            numero_cuenta="1122334455",
            tipo_cuenta="Cuenta Corriente"
        )

        form = BancoForm(
            data={
                'nombre_banco': 'Banco Santander',
                'codigo_sbif': '037',
                'numero_cuenta': '1122334455',
                'tipo_cuenta': 'Cuenta Corriente',
                'activo': True
            },
            empresa=empresa2
        )
        self.assertTrue(form.is_valid(), form.errors)


class ProveedorFormValidationTestCase(TestCase):
    """Pruebas unitarias para las validaciones de RUT (Módulo 11 y formato 12345678-9) y correo electrónico en ProveedorForm."""

    def test_proveedor_form_rut_y_correo_validos(self):
        from apps.configuracion_base.forms import ProveedorForm

        form = ProveedorForm(data={
            'razon_social': 'Imperial S.A.',
            'rut_o_identificacion': '14138344-2',
            'correo_contacto': 'ventas@imperial.cl',
            'nombre_contacto': 'Pedro Ejecutivo'
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['rut_o_identificacion'], '14138344-2')
        self.assertEqual(form.cleaned_data['correo_contacto'], 'ventas@imperial.cl')

    def test_proveedor_form_rut_formato_invalido_con_puntos(self):
        from apps.configuracion_base.forms import ProveedorForm

        form = ProveedorForm(data={
            'razon_social': 'Imperial S.A.',
            'rut_o_identificacion': '14.138.344-2',  # Con puntos -> debe fallar formato
            'correo_contacto': 'ventas@imperial.cl'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rut_o_identificacion', form.errors)
        self.assertIn('formato 12345678-9', form.errors['rut_o_identificacion'][0])

    def test_proveedor_form_rut_modulo11_invalido(self):
        from apps.configuracion_base.forms import ProveedorForm

        form = ProveedorForm(data={
            'razon_social': 'Imperial S.A.',
            'rut_o_identificacion': '14138344-9',  # DV debería ser 2 -> debe fallar Módulo 11
            'correo_contacto': 'ventas@imperial.cl'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rut_o_identificacion', form.errors)
        self.assertIn('Módulo 11', form.errors['rut_o_identificacion'][0])

    def test_proveedor_form_correo_invalido(self):
        from apps.configuracion_base.forms import ProveedorForm

        form = ProveedorForm(data={
            'razon_social': 'Imperial S.A.',
            'rut_o_identificacion': '14138344-2',
            'correo_contacto': 'correo_sin_dominio_valido'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('correo_contacto', form.errors)
        self.assertIn('formato usuario@dominio.com', form.errors['correo_contacto'][0])









