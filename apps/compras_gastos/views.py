import logging
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import ValidationError

from .models import FacturaCompra, GastoProyecto, RegistroTiempo
from .forms import FacturaCompraForm, GastoProyectoDesgloseForm, RegistroTiempoForm
from .services import registrar_factura_y_distribuir_gastos
from apps.ordenes_trabajo.models import Proyecto
from apps.core_auth.models import AuditoriaLog

logger = logging.getLogger('saas_taller')


class FacturaCompraListView(LoginRequiredMixin, View):
    """Lista de facturas de compra registradas."""
    def get(self, request):
        facturas = FacturaCompra.objects.filter(id_empresa=request.tenant).select_related('id_usuario_registro').prefetch_related('gastos_distribuidos__id_proyecto')
        return render(request, 'compras_gastos/facturas_list.html', {'facturas': facturas})


class FacturaCompraCreateView(LoginRequiredMixin, View):
    """Vista web responsive para ingreso de facturas y desglose por proyecto con cuadratura."""
    def get(self, request):
        header_form = FacturaCompraForm(empresa=request.tenant)
        desglose_form = GastoProyectoDesgloseForm(empresa=request.tenant)
        proyectos = Proyecto.objects.filter(id_empresa=request.tenant, estado__in=['planificado', 'corte', 'armado', 'laca_pintura', 'montaje'])

        context = {
            'header_form': header_form,
            'desglose_form': desglose_form,
            'proyectos': proyectos,
        }
        return render(request, 'compras_gastos/factura_form.html', context)

    def post(self, request):
        header_form = FacturaCompraForm(request.POST, empresa=request.tenant)

        # Capturar listas dinámicas de desgloses enviadas por el formulario
        proyectos_ids = request.POST.getlist('desglose_proyecto_id')
        items_ids = request.POST.getlist('desglose_item_id')
        tipos_gasto = request.POST.getlist('desglose_tipo_gasto')
        descripciones = request.POST.getlist('desglose_descripcion')
        montos = request.POST.getlist('desglose_monto')

        desgloses_list = []
        for i in range(len(proyectos_ids)):
            proyecto_id = proyectos_ids[i]
            monto_val = montos[i] if i < len(montos) else '0'
            try:
                monto_dec = Decimal(monto_val)
            except (ValueError, TypeError):
                monto_dec = Decimal('0.00')

            if proyecto_id and monto_dec > 0:
                try:
                    proyecto_obj = Proyecto.objects.get(id=proyecto_id, id_empresa=request.tenant)
                    item_id = items_ids[i] if i < len(items_ids) else ''
                    desgloses_list.append({
                        'proyecto': proyecto_obj,
                        'item_id': item_id if item_id else None,
                        'tipo_gasto': tipos_gasto[i] if i < len(tipos_gasto) else 'Material',
                        'descripcion': descripciones[i] if i < len(descripciones) else '',
                        'monto_neto_asignado': monto_dec
                    })
                except (Proyecto.DoesNotExist, ValueError):
                    continue

        if header_form.is_valid():
            try:
                factura_data = header_form.cleaned_data
                factura = registrar_factura_y_distribuir_gastos(factura_data, desgloses_list, request.user)
                messages.success(request, f"Factura '{factura.numero_factura}' de {factura.proveedor} registrada exitosamente.")
                return redirect('compras_gastos:facturas_list')
            except ValidationError as e:
                messages.error(request, e.message)
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")

        context = {
            'header_form': header_form,
            'desglose_form': GastoProyectoDesgloseForm(empresa=request.tenant),
            'proyectos': Proyecto.objects.filter(id_empresa=request.tenant),
        }
        return render(request, 'compras_gastos/factura_form.html', context)


class FacturaCompraDetailView(LoginRequiredMixin, View):
    """Detalle de factura de compra y gastos asignados."""
    def get(self, request, pk):
        factura = get_object_or_404(FacturaCompra, pk=pk, id_empresa=request.tenant)
        gastos = factura.gastos_distribuidos.all().select_related('id_proyecto', 'id_proyecto__id_cliente', 'id_item_proyecto')
        return render(request, 'compras_gastos/factura_detail.html', {'factura': factura, 'gastos': gastos})


class RegistroTiempoImputarView(LoginRequiredMixin, View):
    """Formulario ágil para que el Jefe de Taller impute horas trabajadas (MOD)."""
    def get(self, request):
        form = RegistroTiempoForm(empresa=request.tenant)
        return render(request, 'compras_gastos/tiempos_imputar.html', {'form': form})

    def post(self, request):
        form = RegistroTiempoForm(request.POST, empresa=request.tenant)
        if form.is_valid():
            registro = form.save(commit=False)
            registro.id_empresa = request.tenant
            registro.registrado_por = request.user
            registro.save()

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='IMPUTAR_TIEMPO_MOD',
                detalles=f'Imputadas {registro.horas_trabajadas} hrs a {registro.id_usuario.nombre_completo} en OT {registro.id_proyecto.codigo_ot}'
            )

            messages.success(request, f"Imputación de {registro.horas_trabajadas} hrs para '{registro.id_usuario.nombre_completo}' registrada con éxito.")
            return redirect('compras_gastos:tiempos_list')

        return render(request, 'compras_gastos/tiempos_imputar.html', {'form': form})


class RegistroTiempoListView(LoginRequiredMixin, View):
    """Historial de horas trabajadas (MOD) imputadas por proyecto."""
    def get(self, request):
        tiempos = RegistroTiempo.objects.filter(id_empresa=request.tenant).select_related('id_proyecto', 'id_usuario', 'registrado_por')
        return render(request, 'compras_gastos/tiempos_list.html', {'tiempos': tiempos})
