import uuid
from decimal import Decimal
from django.db import models
from django.db.models import Max
from apps.core_auth.models import TenantAwareModel, SoftDeleteModel, Usuario


class Cliente(TenantAwareModel):
    """Directorio unificado de Clientes B2B/B2C del Taller."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    razon_social = models.CharField(max_length=255)
    rut_o_identificacion = models.CharField(max_length=50, blank=True, null=True)
    correo_general = models.EmailField(max_length=255, blank=True, null=True)
    telefono_general = models.CharField(max_length=50, blank=True, null=True)
    nombre_contacto = models.CharField(max_length=255)
    correo_contacto = models.EmailField(max_length=255, blank=True, null=True)
    telefono_contacto = models.CharField(max_length=255, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    comuna = models.CharField(max_length=100, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['razon_social']

    def __str__(self):
        return self.razon_social


class Proveedor(TenantAwareModel):
    """Directorio de Proveedores e Insumidores del Taller."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    razon_social = models.CharField(max_length=255, verbose_name='Razón Social / Nombre')
    rut_o_identificacion = models.CharField(max_length=50, blank=True, null=True, verbose_name='RUT / ID Fiscal')
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name='Dirección')
    comuna = models.CharField(max_length=100, blank=True, null=True, verbose_name='Comuna')
    ciudad = models.CharField(max_length=100, blank=True, null=True, verbose_name='Ciudad')
    nombre_contacto = models.CharField(max_length=255, blank=True, null=True, verbose_name='Persona de Contacto')
    telefono_contacto = models.CharField(max_length=50, blank=True, null=True, verbose_name='Teléfono')
    correo_contacto = models.EmailField(max_length=255, blank=True, null=True, verbose_name='Correo Electrónico')
    
    # Datos Bancarios para pagos/transferencias
    banco_nombre = models.CharField(max_length=100, blank=True, null=True, verbose_name='Banco')
    tipo_cuenta = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tipo de Cuenta')
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True, verbose_name='N° de Cuenta')
    
    observaciones = models.TextField(blank=True, null=True, verbose_name='Observaciones / Notas')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'proveedores'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['razon_social']

    def __str__(self):
        if self.rut_o_identificacion:
            return f"{self.razon_social} ({self.rut_o_identificacion})"
        return self.razon_social


class MaterialGlobal(SoftDeleteModel):
    """Catálogo Global de Materiales de Referencia (poblado por Scraping)."""
    CATEGORIAS = (
        ('Tableros', 'Tableros'),
        ('Maderas', 'Maderas'),
        ('Quincalleria', 'Quincallería'),
        ('Insumos', 'Insumos'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # SKU interno del sistema: generado automáticamente (TL-000001). Estable e inmutable.
    sku_interno = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name='SKU Interno'
    )

    # SKU real del proveedor (Imperial u otros). Clave de deduplicación del scraping.
    sku_proveedor = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        verbose_name='SKU Proveedor'
    )

    nombre = models.CharField(max_length=255)
    categoria = models.CharField(max_length=100, choices=CATEGORIAS)
    unidad_medida = models.CharField(max_length=50)  # Plancha, ML, Unidad, Caja, Par
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    proveedor = models.CharField(max_length=100, default='Imperial')
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'materiales_globales'
        verbose_name = 'Material Global'
        verbose_name_plural = 'Materiales Globales'
        ordering = ['categoria', 'nombre']

    def _generar_sku_interno(self):
        """Genera un SKU interno secuencial único: TL-000001, TL-000002, ..."""
        ultimo = MaterialGlobal.objects.aggregate(Max('sku_interno'))['sku_interno__max']
        if ultimo and ultimo.startswith('TL-'):
            try:
                siguiente = int(ultimo.split('-')[1]) + 1
            except (IndexError, ValueError):
                siguiente = 1
        else:
            siguiente = 1
        return f'TL-{siguiente:06d}'

    def save(self, *args, **kwargs):
        """Auto-genera sku_interno en la primera creación. Nunca se modifica después."""
        if not self.sku_interno:
            self.sku_interno = self._generar_sku_interno()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.sku_interno} | {self.sku_proveedor}] {self.nombre} - ${self.costo_unitario}"


class Material(TenantAwareModel):
    """Catálogo de Materiales e Insumos por unidades comerciales completas y control de bodega."""
    CATEGORIAS = (
        ('Tableros', 'Tableros'),
        ('Maderas', 'Maderas'),
        ('Quincalleria', 'Quincallería'),
        ('Insumos', 'Insumos'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=255)
    categoria = models.CharField(max_length=100, choices=CATEGORIAS)
    unidad_medida = models.CharField(max_length=50)  # Plancha, ML, Unidad, Caja, Par
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    porcentaje_merma_defecto = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))
    proveedor = models.CharField(max_length=100, blank=True, null=True, verbose_name='Proveedor')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Notas / Información de Contacto')


    # Inventario / Stock en Bodega
    stock_actual = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Stock Actual en Bodega')
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name='Stock Mínimo de Alerta')

    # Vinculación con Catálogo Global y sincronización
    material_global = models.ForeignKey(
        MaterialGlobal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materiales_talleres'
    )
    sku_proveedor = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    actualizacion_automatica = models.BooleanField(default=True)

    class Meta:
        db_table = 'materiales'
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'
        ordering = ['categoria', 'nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['id_empresa', 'sku_proveedor'],
                condition=models.Q(sku_proveedor__isnull=False),
                name='unique_tenant_sku'
            )
        ]

    def __str__(self):
        return f"{self.nombre} ({self.unidad_medida}) - ${self.costo_unitario} [Stock: {self.stock_actual}]"


