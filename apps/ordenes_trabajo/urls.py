from django.urls import path
from .views import (
    AprobarCotizacionView, ProyectoListView, ProyectoDetailView,
    ItemProyectoRectificacionCreateView, ProyectoCambiarEstadoView,
    ProyectoItemsAPIView, AsignarBodegaItemProyectoView
)

app_name = 'ordenes_trabajo'

urlpatterns = [
    path('', ProyectoListView.as_view(), name='proyectos_list'),
    path('<uuid:pk>/', ProyectoDetailView.as_view(), name='proyecto_detail'),
    path('aprobar-cotizacion/<uuid:cotizacion_pk>/', AprobarCotizacionView.as_view(), name='aprobar_cotizacion'),
    path('<uuid:proyecto_pk>/rectificacion/agregar/', ItemProyectoRectificacionCreateView.as_view(), name='rectificacion_create'),
    path('<uuid:pk>/cambiar-estado/', ProyectoCambiarEstadoView.as_view(), name='proyecto_cambiar_estado'),
    path('items/<uuid:item_pk>/asignar-bodega/', AsignarBodegaItemProyectoView.as_view(), name='item_asignar_bodega'),
    path('api/proyectos/<uuid:proyecto_id>/items/', ProyectoItemsAPIView.as_view(), name='api_proyecto_items'),
]

