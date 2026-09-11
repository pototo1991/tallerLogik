from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from ..models import ServicioTarifa
from ..forms import ServicioTarifaForm


class ServicioTarifaListView(LoginRequiredMixin, View):
    """Tarifario maestro de fletes, montajes y subcontratos."""
    def get(self, request):
        servicios = ServicioTarifa.objects.filter(id_empresa=request.tenant)
        return render(request, 'configuracion_base/servicios_list.html', {'servicios': servicios})


class ServicioTarifaCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = ServicioTarifaForm()
        return render(request, 'configuracion_base/servicio_form.html', {'form': form, 'titulo': 'Nuevo Servicio / Tarifa'})

    def post(self, request):
        form = ServicioTarifaForm(request.POST)
        if form.is_valid():
            servicio = form.save(commit=False)
            servicio.id_empresa = request.tenant
            servicio.save()
            messages.success(request, f"Servicio '{servicio.nombre_servicio}' añadido al tarifario.")
            return redirect('configuracion_base:servicios_list')
        return render(request, 'configuracion_base/servicio_form.html', {'form': form, 'titulo': 'Nuevo Servicio / Tarifa'})


class ServicioTarifaUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        servicio = get_object_or_404(ServicioTarifa, pk=pk, id_empresa=request.tenant)
        form = ServicioTarifaForm(instance=servicio)
        return render(request, 'configuracion_base/servicio_form.html', {'form': form, 'titulo': 'Editar Servicio / Tarifa', 'servicio': servicio})

    def post(self, request, pk):
        servicio = get_object_or_404(ServicioTarifa, pk=pk, id_empresa=request.tenant)
        form = ServicioTarifaForm(request.POST, instance=servicio)
        if form.is_valid():
            form.save()
            messages.success(request, f"Servicio '{servicio.nombre_servicio}' actualizado.")
            return redirect('configuracion_base:servicios_list')
        return render(request, 'configuracion_base/servicio_form.html', {'form': form, 'titulo': 'Editar Servicio / Tarifa', 'servicio': servicio})


class ServicioTarifaDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        servicio = get_object_or_404(ServicioTarifa, pk=pk, id_empresa=request.tenant)
        nombre = servicio.nombre_servicio
        servicio.delete()
        messages.success(request, f"Servicio '{nombre}' eliminado.")
        return redirect('configuracion_base:servicios_list')
