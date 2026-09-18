from apps.ordenes_trabajo.views import ImportarExcelOTView


class ImportarExcelView(ImportarExcelOTView):
    """
    Punto de entrada en /configuracion/importar-excel/ para la ingesta
    de planillas Excel OT y presupuestos (vía subida web, ruta local o lote nocturno).
    """
    pass
