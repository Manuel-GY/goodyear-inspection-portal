from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ToolCart, DrawerTool, Inspection5S, InspectionMissingItem
import json

def index_view(request):
    """Renderiza el portal de inspección 5S."""
    return render(request, 'index.html')

def api_drawer_structure(request):
    """Devuelve la estructura de herramientas estándar por categoría (TURNO, MECANICO, ELECTRICO, MECATRONICO)."""
    from .management.commands.seed_data import DRAWER_STRUCTURE
    return JsonResponse({"status": "success", "drawers": DRAWER_STRUCTURE})

@csrf_exempt
def api_carts_list_create(request):
    """
    GET: Listado completo de carros de herramientas con conteos y gavetas.
    POST: Creación de un nuevo carro de herramientas.
    """
    if request.method == 'GET':
        carts = ToolCart.objects.all()
        data = {}
        for c in carts:
            drawer_photos = {}
            if c.fotos_gavetas_json:
                try:
                    drawer_photos = json.loads(c.fotos_gavetas_json)
                except Exception:
                    drawer_photos = {}

            data[c.codigo_carro] = {
                "name": c.nombre_carro,
                "category": c.categoria,
                "type": c.especialidad_tipo or f"Carro {c.categoria}",
                "area": c.area,
                "toolsCount": c.total_herramientas,
                "status": c.estado_general,
                "supervisor": c.supervisor_responsable,
                "locationDetails": c.ubicacion_especifica,
                "locationPhoto": c.foto_ubicacion_url,
                "drawerPhotos": drawer_photos
            }
        return JsonResponse({"status": "success", "count": len(data), "carts": data})

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
            cart_id = body.get('codigo_carro', '').strip().upper()
            name = body.get('nombre_carro', '').strip()
            category = body.get('categoria', 'TURNO').strip()
            area = body.get('area', 'Planta Goodyear').strip()
            supervisor = body.get('supervisor_responsable', 'Juanito Arias').strip()
            location = body.get('ubicacion_especifica', 'Bahía de Mantenimiento').strip()

            if not cart_id or not name:
                return JsonResponse({"status": "error", "message": "Código y Nombre del carro son obligatorios."}, status=400)

            if ToolCart.objects.filter(codigo_carro=cart_id).exists():
                return JsonResponse({"status": "error", "message": f"Ya existe un carro con código {cart_id}."}, status=400)

            cart_type = f"Carro {category}"
            if category == 'TURNO':
                cart_type = name
            elif category == 'MECANICO':
                cart_type = "Carro Mantenimiento Mecánico"
            elif category == 'ELECTRICO':
                cart_type = "Carro Instrumentación & Eléctrico"
            elif category == 'MECATRONICO':
                cart_type = "Carro Mecatrónico / Automatización"

            cart = ToolCart.objects.create(
                codigo_carro=cart_id,
                nombre_carro=name,
                categoria=category,
                especialidad_tipo=cart_type,
                area=area,
                supervisor_responsable=supervisor,
                ubicacion_especifica=location,
                total_herramientas=0,
                estado_general="Sin Configurar",
                fotos_gavetas_json="{}"
            )

            return JsonResponse({
                "status": "success",
                "message": f"Carro {name} ({cart_id}) creado exitosamente.",
                "cart": {
                    "codigo_carro": cart.codigo_carro,
                    "nombre_carro": cart.nombre_carro,
                    "area": cart.area,
                    "category": cart.categoria,
                    "supervisor": cart.supervisor_responsable
                }
            }, status=201)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


