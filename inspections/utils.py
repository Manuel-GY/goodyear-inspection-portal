import re
import unicodedata

def normalize_text(text: str) -> str:
    """Elimina tildes y espacios redundantes."""
    if not text:
        return ""
    text_nfkd = unicodedata.normalize('NFKD', str(text))
    return "".join([c for c in text_nfkd if not unicodedata.combining(c)]).strip()


KNOWN_AREAS = {
    'ASRS': ('ASRS', 'Área ASRS', 'ASRS'),
    'CONSTRUCCION': ('CST', 'Área Construcción', 'Construcción'),
    'CST': ('CST', 'Área Construcción', 'Construcción'),
    'FINAL FINISH': ('FF', 'Área Final Finish', 'Final Finish'),
    'FF': ('FF', 'Área Final Finish', 'Final Finish'),
    'BANBURY': ('BNB', 'Área Banbury', 'Banbury'),
    'BNB': ('BNB', 'Área Banbury', 'Banbury'),
    'VULCANIZACION': ('VLC', 'Área Vulcanización', 'Vulcanización'),
    'VLC': ('VLC', 'Área Vulcanización', 'Vulcanización'),
}


def parse_area(area_input: str):
    """
    Retorna (area_code, area_full_name, area_short_name).
    Ejemplo: 'Construcción' -> ('CST', 'Área Construcción', 'Construcción')
    """
    clean = normalize_text(area_input).upper()
    if clean.startswith('AREA '):
        clean = clean[5:].strip()

    if clean in KNOWN_AREAS:
        return KNOWN_AREAS[clean]

    # Área personalizada
    raw_name = str(area_input).strip() if area_input else 'Planta'
    # Generar código alfanumérico corto (hasta 4 letras)
    code_letters = re.sub(r'[^A-Z0-9]', '', clean)
    code = code_letters[:4] if code_letters else 'GEN'
    full_name = raw_name if raw_name.lower().startswith('área') or raw_name.lower().startswith('area') else f"Área {raw_name}"
    short_name = raw_name.replace('Área ', '').replace('Area ', '').strip()
    return code, full_name, short_name


def generate_cart_code_and_name(tipo_carro: str, turno_o_numero: str, area_input: str, manual_codigo: str = None, manual_nombre: str = None):
    """
    Genera automáticamente el codigo_carro (ej: CH-ASRS-TA, CH-CST-M01)
    y el nombre_carro (ej: Carro Turno A (ASRS), Carro Mecánico 01 (Construcción))
    basado en la categoría, turno/número y área.
    
    Permite sobreescritura manual si se provee manual_codigo o manual_nombre.
    """
    area_code, area_full_name, area_short_name = parse_area(area_input)

    # 1. Normalizar categoría
    tipo_clean = normalize_text(tipo_carro).upper()
    if 'MECATRONIC' in tipo_clean:
        categoria = 'MECATRONICO'
        prefix = 'MT'
        nombre_tipo = 'Carro Mecatrónico'
    elif 'MECANIC' in tipo_clean:
        categoria = 'MECANICO'
        prefix = 'M'
        nombre_tipo = 'Carro Mecánico'
    elif 'ELECTRIC' in tipo_clean:
        categoria = 'ELECTRICO'
        prefix = 'E'
        nombre_tipo = 'Carro Eléctrico'
    else:
        categoria = 'TURNO'
        prefix = 'T'
        nombre_tipo = 'Carro Turno'

    # 2. Generar sufijo y nombre
    val_clean = normalize_text(turno_o_numero).upper()
    
    if categoria == 'TURNO':
        # Detectar letra de turno A, B, C, D o número 1, 2, 3, 4
        turno_letter = 'A'
        for letter in ['A', 'B', 'C', 'D']:
            if letter in val_clean:
                turno_letter = letter
                break
        else:
            # Si introdujeron 1, 2, 3, 4
            digits = re.findall(r'\d+', val_clean)
            if digits:
                num = int(digits[0])
                num_to_letter = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
                turno_letter = num_to_letter.get(num, 'A')

        auto_suffix = f"T{turno_letter}"
        auto_name = f"{nombre_tipo} {turno_letter} ({area_short_name})"
    else:
        # Extraer número (ej: 01, 1, 02)
        digits = re.findall(r'\d+', val_clean)
        num = int(digits[0]) if digits else 1
        num_str = f"{num:02d}"
        auto_suffix = f"{prefix}{num_str}"
        auto_name = f"{nombre_tipo} {num_str} ({area_short_name})"

    auto_codigo = f"CH-{area_code}-{auto_suffix}"

    # Aplicar sobreescritura manual si se suministró explícitamente
    final_codigo = manual_codigo.strip().upper() if (manual_codigo and str(manual_codigo).strip().lower() not in ['none', 'null', '']) else auto_codigo
    final_nombre = manual_nombre.strip() if (manual_nombre and str(manual_nombre).strip().lower() not in ['none', 'null', '']) else auto_name

    return {
        'codigo_carro': final_codigo,
        'nombre_carro': final_nombre,
        'categoria': categoria,
        'area': area_full_name,
        'area_code': area_code
    }
