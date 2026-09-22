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
