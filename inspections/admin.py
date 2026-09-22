from django.contrib import admin
from .models import ToolCart, DrawerTool, Inspection5S, InspectionMissingItem

class DrawerToolInline(admin.TabularInline):
    model = DrawerTool
    extra = 1

@admin.register(ToolCart)
class ToolCartAdmin(admin.ModelAdmin):
    list_display = ('codigo_carro', 'nombre_carro', 'categoria', 'area', 'supervisor_responsable', 'total_herramientas', 'estado_general')
    list_filter = ('area', 'categoria', 'estado_general')
    search_fields = ('codigo_carro', 'nombre_carro', 'supervisor_responsable', 'area')
    inlines = [DrawerToolInline]

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
