import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from .models import PagoProyecto
from .forms import PagoProyectoForm
from .services import calcular_rentabilidad_proyecto, obtener_metricas_globales_taller
from apps.ordenes_trabajo.models import Proyecto
from apps.core_auth.models import AuditoriaLog

logger = logging.getLogger('saas_taller')


class DashboardRentabilidadView(LoginRequiredMixin, View):
    """Dashboard consolidado de rentabilidad real vs. presupuestada y sobrecostos."""
    def get(self, request):
        metricas = obtener_metricas_globales_taller(request.tenant)
        return render(request, 'rentabilidad_cobranzas/dashboard_rentabilidad.html', {'metricas': metricas})


class ProyectoRentabilidadDetailView(LoginRequiredMixin, View):
    """Informe financiero detallado por proyecto / OT."""
    def get(self, request, pk):
        proyecto = get_object_or_404(Proyecto, pk=pk, id_empresa=request.tenant)
        metricas = calcular_rentabilidad_proyecto(proyecto)
        pagos = proyecto.pagos_recibidos.all().select_related('id_usuario_registro')
        gastos = proyecto.gastos.all().select_related('id_factura_compra')
        tiempos = proyecto.tiempos_registrados.all().select_related('id_usuario')

        context = {
            'metricas': metricas,
            'pagos': pagos,
            'gastos': gastos,
            'tiempos': tiempos,
        }
        return render(request, 'rentabilidad_cobranzas/proyecto_rentabilidad_detail.html', context)


class CobranzasListView(LoginRequiredMixin, View):
    """Reporte de gestión de cobranzas y abonos recibidos por cliente/proyecto."""
    def get(self, request):
        proyectos = Proyecto.objects.filter(id_empresa=request.tenant).select_related('id_cliente')
        proyectos_cobranza = []

        for p in proyectos:
            m = calcular_rentabilidad_proyecto(p)
            proyectos_cobranza.append(m)

        pagos_recientes = PagoProyecto.objects.filter(id_empresa=request.tenant).select_related('id_proyecto', 'id_usuario_registro')

        context = {
            'proyectos_cobranza': proyectos_cobranza,
            'pagos_recientes': pagos_recientes,
            'pago_form': PagoProyectoForm(empresa=request.tenant)
        }
        return render(request, 'rentabilidad_cobranzas/cobranzas_list.html', context)


class PagoProyectoCreateView(LoginRequiredMixin, View):
    """Registrar un pago/abono de cliente para una Orden de Trabajo."""
    def get(self, request, proyecto_pk=None):
        initial = {}
        if proyecto_pk:
            proyecto = get_object_or_404(Proyecto, pk=proyecto_pk, id_empresa=request.tenant)
            initial['id_proyecto'] = proyecto

        form = PagoProyectoForm(initial=initial, empresa=request.tenant)
        return render(request, 'rentabilidad_cobranzas/pago_form.html', {'form': form})

    def post(self, request, proyecto_pk=None):
        form = PagoProyectoForm(request.POST, empresa=request.tenant)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.id_empresa = request.tenant
            pago.id_usuario_registro = request.user
            pago.save()

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='REGISTRAR_PAGO_CLIENTE',
                detalles=f'Registrado pago de ${pago.monto_pago} ({pago.get_concepto_hito_display()}) para OT {pago.id_proyecto.codigo_ot}'
            )

            messages.success(request, f"Pago de ${pago.monto_pago} registrado para la OT {pago.id_proyecto.codigo_ot}.")
            return redirect('rentabilidad_cobranzas:cobranzas_list')

        return render(request, 'rentabilidad_cobranzas/pago_form.html', {'form': form})
