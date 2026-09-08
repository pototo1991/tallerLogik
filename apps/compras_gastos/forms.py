from django import forms
from .models import FacturaCompra, GastoProyecto, RegistroTiempo
from apps.ordenes_trabajo.models import Proyecto
from apps.core_auth.models import Usuario
from apps.configuracion_base.models import Proveedor


class FacturaCompraForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['id_proveedor'].queryset = Proveedor.objects.filter(id_empresa=empresa)
        self.fields['proveedor'].required = False

    class Meta:
        model = FacturaCompra
        fields = ['numero_factura', 'id_proveedor', 'proveedor', 'fecha_emision', 'monto_total_neto', 'forma_pago', 'banco_origen', 'observaciones']
        widgets = {
            'numero_factura': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'N° Boleta o Factura'}),
            'id_proveedor': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'proveedor': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ej. Sodimac / Imperial / Otro'}),
            'fecha_emision': forms.DateInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'type': 'date'}),
            'monto_total_neto': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.01', 'id': 'input-monto-total'}),
            'forma_pago': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'banco_origen': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ej. Banco de Chile / BCI'}),
            'observaciones': forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'rows': 2, 'placeholder': 'Notas sobre la compra...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        prov_obj = cleaned_data.get('id_proveedor')
        prov_txt = cleaned_data.get('proveedor')

        if prov_obj:
            cleaned_data['proveedor'] = prov_obj.razon_social
        elif not prov_txt or not prov_txt.strip():
            self.add_error('proveedor', 'Debes seleccionar un proveedor registrado o ingresar el nombre del proveedor.')

        return cleaned_data


class GastoProyectoDesgloseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['id_proyecto'].queryset = Proyecto.objects.filter(id_empresa=empresa)

    class Meta:
        model = GastoProyecto
        fields = ['id_proyecto', 'tipo_gasto', 'descripcion', 'monto_neto_asignado']
        widgets = {
            'id_proyecto': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'tipo_gasto': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'descripcion': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Detalle del insumo o flete'}),
            'monto_neto_asignado': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.01'}),
        }


class RegistroTiempoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['id_proyecto'].queryset = Proyecto.objects.filter(id_empresa=empresa)
            self.fields['id_usuario'].queryset = Usuario.objects.filter(id_empresa=empresa, activo=True)

    class Meta:
        model = RegistroTiempo
        fields = ['id_proyecto', 'id_usuario', 'etapa', 'horas_trabajadas']
        widgets = {
            'id_proyecto': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'id_usuario': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'etapa': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'horas_trabajadas': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.5', 'placeholder': 'Ej. 4.5'}),
        }
