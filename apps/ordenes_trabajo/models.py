import uuid
from decimal import Decimal
from django.db import models
from apps.core_auth.models import TenantAwareModel
from apps.configuracion_base.models import Cliente, Material
from apps.cotizador.models import Cotizacion


class Proyecto(TenantAwareModel):
    """Proyecto u Orden de Trabajo (OT) en producción en el taller."""
    ESTADOS = (
        ('planificado', 'Planificado'),
        ('corte', 'En Corte'),
        ('armado', 'En Armado'),
        ('laca_pintura', 'Laca y Pintura'),
        ('montaje', 'Montaje en Obra'),
        ('entregado', 'Entregado Conforme'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_cotizacion_origen = models.ForeignKey(Cotizacion, on_delete=models.RESTRICT, related_name='proyectos_generados')
    id_cliente = models.ForeignKey(Cliente, on_delete=models.RESTRICT, related_name='proyectos')
    codigo_ot = models.CharField(max_length=50)
    nombre_proyecto = models.CharField(max_length=255)
    estado = models.CharField(max_length=50, choices=ESTADOS, default='planificado')

    precio_cotizado = models.DecimalField(max_digits=12, decimal_places=2)
    costo_presupuestado_total = models.DecimalField(max_digits=12, decimal_places=2)
    margen_objetivo_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('35.00'))

    fecha_inicio_programada = models.DateField(null=True, blank=True)
    fecha_inicio_real = models.DateField(null=True, blank=True)
    fecha_fin_real = models.DateField(null=True, blank=True)
    fecha_compromiso_entrega = models.DateField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'proyectos'
        verbose_name = 'Proyecto / Orden de Trabajo'
        verbose_name_plural = 'Proyectos / Órdenes de Trabajo'
        ordering = ['-fecha_creacion']
        constraints = [
            models.UniqueConstraint(fields=['id_empresa', 'codigo_ot'], name='unique_ot_per_tenant')
        ]

    def __str__(self):
        return f"{self.codigo_ot} - {self.nombre_proyecto}"


class ItemProyecto(TenantAwareModel):
    """Ítem del BOM de producción en la Orden de Trabajo."""
    TIPOS = (
        ('Material', 'Material'),
        ('Mano_Obra', 'Mano de Obra'),
        ('Servicio_Tercero', 'Servicio Tercero'),
        ('Insumo', 'Insumo'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='items_produccion')
    id_material = models.ForeignKey(Material, on_delete=models.RESTRICT, null=True, blank=True)
    descripcion = models.CharField(max_length=255)
    tipo_item = models.CharField(max_length=50, choices=TIPOS)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal_costo = models.DecimalField(max_digits=12, decimal_places=2)
    agregado_rectificacion = models.BooleanField(default=False)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    # Control de Stock e Inventario reservado de Bodega
    cantidad_descontada_stock = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text='Cantidad resuelta desde stock de bodega')
    stock_descontado = models.BooleanField(default=False, help_text='Indica si ya se aplicó el descuento automático de inventario')

    class Meta:
        db_table = 'items_proyecto'
        verbose_name = 'Ítem de Producción'
        verbose_name_plural = 'Ítems de Producción'

    def save(self, *args, **kwargs):
        if not self.subtotal_costo:
            self.subtotal_costo = (self.cantidad * self.costo_unitario).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

