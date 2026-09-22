import csv
import io
import logging

from django.db import transaction
from django.db.models import Count

from .models import ToolCart, DrawerTool
from .utils import generate_cart_code_and_name

logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None

MAX_IMPORT_ROWS = 5000

DEFAULT_SUPERVISOR = 'Juanito Arias'
DEFAULT_UBICACION = 'Bahía de Mantenimiento'


class ImportError_(Exception):
    """Error de negocio en la importación, apto para mostrarse al usuario."""


def _parse_tabular(uploaded_file, file_name, max_rows):
    """Normaliza un .xlsx o .csv a (header, data_rows)."""
    if file_name.endswith('.xlsx'):
        if openpyxl is None:
            raise ImportError_("openpyxl no está instalado en el servidor.")
        wb = openpyxl.load_workbook(uploaded_file, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise ImportError_("El archivo Excel está vacío.")
        header = [str(c).strip().lower() if c is not None else '' for c in rows[0]]
        data_rows = rows[1:]
    elif file_name.endswith('.csv'):
        content = uploaded_file.read().decode('utf-8-sig')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            raise ImportError_("El archivo CSV está vacío.")
        header = [str(c).strip().lower() for c in rows[0]]
        data_rows = rows[1:]
    else:
        raise ImportError_("Formato no compatible. Por favor suba un archivo .xlsx o .csv.")

    if len(data_rows) > max_rows:
        raise ImportError_("El archivo supera el número máximo de filas permitido.")

    return header, data_rows


def _map_columns(header):
    """Detecta las columnas relevantes del archivo por patrón de nombre."""
    col_map = {}
    for idx, raw_col in enumerate(header):
        col = str(raw_col).replace('_', ' ').replace('-', ' ').strip().lower()
        if 'tipo' in col or 'categor' in col:
            col_map['tipo'] = idx
        elif 'turno' in col or 'numero' in col or 'número' in col or 'nro' in col:
            col_map['turno_num'] = idx
        elif 'codigo' in col or 'código' in col or 'id' in col:
            col_map['codigo'] = idx
        elif 'nombre' in col:
            col_map['nombre'] = idx
        elif 'area' in col or 'área' in col:
            col_map['area'] = idx
        elif 'superv' in col or 'responsable' in col:
            col_map['supervisor'] = idx
        elif 'ubicac' in col:
            col_map['ubicacion'] = idx
        elif 'gaveta 1' in col or 'g1' in col or 'gaveta1' in col:
            col_map['g1'] = idx
        elif 'gaveta 2' in col or 'g2' in col or 'gaveta2' in col:
            col_map['g2'] = idx
        elif 'gaveta 3' in col or 'g3' in col or 'gaveta3' in col:
            col_map['g3'] = idx
        elif 'gaveta 4' in col or 'g4' in col or 'gaveta4' in col:
            col_map['g4'] = idx
        elif 'gaveta 5' in col or 'g5' in col or 'gaveta5' in col:
            col_map['g5'] = idx

    if 'tipo' not in col_map and 'codigo' not in col_map and 'area' not in col_map:
        raise ImportError_(
            "No se encontraron columnas requeridas ('tipo_carro', 'area' o 'codigo_carro') en el archivo."
        )
    return col_map


def _cell(row, col_map, key, default):
    idx = col_map.get(key)
    if idx is None:
        return default
    value = row[idx] if idx < len(row) else None
    if value is None or value == '':
        return default
    return str(value).strip()


def _sync_tool_counters(carts):
    """Recalcula total_herramientas y estado_general con una sola consulta agregada."""
    if not carts:
        return
    counts = {
        row['cart_id']: row['total']
        for row in DrawerTool.objects.filter(cart_id__in=carts).values('cart_id').annotate(total=Count('id'))
    }
    for cart in carts:
        count = counts.get(cart.id, 0)
        cart.total_herramientas = count
        if count == 0:
            cart.estado_general = 'Sin Configurar'
        elif cart.estado_general == 'Sin Configurar':
            cart.estado_general = 'OK'
    ToolCart.objects.bulk_update(carts, ['total_herramientas', 'estado_general'])


def import_carts_from_upload(uploaded_file, max_rows=MAX_IMPORT_ROWS):
    """Importa carros y herramientas desde un .xlsx o .csv. Transaccional.

    Devuelve (imported_carts, imported_tools).
    """
    file_name = uploaded_file.name.lower()
    header, data_rows = _parse_tabular(uploaded_file, file_name, max_rows)
    col_map = _map_columns(header)

    imported_carts = 0
    imported_tools = 0

    with transaction.atomic():
        touched_carts = []
        for row in data_rows:
            if not any(row):
                continue

            raw_tipo = _cell(row, col_map, 'tipo', 'TURNO')
            raw_turno_num = _cell(row, col_map, 'turno_num', 'A')
            raw_area = _cell(row, col_map, 'area', 'Planta')
            manual_codigo = _cell(row, col_map, 'codigo', None)
            manual_nombre = _cell(row, col_map, 'nombre', None)

            cart_meta = generate_cart_code_and_name(
                tipo_carro=raw_tipo,
                turno_o_numero=raw_turno_num,
                area_input=raw_area,
                manual_codigo=manual_codigo,
                manual_nombre=manual_nombre,
            )

            codigo = cart_meta['codigo_carro']
            if not codigo or codigo.lower() in ['none', 'null']:
                continue

            supervisor = _cell(row, col_map, 'supervisor', DEFAULT_SUPERVISOR)
            ubicacion = _cell(row, col_map, 'ubicacion', DEFAULT_UBICACION)

            cart, _ = ToolCart.objects.update_or_create(
                codigo_carro=codigo,
                defaults={
                    'nombre_carro': cart_meta['nombre_carro'],
                    'categoria': cart_meta['categoria'],
                    'especialidad_tipo': f"Carro {cart_meta['categoria']}",
                    'area': cart_meta['area'],
                    'supervisor_responsable': supervisor,
                    'ubicacion_especifica': ubicacion,
                },
            )
            imported_carts += 1
            touched_carts.append(cart)

            for g_num in range(1, 6):
                raw_cell = _cell(row, col_map, f'g{g_num}', None)
                if not raw_cell:
                    continue
                raw_tools = raw_cell.replace(';', '\n').replace(',', '\n')
                tools_list = [t.strip() for t in raw_tools.split('\n') if t.strip()]
                if not tools_list:
                    continue
                cart.tools.filter(numero_gaveta=g_num).delete()
                DrawerTool.objects.bulk_create([
                    DrawerTool(
                        cart=cart,
                        numero_gaveta=g_num,
                        nombre_herramienta=tool_name,
                        orden_posicion=idx,
                    )
                    for idx, tool_name in enumerate(tools_list, start=1)
                ])
                imported_tools += len(tools_list)

        _sync_tool_counters(touched_carts)

    return imported_carts, imported_tools