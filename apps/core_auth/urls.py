from django.urls import path
from .views import CustomLoginView, CustomLogoutView, OnboardingTallerView, DashboardView, ToggleEmpresaEstadoView, VerLogsView

app_name = 'core_auth'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('onboarding/', OnboardingTallerView.as_view(), name='onboarding'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('empresa/<uuid:pk>/toggle-estado/', ToggleEmpresaEstadoView.as_view(), name='empresa_toggle_estado'),
    path('logs/', VerLogsView.as_view(), name='logs_viewer'),
]

