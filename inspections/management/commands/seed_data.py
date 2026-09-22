from django.core.management.base import BaseCommand
from inspections.models import ToolCart, DrawerTool
import json

DRAWER_STRUCTURE = {
    'TURNO': {
        1: ["Juego Llaves Combinadas 8-24mm", "Chicharra 1/2\"", "Dados de Impacto 17, 19, 21mm", "Extensión 1/2\" x 5\"", "Maneral de Fuerza"],
        2: ["Destornillador Paleta 6x100mm", "Destornillador Cruz PH2", "Alicate de Corte Diagonal", "Alicate Universal 8\"", "Juego Llaves Allen 1.5-10mm"],
        3: ["Martillo de Bola 500g", "Martillo de Goma Antirebote", "Cincel Plano de Ajuste", "Cepillo de Cerdas de Acero", "Botadores de Precisión"],
        4: ["Cinta Métrica 5 metros", "Flexómetro de Trabajo", "Manguera Neumática con Acople Rápido", "Pistola de Aire de Limpieza"],
        5: ["Candados LOTO Rojos (2 unidades)", "Pinza de Bloqueo Múltiple", "Tarjeta de Advertencia 5S", "Gafas de Seguridad Transparentes", "Guantes Anticorte Nivel 5"]
    },
    'MECANICO': {
        1: ["Juego Dados 1/2\" Heavy Duty (8-32mm)", "Chicharra Pesada 1/2\" Reversible", "Palanca de Fuerza 1/2\" x 15\"", "Barra de Extensión 10\"", "Adaptador Articulado 1/2\""],
        2: ["Extractor de Rodamientos 3 Patas", "Llaves de Corona Acodadas (10-24mm)", "Llave Ajustable de 10\"", "Llave Ajustable de 12\"", "Alicate Caimán / Presión"],
        3: ["Arco de Sierra de Calar Profesional", "Cinceles Planos de Impacto", "Limas de Ajuste Fino (Redonda y Plana)", "Llave Stilson 14\" para Cañerías"],
        4: ["Pistola Neumática de Impacto 1/2\"", "Manómetro Digital de Presión de Aire", "Aceite Lubricante para Neumáticas", "Acoples Neumáticos de Seguridad"],
        5: ["Torquímetro Calibrado 1/2\" (20-200 Nm)", "Pie de Metro / Calibre Digital", "Kit LOTO Mecánico con Candados de Acero", "Lentes de Impacto y Guantes Cuero"]
    },
    'ELECTRICO': {
        1: ["Multímetro Digital TRMS Calibrado", "Pinza Amperimétrica AC/DC", "Detector de Tensión sin Contacto", "Puntas de Prueba Aisladas 1000V", "Secuencímetro de Fases"],
        2: ["Juego Destornilladores VDE 1000V (PH/Paleta)", "Alicate Universal Aislado 1000V", "Alicate de Corte Diagonal VDE", "Alicate Punta Fina Aislado 1000V", "Pelacables Automático de Precisión"],
        3: ["Crimpadora para Terminales Aislados", "Crimpadora para Punteras Huecas / Ferrules", "Cautín Eléctrico de Estaño 60W", "Extractor de Estaño / Succionador", "Juego Llaves de Tableros Eléctricos"],
        4: ["Guía Pasacables de Nylon 30m", "Cuchillo de Electricista Pelacables", "Rotuladora / Cinta de Marcación", "Termómetro Infrarrojo Digital"],
        5: ["Kit Bloqueo de Disyuntores Eléctricos", "Candados Dieléctricos de Nylon (3 unidades)", "Guantes Dieléctricos Clase 00 con Sobreguante", "Gafas de Seguridad Anti-Arco", "Tarjetas de Bloqueo LOTO"]
    },
    'MECATRONICO': {
        1: ["Multímetro Digital TRMS con Puntas", "Amperímetro de Gancho AC/DC", "Osciloscopio Portátil", "Probador de Continuidad y Fusibles"],
        2: ["Destornilladores Dieléctricos 1000V (PH/Paleta)", "Alicate Pelacables de Precisión", "Crimpadora RJ45 y Ferrules", "Pinza Bruja Antiestática"],
        3: ["Juego Llaves Torx Tamper (T5-T40)", "Juego Llaves Allen de Precisión (1.5-6mm)", "Cautín Portátil de Estaño", "Fundente e Hilo de Estaño"],
        4: ["Probador de Cables de Red UTP/STP", "Limpiador Dieléctrico de Contactos", "Fusibles de Repuesto", "Linterna LED de Inspección Articulada"],
        5: ["Pie de Metro Digital de Precisión", "Candados LOTO Dieléctricos de Nylon", "Tarjetas de Bloqueo de Tablero", "Pulsera Antiestática ESD"]
    }
}

