# Plan de Especificación Técnica & Arquitectura de Software

## SaaS de Gestión y Costeo de Proyectos para Mueblería Especializada & Talleres a Medida
 
---

- Documento: Blueprint, Roadmap & Modelo de Datos en Español
- Evolución: Web Responsive
- Modelo: Multi-Tenant B2B SaaS

---
### 1. Resumen Ejecutivo y Flujo de Cotización a Producción

En un taller a medida, no toda cotización se convierte en proyecto. Un taller suele emitir entre 3 a 5 cotizaciones o variantes por cada cliente antes de que una sea aprobada. Por ende, el sistema separa estrictamente la Entidad Comercial (Cotización + Detalle de Ítems) de la Entidad Operativa (Proyecto / Orden de Trabajo activa y su respectiva lista de materiales o BOM de producción).
  
>[!NOTE]
**Flujo de Transformación:** Cliente solicita cotización (se registra el cliente en `clientes` si es nuevo) → Se registran variantes en cotizaciones e insumos completos en `items_cotizacion` (planchas completas, cajas de tornillos, enchapados, horas estimadas) → Si el cliente aprueba la cotización, se marca como aprobada y se genera la Orden de Trabajo en `proyectos`, duplicando los ítems comerciales a la lista de producción (`items_proyecto`). Posteriormente, tras la rectificación de medidas en obra por el Jefe de Taller, se agregan nuevos elementos de ajuste marcándolos como "agregados por rectificación de medidas" para mantener la trazabilidad. En las compras generales de ferretería o proveedores, una factura de compra puede imputarse a uno o varios proyectos mediante `facturas_compra` y `gastos_proyecto`, validando que la suma distribuida cuadre exactamente con el total del comprobante.
  
  
### 2. Mapa de Módulos del Sistema

| M   | Módulo                                                               | Descripción & Funciones Principales                                                                                                                                                                       | UsuariosObjetivo         |
| :-- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| M1  | `core_auth` (Autenticación & Tenants)                                | Registro de empresa (taller), login seguro (email / password), modelo de usuario personalizado (`Usuario`), roles de acceso y aislamiento de consultas por `id_empresa` mediante middleware multi-tenant. | Todos                    |
| M2  | `configuracion_base` (Config Base & Clientes)                        | CRUD de catálogo de materiales por unidades completas, registro de operarios con su costo/hora base, costos indirectos de fabricación (CIF) y directorio de clientes B2B/B2C con contactos.               | Admin / Dueño            |
| M3  | `cotizador` (Cotizador de Proyectos)                                 | Calculadora de presupuestos vinculada a clientes, basada en insumos completos + horas estimadas + margen sobre venta, control de versiones (v1, v2) y generación de presupuestos en PDF con WeasyPrint    | Admin / Diseñador        |
| M4  | `ordenes_trabajo` (Gestión de OTs)                                   | Conversión de cotización aprobada a OT (`proyectos`), duplicación independiente al BOM (`items_proyecto`), registro de ítems por rectificación en obra, programación de fechas y tablero Kanban.          | Admin / Jefe Taller      |
| M5  | `compras_gastos` (Compras e Imprevistos Web)                         | Módulo web responsive (PC, Tablet, Smartphone) para registrar facturas de compra (`facturas_compra`) con distribución de valores netos entre uno o múltiples proyectos (`gastos_proyecto`), garantizando la cuadratura del total neto. | Jefe Taller / Compras    |
| M6  | `dashboard_rentabilidad` (Rentabilidad & Alertas)                    | Control de hitos de cobro (anticipo 50%, avance 30%, saldo contra entrega 20%) y conciliación de transferencias bancarias con folio de transacción.                                                       | Admin / Dueño            |
| M7  | `cobranzas` (Hitos de Pago y Cobranzas)                              | Control de anticipos (50%), estados de pago por avance (30%) y saldo contra entrega conforme (20%), con registro de referencias de transferencia para conciliación.                                       | Admin / Finanzas         |
| M8  | `auditoria_logs` (Trazabilidad & Diagnóstico)                        | Registro estructurado de eventos del sistema, middleware de captura de excepciones y escritura en archivos `.log` con rotación para análisis de causa raíz.                                               | Administrador / Soporte  |

  