class MovimientoInventario(TenantAwareModel):
    """Bitácora inmutable de entradas, salidas y ajustes de stock en bodega."""
    TIPOS_MOVIMIENTO = (
        ('INGRESO_INICIAL', 'Ingreso Inicial / Carga de Stock'),
        ('COMPRA_BODEGA', 'Compra para Stock en Bodega'),
        ('DESCUENTO_OT', 'Descuento por Asignación a Orden de Trabajo'),
        ('AJUSTE_MANUAL', 'Ajuste Manual de Inventario'),
        ('DEVOLUCION', 'Devolución de Proyecto a Bodega'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=50, choices=TIPOS_MOVIMIENTO)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, help_text='Positivo para entradas, Negativo para salidas')
    stock_resultante = models.DecimalField(max_digits=10, decimal_places=2)
    id_proyecto = models.ForeignKey('ordenes_trabajo.Proyecto', on_delete=models.SET_NULL, null=True, blank=True, related_name='movimientos_inventario')
    observaciones = models.TextField(blank=True, null=True)
    id_usuario = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='movimientos_inventario_registrados')
    fecha_movimiento = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'movimientos_inventario'
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha_movimiento']

    def __str__(self):
        return f"{self.get_tipo_movimiento_display()} - {self.id_material.nombre}: {self.cantidad} (Stock: {self.stock_resultante})"


class Banco(TenantAwareModel):
    """Mantenedor de Bancos de la empresa/taller."""
    TIPOS_CUENTA = (
        ('Cuenta Corriente', 'Cuenta Corriente'),
        ('Cuenta Vista', 'Cuenta Vista'),
        ('Cuenta Ahorro', 'Cuenta Ahorro'),
        ('Cuenta Nómina', 'Cuenta Nómina'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_banco = models.CharField(max_length=150, verbose_name='Nombre del Banco')
    codigo_sbif = models.CharField(max_length=20, blank=True, null=True, verbose_name='Código SBIF / Identificador')
    numero_cuenta = models.CharField(max_length=100, blank=True, null=True, verbose_name='N° de Cuenta Corriente / Vista')
    tipo_cuenta = models.CharField(max_length=50, choices=TIPOS_CUENTA, default='Cuenta Corriente', verbose_name='Tipo de Cuenta')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bancos'
        verbose_name = 'Banco'
        verbose_name_plural = 'Bancos'
        ordering = ['nombre_banco']
        constraints = [
            models.UniqueConstraint(
                fields=['id_empresa', 'numero_cuenta'],
                condition=models.Q(numero_cuenta__isnull=False) & ~models.Q(numero_cuenta=''),
                name='unique_tenant_banco_numero_cuenta'
            )
        ]

    def __str__(self):
        if self.numero_cuenta:
            return f"{self.nombre_banco} - {self.tipo_cuenta} ({self.numero_cuenta})"
        return self.nombre_banco


class ServicioTarifa(TenantAwareModel):
    """Tarifario maestro de servicios externos, fletes, traslados y montajes en obra."""
    CATEGORIAS = (
        ('Flete_Traslado', 'Flete y Traslado'),
        ('Montaje_Obra', 'Montaje en Obra'),
        ('Instalacion_Especial', 'Instalación Especial / Eléctrica'),
        ('Subcontrato', 'Subcontrato / Servicio Tercero'),
        ('Otro', 'Otro Servicio'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_servicio = models.CharField(max_length=255, verbose_name='Nombre del Servicio')
    categoria = models.CharField(max_length=100, choices=CATEGORIAS, default='Flete_Traslado', verbose_name='Categoría')
    unidad_medida = models.CharField(max_length=50, default='Global', verbose_name='Unidad de Medida (Global, Día, Hora, Viaje)')
    costo_base_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Costo Base Estimado')
    observaciones = models.TextField(blank=True, null=True, verbose_name='Notas / Descripción')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'servicios_tarifas'
        verbose_name = 'Servicio / Tarifa'
        verbose_name_plural = 'Servicios / Tarifas'
        ordering = ['categoria', 'nombre_servicio']

    def __str__(self):
        return f"{self.nombre_servicio} ({self.get_categoria_display()}) - ${self.costo_base_unitario} / {self.unidad_medida}"