INITIAL_CARTS = [
    # SECCIÓN 1: ÁREA ASRS (12 CARROS)
    {"id": "CH-ASRS-TA", "name": "Carro Turno A (ASRS)", "category": "TURNO", "type": "Carro Operaciones Turno A", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-TB", "name": "Carro Turno B (ASRS)", "category": "TURNO", "type": "Carro Operaciones Turno B", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-TC", "name": "Carro Turno C (ASRS)", "category": "TURNO", "type": "Carro Operaciones Turno C", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-TD", "name": "Carro Turno D (ASRS)", "category": "TURNO", "type": "Carro Operaciones Turno D", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-M01", "name": "Carro Mecánico 01 (ASRS)", "category": "MECANICO", "type": "Carro Mantenimiento Mecánico", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-M02", "name": "Carro Mecánico 02 (ASRS)", "category": "MECANICO", "type": "Carro Mantenimiento Mecánico", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-MT01", "name": "Carro Mecatrónico 01 (ASRS)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-MT02", "name": "Carro Mecatrónico 02 (ASRS)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-MT03", "name": "Carro Mecatrónico 03 (ASRS)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-MT04", "name": "Carro Mecatrónico 04 (ASRS)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-MT05", "name": "Carro Mecatrónico 05 (ASRS)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área ASRS", "with_tools": True},
    {"id": "CH-ASRS-MT06", "name": "Carro Mecatrónico 06 (ASRS)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área ASRS", "with_tools": True},

    # SECCIÓN 2: ÁREA CONSTRUCCIÓN (12 CARROS)
    {"id": "CH-CST-TA", "name": "Carro Turno A (Construcción)", "category": "TURNO", "type": "Carro Operaciones Turno A", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-TB", "name": "Carro Turno B (Construcción)", "category": "TURNO", "type": "Carro Operaciones Turno B", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-TC", "name": "Carro Turno C (Construcción)", "category": "TURNO", "type": "Carro Operaciones Turno C", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-TD", "name": "Carro Turno D (Construcción)", "category": "TURNO", "type": "Carro Operaciones Turno D", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-MT01", "name": "Carro Mecatrónico 01 (Construcción)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-MT02", "name": "Carro Mecatrónico 02 (Construcción)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-MT03", "name": "Carro Mecatrónico 03 (Construcción)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-MT04", "name": "Carro Mecatrónico 04 (Construcción)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-MT05", "name": "Carro Mecatrónico 05 (Construcción)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-MT06", "name": "Carro Mecatrónico 06 (Construcción)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-MT07", "name": "Carro Mecatrónico 07 (Construcción)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área Construcción", "with_tools": False},
    {"id": "CH-CST-MT08", "name": "Carro Mecatrónico 08 (Construcción)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área Construcción", "with_tools": False},

    # SECCIÓN 3: ÁREA FINAL FINISH (4 CARROS)
    {"id": "CH-FF-TA", "name": "Carro Turno A (Final Finish)", "category": "TURNO", "type": "Carro Operaciones Turno A", "area": "Área Final Finish", "with_tools": False},
    {"id": "CH-FF-TB", "name": "Carro Turno B (Final Finish)", "category": "TURNO", "type": "Carro Operaciones Turno B", "area": "Área Final Finish", "with_tools": False},
    {"id": "CH-FF-M01", "name": "Carro Mecánico 01 (Final Finish)", "category": "MECANICO", "type": "Carro Mantenimiento Mecánico", "area": "Área Final Finish", "with_tools": False},
    {"id": "CH-FF-MT01", "name": "Carro Mecatrónico 01 (Final Finish)", "category": "MECATRONICO", "type": "Carro Mecatrónico / Automatización", "area": "Área Final Finish", "with_tools": False},
]

class Command(BaseCommand):
    help = 'Carga la flota inicial de 28 carros Goodyear y sus herramientas oficiales 5S'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("Sembrando datos oficiales de la flota Goodyear (28 carros)..."))

        for c_data in INITIAL_CARTS:
            cart, created = ToolCart.objects.get_or_create(
                codigo_carro=c_data["id"],
                defaults={
                    "nombre_carro": c_data["name"],
                    "categoria": c_data["category"],
                    "especialidad_tipo": c_data["type"],
                    "area": c_data["area"],
                    "ubicacion_especifica": "Bahía de Mantenimiento Planta Goodyear",
                    "supervisor_responsable": "Juanito Arias",
                    "estado_general": "OK" if c_data["with_tools"] else "Sin Configurar",
                    "fotos_gavetas_json": "{}"
                }
            )

            # Si el carro tiene herramientas preconfiguradas y aún no tiene herramientas cargadas
            if c_data["with_tools"] and cart.tools.count() == 0:
                cat_drawers = DRAWER_STRUCTURE.get(c_data["category"], {})
                for drawer_num, tool_list in cat_drawers.items():
                    for idx, tool_name in enumerate(tool_list, start=1):
                        DrawerTool.objects.create(
                            cart=cart,
                            numero_gaveta=drawer_num,
                            nombre_herramienta=tool_name,
                            orden_posicion=idx
                        )
                cart.recalculate_tool_count()

        self.stdout.write(self.style.SUCCESS(f"¡Éxito! Total de carros en base de datos: {ToolCart.objects.count()}"))
