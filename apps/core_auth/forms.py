import re
from django import forms
from django.contrib.auth import authenticate
from django.core.validators import validate_email
from .models import Empresa, Usuario


def validar_rut_chileno_modulo11(rut_str: str) -> tuple[bool, str]:
    """
    Valida un RUT chileno mediante el algoritmo de Módulo 11.
    Retorna una tupla (es_valido, rut_formateado_estandar).
    Formato estándar devuelto: 12345678-9 o 12345678-K.
    """
    if not rut_str:
        return False, ""

    # Eliminar puntos, espacios, guiones y convertir a mayúsculas
    rut_clean = re.sub(r'[^0-9kK]', '', str(rut_str).upper())

    if len(rut_clean) < 8 or len(rut_clean) > 9:
        return False, rut_str

    cuerpo = rut_clean[:-1]
    dv = rut_clean[-1]

    if not cuerpo.isdigit():
        return False, rut_str

    # Algoritmo Módulo 11
    suma = 0
    multiplicador = 2
    for d in reversed(cuerpo):
        suma += int(d) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1

    resto = suma % 11
    diferencia = 11 - resto

    if diferencia == 11:
        dv_esperado = '0'
    elif diferencia == 10:
        dv_esperado = 'K'
    else:
        dv_esperado = str(diferencia)

    if dv == dv_esperado:
        return True, f"{cuerpo}-{dv}"

    return False, rut_str


class LoginForm(forms.Form):
    correo_electronico = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
            'placeholder': 'correo@taller.com'
        })
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
            'placeholder': '••••••••'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('correo_electronico')
        password = cleaned_data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if not user:
                raise forms.ValidationError("Credenciales inválidas. Por favor verifique su correo y contraseña.")
            if not user.activo:
                raise forms.ValidationError("Esta cuenta se encuentra desactivada.")
            cleaned_data['user'] = user
        return cleaned_data


class OnboardingTallerForm(forms.Form):
    nombre_empresa = forms.CharField(
        label="Nombre del Taller / Mueblería",
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
            'placeholder': 'Ej. Muebles & Diseños SpA'
        })
    )
    rut_o_identificacion = forms.CharField(
        label="RUT o Identificación Fiscal",
        max_length=50,
        required=True,
        error_messages={
            'required': 'El RUT o Identificación Fiscal es obligatorio.'
        },
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500 font-mono',
            'placeholder': 'Ej. 12345678-9',
            'x-model': 'rut',
            '@input': 'formatRut()',
            ':class': "{ 'border-emerald-500 focus:border-emerald-500': rutValido === true, 'border-red-500 focus:border-red-500': rutValido === false }"
        })
    )
    nombre_dueno = forms.CharField(
        label="Nombre Completo del Dueño / Administrador",
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
            'placeholder': 'Ej. Juan Pérez Soto'
        })
    )
    correo_electronico = forms.EmailField(
        label="Correo Electrónico de Registro",
        error_messages={
            'required': 'El correo electrónico es obligatorio.',
            'invalid': 'Por favor ingresa un correo electrónico válido (ejemplo: usuario@taller.cl).'
        },
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
            'placeholder': 'admin@mueblesdiseno.cl'
        })
    )
    password = forms.CharField(
        label="Contraseña",
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-sky-500',
            'placeholder': 'Mínimo 8 caracteres'
        })
    )

    def clean_rut_o_identificacion(self):
        rut = self.cleaned_data.get('rut_o_identificacion')
        if not rut:
            raise forms.ValidationError("El RUT o Identificación Fiscal es obligatorio.")

        es_valido, rut_formateado = validar_rut_chileno_modulo11(rut)
        if not es_valido:
            raise forms.ValidationError(
                "El RUT o Identificación Fiscal ingresado no es válido."
            )
        return rut_formateado

    def clean_correo_electronico(self):
        correo = self.cleaned_data.get('correo_electronico')
        if correo:
            correo = correo.lower().strip()
            try:
                validate_email(correo)
            except forms.ValidationError:
                raise forms.ValidationError("Por favor ingresa un correo electrónico válido (ejemplo: usuario@taller.cl).")

            if Usuario.objects.filter(correo_electronico=correo).exists():
                raise forms.ValidationError("Este correo electrónico ya se encuentra registrado.")
        return correo

