from django.urls import path
from .views import (
    DashboardRentabilidadView, ProyectoRentabilidadDetailView,
    CobranzasListView, PagoProyectoCreateView
)

app_name = 'rentabilidad_cobranzas'

urlpatterns = [
    path('rentabilidad/', DashboardRentabilidadView.as_view(), name='dashboard_rentabilidad'),
    path('rentabilidad/proyecto/<uuid:pk>/', ProyectoRentabilidadDetailView.as_view(), name='proyecto_rentabilidad_detail'),
    path('cobranzas/', CobranzasListView.as_view(), name='cobranzas_list'),
    path('cobranzas/registrar/', PagoProyectoCreateView.as_view(), name='pago_create'),
    path('cobranzas/registrar/<uuid:proyecto_pk>/', PagoProyectoCreateView.as_view(), name='pago_create_proyecto'),
]
