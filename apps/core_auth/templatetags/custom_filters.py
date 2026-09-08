from decimal import Decimal, ROUND_HALF_UP
from django import template

register = template.Library()

@register.filter(name='clp')
def clp(value):
    """
    Formatea un número como pesos chilenos con signo de peso: $163.220 (sin decimales).
    """
    if value is None or value == '':
        return '$0'
    try:
        val_dec = Decimal(str(value))
        val_int = int(val_dec.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        formatted = f"{val_int:,}".replace(",", ".")
        return f"${formatted}"
    except Exception:
        return f"${value}"


@register.filter(name='clp_raw')
def clp_raw(value):
    """
    Formatea un número con punto separador de miles sin el signo de peso: 163.220
    """
    if value is None or value == '':
        return '0'
    try:
        val_dec = Decimal(str(value))
        val_int = int(val_dec.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        return f"{val_int:,}".replace(",", ".")
    except Exception:
        return str(value)


@register.filter(name='cantidad_format')
def cantidad_format(value):
    """
    Formatea cantidades sin decimales si es entero (ej. 3.00 -> 3),
    o con coma para decimales si tiene fracción (ej. 3.50 -> 3,5).
    """
    if value is None or value == '':
        return '0'
    try:
        val_dec = Decimal(str(value))
        if val_dec % 1 == 0:
            return str(int(val_dec))
        else:
            val_norm = val_dec.normalize()
            return f"{val_norm:f}".replace('.', ',')
    except Exception:
        return str(value)


@register.filter(name='pct_entero')
def pct_entero(value):
    """
    Redondea un porcentaje al entero más cercano con regla ROUND_HALF_UP:
    >= 0.5 hacia arriba, < 0.5 hacia abajo (ej. 35.5 -> 36, 35.4 -> 35).
    """
    if value is None or value == '':
        return '0'
    try:
        val_dec = Decimal(str(value))
        val_int = int(val_dec.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        return str(val_int)
    except Exception:
        return str(value)
