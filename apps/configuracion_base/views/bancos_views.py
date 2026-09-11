from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from ..models import Banco
from ..forms import BancoForm


class BancoListView(LoginRequiredMixin, View):
    """Lista de bancos registrados por el taller."""
    def get(self, request):
        bancos = Banco.objects.filter(id_empresa=request.tenant)
        return render(request, 'configuracion_base/bancos_list.html', {'bancos': bancos})


class BancoCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = BancoForm(empresa=request.tenant)
        return render(request, 'configuracion_base/banco_form.html', {'form': form, 'titulo': 'Nuevo Banco'})

    def post(self, request):
        form = BancoForm(request.POST, empresa=request.tenant)
        if form.is_valid():
            banco = form.save(commit=False)
            banco.id_empresa = request.tenant
            banco.save()
            messages.success(request, f"Banco '{banco.nombre_banco}' registrado exitosamente.")
            return redirect('configuracion_base:bancos_list')
        return render(request, 'configuracion_base/banco_form.html', {'form': form, 'titulo': 'Nuevo Banco'})


class BancoUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        banco = get_object_or_404(Banco, pk=pk, id_empresa=request.tenant)
        form = BancoForm(instance=banco, empresa=request.tenant)
        return render(request, 'configuracion_base/banco_form.html', {'form': form, 'titulo': 'Editar Banco', 'banco': banco})

    def post(self, request, pk):
        banco = get_object_or_404(Banco, pk=pk, id_empresa=request.tenant)
        form = BancoForm(request.POST, instance=banco, empresa=request.tenant)
        if form.is_valid():
            form.save()
            messages.success(request, f"Banco '{banco.nombre_banco}' actualizado.")
            return redirect('configuracion_base:bancos_list')
        return render(request, 'configuracion_base/banco_form.html', {'form': form, 'titulo': 'Editar Banco', 'banco': banco})


class BancoDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        banco = get_object_or_404(Banco, pk=pk, id_empresa=request.tenant)
        nombre = banco.nombre_banco
        banco.delete()
        messages.success(request, f"Banco '{nombre}' eliminado.")
        return redirect('configuracion_base:bancos_list')
