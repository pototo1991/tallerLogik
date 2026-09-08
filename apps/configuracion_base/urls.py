from django.urls import path
from .views import (
    ClienteListView, ClienteCreateView, ClienteUpdateView, ClienteDeleteView,
    ProveedorListView, ProveedorCreateView, ProveedorUpdateView, ProveedorDeleteView,
    MaterialListView, MaterialCreateView, MaterialUpdateView, MaterialDeleteView,
    MaterialAjustarStockView, MaterialHistorialMovimientosView,
    OperarioListView, OperarioCreateView, OperarioUpdateView, OperarioResetPasswordView, OperarioToggleActivoView,
    MaterialGlobalBuscarView, MaterialImportarActionView,
    EjecutarScrapingManualView, ScrapingTaskStatusView
)

app_name = 'configuracion_base'

urlpatterns = [
    # Rutas de Clientes
    path('clientes/', ClienteListView.as_view(), name='clientes_list'),
    path('clientes/crear/', ClienteCreateView.as_view(), name='cliente_create'),
    path('clientes/<uuid:pk>/editar/', ClienteUpdateView.as_view(), name='cliente_update'),
    path('clientes/<uuid:pk>/eliminar/', ClienteDeleteView.as_view(), name='cliente_delete'),

    # Rutas de Proveedores
    path('proveedores/', ProveedorListView.as_view(), name='proveedores_list'),
    path('proveedores/crear/', ProveedorCreateView.as_view(), name='proveedor_create'),
    path('proveedores/<uuid:pk>/editar/', ProveedorUpdateView.as_view(), name='proveedor_update'),
    path('proveedores/<uuid:pk>/eliminar/', ProveedorDeleteView.as_view(), name='proveedor_delete'),

    # Rutas de Materiales
    path('materiales/', MaterialListView.as_view(), name='materiales_list'),
    path('materiales/crear/', MaterialCreateView.as_view(), name='material_create'),
    path('materiales/<uuid:pk>/editar/', MaterialUpdateView.as_view(), name='material_update'),
    path('materiales/<uuid:pk>/eliminar/', MaterialDeleteView.as_view(), name='material_delete'),
    path('materiales/<uuid:pk>/ajustar-stock/', MaterialAjustarStockView.as_view(), name='material_ajustar_stock'),
    path('materiales/<uuid:pk>/historial-stock/', MaterialHistorialMovimientosView.as_view(), name='material_historial_stock'),
    path('materiales/catalogo-global/', MaterialGlobalBuscarView.as_view(), name='materiales_global_buscar'),
    path('materiales/importar/<uuid:global_id>/', MaterialImportarActionView.as_view(), name='material_importar'),
    path('materiales/ejecutar-scraping/', EjecutarScrapingManualView.as_view(), name='materiales_ejecutar_scraping'),
    path('materiales/ejecutar-scraping/status/<str:task_id>/', ScrapingTaskStatusView.as_view(), name='scraping_task_status'),


    # Rutas de Personal / Operarios
    path('operarios/', OperarioListView.as_view(), name='operarios_list'),
    path('operarios/crear/', OperarioCreateView.as_view(), name='operario_create'),
    path('operarios/<uuid:pk>/editar/', OperarioUpdateView.as_view(), name='operario_update'),
    path('operarios/<uuid:pk>/reestablecer-password/', OperarioResetPasswordView.as_view(), name='operario_reset_password'),
    path('operarios/<uuid:pk>/toggle-activo/', OperarioToggleActivoView.as_view(), name='operario_toggle_activo'),
]

