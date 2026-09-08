from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('apps.core_auth.urls')),
    path('configuracion/', include('apps.configuracion_base.urls')),
    path('cotizador/', include('apps.cotizador.urls')),
    path('proyectos/', include('apps.ordenes_trabajo.urls')),
    path('', include('apps.compras_gastos.urls')),
    path('', include('apps.rentabilidad_cobranzas.urls')),
    path('', RedirectView.as_view(url='/auth/dashboard/', permanent=False)),
]
