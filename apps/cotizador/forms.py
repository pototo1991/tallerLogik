from decimal import Decimal
from django import forms
from .models import Cotizacion, ItemCotizacion
from apps.configuracion_base.models import Cliente, Material


class IntegerNumberInput(forms.NumberInput):
    def format_value(self, value):
        if value is None or value == '':
            return ''
        try:
            return str(int(float(value)))
        except (ValueError, TypeError):
            return str(value)


class CotizacionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['id_cliente'].queryset = Cliente.objects.filter(id_empresa=empresa)
        self.fields['fecha_entrega_manual'].required = False
        self.fields['fecha_inicio_estimada'].required = False

    class Meta:
        model = Cotizacion
        fields = ['id_cliente', 'titulo_propuesta', 'margen_objetivo_pct', 'dias_validez', 'fecha_inicio_estimada', 'fecha_entrega_manual', 'costo_indirecto_cif_estimado', 'notas_condiciones']
        widgets = {
            'id_cliente': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'titulo_propuesta': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ej. Cocina Isla Madera Encina Mueble Bajo'}),
            'margen_objetivo_pct': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.01'}),
            'dias_validez': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'fecha_inicio_estimada': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'fecha_entrega_manual': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'costo_indirecto_cif_estimado': IntegerNumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '1'}),
            'notas_condiciones': forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'rows': 3, 'placeholder': 'Condiciones comerciales, forma de pago (50% anticipo), tiempos de entrega...'}),
        }


def clean_currency_string(val):
    if not val or not str(val).strip():
        return None
    val_str = str(val).strip()
    if ',' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif val_str.count('.') > 1:
        val_str = val_str.replace('.', '')
    elif val_str.count('.') == 1:
        parts = val_str.split('.')
        if len(parts[1]) == 3 and len(parts[0]) <= 3:
            val_str = val_str.replace('.', '')
    return Decimal(val_str)


class CotizacionHeaderForm(forms.ModelForm):
    precio_venta_neto = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        self.fields['fecha_entrega_manual'].required = False
        self.fields['fecha_inicio_estimada'].required = False
        self.fields['precio_venta_neto'].required = False

    def clean_precio_venta_neto(self):
        val = self.cleaned_data.get('precio_venta_neto')
        try:
            return clean_currency_string(val)
        except (ValueError, TypeError, ArithmeticError):
            raise forms.ValidationError("Introduzca un número válido.")

    class Meta:
        model = Cotizacion
        fields = ['margen_objetivo_pct', 'precio_venta_neto', 'dias_validez', 'fecha_inicio_estimada', 'fecha_entrega_manual', 'costo_indirecto_cif_estimado', 'notas_condiciones']
        widgets = {
            'margen_objetivo_pct': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white font-mono focus:outline-none focus:border-sky-500', 'step': '0.01'}),
            'precio_venta_neto': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white font-mono font-bold text-sky-400 focus:outline-none focus:border-sky-500'}),
            'dias_validez': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'fecha_inicio_estimada': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'fecha_entrega_manual': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'costo_indirecto_cif_estimado': IntegerNumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '1'}),
            'notas_condiciones': forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'rows': 3, 'placeholder': 'Condiciones comerciales, forma de pago (50% anticipo), tiempos de entrega...'}),
        }


class ItemCotizacionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['id_material'].queryset = Material.objects.filter(id_empresa=empresa)
        self.fields['id_material'].required = False
        self.fields['id_material'].empty_label = "-------- Seleccionar Material (Opcional) --------"
        self.fields['tipo_item'].required = False
        self.fields['tipo_item'].initial = 'Material'

    def clean_tipo_item(self):
        return self.cleaned_data.get('tipo_item') or 'Material'

    class Meta:
        model = ItemCotizacion
        fields = ['tipo_item', 'id_material', 'costo_unitario', 'cantidad', 'descripcion']
        widgets = {
            'tipo_item': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
                'x-model': 'tipoItem',
            }),
            'id_material': forms.Select(attrs={
                'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
                'x-model': 'selectedMaterial',
                '@change': 'onMaterialChange()'
            }),
            'costo_unitario': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500 font-mono',
                'step': '0.01',
                'x-model.number': 'costoUnitario',
                'placeholder': '0.00'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500 font-mono',
                'step': '0.01',
                'x-model.number': 'cantidad',
                'placeholder': '1'
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
                'x-model': 'descripcion',
                'placeholder': 'Descripción o detalle del insumo o servicio'
            }),
        }
