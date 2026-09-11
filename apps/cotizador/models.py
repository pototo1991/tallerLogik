import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db import models
from django.utils import timezone
from apps.core_auth.models import TenantAwareModel
from apps.configuracion_base.models import Cliente, Material


class Cotizacion(TenantAwareModel):
    """Cotización comercial con control de versiones (v1, v2) y margen sobre venta."""
    ESTADOS = (
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada al Cliente'),
        ('aprobada', 'Aprobada (Convertida a OT)'),
        ('rechazada', 'Rechazada'),
        ('expirada', 'Expirada'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_cliente = models.ForeignKey(Cliente, on_delete=models.RESTRICT, related_name='cotizaciones')
    numero_cotizacion = models.CharField(max_length=50)
    version = models.IntegerField(default=1)
    titulo_propuesta = models.CharField(max_length=255)

    # Costos estimados desglosados
    costo_materiales_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    costo_mano_obra_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    costo_servicios_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    costo_indirecto_cif_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    costo_total_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Cálculo de Margen sobre Venta: Precio = Costo / (1 - (Margen% / 100))
    margen_objetivo_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('35.00'))
    precio_venta_neto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    estado = models.CharField(max_length=50, choices=ESTADOS, default='borrador')
    dias_validez = models.IntegerField(default=15)
    fecha_inicio_estimada = models.DateField(default=timezone.now, verbose_name="Fecha de Inicio Estimada")
    fecha_entrega_manual = models.DateField(null=True, blank=True, verbose_name="Fecha de Entrega Fija/Prometida")
    notas_condiciones = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    @property
    def dias_mano_obra_estimados(self):
        """Calcula el total de días laborables acumulados por los ítems de mano de obra (8 hrs = 1 día)."""
        hrs_mo = self.items.filter(tipo_item='Mano_Obra').aggregate(total=models.Sum('cantidad'))['total'] or Decimal('0.00')
        return int((hrs_mo / Decimal('8.00')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

    @property
    def fecha_inicio_proyecto(self):
        """Retorna la fecha de inicio estimada, o en su defecto la fecha de creación."""
        if self.fecha_inicio_estimada:
            return self.fecha_inicio_estimada
        if self.fecha_creacion:
            return self.fecha_creacion.date()
        return timezone.now().date()

    @property
    def monto_margen_estimado(self):
        """Retorna el monto estimado de utilidad/margen comercial en pesos (Precio Venta Neto - Costo Total)."""
        if self.precio_venta_neto and self.costo_total_estimado:
            return max(Decimal('0.00'), self.precio_venta_neto - self.costo_total_estimado)
        return Decimal('0.00')

    @property
    def fecha_entrega_sugerida(self):
        """
        Retorna la fecha de entrega fija si se estableció manualmente.
        De lo contrario, calcula la fecha sugerida = fecha_inicio + días_mano_obra_estimados.
        """
        if self.fecha_entrega_manual:
            return self.fecha_entrega_manual
        return self.fecha_inicio_proyecto + timedelta(days=self.dias_mano_obra_estimados)

    class Meta:
        db_table = 'cotizaciones'
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'
        ordering = ['-fecha_creacion', 'version']
        constraints = [
            models.UniqueConstraint(fields=['id_empresa', 'numero_cotizacion', 'version'], name='unique_cotizacion_per_tenant')
        ]

    def __str__(self):
        return f"{self.numero_cotizacion} (v{self.version}) - {self.titulo_propuesta}"

    def calcular_totales(self, nuevo_precio_venta=None):
        """Suma los componentes de costo y calcula el precio de venta según el margen sobre venta, o recalcula el margen si se provee un precio."""
        self.costo_total_estimado = (
            self.costo_materiales_estimado +
            self.costo_mano_obra_estimado +
            self.costo_servicios_estimado +
            self.costo_indirecto_cif_estimado
        )

        if nuevo_precio_venta is not None:
            try:
                precio = Decimal(str(nuevo_precio_venta))
                if precio > Decimal('0.00'):
                    self.precio_venta_neto = precio.quantize(Decimal('0.01'))
                    margen = ((self.precio_venta_neto - self.costo_total_estimado) / self.precio_venta_neto) * Decimal('100.00')
                    if margen >= Decimal('100.00'):
                        margen = Decimal('99.99')
                    self.margen_objetivo_pct = margen.quantize(Decimal('0.01'))
                else:
                    self.precio_venta_neto = Decimal('0.00')
                    self.margen_objetivo_pct = Decimal('0.00')
            except (ValueError, TypeError, ArithmeticError):
                pass
        else:
            # Margen sobre venta: P = C / (1 - M)
            margen = self.margen_objetivo_pct or Decimal('0.00')
            if margen >= Decimal('100.00'):
                margen = Decimal('99.99')
            factor_margen = Decimal('1.00') - (margen / Decimal('100.00'))

            if factor_margen > Decimal('0.00'):
                self.precio_venta_neto = (self.costo_total_estimado / factor_margen).quantize(Decimal('0.01'))
            else:
                self.precio_venta_neto = self.costo_total_estimado
        self.save()


class ItemCotizacion(TenantAwareModel):
    """Ítem de costo que compone el presupuesto comercial."""
    TIPOS = (
        ('Material', 'Material'),
        ('Mano_Obra', 'Mano de Obra'),
        ('Servicio_Tercero', 'Servicio Tercero'),
        ('Insumo', 'Insumo'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name='items')
    id_material = models.ForeignKey(Material, on_delete=models.RESTRICT, null=True, blank=True)
    descripcion = models.CharField(max_length=255)
    tipo_item = models.CharField(max_length=50, choices=TIPOS, default='Material')
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    porcentaje_merma_aplicado = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    subtotal_costo = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'items_cotizacion'
        verbose_name = 'Ítem de Cotización'
        verbose_name_plural = 'Ítems de Cotización'

    def save(self, *args, **kwargs):
        if not self.tipo_item:
            self.tipo_item = 'Material'
        if self.porcentaje_merma_aplicado is None:
            self.porcentaje_merma_aplicado = Decimal('0.00')
        factor_merma = Decimal('1.00') + (self.porcentaje_merma_aplicado / Decimal('100.00'))
        self.subtotal_costo = ((self.cantidad * self.costo_unitario) * factor_merma).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
