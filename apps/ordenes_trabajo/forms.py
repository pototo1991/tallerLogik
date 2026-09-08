from django import forms
from .models import Proyecto, ItemProyecto
from apps.configuracion_base.models import Material


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ['nombre_proyecto', 'estado', 'fecha_inicio_programada', 'fecha_compromiso_entrega']
        widgets = {
            'nombre_proyecto': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'estado': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'fecha_inicio_programada': forms.DateInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'type': 'date'}),
            'fecha_compromiso_entrega': forms.DateInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'type': 'date'}),
        }


class ItemProyectoRectificacionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['id_material'].queryset = Material.objects.filter(id_empresa=empresa)
        self.fields['id_material'].required = False

    class Meta:
        model = ItemProyecto
        fields = ['tipo_item', 'id_material', 'descripcion', 'cantidad', 'costo_unitario']
        widgets = {
            'tipo_item': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'id_material': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'descripcion': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ej. Plancha extra por ajuste de descuadre en muro'}),
            'cantidad': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.01'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '1', 'placeholder': '15000'}),
        }


class AsignarMaterialBodegaForm(forms.Form):
    id_material = forms.ModelChoiceField(
        queryset=Material.objects.none(),
        label="Material / Insumo en Bodega",
        widget=forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'})
    )
    cantidad = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.01'})
    )

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['id_material'].queryset = Material.objects.filter(id_empresa=empresa)

