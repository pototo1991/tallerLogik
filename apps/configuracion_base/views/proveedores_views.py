from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from ..models import Proveedor
from ..forms import ProveedorForm
from apps.core_auth.models import AuditoriaLog


class ProveedorListView(LoginRequiredMixin, View):
    """Lista de proveedores del taller activo."""
    def get(self, request):
        proveedores = Proveedor.objects.filter(id_empresa=request.tenant)
        return render(request, 'configuracion_base/proveedores_list.html', {'proveedores': proveedores})


class ProveedorCreateView(LoginRequiredMixin, View):
    """Creación de nuevo proveedor."""
    def get(self, request):
        if not request.tenant:
            messages.warning(request, "Debes seleccionar primero una Empresa/Taller activa.")
            return redirect('core_auth:dashboard')
        form = ProveedorForm()
        return render(request, 'configuracion_base/proveedor_form.html', {'form': form, 'titulo': 'Nuevo Proveedor'})

    def post(self, request):
        if not request.tenant:
            messages.error(request, "No se puede crear un proveedor sin una Empresa/Taller activa.")
            return redirect('core_auth:dashboard')
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.id_empresa = request.tenant
            proveedor.save()

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='CREAR_PROVEEDOR',
                detalles=f'Proveedor {proveedor.razon_social} creado.',
                direccion_ip=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Proveedor '{proveedor.razon_social}' creado con éxito.")
            return redirect('configuracion_base:proveedores_list')
        return render(request, 'configuracion_base/proveedor_form.html', {'form': form, 'titulo': 'Nuevo Proveedor'})


class ProveedorUpdateView(LoginRequiredMixin, View):
    """Edición de proveedor existente."""
    def get(self, request, pk):
        proveedor = get_object_or_404(Proveedor, pk=pk, id_empresa=request.tenant)
        form = ProveedorForm(instance=proveedor)
        return render(request, 'configuracion_base/proveedor_form.html', {'form': form, 'titulo': 'Editar Proveedor', 'proveedor': proveedor})

    def post(self, request, pk):
        proveedor = get_object_or_404(Proveedor, pk=pk, id_empresa=request.tenant)
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, f"Proveedor '{proveedor.razon_social}' actualizado.")
            return redirect('configuracion_base:proveedores_list')
        return render(request, 'configuracion_base/proveedor_form.html', {'form': form, 'titulo': 'Editar Proveedor', 'proveedor': proveedor})


class ProveedorDeleteView(LoginRequiredMixin, View):
    """Borrado de proveedor."""
    def post(self, request, pk):
        proveedor = get_object_or_404(Proveedor, pk=pk, id_empresa=request.tenant)
        razon_social = proveedor.razon_social
        proveedor.delete()

        AuditoriaLog.objects.create(
            id_empresa=request.tenant,
            id_usuario=request.user,
            accion='BORRAR_PROVEEDOR',
            detalles=f'Proveedor {razon_social} eliminado.',
            direccion_ip=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Proveedor '{razon_social}' eliminado.")
        return redirect('configuracion_base:proveedores_list')
