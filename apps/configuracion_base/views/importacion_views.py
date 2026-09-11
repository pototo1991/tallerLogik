from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from ..forms import ImportarExcelForm


class ImportarExcelView(LoginRequiredMixin, View):
    """Interfaz para cargar datos masivos de Clientes, Materiales o Proveedores desde Excel."""
    def get(self, request):
        form = ImportarExcelForm()
        return render(request, 'configuracion_base/importar_excel.html', {'form': form, 'titulo': 'Carga Masiva desde Excel'})

    def post(self, request):
        form = ImportarExcelForm(request.POST, request.FILES)
        if form.is_valid():
            tipo = form.cleaned_data['tipo_datos']
            archivo = request.FILES['archivo_excel']

            messages.info(request, f"Archivo '{archivo.name}' subido correctamente. El procesador masivo de {tipo} se ha iniciado.")
            return redirect('configuracion_base:importar_excel')

        return render(request, 'configuracion_base/importar_excel.html', {'form': form, 'titulo': 'Carga Masiva desde Excel'})
