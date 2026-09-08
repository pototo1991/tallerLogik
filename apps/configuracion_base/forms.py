import re
from decimal import Decimal
from django import forms
from django.core.validators import validate_email
from .models import Cliente, Material, Proveedor

from apps.core_auth.models import Usuario
from apps.core_auth.forms import validar_rut_chileno_modulo11


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            'razon_social', 'rut_o_identificacion', 'direccion', 'comuna', 'ciudad',
            'nombre_contacto', 'telefono_contacto', 'correo_contacto',
            'banco_nombre', 'tipo_cuenta', 'numero_cuenta', 'observaciones'
        ]
        widgets = {
            'razon_social': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ej. Imperial S.A. / Sodimac / Ferretería Central'}),
            'rut_o_identificacion': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500 font-mono', 'placeholder': 'Ej. 76123456-7'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Av. Principal #1234'}),
            'comuna': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Comuna'}),
            'ciudad': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ciudad'}),
            'nombre_contacto': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Nombre del Vendedor / Ejecutivo'}),
            'telefono_contacto': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': '+56 9 ...'}),
            'correo_contacto': forms.EmailInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'ventas@proveedor.com'}),
            'banco_nombre': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ej. Banco de Chile, BCI, Estado'}),
            'tipo_cuenta': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Cuenta Corriente / Vista / Chequera'}),
            'numero_cuenta': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500 font-mono', 'placeholder': 'N° de cuenta bancaria'}),
            'observaciones': forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'rows': 2, 'placeholder': 'Líneas de crédito, condiciones de despacho, etc.'}),
        }

    def clean_rut_o_identificacion(self):
        rut = self.cleaned_data.get('rut_o_identificacion')
        if not rut or not str(rut).strip():
            return None
        rut_str = str(rut).strip()
        if not re.match(r'^\d{7,8}-[\dkK]$', rut_str):
            raise forms.ValidationError("El RUT debe tener el formato 12345678-9 (sin puntos y con guion).")
        es_valido, rut_formateado = validar_rut_chileno_modulo11(rut_str)
        if not es_valido:
            raise forms.ValidationError("El dígito verificador del RUT no es válido según el algoritmo Módulo 11.")
        return rut_formateado

    def clean_correo_contacto(self):
        correo = self.cleaned_data.get('correo_contacto')
        if not correo or not str(correo).strip():
            return None
        correo_clean = str(correo).strip().lower()
        try:
            validate_email(correo_clean)
        except forms.ValidationError:
            raise forms.ValidationError("Por favor ingrese un correo electrónico válido.")
        return correo_clean


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'razon_social', 'rut_o_identificacion', 'nombre_contacto',
            'correo_contacto', 'telefono_contacto', 'correo_general',
            'telefono_general', 'direccion', 'comuna', 'ciudad'
        ]
        widgets = {
            'razon_social': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Razón Social o Nombre'}),
            'rut_o_identificacion': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500 font-mono', 'placeholder': 'Ej. 12345678-9'}),
            'nombre_contacto': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Nombre Persona Contacto'}),
            'correo_contacto': forms.EmailInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'contacto@cliente.com'}),
            'telefono_contacto': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': '+56 9 ...'}),
            'correo_general': forms.EmailInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'facturacion@cliente.com'}),
            'telefono_general': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Teléfono Empresa'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Calle, Número, Depto/Local'}),
            'comuna': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Comuna'}),
            'ciudad': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ciudad'}),
        }

    def clean_rut_o_identificacion(self):
        rut = self.cleaned_data.get('rut_o_identificacion')
        if not rut or not str(rut).strip():
            return None

        rut_str = str(rut).strip()
        # Validar formato estricto 12345678-9 (sin puntos y con guion)
        if not re.match(r'^\d{7,8}-[\dkK]$', rut_str):
            raise forms.ValidationError(
                "El RUT debe tener el formato 12345678-9 (sin puntos y con guion)."
            )

        es_valido, rut_formateado = validar_rut_chileno_modulo11(rut_str)
        if not es_valido:
            raise forms.ValidationError(
                "El dígito verificador del RUT no es válido según el algoritmo Módulo 11."
            )

        return rut_formateado

    def clean_correo_contacto(self):
        correo = self.cleaned_data.get('correo_contacto')
        if not correo or not str(correo).strip():
            return None
        correo_clean = str(correo).strip().lower()
        try:
            validate_email(correo_clean)
        except forms.ValidationError:
            raise forms.ValidationError(
                "Por favor ingrese un correo electrónico válido (ejemplo: contacto@empresa.com)."
            )
        return correo_clean

    def clean_correo_general(self):
        correo = self.cleaned_data.get('correo_general')
        if not correo or not str(correo).strip():
            return None
        correo_clean = str(correo).strip().lower()
        try:
            validate_email(correo_clean)
        except forms.ValidationError:
            raise forms.ValidationError(
                "Por favor ingrese un correo electrónico válido (ejemplo: facturacion@empresa.com)."
            )
        return correo_clean



