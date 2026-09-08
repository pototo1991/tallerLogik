from django.contrib import admin
from .models import Cotizacion, ItemCotizacion


class ItemCotizacionInline(admin.TabularInline):
    model = ItemCotizacion
    extra = 1


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ('numero_cotizacion', 'version', 'titulo_propuesta', 'id_cliente', 'estado', 'costo_total_estimado', 'precio_venta_neto', 'id_empresa')
    list_filter = ('estado', 'version', 'id_empresa')
    search_fields = ('numero_cotizacion', 'titulo_propuesta', 'id_cliente__razon_social')
    inlines = [ItemCotizacionInline]


@admin.register(ItemCotizacion)
class ItemCotizacionAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'tipo_item', 'cantidad', 'costo_unitario', 'porcentaje_merma_aplicado', 'subtotal_costo', 'id_cotizacion')
    list_filter = ('tipo_item', 'id_empresa')
    search_fields = ('descripcion',)
