import logging
import urllib.request
import json
from decimal import Decimal
from django.core.exceptions import ValidationError
from .models import MaterialGlobal, Material
from apps.core_auth.models import AuditoriaLog

logger = logging.getLogger('saas_taller')


def _extraer_materiales_en_vivo_imperial():
    """
    Consulta la API REST pública de Oracle Commerce Cloud de Imperial Chile (/ccstore/v1/)
    y extrae en tiempo real los productos, SKUs reales, categorías, unidades de medida y precios.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    search_terms = [
        'melamina', 'terciado', 'osb', 'mdf', 'aglomerado', 'pino', 'madera',
        'bisagra', 'corredera', 'soberbio', 'tornillo', 'cola', 'tapacanto', 'herraje'
    ]

    productos_encontrados = {}

    # 1. Búsqueda de SKUs por términos clave en el catálogo de Imperial
    for term in search_terms:
        search_url = f'https://www.imperial.cl/ccstore/v1/search?Ntt={term}&totalResults=40'
        try:
            req = urllib.request.Request(search_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as res:
                data = json.loads(res.read().decode('utf-8'))
                records = data.get('resultsList', {}).get('records', [])
                for r in records:
                    sub = r.get('records', [{}])[0].get('attributes', {})
                    pid = sub.get('product.repositoryId', [None])[0]
                    name = sub.get('product.displayName', [None])[0]
                    if pid and name and pid not in productos_encontrados:
                        productos_encontrados[pid] = name
        except Exception as e:
            logger.warning(f"Error al buscar término '{term}' en Imperial Chile API: {e}")

    materiales_extraidos = []

    # 2. Obtención de detalle de precio y atributos de cada producto
    for pid, display_name in productos_encontrados.items():
        detail_url = f'https://www.imperial.cl/ccstore/v1/products/{pid}'
        try:
            req = urllib.request.Request(detail_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as res:
                pdata = json.loads(res.read().decode('utf-8'))

                skus = pdata.get('childSKUs', [])
                price = None
                if skus:
                    s0 = skus[0]
                    price = s0.get('listPrice') or s0.get('salePrice') or s0.get('listPrices', {}).get('_default_price_book')
                if not price:
                    price = pdata.get('listPrice') or pdata.get('salePrice') or pdata.get('listPrices', {}).get('_default_price_book')

                if not price or float(price) <= 0:
                    continue

                # Determinar Categoría
                name_lower = display_name.lower()
                if any(w in name_lower for w in ['melamina', 'terciado', 'osb', 'mdf', 'aglomerado', 'durolac', 'plancha', 'trupan', 'chapa']):
                    categoria = 'Tableros'
                elif any(w in name_lower for w in ['pino', 'madera', 'liston', 'viga', 'caña', 'taco', 'puntal']):
                    categoria = 'Maderas'
                elif any(w in name_lower for w in ['bisagra', 'corredera', 'telescopica', 'jaladera', 'tirador', 'piston', 'herraje', 'cierre', 'riel', 'pomo', 'cerradura', 'soporte']):
                    categoria = 'Quincalleria'
                else:
                    categoria = 'Insumos'

                # Determinar Unidad de Medida
                if categoria == 'Tableros':
                    unidad = 'Plancha'
                elif any(w in name_lower for w in [' (par)', ' par', 'pares']):
                    unidad = 'Par'
                elif any(w in name_lower for w in ['caja', 'cajas']):
                    unidad = 'Caja'
                elif any(w in name_lower for w in ['rollo', 'rollos']):
                    unidad = 'Rollo'
                elif any(w in name_lower for w in ['paquete', 'paquetes']):
                    unidad = 'Paquete'
                elif any(w in name_lower for w in ['bolsa', 'bolsas']):
                    unidad = 'Bolsa'
                elif any(w in name_lower for w in ['juego', 'juegos', 'set']):
                    unidad = 'Juego'
                elif any(w in name_lower for w in ['3mt', '3m', '2.44m', 'metro', 'ml']):
                    unidad = 'ML'
                else:
                    unidad = 'Unidad'

                materiales_extraidos.append({
                    'sku': str(pid),
                    'nombre': display_name,
                    'categoria': categoria,
                    'unidad_medida': unidad,
                    'precio': float(price)
                })
        except Exception as e:
            logger.warning(f"Error extrayendo detalle del producto Imperial SKU {pid}: {e}")

    logger.info(f"Scraping en vivo completado: {len(materiales_extraidos)} materiales procesados desde Imperial Chile.")
    return materiales_extraidos


def ejecutar_scraping_imperial(use_mock=False):
    """
    Realiza el raspado (scraping) de productos en vivo desde la API de Imperial Chile.
    Actualiza el Catálogo Maestro (MaterialGlobal) y propaga los precios actualizados
    a los materiales importados por cada taller.
    """
    logger.info(f"Iniciando tarea de scraping de Imperial (use_mock={use_mock})...")

    materiales_datos = []

    if not use_mock:
        try:
            materiales_datos = _extraer_materiales_en_vivo_imperial()
        except Exception as e:
            logger.error(f"Error crítico en scraping en vivo de Imperial: {e}")

    # Fallback si no se obtuvo ningún producto o si use_mock es True
    if not materiales_datos:
        logger.warning("Usando set de respaldo de materiales...")
        materiales_datos = [
            {'sku': '115846', 'nombre': 'Melamina blanca 15mm 1,83x2,50mt', 'categoria': 'Tableros', 'unidad_medida': 'Plancha', 'precio': 37900.00},
            {'sku': '115847', 'nombre': 'Melamina blanca 18mm 1,83x2,50mt', 'categoria': 'Tableros', 'unidad_medida': 'Plancha', 'precio': 42900.00},
            {'sku': '126432', 'nombre': 'Bisagra recta 35 mm 2 unidades con tornillos', 'categoria': 'Quincalleria', 'unidad_medida': 'Par', 'precio': 790.00},
            {'sku': '125031', 'nombre': 'Telescopica H35-estandar zincado 25kg 400mm', 'categoria': 'Quincalleria', 'unidad_medida': 'Par', 'precio': 1890.00},
            {'sku': '118607', 'nombre': 'Soberbio 3/16x2" 100uds', 'categoria': 'Insumos', 'unidad_medida': 'Caja', 'precio': 3090.00},
            {'sku': '75943',  'nombre': '1/2 caña pino MC7 20x20x3mt', 'categoria': 'Maderas', 'unidad_medida': 'ML', 'precio': 1490.00},
        ]

    total_actualizados = 0
    total_creados = 0

    for item in materiales_datos:
        precio_decimal = Decimal(str(item['precio']))
        try:
            # Comprobar si el producto ya existe en el catálogo global
            mg = MaterialGlobal.objects.get(sku_proveedor=item['sku'])
            old_price = mg.costo_unitario

            # Actualizar datos del producto global
            mg.nombre = item['nombre']
            mg.categoria = item['categoria']
            mg.unidad_medida = item['unidad_medida']
            mg.costo_unitario = precio_decimal
            mg.save()

            if old_price != precio_decimal:
                total_actualizados += 1
                # Propagar cambio de precio a los materiales importados del taller con actualización automática activa
                materiales_talleres = Material.objects.filter(
                    material_global=mg,
                    actualizacion_automatica=True
                )
                count = 0
                for mat in materiales_talleres:
                    mat.costo_unitario = precio_decimal
                    mat.save()
                    count += 1
                logger.info(
                    f"Precio del SKU: {mg.sku_proveedor} cambió de ${old_price} a ${precio_decimal}. "
                    f"Propagado a {count} talleres."
                )
        except MaterialGlobal.DoesNotExist:
            # Crear producto nuevo en el catálogo global (auto-genera sku_interno en save)
            MaterialGlobal.objects.create(
                sku_proveedor=item['sku'],
                nombre=item['nombre'],
                categoria=item['categoria'],
                unidad_medida=item['unidad_medida'],
                costo_unitario=precio_decimal,
                proveedor='Imperial'
            )
            total_creados += 1

    logger.info(f"Scraping completado. Creados: {total_creados}, Actualizados: {total_actualizados}")
    return total_creados, total_actualizados


def importar_material_a_taller(material_global_id, empresa, usuario=None):
    """
    Clona un material global del catálogo maestro al catálogo privado de la empresa (tenant).
    """
    try:
        material_global = MaterialGlobal.objects.get(id=material_global_id)
    except MaterialGlobal.DoesNotExist:
        raise ValidationError("El material global seleccionado no existe.")

    # Validar si ya está importado
    if Material.objects.filter(id_empresa=empresa, sku_proveedor=material_global.sku_proveedor).exists():
        raise ValidationError("Este material ya ha sido importado previamente por el taller.")

    # Crear la copia privada en el inventario del taller
    material_taller = Material.objects.create(
        id_empresa=empresa,
        nombre=material_global.nombre,
        categoria=material_global.categoria,
        unidad_medida=material_global.unidad_medida,
        costo_unitario=material_global.costo_unitario,
        porcentaje_merma_defecto=Decimal('10.00'),  # Merma predeterminada en taller (10%)
        proveedor=material_global.proveedor,
        material_global=material_global,
        sku_proveedor=material_global.sku_proveedor,
        actualizacion_automatica=True
    )

    # Registro en Auditoría
    AuditoriaLog.objects.create(
        id_empresa=empresa,
        id_usuario=usuario,
        accion='IMPORTAR_MATERIAL_GLOBAL',
        detalles=f"Material global '{material_global.nombre}' (SKU real: {material_global.sku_proveedor} | SKU interno: {material_global.sku_interno}) importado al catálogo privado."
    )

    return material_taller
