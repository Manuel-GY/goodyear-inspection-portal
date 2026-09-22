from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from .models import ToolCart, DrawerTool, Inspection5S, InspectionMissingItem
import io, csv, openpyxl

# Personalización de títulos del panel administrativo
admin.site.site_header = "Portal de Inspección de Carros 5S — Goodyear"
admin.site.site_title = "Goodyear 5S Admin"
admin.site.index_title = "Administración de Flota, Gavetas y Auditorías 5S"

class DrawerToolInline(admin.TabularInline):
    model = DrawerTool
    extra = 1

@admin.register(ToolCart)
class ToolCartAdmin(admin.ModelAdmin):
    list_display = ('codigo_carro', 'nombre_carro', 'categoria', 'area', 'supervisor_responsable', 'total_herramientas', 'estado_general')
    list_filter = ('area', 'categoria', 'estado_general')
    search_fields = ('codigo_carro', 'nombre_carro', 'supervisor_responsable', 'area')
    inlines = [DrawerToolInline]
    change_list_template = "admin/inspections/toolcart/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-excel/', self.admin_site.admin_view(self.import_excel_view), name='inspections_toolcart_import_excel'),
        ]
        return custom_urls + urls

    def import_excel_view(self, request):
        if request.method == 'POST':
            if 'file' not in request.FILES:
                messages.error(request, "Por favor seleccione un archivo Excel (.xlsx) o CSV.")
                return redirect('..')

            uploaded_file = request.FILES['file']
            file_name = uploaded_file.name.lower()

            try:
                if file_name.endswith('.xlsx'):
                    wb = openpyxl.load_workbook(uploaded_file, data_only=True)
                    ws = wb.active
                    rows = list(ws.iter_rows(values_only=True))
                    if not rows:
                        messages.error(request, "El archivo Excel está vacío.")
                        return redirect('..')
                    header = [str(c).strip().lower() if c is not None else '' for c in rows[0]]
                    data_rows = rows[1:]
                elif file_name.endswith('.csv'):
                    content = uploaded_file.read().decode('utf-8-sig')
                    reader = csv.reader(io.StringIO(content))
                    rows = list(reader)
                    if not rows:
                        messages.error(request, "El archivo CSV está vacío.")
                        return redirect('..')
                    header = [str(c).strip().lower() for c in rows[0]]
                    data_rows = rows[1:]
                else:
                    messages.error(request, "Formato no compatible. Por favor suba un archivo .xlsx o .csv.")
                    return redirect('..')

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
                    messages.error(request, "No se encontró la columna 'codigo_carro' en el archivo.")
                    return redirect('..')

                imported_carts = 0
                imported_tools = 0

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
                                for idx, tool_name in enumerate(tools_list, start=1):
                                    DrawerTool.objects.create(
                                        cart=cart,
                                        numero_gaveta=g_num,
                                        nombre_herramienta=tool_name,
                                        orden_posicion=idx
                                    )
                                    imported_tools += 1

                    cart.recalculate_tool_count()

                messages.success(request, f"¡Importación Exitosa! Se procesaron {imported_carts} carros y {imported_tools} herramientas en la base de datos.")
                return redirect('..')

            except Exception as e:
                messages.error(request, f"Error al procesar archivo: {str(e)}")
                return redirect('..')

        context = dict(
            self.admin_site.each_context(request),
            title="Importar Carros y Herramientas desde Excel / CSV",
            opts=self.model._meta,
        )
        return render(request, "admin/inspections/toolcart/import_excel.html", context)


@admin.register(DrawerTool)
class DrawerToolAdmin(admin.ModelAdmin):
    list_display = ('cart', 'numero_gaveta', 'nombre_herramienta', 'orden_posicion')
    list_filter = ('numero_gaveta', 'cart__area', 'cart__categoria')
    search_fields = ('nombre_herramienta', 'cart__codigo_carro', 'cart__nombre_carro')

class InspectionMissingItemInline(admin.TabularInline):
    model = InspectionMissingItem
    extra = 0

@admin.register(Inspection5S)
class Inspection5SAdmin(admin.ModelAdmin):
    list_display = ('folio', 'codigo_carro', 'area', 'nombre_auditor', 'responsable_carro_auditado', 'estado_dictamen', 'fecha_inspeccion')
    list_filter = ('estado_dictamen', 'area', 'fecha_inspeccion')
    search_fields = ('folio', 'codigo_carro', 'nombre_auditor', 'responsable_carro_auditado')
    inlines = [InspectionMissingItemInline]