@csrf_exempt
def api_cart_detail_update_delete(request, cart_id):
    """
    GET: Detalle de un carro con todas sus herramientas organizadas por gaveta (1 a 5).
    PUT/PATCH: Actualización de datos generales, fotos o ubicación del carro.
    DELETE: Eliminación del carro de la base de datos.
    """
    cart = get_object_or_404(ToolCart, codigo_carro=cart_id.upper())

    if request.method == 'GET':
        drawers = {1: [], 2: [], 3: [], 4: [], 5: []}
        for tool in cart.tools.all():
            if tool.numero_gaveta in drawers:
                drawers[tool.numero_gaveta].append(tool.nombre_herramienta)

        drawer_photos = {}
        if cart.fotos_gavetas_json:
            try:
                drawer_photos = json.loads(cart.fotos_gavetas_json)
            except Exception:
                drawer_photos = {}

        return JsonResponse({
            "status": "success",
            "cart": {
                "codigo_carro": cart.codigo_carro,
                "nombre_carro": cart.nombre_carro,
                "categoria": cart.categoria,
                "especialidad_tipo": cart.especialidad_tipo,
                "area": cart.area,
                "supervisor_responsable": cart.supervisor_responsable,
                "ubicacion_especifica": cart.ubicacion_especifica,
                "foto_ubicacion_url": cart.foto_ubicacion_url,
                "total_herramientas": cart.total_herramientas,
                "estado_general": cart.estado_general,
                "drawerPhotos": drawer_photos,
                "drawers": drawers
            }
        })

    elif request.method in ['PUT', 'PATCH']:
        try:
            body = json.loads(request.body.decode('utf-8'))
            if 'nombre_carro' in body:
                cart.nombre_carro = body['nombre_carro'].strip()
            if 'categoria' in body:
                cart.categoria = body['categoria'].strip()
            if 'area' in body:
                cart.area = body['area'].strip()
            if 'supervisor_responsable' in body:
                cart.supervisor_responsable = body['supervisor_responsable'].strip()
            if 'ubicacion_especifica' in body:
                cart.ubicacion_especifica = body['ubicacion_especifica'].strip()
            if 'foto_ubicacion_url' in body:
                cart.foto_ubicacion_url = body['foto_ubicacion_url']
            if 'drawerPhotos' in body:
                cart.fotos_gavetas_json = json.dumps(body['drawerPhotos'])
            if 'estado_general' in body:
                cart.estado_general = body['estado_general']

            cart.save()
            return JsonResponse({"status": "success", "message": f"Carro {cart.codigo_carro} actualizado correctamente."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    elif request.method == 'DELETE':
        code = cart.codigo_carro
        cart_name = cart.nombre_carro
        cart.delete()
        return JsonResponse({"status": "success", "message": f"Carro {cart_name} ({code}) eliminado correctamente."})

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


@csrf_exempt
def api_cart_drawer_tools(request, cart_id, drawer_num):
    """
    POST: Actualiza el listado completo de herramientas de una gaveta específica (1 a 5).
    """
    if request.method == 'POST':
        cart = get_object_or_404(ToolCart, codigo_carro=cart_id.upper())
        try:
            body = json.loads(request.body.decode('utf-8'))
            tools_list = body.get('tools', [])

            # Eliminar herramientas actuales de esta gaveta
            cart.tools.filter(numero_gaveta=drawer_num).delete()

            # Insertar las nuevas herramientas
            for idx, tool_name in enumerate(tools_list, start=1):
                clean_name = str(tool_name).strip()
                if clean_name:
                    DrawerTool.objects.create(
                        cart=cart,
                        numero_gaveta=drawer_num,
                        nombre_herramienta=clean_name,
                        orden_posicion=idx
                    )

            cart.recalculate_tool_count()

            return JsonResponse({
                "status": "success",
                "message": f"Gaveta {drawer_num} del carro {cart.codigo_carro} actualizada con {len(tools_list)} herramientas.",
                "total_herramientas": cart.total_herramientas
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


@csrf_exempt
def api_inspections_list_create(request):
    """
    GET: Listado histórico de inspecciones 5S realizadas.
    POST: Registro de una nueva inspección 5S (con firmas digitales y faltantes).
    """
    if request.method == 'GET':
        inspections = Inspection5S.objects.all().order_by('-fecha_inspeccion')
        data = []
        for insp in inspections:
            data.append({
                "folio": insp.folio,
                "date": insp.fecha_inspeccion.strftime('%d/%m/%Y %H:%M'),
                "cartId": insp.codigo_carro,
                "cartName": insp.cart.nombre_carro if insp.cart else insp.codigo_carro,
                "cartArea": insp.area,
                "auditor": insp.nombre_auditor,
                "responsible": insp.responsable_carro_auditado,
                "supervisor": insp.supervisor_responsable,
                "status": insp.estado_dictamen,
                "totalChecked": insp.total_verificadas,
                "totalTools": insp.total_herramientas,
                "missingCount": insp.total_herramientas - insp.total_verificadas if (insp.total_herramientas > insp.total_verificadas) else 0,
                "missingDetails": insp.detalles_faltantes,
                "comments": insp.comentarios_auditor,
                "auditorSign": insp.firma_auditor_base64,
                "respSign": insp.firma_responsable_base64,
                "ldapAuditor": insp.ldap_auditor_id,
                "ldapResp": insp.ldap_responsable_id
            })
        return JsonResponse({"status": "success", "count": len(data), "inspections": data})

    elif request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
            cart_code = body.get('cartId', '').strip().upper()
            cart = ToolCart.objects.filter(codigo_carro=cart_code).first()

            folio = body.get('folio')
            if not folio:
                from datetime import datetime
                folio = f"INS-GY-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            auditor = body.get('auditor', 'Inspector Goodyear').strip()
            responsible = body.get('responsible', 'Mecánico de Turno').strip()
            supervisor = body.get('supervisor', cart.supervisor_responsable if cart else 'Juanito Arias').strip()
            area = body.get('cartArea', cart.area if cart else 'Planta Goodyear').strip()
            status = body.get('status', 'CONFORME 100%').strip()
            total_checked = int(body.get('totalChecked', 0))
            total_tools = int(body.get('totalTools', 0))
            missing_details = body.get('missingDetails', '')
            comments = body.get('comments', '')
            auditor_sign = body.get('auditorSign')
            resp_sign = body.get('respSign')
            ldap_auditor = body.get('ldapAuditor', '')
            ldap_resp = body.get('ldapResp', '')

            insp = Inspection5S.objects.create(
                folio=folio,
                cart=cart,
                codigo_carro=cart_code,
                nombre_auditor=auditor,
                responsable_carro_auditado=responsible,
                supervisor_responsable=supervisor,
                area=area,
                estado_dictamen=status,
                total_verificadas=total_checked,
                total_herramientas=total_tools,
                detalles_faltantes=missing_details,
                comentarios_auditor=comments,
                firma_auditor_base64=auditor_sign,
                firma_responsable_base64=resp_sign,
                ldap_auditor_id=ldap_auditor,
                ldap_responsable_id=ldap_resp
            )

            # Registrar faltantes si vienen desglosados
            missing_items = body.get('missingItemsList', [])
            for item in missing_items:
                InspectionMissingItem.objects.create(
                    inspection=insp,
                    numero_gaveta=int(item.get('drawer', 1)),
                    nombre_herramienta_faltante=str(item.get('tool', '')).strip()
                )

            return JsonResponse({
                "status": "success",
                "message": f"Inspección {folio} registrada exitosamente.",
                "folio": folio
            }, status=201)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


def api_dashboard_stats(request):
    """
    GET: Estadísticas consolidadas para KPIs y gráficos del Dashboard.
    """
    total_carts = ToolCart.objects.count()
    total_audits = Inspection5S.objects.count()

    compliant_count = Inspection5S.objects.filter(
        estado_dictamen__icontains='100%'
    ).count() | Inspection5S.objects.filter(
        estado_dictamen__icontains='CONFORME'
    ).count()

    missing_count = total_audits - compliant_count

    # Distribución por áreas
    areas = {}
    for c in ToolCart.objects.all():
        area_key = c.area or 'Planta Goodyear'
        if area_key not in areas:
            areas[area_key] = {"carts": 0, "audits": 0}
        areas[area_key]["carts"] += 1

    for insp in Inspection5S.objects.all():
        area_key = insp.area or 'Planta Goodyear'
        if area_key not in areas:
            areas[area_key] = {"carts": 0, "audits": 0}
        areas[area_key]["audits"] += 1

    return JsonResponse({
        "status": "success",
        "totalCarts": total_carts,
        "totalAudits": total_audits,
        "compliantAudits": compliant_count,
        "missingAudits": max(0, missing_count),
        "passRate": round((compliant_count / total_audits) * 100) if total_audits > 0 else 0,
        "areas": areas
    })


@csrf_exempt
def api_reset_factory(request):
    """
    POST: Restablece todos los carros y herramientas al estado inicial de fábrica (28 carros).
    """
    if request.method == 'POST':
        try:
            ToolCart.objects.all().delete()
            from django.core.management import call_command
            call_command('seed_data')
            return JsonResponse({
                "status": "success",
                "message": "Base de datos restablecida al estándar oficial de fábrica Goodyear (28 carros)."
            })
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


def api_download_excel_template(request):
    """
    GET: Genera y descarga un archivo Excel (.xlsx) con la plantilla oficial Goodyear.
    """
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

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

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="plantilla_carros_goodyear.xlsx"'
    return response


@csrf_exempt
def api_import_excel(request):
    """
    POST: Importa carros y herramientas desde un archivo Excel (.xlsx) o CSV subido en multipart/form-data.
    """
    if request.method == 'POST':
        if 'file' not in request.FILES:
            return JsonResponse({"status": "error", "message": "No se ha subido ningún archivo."}, status=400)

        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name.lower()

        try:
            import io, csv, openpyxl
            if file_name.endswith('.xlsx'):
                wb = openpyxl.load_workbook(uploaded_file, data_only=True)
                ws = wb.active
                rows = list(ws.iter_rows(values_only=True))
                if not rows:
                    return JsonResponse({"status": "error", "message": "El archivo Excel está vacío."}, status=400)
                header = [str(c).strip().lower() if c is not None else '' for c in rows[0]]
                data_rows = rows[1:]
            elif file_name.endswith('.csv'):
                content = uploaded_file.read().decode('utf-8-sig')
                reader = csv.reader(io.StringIO(content))
                rows = list(reader)
                if not rows:
                    return JsonResponse({"status": "error", "message": "El archivo CSV está vacío."}, status=400)
                header = [str(c).strip().lower() for c in rows[0]]
                data_rows = rows[1:]
            else:
                return JsonResponse({"status": "error", "message": "Formato no compatible. Por favor suba un archivo .xlsx o .csv."}, status=400)

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
                return JsonResponse({"status": "error", "message": "No se encontró la columna 'codigo_carro' en el archivo."}, status=400)

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

            return JsonResponse({
                "status": "success",
                "message": f"¡Importación completada! Se procesaron {imported_carts} carros y {imported_tools} herramientas.",
                "imported_carts": imported_carts,
                "imported_tools": imported_tools,
                "total_carts_db": ToolCart.objects.count()
            })

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error procesando archivo: {str(e)}"}, status=500)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)

