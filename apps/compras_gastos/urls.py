from django.urls import path
from .views import (
    FacturaCompraListView, FacturaCompraCreateView, FacturaCompraDetailView,
    RegistroTiempoImputarView, RegistroTiempoListView
)

app_name = 'compras_gastos'

urlpatterns = [
    path('compras/', FacturaCompraListView.as_view(), name='facturas_list'),
    path('compras/registrar/', FacturaCompraCreateView.as_view(), name='factura_create'),
    path('compras/<uuid:pk>/', FacturaCompraDetailView.as_view(), name='factura_detail'),
    path('tiempos/', RegistroTiempoListView.as_view(), name='tiempos_list'),
    path('tiempos/imputar/', RegistroTiempoImputarView.as_view(), name='tiempos_imputar'),
]
