from django import forms
from .models import PagoProyecto
from apps.ordenes_trabajo.models import Proyecto


class PagoProyectoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        if empresa:
            self.fields['id_proyecto'].queryset = Proyecto.objects.filter(id_empresa=empresa)

    class Meta:
        model = PagoProyecto
        fields = ['id_proyecto', 'concepto_hito', 'monto_pago', 'medio_pago', 'fecha_pago', 'comprobante_referencia']
        widgets = {
            'id_proyecto': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'concepto_hito': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'monto_pago': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '1', 'placeholder': '500000'}),
            'medio_pago': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'fecha_pago': forms.DateInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'type': 'date'}),
            'comprobante_referencia': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ej. N° Transferencia Bancaria o Recibo'}),
        }
