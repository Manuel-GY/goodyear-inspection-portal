from django.db import models
import json

class ToolCart(models.Model):
    CATEGORIES = [
        ('TURNO', 'Turno Operativo'),
        ('MECANICO', 'Mecánico'),
        ('ELECTRICO', 'Eléctrico / Instrumentación'),
        ('MECATRONICO', 'Mecatrónico / Automatización'),
    ]

    codigo_carro = models.CharField(max_length=50, unique=True, db_index=True)
    nombre_carro = models.CharField(max_length=150)
    categoria = models.CharField(max_length=50, choices=CATEGORIES, default='TURNO')
    especialidad_tipo = models.CharField(max_length=150, blank=True, default='')
    area = models.CharField(max_length=150, default='Planta Goodyear')
    ubicacion_especifica = models.CharField(max_length=200, blank=True, default='Bahía de Mantenimiento')
    foto_ubicacion_url = models.TextField(blank=True, null=True)
    fotos_gavetas_json = models.TextField(blank=True, default='{}') # Dict JSON de fotos {1: "url", 2: "url", ...}
    supervisor_responsable = models.CharField(max_length=150, default='Juanito Arias')
    total_herramientas = models.IntegerField(default=0)
    estado_general = models.CharField(max_length=50, default='OK')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Carro de Herramientas'
        verbose_name_plural = 'Carros de Herramientas'
        ordering = ['codigo_carro']
        indexes = [
            models.Index(fields=['categoria']),
            models.Index(fields=['area']),
        ]

    def __str__(self):
        return f"{self.codigo_carro} - {self.nombre_carro} ({self.area})"

    def recalculate_tool_count(self):
        count = self.tools.count()
        self.total_herramientas = count
        if count == 0:
            self.estado_general = 'Sin Configurar'
        elif self.estado_general == 'Sin Configurar':
            self.estado_general = 'OK'
        self.save(update_fields=['total_herramientas', 'estado_general'])
        return count


class DrawerTool(models.Model):
    cart = models.ForeignKey(ToolCart, on_delete=models.CASCADE, related_name='tools')
    numero_gaveta = models.IntegerField(choices=[(1, 'Gaveta 1'), (2, 'Gaveta 2'), (3, 'Gaveta 3'), (4, 'Gaveta 4'), (5, 'Gaveta 5')])
    nombre_herramienta = models.CharField(max_length=200)
    orden_posicion = models.IntegerField(default=1)

    class Meta:
        verbose_name = 'Herramienta de Gaveta'
        verbose_name_plural = 'Herramientas de Gavetas'
        ordering = ['numero_gaveta', 'orden_posicion', 'id']
        indexes = [
            models.Index(fields=['cart', 'numero_gaveta']),
        ]

    def __str__(self):
        return f"[{self.cart.codigo_carro} G{self.numero_gaveta}] {self.nombre_herramienta}"


class Inspection5S(models.Model):
    folio = models.CharField(max_length=50, unique=True, db_index=True)
    cart = models.ForeignKey(ToolCart, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspections')
    codigo_carro = models.CharField(max_length=50, db_index=True)
    nombre_auditor = models.CharField(max_length=150)
    responsable_carro_auditado = models.CharField(max_length=150)
    supervisor_responsable = models.CharField(max_length=150, default='Juanito Arias')
    area = models.CharField(max_length=150)
    estado_dictamen = models.CharField(max_length=100) # 'CONFORME 100%', 'HERRAMIENTA FALTANTE', 'OBSERVADO'
    total_verificadas = models.IntegerField(default=0)
    total_herramientas = models.IntegerField(default=0)
    detalles_faltantes = models.TextField(blank=True, default='')
    comentarios_auditor = models.TextField(blank=True, default='')
    firma_auditor_base64 = models.TextField(blank=True, null=True)
    firma_responsable_base64 = models.TextField(blank=True, null=True)
    ldap_auditor_id = models.CharField(max_length=50, blank=True, default='')
    ldap_responsable_id = models.CharField(max_length=50, blank=True, default='')
    fecha_inspeccion = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Inspección 5S'
        verbose_name_plural = 'Inspecciones 5S'
        ordering = ['-fecha_inspeccion']
        indexes = [
            models.Index(fields=['codigo_carro', '-fecha_inspeccion']),
        ]

    def __str__(self):
        return f"{self.folio} - {self.codigo_carro} ({self.estado_dictamen}) - {self.fecha_inspeccion.strftime('%d/%m/%Y %H:%M')}"


class InspectionMissingItem(models.Model):
    inspection = models.ForeignKey(Inspection5S, on_delete=models.CASCADE, related_name='missing_items')
    numero_gaveta = models.IntegerField()
    nombre_herramienta_faltante = models.CharField(max_length=200)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Detalle de Faltante'
        verbose_name_plural = 'Detalles de Faltantes'
        indexes = [
            models.Index(fields=['inspection', 'numero_gaveta']),
        ]

    def __str__(self):
        return f"{self.inspection.folio} - G{self.numero_gaveta}: {self.nombre_herramienta_faltante}"