### 3. Orden de Construcción Paso a Paso (Roadmap de Desarrollo)

>[!FASE 1] FASE 1: El Núcleo de Configuración, Tenants & Clientes (Semanas 1 a 3)
>Objetivo: Configurar Django con PostgreSQL, Custom User Model, Middleware Multi-Tenant y Django Admin personalizado. Paso 1.1: Módulo `core_auth` — Registro de empresa (`Empresa`), login, Custom User (`Usuario`), roles y TenantMiddleware. Paso 1.2: Módulo `configuracion_base` — Modelos y vistas para `Cliente`, `Material` (por unidades completas) y parámetros del taller. Paso 1.3: Sistema de Logging — Configuración de `logging` en Django y middleware de auditoría a archivo/tabla.

>[!FASE 2] FASE 2: Comercial & Órdenes de Trabajo (Semanas 4 a 6)
>Objetivo: Construir el cotizador dinámico con HTMX y el motor de conversión a OTs. 
>Paso 2.1: Módulo `cotizador` — Vistas Django + HTMX para agregar insumos dinámicamente, cálculo de margen sobre venta y generación de PDFs con WeasyPrint. 
>Paso 2.2: Módulo `ordenes_trabajo` — Lógica de servicio en Django para clonar `ItemCotizacion` a `ItemProyecto` y registrar ítems por rectificación.
 
>[!FASE 3] FASE 3: Captura de Gastos y Compras Web Responsive (Semanas 7 a 9)
>Objetivo: Registrar facturas de compra y desglose neto por proyectos activos, más horas de taller de forma centralizada sin almacenamiento de imágenes (100% datos estructurados). 
>Paso 3.1: Módulo `compras_gastos` — Vista web responsive para ingreso de facturas de compra y desglose en valores netos distribuidos hacia uno o múltiples proyectos (`gastos_proyecto`) validando cuadratura exacta. 
>Paso 3.2: Registro de Tiempos Manual — Formulario HTMX para que el Jefe de Taller impute horas trabajadas por operario/etapa sin temporizadores en tablet/smartphone.
  
>Objetivo: Dashboards de rentabilidad, hitos de pago. 
>Paso 4.1: Módulo `dashboard_rentabilidad` — Agregaciones ORM con `DecimalField` para comparar Costo Real vs. Presupuestado y emitir alertas. 
>Paso 4.2: Módulo `cobranzas` — Gestión de cuotas 50/30/20 y validación de transferencias. 


  

### 4. Pila Tecnológica & Paleta de Colores

| Componente              | Tecnología / Valor                          | Uso Principal                                                         |
| :---------------------- | ------------------------------------------- | ---------------------------------------------------------------------- |
| Backend & Framework     | Python 3.12+ / Django 5.x                   | Núcleo web, ORM relacional, autenticación y lógica de negocio.         |
| Frontend & Reactividad  | Django Templates + HTMX + Alpine.js         | Formularios dinámicos, cotizador en vivo y tablas sin recargar página. |
| Estilos UI              | Tailwind CSS                                | Interfaz web responsive para navegador en PC, tablet o smartphone.     |
| Base de Datos           | PostgreSQL                                  | Motor relacional con aislamiento `id_empresa` e índices de unicidad.   |
| Almacenamiento Datos    | PostgreSQL (Datos Estructurados)            | Registro 100% de datos en BD (sin almacenamiento de imágenes/archivos).|
| Generación de PDFs      | WeasyPrint                                  | Renderizado de cotizaciones comerciales profesionales en PDF.          |
| Tareas en Segundo Plano | **Celery / Redis** (o Django-Q)             | Procesamiento asíncrono de PDFs pesados de cotizaciones y reportes.    |
| Entorno Desarrollo      | **WSL Ubuntu 24.04 + Docker**               | Contenedores locales en Windows 11 para PostgreSQL y Django.           |
| Color Primario          | `#0F172A` (Pizarra Oscura)                  | Barras de navegación, cabeceras y tarjetas principales.                |
| Color Acento            | `#0284C7` (Azul Eléctrico)                  | Botones de acción (Guardar, Cotizar, Aprobar OT).                      |
| Color Alertas           | `#DC2626` (Rojo Alerta)                     | Avisos de sobrecostos o cotizaciones vencidas.                         |

