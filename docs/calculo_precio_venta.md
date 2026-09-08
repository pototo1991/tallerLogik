# Guía de Costeo y Cálculo del Precio de Venta Neto
Este documento explica en detalle el modelo financiero utilizado por **TallerLogik** para costear proyectos y calcular el precio de venta final para el cliente, asegurando la rentabilidad real del taller.

---

## 1. Filosofía Financiera: Margen sobre Venta vs. Margen sobre Costo

En el rubro de talleres a medida y manufactura, existen dos metodologías para calcular el precio de venta en base a los costos:

### A. Margen sobre Costo (Markup)
Consiste en sumarle un porcentaje directo al costo total de fabricación.
* **Fórmula**: $\text{Precio} = \text{Costo} \times (1 + \text{Margen}\%)$
* **Ejemplo**: Si un mueble cuesta $\$100.000$ fabricarlo y deseas ganar un $35\%$:
  $$\text{Precio} = \$100.000 \times 1.35 = \$135.000$$
* **El Peligro**: Si bien parece que ganaste un $35\%$, en realidad estás midiendo tu utilidad sobre el *costo*, no sobre la *venta*. Si calculas el porcentaje que representa tu ganancia ($\$35.000$) sobre el dinero que cobraste ($\$135.000$), la rentabilidad real de la transacción fue de **$25.9\%$** ($\$35.000 / \$135.000$). Si otorgas un descuento comercial del $30\%$, terminarás vendiendo bajo el costo.

### B. Margen sobre Venta (Margin) — *El estándar de TallerLogik*
Consiste en fijar el precio de venta de tal manera que el porcentaje de ganancia acordado sea el **porcentaje neto real del dinero total facturado al cliente**.
* **Fórmula**: $\text{Precio} = \frac{\text{Costo}}{1 - \frac{\text{Margen}\%}{100}}$
* **Ejemplo**: Si fabricar te cuesta $\$100.000$ y quieres asegurar un margen real de utilidad del $35\%$ sobre el total de la venta:
  $$\text{Precio} = \frac{\$100.000}{1 - 0.35} = \frac{\$100.000}{0.65} = \$153.846$$
* **La Utilidad Real**: Tu ganancia neta es de $\$53.846$. Si calculas qué proporción representa tu utilidad sobre el dinero que ingresó a caja:
  $$\frac{\$53.846}{\$153.846} = 0.35 \quad \mathbf{(35\% \text{ exacto})}$$
  De esta forma, proteges el margen del taller frente a futuros descuentos o variaciones de CIF.

---

## 2. Caso Práctico: Desglose de la Cotización `COT-2026-001`
Tomaremos como ejemplo real la cotización de **"mueble cocina"** registrada en la base de datos de desarrollo.

### Paso 1: Costeo de Ítems (BOM de Materiales)
La cotización contiene los siguientes materiales en su lista de insumos:

| Ítem | Cantidad | Costo Unitario | % Merma Aplicado | Fórmula de Subtotal | Subtotal Costo |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Aglomerado desnudo 12mm | 5.00 | $\$22.030$ | $0.00\%$ | $(5 \times 22.030) \times 1.00$ | **$\$110.150$** |
| Clavo 2" madera | 10.00 | $\$1.500$ | $0.00\%$ | $(10 \times 1.500) \times 1.00$ | **$\$15.000$** |

* **Total Costo Materiales**: $\$110.150 + \$15.000 = \$125.150$
* **Mano de Obra Directa (MOD)**: $\$0$
* **Servicios Externos**: $\$0$
* **Costos Indirectos de Fabricación (CIF)**: $\$0$

$$\text{Costo Total Estimado } (C) = \$125.150$$

---

### Paso 2: Cálculo del Precio Neto (Margen de 35%)
El usuario definió para esta cotización un **Margen Objetivo ($M$) del $35\%$**.

Esto significa que los costos del taller deben representar el **$65\%$** restante del precio final cobrado ($100\% - 35\% = 65\%$).

1. **Ecuación inicial**: El $65\%$ del precio final de venta ($P$) es igual al costo ($C$).
   $$P \times 0.65 = \$125.150$$

2. **Despeje**: Para calcular el precio ($P$), pasamos el $0.65$ dividiendo al otro lado de la igualdad:
   $$P = \frac{\$125.150}{0.65}$$

3. **Cálculo decimal exacto**:
   $$P = \$192.538,461538...$$

El sistema redondea internamente el valor a dos decimales y lo almacena en la base de datos como:
$$\text{Precio Venta Neto} = \mathbf{\$192.538,46}$$

---

### Paso 3: Redondeo e Interfaz en CLP
En Chile, el peso chileno no utiliza centavos en el ámbito comercial. Por lo tanto, el sistema aplica el filtro de visualización `|clp` antes de pintar la tabla en pantalla:

* **Valor almacenado**: $\$192.538,46$
* **Operación de redondeo (`ROUND_HALF_UP`)**: Al ser los decimales `.46` menores a `.50`, se redondea hacia abajo al entero más cercano.
* **Resultado final visible**: **`$192.538`**

---

## 3. ¿Dónde se encuentra esta lógica en el código?

Si necesitas revisar o modificar cómo se realizan estos cálculos en el backend del software, los archivos clave son:

1. **Lógica de Cálculo Financiero**:
   * Archivo: [models.py](file:///home/whsg27/proyectos/tallerLogik/apps/cotizador/models.py)
   * Método de la Cotización: `calcular_totales(self)` (línea 81).
   * Lógica de Mermas y Subtotales: `save(self, *args, **kwargs)` del modelo `ItemCotizacion` (línea 126).

2. **Filtro de Formateo de Moneda**:
   * Archivo: [custom_filters.py](file:///home/whsg27/proyectos/tallerLogik/apps/core_auth/templatetags/custom_filters.py)
   * Función: `clp(value)` (línea 7) que aproxima y formatea a la moneda local con puntos de miles.
