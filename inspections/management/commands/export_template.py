from django.core.management.base import BaseCommand
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

class Command(BaseCommand):
    help = 'Genera una plantilla Excel modelo (plantilla_carros_goodyear.xlsx) para importar carros'

    def handle(self, *args, **options):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Plantilla Carros 5S"

        headers = [
            "codigo_carro",
            "nombre_carro",
            "categoria",
            "area",
            "supervisor",
            "ubicacion_especifica",
            "gaveta_1_herramientas",
            "gaveta_2_herramientas",
            "gaveta_3_herramientas",
            "gaveta_4_herramientas",
            "gaveta_5_herramientas"
        ]

        ws.append(headers)

        # Estilo de cabecera Goodyear
        header_fill = PatternFill(start_color="0B1D45", end_color="0B1D45", fill_type="solid")
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FBBD00")
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        for col_num, cell in enumerate(ws[1], 1):
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Filas de ejemplo
        sample_rows = [
            [
                "CH-ASRS-TA",
                "Carro Turno A (ASRS)",
                "TURNO",
                "Área ASRS",
                "Juanito Arias",
                "Pasillo Principal Bahía 1",
                "Juego Llaves Combinadas 8-24mm, Chicharra 1/2\", Dados de Impacto 17-21mm",
                "Destornillador Paleta 6x100mm, Destornillador Cruz PH2, Alicate Universal 8\"",
                "Martillo de Bola 500g, Martillo de Goma, Cincel Plano, Cepillo de Acero",
                "Cinta Métrica 5m, Flexómetro de Trabajo, Manguera Neumática, Pistola de Aire",
                "Candados LOTO Rojos (2 un), Pinza Bloqueo, Tarjeta 5S, Gafas de Seguridad"
            ],
            [
                "CH-CST-M01",
                "Carro Mecánico 01 (Construcción)",
                "MECANICO",
                "Área Construcción",
                "Juanito Arias",
                "Bahía Mantenimiento Construcción",
                "Juego Dados 1/2\" Heavy Duty (8-32mm), Chicharra Pesada 1/2\", Palanca de Fuerza",
                "Extractor de Rodamientos 3 Patas, Llaves Corona 10-24mm, Llave Ajustable 12\"",
                "Arco de Sierra Profesional, Cinceles Planos, Limas de Ajuste, Llave Stilson 14\"",
                "Pistola Neumática de Impacto 1/2\", Manómetro Digital, Aceite Lubricante",
                "Torquímetro Calibrado 1/2\" (20-200 Nm), Pie de Metro Digital, Kit LOTO"
            ]
        ]

        for row in sample_rows:
            ws.append(row)

        for row in ws.iter_rows(min_row=2, max_row=len(sample_rows)+1):
            for cell in row:
                cell.font = Font(name="Segoe UI", size=10)
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center", wrap_text=True)

        column_widths = [16, 32, 16, 22, 20, 30, 45, 45, 45, 45, 45]
        for idx, width in enumerate(column_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(idx)].width = width

        output_path = "plantilla_carros_goodyear.xlsx"
        wb.save(output_path)
        self.stdout.write(self.style.SUCCESS(f"Plantilla Excel generada exitosamente en: {output_path}"))