### 5. Configuración de Logging y Trazabilidad de Eventos

Para garantizar que todo lo que ocurre en el sistema quede registrado en un archivo de log físico con rotación y contexto del taller, se implementa la siguiente configuración:

#### A. Configuración en `settings.py` (Django Logging)

```Python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] [{levelname}] [T:{empresa_id}] [U:{usuario_email}] [{name}:{lineno}] - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{asctime}] [{levelname}] - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'tenant_context_filter': {
            '()': 'apps.core_auth.log_filters.TenantContextFilter',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'archivo_actividad': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sistema_actividad.log',
            'maxBytes': 1024 * 1024 * 15, # 15 MB
            'backupCount': 10,
            'formatter': 'verbose',
            'filters': ['tenant_context_filter'],
            'encoding': 'utf-8',
        },
        'archivo_errores': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sistema_errores.log',
            'maxBytes': 1024 * 1024 * 10, # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'filters': ['tenant_context_filter'],
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'archivo_errores'],
            'level': 'INFO',
            'propagate': False,
        },
        'saas_taller': {
            'handlers': ['console', 'archivo_actividad', 'archivo_errores'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

#### B. Filtro de Contexto Multi-Tenant para Logs (`apps/core_auth/log_filters.py`)

```Python
import logging
from apps.core_auth.middleware import get_current_tenant_and_user

class TenantContextFilter(logging.Filter):
    """Inyecta el ID de la empresa y el correo del usuario en cada línea de log."""
    def filter(self, record):
        tenant_id, user_email = get_current_tenant_and_user()
        record.empresa_id = tenant_id or 'GLOBAL'
        record.usuario_email = user_email or 'ANON'
        return True
```


### 6. Modelos de Base de Datos en Django (ORM / `models.py`)

Esquema con borrado lógico (`SoftDeleteModel`), aislamiento multi-tenant (`TenantAwareModel`) y tipado monetario exacto con `DecimalField`:

```Python
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# -------------------------------------------------------------
# MODELOS BASE Y MANAGERS
# -------------------------------------------------------------

class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(eliminado_en__isnull=True)

class SoftDeleteModel(models.Model):
    eliminado_en = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.eliminado_en = timezone.now()
        self.save(update_fields=['eliminado_en'])

class TenantAwareModel(SoftDeleteModel):
    id_empresa = models.ForeignKey('Empresa', on_delete=models.RESTRICT, related_name="%(class)s_set")

    class Meta:
        abstract = True

# -------------------------------------------------------------
# 1. EMPRESAS (TENANTS)
# -------------------------------------------------------------