class MaterialForm(forms.ModelForm):
    stock_actual = forms.DecimalField(
        required=False,
        initial=Decimal('0'),
        widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '1', 'placeholder': '0'})
    )
    stock_minimo = forms.DecimalField(
        required=False,
        initial=Decimal('0'),
        widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '1', 'placeholder': '0'})
    )

    class Meta:
        model = Material
        fields = ['nombre', 'categoria', 'unidad_medida', 'costo_unitario', 'porcentaje_merma_defecto', 'stock_actual', 'stock_minimo', 'proveedor', 'observaciones']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ej. Plancha MDF 18mm 2440x1220'}),
            'categoria': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Plancha, ML, Unidad, Caja'}),
            'costo_unitario': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.01'}),
            'porcentaje_merma_defecto': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.01'}),
            'proveedor': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Ej. Imperial, Sodimac, Dap Ducasse, Ferretería local...'}),
            'observaciones': forms.Textarea(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'rows': 3, 'placeholder': 'Teléfono: +56 9 ..., Contacto: ..., Dirección: ..., o notas del insumo'}),
        }


    def clean_stock_actual(self):
        stock = self.cleaned_data.get('stock_actual')
        return stock if stock is not None else Decimal('0.00')

    def clean_stock_minimo(self):
        stock = self.cleaned_data.get('stock_minimo')
        return stock if stock is not None else Decimal('0.00')



class AjusteStockForm(forms.Form):
    TIPOS_OPERACION = (
        ('INGRESO_INICIAL', '📥 Ingreso / Carga de Stock (+)'),
        ('COMPRA_BODEGA', '📦 Compra para Bodega (+)'),
        ('AJUSTE_MANUAL', '✏️ Ajuste por Corrección / Pérdida (-)'),
        ('DEVOLUCION', '↩️ Devolución de Sobrante (+)'),
    )

    tipo_operacion = forms.ChoiceField(
        choices=TIPOS_OPERACION,
        widget=forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'})
    )
    cantidad = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '1', 'placeholder': 'Ej. 5'})
    )

    observaciones = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'placeholder': 'Motivo del ajuste de stock...'})
    )



class OperarioForm(forms.ModelForm):
    correo_electronico = forms.EmailField(
        label="Correo Electrónico",
        error_messages={
            'required': 'El correo electrónico es obligatorio.',
            'invalid': 'Por favor ingrese un correo electrónico válido (ejemplo: operario@taller.com).'
        },
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
            'placeholder': 'ejemplo: operario@taller.com',
            'x-model': 'email',
            '@input': 'validarEmail()',
            ':class': "{ 'border-emerald-500 focus:border-emerald-500': emailValido === true, 'border-red-500 focus:border-red-500': emailValido === false }"
        })
    )
    password = forms.CharField(
        label="Contraseña Inicial",
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'})
    )

    class Meta:
        model = Usuario
        fields = ['nombre_completo', 'correo_electronico', 'rol', 'costo_hora']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'rol': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'costo_hora': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.01'}),
        }

    def clean_correo_electronico(self):
        correo = self.cleaned_data.get('correo_electronico')
        if not correo:
            return correo

        correo_clean = str(correo).strip().lower()
        qs = Usuario.objects.filter(correo_electronico=correo_clean)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "Este correo electrónico ya se encuentra registrado."
            )

        return correo_clean


class OperarioEditForm(forms.ModelForm):
    correo_electronico = forms.EmailField(
        label="Correo Electrónico",
        error_messages={
            'required': 'El correo electrónico es obligatorio.',
            'invalid': 'Por favor ingrese un correo electrónico válido (ejemplo: operario@taller.com).'
        },
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
            'placeholder': 'ejemplo: operario@taller.com',
            'x-model': 'email',
            '@input': 'validarEmail()',
            ':class': "{ 'border-emerald-500 focus:border-emerald-500': emailValido === true, 'border-red-500 focus:border-red-500': emailValido === false }"
        })
    )

    class Meta:
        model = Usuario
        fields = ['nombre_completo', 'correo_electronico', 'rol', 'costo_hora']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'rol': forms.Select(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500'}),
            'costo_hora': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500', 'step': '0.01'}),
        }

    def clean_correo_electronico(self):
        correo = self.cleaned_data.get('correo_electronico')
        if not correo:
            return correo

        correo_clean = str(correo).strip().lower()
        qs = Usuario.objects.filter(correo_electronico=correo_clean)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "Este correo electrónico ya se encuentra registrado por otro usuario."
            )

        return correo_clean



class ReestablecerPasswordForm(forms.Form):
    password = forms.CharField(
        label="Nueva Contraseña",
        min_length=8,
        required=True,
        error_messages={
            'required': 'La contraseña es obligatoria y no puede quedar vacía.',
            'min_length': 'La contraseña debe tener al menos 8 caracteres.'
        },
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
            'placeholder': 'Mínimo 8 caracteres'
        })
    )

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if not password or not str(password).strip():
            raise forms.ValidationError("La contraseña no puede estar vacía ni contener únicamente espacios.")
        return str(password).strip()



