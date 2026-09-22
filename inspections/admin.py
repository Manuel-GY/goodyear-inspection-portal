from django.conf import settings
from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from .models import ToolCart, DrawerTool, Inspection5S, InspectionMissingItem
from .importer import import_carts_from_upload, ImportError_
import logging

logger = logging.getLogger(__name__)

# Personalización de títulos del panel administrativo
admin.site.site_header = "Portal de Inspección de Carros 5S — Goodyear"
admin.site.site_title = "Goodyear 5S Admin"
admin.site.index_title = "Administración de Flota, Gavetas y Auditorías 5S"


class DrawerToolInline(admin.TabularInline):
    model = DrawerTool
    extra = 1
    fields = ('numero_gaveta', 'nombre_herramienta', 'orden_posicion')
    ordering = ('numero_gaveta', 'orden_posicion')


@admin.register(ToolCart)
class ToolCartAdmin(admin.ModelAdmin):
    list_display = ('codigo_carro', 'nombre_carro', 'categoria', 'area', 'supervisor_responsable', 'total_herramientas', 'estado_general')
    list_filter = ('area', 'categoria', 'estado_general')
    search_fields = ('codigo_carro', 'nombre_carro', 'supervisor_responsable', 'area', 'ubicacion_especifica')
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
            max_upload_size = getattr(settings, 'IMPORT_MAX_FILE_SIZE', 10 * 1024 * 1024)
            if uploaded_file.size > max_upload_size:
                messages.error(request, "El archivo supera el tamaño máximo permitido.")
                return redirect('..')

            try:
                imported_carts, imported_tools = import_carts_from_upload(
                    uploaded_file,
                    max_rows=getattr(settings, 'IMPORT_MAX_ROWS', 5000),
                )
            except ImportError_ as e:
                messages.error(request, str(e))
                return redirect('..')
            except UnicodeDecodeError:
                messages.error(request, "El archivo CSV debe usar codificación UTF-8.")
                return redirect('..')
            except Exception:
                logger.exception('Error al procesar archivo en el administrador')
                messages.error(request, "Error interno al procesar el archivo.")
                return redirect('..')

            messages.success(
                request,
                f"¡Importación Exitosa! Se procesaron {imported_carts} carros y {imported_tools} herramientas en la base de datos.",
            )
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
    list_select_related = ('cart',)


class InspectionMissingItemInline(admin.TabularInline):
    model = InspectionMissingItem
    extra = 0
    readonly_fields = ('fecha_registro',)


@admin.register(Inspection5S)
class Inspection5SAdmin(admin.ModelAdmin):
    list_display = ('folio', 'codigo_carro', 'area', 'nombre_auditor', 'responsable_carro_auditado', 'estado_dictamen', 'total_verificadas', 'total_herramientas', 'fecha_inspeccion')
    list_filter = ('estado_dictamen', 'area', 'fecha_inspeccion')
    search_fields = ('folio', 'codigo_carro', 'nombre_auditor', 'responsable_carro_auditado', 'supervisor_responsable')
    list_select_related = ('cart',)
    inlines = [InspectionMissingItemInline]
    date_hierarchy = 'fecha_inspeccion'