class Empresa(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_empresa = models.CharField(max_length=255)
    rut_o_identificacion = models.CharField(max_length=50, blank=True, null=True)
    plan_suscripcion = models.CharField(max_length=50, default='basico')
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'empresas'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nombre_empresa

# -------------------------------------------------------------
# 2. USUARIOS Y ROLES
# -------------------------------------------------------------

class UsuarioManager(BaseUserManager):
    def create_user(self, correo_electronico, password=None, **extra_fields):
        if not correo_electronico:
            raise ValueError('El correo electrónico es obligatorio')
        correo = self.normalize_email(correo_electronico)
        user = self.model(correo_electronico=correo, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo_electronico, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', 'administrador')
        return self.create_user(correo_electronico, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    ROLES = (
        ('superadmin_saas', 'Administrador SaaS Global'),
        ('dueno_taller', 'Dueño / Admin del Taller'),
        ('jefe_taller', 'Jefe de Taller'),
        ('operario', 'Operario'),
        ('montador', 'Montador'),
        ('compras', 'Compras'),
        ('disenador', 'Diseñador'),
        ('vendedor', 'Vendedor'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_empresa = models.ForeignKey(Empresa, on_delete=models.RESTRICT, null=True, blank=True, related_name='usuarios')
    correo_electronico = models.EmailField(max_length=255, unique=True)
    nombre_completo = models.CharField(max_length=255)
    rol = models.CharField(max_length=50, choices=ROLES, default='operario')
    costo_hora = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    activo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'correo_electronico'
    REQUIRED_FIELDS = ['nombre_completo']

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.nombre_completo} ({self.rol})"

# -------------------------------------------------------------
# 3. CLIENTES (DIRECTORIO UNIFICADO)
# -------------------------------------------------------------

class Cliente(TenantAwareModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    razon_social = models.CharField(max_length=255)
    rut_o_identificacion = models.CharField(max_length=50, blank=True, null=True)
    correo_general = models.EmailField(max_length=255, blank=True, null=True)
    telefono_general = models.CharField(max_length=50, blank=True, null=True)
    nombre_contacto = models.CharField(max_length=255)
    correo_contacto = models.EmailField(max_length=255, blank=True, null=True)
    telefono_contacto = models.CharField(max_length=50, blank=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    comuna = models.CharField(max_length=100, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return self.razon_social

# -------------------------------------------------------------
# 4. CATÁLOGO DE MATERIALES E INSUMOS
# -------------------------------------------------------------

class Material(TenantAwareModel):
    CATEGORIAS = (
        ('Tableros', 'Tableros'),
        ('Maderas', 'Maderas'),
        ('Quincalleria', 'Quincallería'),
        ('Insumos', 'Insumos'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=255)
    categoria = models.CharField(max_length=100, choices=CATEGORIAS)
    unidad_medida = models.CharField(max_length=50) # Plancha, ML, Unidad, Caja, Par
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    porcentaje_merma_defecto = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('10.00'))

    class Meta:
        db_table = 'materiales'
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'

    def __str__(self):
        return f"{self.nombre} ({self.unidad_medida})"

# -------------------------------------------------------------
# 5. COTIZACIONES COMERCIALES
# -------------------------------------------------------------

class Cotizacion(TenantAwareModel):
    ESTADOS = (
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('expirada', 'Expirada'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_cliente = models.ForeignKey(Cliente, on_delete=models.RESTRICT, related_name='cotizaciones')
    numero_cotizacion = models.CharField(max_length=50)
    version = models.IntegerField(default=1)
    titulo_propuesta = models.CharField(max_length=255)
    costo_materiales_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    costo_mano_obra_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    costo_servicios_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    costo_indirecto_cif_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    costo_total_estimado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    margen_objetivo_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('35.00'))
    precio_venta_neto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    estado = models.CharField(max_length=50, choices=ESTADOS, default='borrador')
    dias_validez = models.IntegerField(default=15)
    notas_condiciones = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cotizaciones'
        constraints = [
            models.UniqueConstraint(fields=['id_empresa', 'numero_cotizacion', 'version'], name='unique_cotizacion_per_tenant')
        ]

    def calcular_totales(self):
        """Calcula el costo total y el precio de venta con margen sobre venta."""
        self.costo_total_estimado = (
            self.costo_materiales_estimado +
            self.costo_mano_obra_estimado +
            self.costo_servicios_estimado +
            self.costo_indirecto_cif_estimado
        )
        factor_margen = Decimal('1.00') - (self.margen_objetivo_pct / Decimal('100.00'))
        if factor_margen > Decimal('0.00'):
            self.precio_venta_neto = self.costo_total_estimado / factor_margen
        else:
            self.precio_venta_neto = self.costo_total_estimado
        self.save()

# -------------------------------------------------------------
# 6. ÍTEMS DE COTIZACIÓN
# -------------------------------------------------------------

class ItemCotizacion(TenantAwareModel):
    TIPOS = (
        ('Material', 'Material'),
        ('Mano_Obra', 'Mano de Obra'),
        ('Servicio_Tercero', 'Servicio Tercero'),
        ('Insumo', 'Insumo'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name='items')
    id_material = models.ForeignKey(Material, on_delete=models.RESTRICT, null=True, blank=True)
    descripcion = models.CharField(max_length=255)
    tipo_item = models.CharField(max_length=50, choices=TIPOS)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    porcentaje_merma_aplicado = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    subtotal_costo = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'items_cotizacion'

    def save(self, *args, **kwargs):
        factor_merma = Decimal('1.00') + (self.porcentaje_merma_aplicado / Decimal('100.00'))
        self.subtotal_costo = (self.cantidad * self.costo_unitario) * factor_merma
        super().save(*args, **kwargs)

# -------------------------------------------------------------
# 7. PROYECTOS / ÓRDENES DE TRABAJO (OT)
# -------------------------------------------------------------

class Proyecto(TenantAwareModel):
    ESTADOS = (
        ('planificado', 'Planificado'),
        ('corte', 'Corte'),
        ('armado', 'Armado'),
        ('laca_pintura', 'Laca y Pintura'),
        ('montaje', 'Montaje en Obra'),
        ('entregado', 'Entregado Conforme'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_cotizacion_origen = models.ForeignKey(Cotizacion, on_delete=models.RESTRICT, related_name='proyectos_generados')
    id_cliente = models.ForeignKey(Cliente, on_delete=models.RESTRICT, related_name='proyectos')
    codigo_ot = models.CharField(max_length=50)
    nombre_proyecto = models.CharField(max_length=255)
    estado = models.CharField(max_length=50, choices=ESTADOS, default='planificado')
    precio_cotizado = models.DecimalField(max_digits=12, decimal_places=2)
    costo_presupuestado_total = models.DecimalField(max_digits=12, decimal_places=2)
    margen_objetivo_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('35.00'))
    fecha_inicio_programada = models.DateField(null=True, blank=True)
    fecha_inicio_real = models.DateField(null=True, blank=True)
    fecha_fin_real = models.DateField(null=True, blank=True)
    fecha_compromiso_entrega = models.DateField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'proyectos'
        constraints = [
            models.UniqueConstraint(fields=['id_empresa', 'codigo_ot'], name='unique_ot_per_tenant')
        ]

    def __str__(self):
        return f"{self.codigo_ot} - {self.nombre_proyecto}"

# -------------------------------------------------------------
# 8. ÍTEMS DE PRODUCCIÓN (BOM DE LA OT)
# -------------------------------------------------------------

class ItemProyecto(TenantAwareModel):
    TIPOS = (
        ('Material', 'Material'),
        ('Mano_Obra', 'Mano de Obra'),
        ('Servicio_Tercero', 'Servicio Tercero'),
        ('Insumo', 'Insumo'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='items_produccion')
    id_material = models.ForeignKey(Material, on_delete=models.RESTRICT, null=True, blank=True)
    descripcion = models.CharField(max_length=255)
    tipo_item = models.CharField(max_length=50, choices=TIPOS)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal_costo = models.DecimalField(max_digits=12, decimal_places=2)
    agregado_rectificacion = models.BooleanField(default=False)
    fecha_agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'items_proyecto'

# -------------------------------------------------------------
# 9. REGISTRO MANUAL DE TIEMPOS (MOD)
# -------------------------------------------------------------

class RegistroTiempo(TenantAwareModel):
    ETAPAS = (
        ('Corte', 'Corte'),
        ('Armado', 'Armado'),
        ('Laca_Pintura', 'Laca y Pintura'),
        ('Montaje', 'Montaje'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_proyecto = models.ForeignKey(Proyecto, on_delete=models.RESTRICT, related_name='tiempos_registrados')
    id_usuario = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='horas_computadas')
    etapa = models.CharField(max_length=100, choices=ETAPAS)
    horas_trabajadas = models.DecimalField(max_digits=10, decimal_places=2)
    costo_mano_obra_calculado = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='tiempos_ingresados')

    class Meta:
        db_table = 'registros_tiempo'

    def save(self, *args, **kwargs):
        if not self.costo_mano_obra_calculado:
            self.costo_mano_obra_calculado = self.horas_trabajadas * self.id_usuario.costo_hora
        super().save(*args, **kwargs)

# -------------------------------------------------------------
# 10. FACTURAS DE COMPRA Y GASTOS DISTRIBUIDOS
# -------------------------------------------------------------

class FacturaCompra(TenantAwareModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_factura = models.CharField(max_length=100)
    proveedor = models.CharField(max_length=255)
    fecha_emision = models.DateField(default=timezone.now)
    monto_total_neto = models.DecimalField(max_digits=12, decimal_places=2)
    observaciones = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    id_usuario_registro = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='facturas_registradas')

    class Meta:
        db_table = 'facturas_compra'
        constraints = [
            models.UniqueConstraint(fields=['id_empresa', 'numero_factura', 'proveedor'], name='unique_factura_proveedor_per_tenant')
        ]

    def __str__(self):
        return f"Factura {self.numero_factura} - {self.proveedor} (${self.monto_total_neto})"

class GastoProyecto(TenantAwareModel):
    TIPOS_GASTO = (
        ('Material', 'Material'),
        ('Ferreteria_Imprevista', 'Ferretería Imprevista'),
        ('Flete', 'Flete'),
        ('Subcontrato', 'Subcontrato'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_factura_compra = models.ForeignKey(FacturaCompra, on_delete=models.CASCADE, related_name='gastos_distribuidos')
    id_proyecto = models.ForeignKey(Proyecto, on_delete=models.RESTRICT, related_name='gastos')
    descripcion = models.CharField(max_length=255)
    tipo_gasto = models.CharField(max_length=50, choices=TIPOS_GASTO)
    monto_neto_asignado = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_gasto = models.DateTimeField(auto_now_add=True)
    id_usuario_registro = models.ForeignKey(Usuario, on_delete=models.RESTRICT, related_name='gastos_registrados')

    class Meta:
        db_table = 'gastos_proyecto'

# -------------------------------------------------------------
# 11. HITOS DE PAGO Y COBRANZAS
# -------------------------------------------------------------

class PagoProyecto(TenantAwareModel):
    TIPOS_PAGO = (
        ('Anticipo_50', 'Anticipo 50%'),
        ('Avance_30', 'Avance 30%'),
        ('Saldo_20', 'Saldo contra Entrega 20%'),
    )
    METODOS = (
        ('Transferencia', 'Transferencia'),
        ('Efectivo', 'Efectivo'),
        ('Tarjeta', 'Tarjeta'),
        ('Cheque', 'Cheque'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_proyecto = models.ForeignKey(Proyecto, on_delete=models.RESTRICT, related_name='pagos')
    tipo_pago = models.CharField(max_length=50, choices=TIPOS_PAGO)
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(max_length=50, choices=METODOS, blank=True, null=True)
    pagado = models.BooleanField(default=False)
    referencia_transaccion = models.CharField(max_length=255, blank=True, null=True)
    fecha_pago = models.DateTimeField(blank=True, null=True)
    id_usuario_registro = models.ForeignKey(Usuario, on_delete=models.RESTRICT, null=True, blank=True)

    class Meta:
        db_table = 'pagos_proyecto'

# -------------------------------------------------------------
# 12. AUDITORÍA Y TRAZABILIDAD EN BASE DE DATOS
# -------------------------------------------------------------

class AuditoriaLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs_auditoria')
    id_usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='acciones_auditadas')
    accion = models.CharField(max_length=100) # Ej: REGISTRO_EMPRESA, CREAR_COTIZACION, APROBAR_OT, CREAR_FACTURA, BORRADO_LOGICO
    detalles = models.TextField(blank=True, null=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auditoria_logs'
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"[{self.fecha_registro}] {self.accion} por {self.id_usuario}"
```

  

