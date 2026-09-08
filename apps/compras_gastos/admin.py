from django.contrib import admin
from .models import FacturaCompra, GastoProyecto, RegistroTiempo


class GastoProyectoInline(admin.TabularInline):
    model = GastoProyecto
    extra = 1


@admin.register(FacturaCompra)
class FacturaCompraAdmin(admin.ModelAdmin):
    list_display = ('numero_factura', 'proveedor', 'fecha_emision', 'monto_total_neto', 'id_usuario_registro', 'id_empresa')
    list_filter = ('fecha_emision', 'id_empresa')
    search_fields = ('numero_factura', 'proveedor')
    inlines = [GastoProyectoInline]


@admin.register(GastoProyecto)
class GastoProyectoAdmin(admin.ModelAdmin):
    list_display = ('id_proyecto', 'tipo_gasto', 'monto_neto_asignado', 'id_factura_compra', 'id_empresa')
    list_filter = ('tipo_gasto', 'id_empresa')
    search_fields = ('descripcion', 'id_proyecto__codigo_ot')


@admin.register(RegistroTiempo)
class RegistroTiempoAdmin(admin.ModelAdmin):
    list_display = ('id_proyecto', 'id_usuario', 'etapa', 'horas_trabajadas', 'costo_mano_obra_calculado', 'fecha_registro', 'id_empresa')
    list_filter = ('etapa', 'id_empresa')
    search_fields = ('id_usuario__nombre_completo', 'id_proyecto__codigo_ot')
