from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from ..models import Cliente
from ..forms import ClienteForm
from apps.core_auth.models import AuditoriaLog


class ClienteListView(LoginRequiredMixin, View):
    """Lista de clientes del taller activo."""
    def get(self, request):
        clientes = Cliente.objects.filter(id_empresa=request.tenant)
        return render(request, 'configuracion_base/clientes_list.html', {'clientes': clientes})


class ClienteCreateView(LoginRequiredMixin, View):
    """Creación de nuevo cliente con soporte para HTMX modal/fragmento."""
    def get(self, request):
        if not request.tenant:
            messages.warning(request, "Como Superadministrador Global del SaaS, debes registrar o seleccionar primero una Empresa/Taller (Nivel 2) para gestionar sus clientes.")
            return redirect('core_auth:dashboard')
        form = ClienteForm()
        return render(request, 'configuracion_base/cliente_form.html', {'form': form, 'titulo': 'Nuevo Cliente'})

    def post(self, request):
        if not request.tenant:
            messages.error(request, "No se puede crear un cliente sin una Empresa/Taller activa asociadas.")
            return redirect('core_auth:dashboard')
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.id_empresa = request.tenant
            cliente.save()

            AuditoriaLog.objects.create(
                id_empresa=request.tenant,
                id_usuario=request.user,
                accion='CREAR_CLIENTE',
                detalles=f'Cliente {cliente.razon_social} creado.',
                direccion_ip=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Cliente '{cliente.razon_social}' creado con éxito.")
            return redirect('configuracion_base:clientes_list')
        return render(request, 'configuracion_base/cliente_form.html', {'form': form, 'titulo': 'Nuevo Cliente'})


class ClienteUpdateView(LoginRequiredMixin, View):
    """Edición de cliente existente."""
    def get(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk, id_empresa=request.tenant)
        form = ClienteForm(instance=cliente)
        return render(request, 'configuracion_base/cliente_form.html', {'form': form, 'titulo': 'Editar Cliente', 'cliente': cliente})

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk, id_empresa=request.tenant)
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cliente '{cliente.razon_social}' actualizado.")
            return redirect('configuracion_base:clientes_list')
        return render(request, 'configuracion_base/cliente_form.html', {'form': form, 'titulo': 'Editar Cliente', 'cliente': cliente})


class ClienteDeleteView(LoginRequiredMixin, View):
    """Borrado lógico de cliente."""
    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk, id_empresa=request.tenant)
        razon_social = cliente.razon_social
        cliente.delete()

        AuditoriaLog.objects.create(
            id_empresa=request.tenant,
            id_usuario=request.user,
            accion='BORRAR_CLIENTE',
            detalles=f'Cliente {razon_social} eliminado lógicamente.',
            direccion_ip=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Cliente '{razon_social}' eliminado.")
        return redirect('configuracion_base:clientes_list')
