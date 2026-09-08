from django.urls import path
from .views import (
    CotizacionListView, CotizacionCreateView, CotizacionDetailView,
    ItemCotizacionCreateView, ItemCotizacionDeleteView,
    CotizacionClonarVersionView, CotizacionPDFView
)

app_name = 'cotizador'

urlpatterns = [
    path('', CotizacionListView.as_view(), name='cotizaciones_list'),
    path('crear/', CotizacionCreateView.as_view(), name='cotizacion_create'),
    path('<uuid:pk>/', CotizacionDetailView.as_view(), name='cotizacion_detail'),
    path('<uuid:cotizacion_pk>/item/agregar/', ItemCotizacionCreateView.as_view(), name='item_create'),
    path('<uuid:cotizacion_pk>/item/<uuid:item_pk>/eliminar/', ItemCotizacionDeleteView.as_view(), name='item_delete'),
    path('<uuid:pk>/clonar/', CotizacionClonarVersionView.as_view(), name='cotizacion_clonar'),
    path('<uuid:pk>/pdf/', CotizacionPDFView.as_view(), name='cotizacion_pdf'),
]
