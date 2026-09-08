from django.contrib import admin
from .models import Cliente, Material


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('razon_social', 'rut_o_identificacion', 'nombre_contacto', 'correo_contacto', 'telefono_contacto', 'id_empresa')
    list_filter = ('id_empresa', 'ciudad')
    search_fields = ('razon_social', 'rut_o_identificacion', 'nombre_contacto')


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'unidad_medida', 'costo_unitario', 'porcentaje_merma_defecto', 'id_empresa')
    list_filter = ('categoria', 'id_empresa')
    search_fields = ('nombre', 'categoria')
