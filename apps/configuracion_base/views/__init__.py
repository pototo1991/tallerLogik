from .clientes_views import (
    ClienteListView,
    ClienteCreateView,
    ClienteUpdateView,
    ClienteDeleteView,
)
from .proveedores_views import (
    ProveedorListView,
    ProveedorCreateView,
    ProveedorUpdateView,
    ProveedorDeleteView,
)
from .materiales_views import (
    MaterialListView,
    MaterialCreateView,
    MaterialUpdateView,
    MaterialDeleteView,
    MaterialAjustarStockView,
    MaterialHistorialMovimientosView,
)
from .operarios_views import (
    OperarioListView,
    OperarioCreateView,
    OperarioUpdateView,
    OperarioResetPasswordView,
    OperarioToggleActivoView,
)
from .scraping_views import (
    MaterialGlobalBuscarView,
    MaterialImportarActionView,
    EjecutarScrapingManualView,
    ScrapingTaskStatusView,
    tarea_scraping_manual_async,
    AsyncResult,
)
from .bancos_views import (
    BancoListView,
    BancoCreateView,
    BancoUpdateView,
    BancoDeleteView,
)
from .servicios_views import (
    ServicioTarifaListView,
    ServicioTarifaCreateView,
    ServicioTarifaUpdateView,
    ServicioTarifaDeleteView,
)
from .importacion_views import (
    ImportarExcelView,
)

__all__ = [
    'ClienteListView',
    'ClienteCreateView',
    'ClienteUpdateView',
    'ClienteDeleteView',
    'ProveedorListView',
    'ProveedorCreateView',
    'ProveedorUpdateView',
    'ProveedorDeleteView',
    'MaterialListView',
    'MaterialCreateView',
    'MaterialUpdateView',
    'MaterialDeleteView',
    'MaterialAjustarStockView',
    'MaterialHistorialMovimientosView',
    'OperarioListView',
    'OperarioCreateView',
    'OperarioUpdateView',
    'OperarioResetPasswordView',
    'OperarioToggleActivoView',
    'MaterialGlobalBuscarView',
    'MaterialImportarActionView',
    'EjecutarScrapingManualView',
    'ScrapingTaskStatusView',
    'BancoListView',
    'BancoCreateView',
    'BancoUpdateView',
    'BancoDeleteView',
    'ServicioTarifaListView',
    'ServicioTarifaCreateView',
    'ServicioTarifaUpdateView',
    'ServicioTarifaDeleteView',
    'ImportarExcelView',
]
