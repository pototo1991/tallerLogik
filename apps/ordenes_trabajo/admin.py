from django.contrib import admin
from .models import Proyecto, ItemProyecto


class ItemProyectoInline(admin.TabularInline):
    model = ItemProyecto
    extra = 1


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ('codigo_ot', 'nombre_proyecto', 'id_cliente', 'estado', 'precio_cotizado', 'costo_presupuestado_total', 'id_empresa')
    list_filter = ('estado', 'id_empresa')
    search_fields = ('codigo_ot', 'nombre_proyecto', 'id_cliente__razon_social')
    inlines = [ItemProyectoInline]


@admin.register(ItemProyecto)
class ItemProyectoAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'tipo_item', 'cantidad', 'costo_unitario', 'subtotal_costo', 'agregado_rectificacion', 'id_proyecto')
    list_filter = ('tipo_item', 'agregado_rectificacion', 'id_empresa')
    search_fields = ('descripcion',)
