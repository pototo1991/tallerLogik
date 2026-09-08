import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core_auth.models import TenantAwareModel, Usuario
from apps.ordenes_trabajo.models import Proyecto


class PagoProyecto(TenantAwareModel):
    """Registro de abonos y pagos de clientes asociados a una Orden de Trabajo (OT)."""
    HITOS = (
        ('Anticipo_50', 'Anticipo 50%'),
        ('Avance_30', 'Avance 30%'),
        ('Saldo_Entrega_20', 'Saldo Entrega 20%'),
        ('Otro', 'Otro Abono / Pago Parcial'),
    )

    MEDIOS = (
        ('Transferencia', 'Transferencia Bancaria'),
        ('Efectivo', 'Efectivo'),
        ('Cheque', 'Cheque'),
        ('Tarjeta', 'Tarjeta Débito / Crédito'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_proyecto = models.ForeignKey(Proyecto, on_delete=models.RESTRICT, related_name='pagos_recibidos')
    concepto_hito = models.CharField(max_length=50, choices=HITOS)
    monto_pago = models.DecimalField(max_digits=12, decimal_places=2)
    medio_pago = models.CharField(max_length=50, choices=MEDIOS)
    fecha_pago = models.DateField(default=timezone.now)
    comprobante_referencia = models.CharField(max_length=100, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    id_usuario_registro = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='pagos_registrados')

    class Meta:
        db_table = 'pagos_proyecto'
        verbose_name = 'Pago / Abono de Proyecto'
        verbose_name_plural = 'Pagos / Abonos de Proyectos'
        ordering = ['-fecha_pago', '-fecha_registro']

    def __str__(self):
        return f"{self.id_proyecto.codigo_ot} - {self.get_concepto_hito_display()}: ${self.monto_pago}"
