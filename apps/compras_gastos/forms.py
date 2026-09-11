from django import forms
from .models import FacturaCompra, GastoProyecto, RegistroTiempo
from apps.ordenes_trabajo.models import Proyecto
from apps.core_auth.models import Usuario
from apps.configuracion_base.models import Proveedor, Banco


class FacturaCompraForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['id_proveedor'].queryset = Proveedor.objects.filter(id_empresa=empresa)
            self.fields['id_banco'].queryset = Banco.objects.filter(id_empresa=empresa, activo=True)
        self.fields['proveedor'].required = False
        self.fields['id_banco'].required = False
        self.fields['fecha_vencimiento_cheque'].required = False
        self.fields['numero_cheque'].required = False

    class Meta:
        model = FacturaCompra
        fields = [
            'numero_factura', 'id_proveedor', 'proveedor', 'fecha_emision',
            'monto_total_neto', 'forma_pago', 'id_banco', 'banco_origen',
            'fecha_vencimiento_cheque', 'numero_cheque', 'observaciones'
        ]
        widgets = {
            'numero_factura': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'N° Boleta o Factura'}),
            'id_proveedor': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'proveedor': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ej. Sodimac / Imperial / Otro'}),
            'fecha_emision': forms.DateInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'type': 'date'}),
            'monto_total_neto': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.01', 'id': 'input-monto-total'}),
            'forma_pago': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'id': 'id_forma_pago'}),
            'id_banco': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'id': 'id_id_banco'}),
            'banco_origen': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Banco no registrado: Ej. Banco de Chile / BCI'}),
            'fecha_vencimiento_cheque': forms.DateInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'type': 'date', 'id': 'id_fecha_vencimiento_cheque'}),
            'numero_cheque': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'N° de Cheque (Ej. 00012345)', 'id': 'id_numero_cheque'}),
            'observaciones': forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'rows': 2, 'placeholder': 'Notas sobre la compra...'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        prov_obj = cleaned_data.get('id_proveedor')
        prov_txt = cleaned_data.get('proveedor')
        forma_pago = cleaned_data.get('forma_pago')
        numero_cheque = cleaned_data.get('numero_cheque')

        if prov_obj:
            cleaned_data['proveedor'] = prov_obj.razon_social
        elif not prov_txt or not str(prov_txt).strip():
            self.add_error('id_proveedor', 'Debes seleccionar un proveedor registrado.')

        if forma_pago == 'CHEQUE' and not numero_cheque:
            self.add_error('numero_cheque', 'Debes ingresar el número de cheque utilizado.')

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
