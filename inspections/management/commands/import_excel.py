from django.core.management.base import BaseCommand
from django.db import transaction
from inspections.models import ToolCart, DrawerTool
import os, csv

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

class Command(BaseCommand):
    help = 'Importa carros y herramientas desde un archivo Excel (.xlsx) o CSV'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Ruta al archivo Excel (.xlsx) o CSV')

    def handle(self, *args, **options):
        file_path = options['file_path']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"El archivo {file_path} no existe."))
            return

        self.stdout.write(self.style.NOTICE(f"Iniciando importación desde: {file_path}..."))

        imported_carts = 0
        imported_tools = 0

        if file_path.endswith('.xlsx'):
            if not HAS_OPENPYXL:
                self.stdout.write(self.style.ERROR("openpyxl no está instalado. Ejecute: pip install openpyxl"))
                return
            wb = openpyxl.load_workbook(file_path, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                self.stdout.write(self.style.WARNING("El archivo Excel está vacío."))
                return

            header = [str(cell).strip().lower() if cell is not None else '' for cell in rows[0]]
            data_rows = rows[1:]
        else:
            with open(file_path, mode='r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                rows = list(reader)
                if not rows:
                    self.stdout.write(self.style.WARNING("El archivo CSV está vacío."))
                    return
                header = [str(cell).strip().lower() for cell in rows[0]]
                data_rows = rows[1:]

        # Mapeo flexible de columnas
        col_map = {}
        for idx, raw_col in enumerate(header):
            col = str(raw_col).replace('_', ' ').replace('-', ' ').strip().lower()
            if 'codigo' in col or 'código' in col or 'id' in col:
                col_map['codigo'] = idx
            elif 'nombre' in col or 'carro' in col:
                col_map['nombre'] = idx
            elif 'categor' in col:
                col_map['categoria'] = idx
            elif 'area' in col or 'área' in col:
                col_map['area'] = idx
            elif 'superv' in col:
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

        if 'codigo' not in col_map:
            self.stdout.write(self.style.ERROR("No se encontró la columna 'codigo_carro' en el archivo."))
            return

        with transaction.atomic():
            for row in data_rows:
                if not any(row):
                    continue

                codigo = str(row[col_map['codigo']]).strip().upper() if col_map.get('codigo') is not None and row[col_map['codigo']] else ''
                if not codigo or codigo.lower() in ['none', 'null']:
                    continue

                nombre = str(row[col_map.get('nombre', 0)]).strip() if col_map.get('nombre') is not None and row[col_map.get('nombre')] else codigo
                categoria = str(row[col_map.get('categoria', 0)]).strip().upper() if col_map.get('categoria') is not None and row[col_map.get('categoria')] else 'TURNO'
                if categoria not in ['TURNO', 'MECANICO', 'ELECTRICO', 'MECATRONICO']:
                    categoria = 'TURNO'

                area = str(row[col_map.get('area', 0)]).strip() if col_map.get('area') is not None and row[col_map.get('area')] else 'Planta Goodyear'
                supervisor = str(row[col_map.get('supervisor', 0)]).strip() if col_map.get('supervisor') is not None and row[col_map.get('supervisor')] else 'Juanito Arias'
                ubicacion = str(row[col_map.get('ubicacion', 0)]).strip() if col_map.get('ubicacion') is not None and row[col_map.get('ubicacion')] else 'Bahía de Mantenimiento'

                cart, created = ToolCart.objects.update_or_create(
                    codigo_carro=codigo,
                    defaults={
                        'nombre_carro': nombre,
                        'categoria': categoria,
                        'especialidad_tipo': f"Carro {categoria}",
                        'area': area,
                        'supervisor_responsable': supervisor,
                        'ubicacion_especifica': ubicacion,
                    }
                )
                imported_carts += 1

                for g_num in range(1, 6):
                    g_key = f"g{g_num}"
                    if col_map.get(g_key) is not None and row[col_map[g_key]]:
                        raw_tools = str(row[col_map[g_key]]).replace(';', '\n').replace(',', '\n')
                        tools_list = [t.strip() for t in raw_tools.split('\n') if t.strip()]

                        if tools_list:
                            cart.tools.filter(numero_gaveta=g_num).delete()
                            tools_to_create = [
                                DrawerTool(
                                    cart=cart,
                                    numero_gaveta=g_num,
                                    nombre_herramienta=tool_name,
                                    orden_posicion=idx
                                )
                                for idx, tool_name in enumerate(tools_list, start=1)
                            ]
                            DrawerTool.objects.bulk_create(tools_to_create)
                            imported_tools += len(tools_to_create)

                cart.recalculate_tool_count()

        self.stdout.write(self.style.SUCCESS(f"¡Importación completada! Carros procesados: {imported_carts}, Herramientas cargadas: {imported_tools}"))
