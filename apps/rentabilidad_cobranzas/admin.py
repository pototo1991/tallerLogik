from django.contrib import admin
from .models import PagoProyecto


@admin.register(PagoProyecto)
class PagoProyectoAdmin(admin.ModelAdmin):
    list_display = ('id_proyecto', 'concepto_hito', 'monto_pago', 'medio_pago', 'fecha_pago', 'comprobante_referencia', 'id_empresa')
    list_filter = ('concepto_hito', 'medio_pago', 'id_empresa')
    search_fields = ('id_proyecto__codigo_ot', 'comprobante_referencia')
