import uuid
import re
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core_auth.models import TenantAwareModel, Usuario
from apps.ordenes_trabajo.models import Proyecto


class FacturaCompra(TenantAwareModel):
    """Cabecera de Factura o Comprobante de Compra de Materiales/Insumos."""
    FORMAS_PAGO = (
        ('EFECTIVO', 'Efectivo'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
        ('TARJETA_DEBITO', 'Tarjeta de Débito'),
        ('TARJETA_CREDITO', 'Tarjeta de Crédito'),
        ('CHEQUE', 'Cheque'),
        ('CREDITO_PROVEEDOR', 'Crédito Proveedor / Cta. Corriente'),
        ('OTRO', 'Otro / Varios'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_factura = models.CharField(max_length=100)
    id_proveedor = models.ForeignKey('configuracion_base.Proveedor', on_delete=models.SET_NULL, null=True, blank=True, related_name='facturas_compra', verbose_name='Proveedor Registrado')
    proveedor = models.CharField(max_length=255, help_text='Nombre o razón social del proveedor')
    fecha_emision = models.DateField(default=timezone.now)
    monto_total_neto = models.DecimalField(max_digits=12, decimal_places=2)
    forma_pago = models.CharField(max_length=50, choices=FORMAS_PAGO, default='TRANSFERENCIA', verbose_name='Forma de Pago')
    banco_origen = models.CharField(max_length=100, blank=True, null=True, verbose_name='Banco / Institución Textual')
    id_banco = models.ForeignKey('configuracion_base.Banco', on_delete=models.SET_NULL, null=True, blank=True, related_name='facturas_compra', verbose_name='Banco Registrado')
    fecha_vencimiento_cheque = models.DateField(blank=True, null=True, verbose_name='Fecha Vencimiento Cheque / Plazo')
    numero_cheque = models.CharField(max_length=100, blank=True, null=True, verbose_name='N° de Cheque')
    observaciones = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    id_usuario_registro = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='facturas_registradas')

    class Meta:
        db_table = 'facturas_compra'
        verbose_name = 'Factura de Compra'
        verbose_name_plural = 'Facturas de Compra'
        ordering = ['-fecha_emision', '-fecha_registro']
        constraints = [
            models.UniqueConstraint(fields=['id_empresa', 'numero_factura', 'proveedor'], name='unique_factura_proveedor_per_tenant')
        ]

    @property
    def total_ots_distintas(self):
        """Retorna la cantidad de Órdenes de Trabajo (OTs) distintas a las que se distribuyó la factura."""
        return self.gastos_distribuidos.values('id_proyecto').distinct().count()

    @property
    def ots_afectadas(self):
        """Retorna la lista de códigos de las OTs distintas asociadas a esta factura."""
        codes = list(self.gastos_distribuidos.filter(id_proyecto__isnull=False).values_list('id_proyecto__codigo_ot', flat=True).distinct())
        return codes

    def __str__(self):
        return f"Factura {self.numero_factura} - {self.proveedor} (${self.monto_total_neto})"


class GastoProyecto(TenantAwareModel):
    """Desglose de monto neto de una factura asignado a un proyecto u OT en producción."""
    TIPOS_GASTO = (
        ('Material', 'Material'),
        ('Ferreteria_Imprevista', 'Ferretería Imprevista'),
        ('Flete', 'Flete'),
        ('Subcontrato', 'Subcontrato'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_factura_compra = models.ForeignKey(FacturaCompra, on_delete=models.CASCADE, related_name='gastos_distribuidos')
    id_proyecto = models.ForeignKey(Proyecto, on_delete=models.RESTRICT, related_name='gastos')
    id_item_proyecto = models.ForeignKey('ordenes_trabajo.ItemProyecto', on_delete=models.SET_NULL, null=True, blank=True, related_name='gastos')
    descripcion = models.CharField(max_length=255)
    tipo_gasto = models.CharField(max_length=50, choices=TIPOS_GASTO)
    monto_neto_asignado = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_gasto = models.DateTimeField(auto_now_add=True)
    id_usuario_registro = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='gastos_registrados')

    class Meta:
        db_table = 'gastos_proyecto'
        verbose_name = 'Gasto Distribuido a Proyecto'
        verbose_name_plural = 'Gastos Distribuidos a Proyectos'

    @property
    def items_desglosados(self):
        """
        Si la descripción contiene '/', separa los distintos ítems.
        Para cada ítem extrae su descripción textual y su cantidad correspondiente.
        """
        if not self.descripcion:
            return [{'descripcion': '', 'cantidad': '1'}]

        parts = [p.strip() for p in self.descripcion.split('/') if p.strip()]
        if not parts:
            return [{'descripcion': self.descripcion, 'cantidad': '1'}]

        desglose = []
        for part in parts:
            matches = re.findall(
                r'CANT[\.\s:]*(\d+(?:[.,]\d+)?(?:\s*(?:MTS|LT|L|UND|UNID|M2|ML|KG|PCS|PARES|UND))?)',
                part,
                re.IGNORECASE
            )
            if matches:
                cant_str = ', '.join([m.strip() for m in matches])
            else:
                cant_str = '1'

            desglose.append({
                'descripcion': part,
                'cantidad': cant_str
            })
        return desglose

    @property
    def cantidad_extraida(self):
        """Extrae la cantidad o volumen desde el texto de la descripción del gasto."""
        items = self.items_desglosados
        return ', '.join([item['cantidad'] for item in items])

    def __str__(self):
        return f"{self.id_proyecto.codigo_ot}: ${self.monto_neto_asignado} ({self.tipo_gasto})"


class RegistroTiempo(TenantAwareModel):
    """Imputación manual de horas trabajadas por operario (Mano de Obra Directa - MOD)."""
    ETAPAS = (
        ('Corte', 'Corte'),
        ('Armado', 'Armado'),
        ('Laca_Pintura', 'Laca y Pintura'),
        ('Montaje', 'Montaje'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_proyecto = models.ForeignKey(Proyecto, on_delete=models.RESTRICT, related_name='tiempos_registrados')
    id_usuario = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='horas_computadas')
    etapa = models.CharField(max_length=100, choices=ETAPAS)
    horas_trabajadas = models.DecimalField(max_digits=10, decimal_places=2)
    costo_mano_obra_calculado = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='tiempos_ingresados')

    class Meta:
        db_table = 'registros_tiempo'
        verbose_name = 'Registro de Tiempo (MOD)'
        verbose_name_plural = 'Registros de Tiempo (MOD)'
        ordering = ['-fecha_registro']

    def save(self, *args, **kwargs):
        if not self.costo_mano_obra_calculado:
            self.costo_mano_obra_calculado = (self.horas_trabajadas * self.id_usuario.costo_hora).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)
