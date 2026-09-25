from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse, FileResponse
from django.middleware.csrf import get_token
from django.db import transaction
from django.db.models import Count, Q
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.core.paginator import EmptyPage, Paginator
from .models import ToolCart, DrawerTool, Inspection5S, InspectionMissingItem
from .utils import generate_cart_code_and_name
import json
import logging
import os
import io
import csv
import urllib.error
import urllib.request
from functools import wraps

logger = logging.getLogger(__name__)

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


def staff_required_for_methods(*protected_methods):
    """Require an authenticated staff user only for mutating API methods."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.method in protected_methods:
                portal_admin = request.session.get('portal_admin_authenticated') is True
                if not request.user.is_authenticated and not portal_admin:
                    return JsonResponse(
                        {"status": "error", "message": "Autenticación administrativa requerida."},
                        status=401
                    )
                if not portal_admin and not request.user.is_staff:
                    return JsonResponse(
                        {"status": "error", "message": "No tiene permisos administrativos."},
                        status=403
                    )
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def _pagination(request, default_size=50):
    """Return a bounded paginator page number and size from query parameters."""
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(
            max(1, int(request.GET.get('page_size', default_size))),
            getattr(settings, 'API_MAX_PAGE_SIZE', 100),
        )
    except (TypeError, ValueError):
        page_size = default_size
    return page, page_size


def _generic_server_error(logger_name, exc):
    logger.exception('%s: %s', logger_name, exc)
    return JsonResponse(
        {"status": "error", "message": "No fue posible completar la operación."},
        status=500,
    )


def _bounded_text(value, field, max_length, required=False):
    text = str(value or '').strip()
    if required and not text:
        raise ValueError(f"El campo '{field}' es obligatorio.")
    if len(text) > max_length:
        raise ValueError(f"El campo '{field}' supera el máximo permitido.")
    return text


def index_view(request):
    """Renderiza el portal de inspección 5S."""
    get_token(request)
    return render(request, 'index.html')


def logo_view(request):
    """Sirve directamente el logo oficial de Goodyear."""
    logo_path = settings.BASE_DIR / 'static' / 'logo-goodyear.png'
    if not os.path.exists(logo_path):
        logo_path = settings.BASE_DIR / 'logo-goodyear.png'
    if os.path.exists(logo_path):
        return FileResponse(open(logo_path, 'rb'), content_type='image/png')
    return HttpResponse(status=404)


def api_admin_status(request):
    """Indica si la sesión actual puede acceder a la administración del portal."""
    portal_admin = request.session.get('portal_admin_authenticated') is True
    return JsonResponse({
        "authenticated": portal_admin or request.user.is_authenticated,
        "is_staff": portal_admin or request.user.is_staff,
    })


def api_ldap_login(request):
    """Validate corporate credentials through the LDAP gateway and create a Django session."""
    if request.method == 'POST':
        try:
            body = json.loads(request.body.decode('utf-8'))
            username = str(body.get('username', '')).strip().lower()
            password = body.get('password', '')
            if not username or not isinstance(password, str) or not password:
                return JsonResponse(
                    {"status": "error", "message": "Usuario y contraseña son obligatorios."},
                    status=400
                )

            payload = json.dumps({"username": username, "password": password}).encode('utf-8')
            if not settings.LDAP_AUTH_API_URL:
                return JsonResponse(
                    {"status": "error", "message": "El servicio LDAP no está configurado."},
                    status=503
                )
            ldap_request = urllib.request.Request(
                settings.LDAP_AUTH_API_URL,
                data=payload,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(
                ldap_request,
                timeout=settings.LDAP_AUTH_API_TIMEOUT
            ) as ldap_response:
                ldap_result = json.loads(ldap_response.read().decode('utf-8'))

            if ldap_result.get('status') != 'ok':
                return JsonResponse(
                    {"status": "error", "message": "Las credenciales corporativas no son válidas."},
                    status=401
                )
            if ldap_result.get('is_admin') is not True:
                return JsonResponse(
                    {"status": "error", "message": "La cuenta no tiene privilegios administrativos."},
                    status=403
                )

            User = get_user_model()
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'is_staff': False, 'is_active': True}
            )
            user.is_staff = False
            user.is_active = True
            user.set_unusable_password()
            user.save(update_fields=['is_staff', 'is_active', 'password'])
            login(request, user)
            request.session['portal_admin_authenticated'] = True
            request.session['portal_admin_username'] = username

            return JsonResponse({
                "status": "ok",
                "is_admin": True,
                "username": username,
                "full_name": ldap_result.get('full_name', ''),
            })
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Solicitud JSON inválida."}, status=400)
        except urllib.error.HTTPError as error:
            if 400 <= error.code < 500:
                return JsonResponse(
                    {"status": "error", "message": "Las credenciales corporativas no son válidas."},
                    status=401
                )
            return JsonResponse(
                {"status": "error", "message": "El servicio LDAP no está disponible."},
                status=502
            )
        except (urllib.error.URLError, TimeoutError, ValueError):
            return JsonResponse(
                {"status": "error", "message": "No fue posible contactar el servicio LDAP."},
                status=502
            )
        except Exception:
            return JsonResponse(
                {"status": "error", "message": "No fue posible completar la autenticación."},
                status=500
            )

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


def api_ldap_logout(request):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)
    portal_admin = request.session.get('portal_admin_authenticated') is True
    request.session.pop('portal_admin_authenticated', None)
    request.session.pop('portal_admin_username', None)
    if portal_admin:
        logout(request)
    return JsonResponse({"status": "ok"})


def api_drawer_structure(request):
    """Devuelve la estructura de herramientas estándar por categoría (TURNO, MECANICO, ELECTRICO, MECATRONICO)."""
    from .management.commands.seed_data import DRAWER_STRUCTURE
    return JsonResponse({"status": "success", "drawers": DRAWER_STRUCTURE})


@staff_required_for_methods('POST')
def api_carts_list_create(request):
    """
    GET: Listado completo de carros de herramientas con conteos y gavetas.
    POST: Creación de un nuevo carro de herramientas (transaccional).
    """
    if request.method == 'GET':
        try:
            page, page_size = _pagination(request)
            paginator = Paginator(
                ToolCart.objects.all().order_by('codigo_carro'),
                page_size,
            )
            try:
                carts = paginator.page(page)
            except EmptyPage:
                return JsonResponse(
                    {"status": "error", "message": "Página fuera de rango."},
                    status=404,
                )
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
            return JsonResponse({
                "status": "success",
                "count": paginator.count,
                "carts": data,
                "pagination": {
                    "page": carts.number,
                    "page_size": page_size,
                    "total_pages": paginator.num_pages,
                },
            })
        except Exception as e:
            return _generic_server_error('Error al consultar carros', e)

    elif request.method == 'POST':
        try:
            try:
                body = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({"status": "error", "message": "Cuerpo JSON inválido o malformado."}, status=400)

            cart_id = _bounded_text(body.get('codigo_carro'), 'codigo_carro', 50, required=True).upper()
            name = _bounded_text(body.get('nombre_carro'), 'nombre_carro', 150, required=True)
            category = str(body.get('categoria', 'TURNO')).strip().upper()
            area = _bounded_text(body.get('area', 'Planta Goodyear'), 'area', 150, required=True)
            supervisor = _bounded_text(body.get('supervisor_responsable', 'Juanito Arias'), 'supervisor_responsable', 150)
            location = _bounded_text(body.get('ubicacion_especifica', 'Bahía de Mantenimiento'), 'ubicacion_especifica', 200)

            valid_categories = ['TURNO', 'MECANICO', 'ELECTRICO', 'MECATRONICO']
            if category not in valid_categories:
                category = 'TURNO'

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

            with transaction.atomic():
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

        except ValueError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
        except Exception as e:
            return _generic_server_error('Error al crear carro', e)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


@staff_required_for_methods('PUT', 'PATCH', 'DELETE')
def api_cart_detail_update_delete(request, cart_id):
    """
    GET: Detalle de un carro con todas sus herramientas organizadas por gaveta (1 a 5).
    PUT/PATCH: Actualización transaccional de datos generales, fotos o ubicación del carro.
    DELETE: Eliminación transaccional del carro de la base de datos.
    """
    clean_code = str(cart_id).strip().upper()
    cart = ToolCart.objects.filter(codigo_carro=clean_code).prefetch_related('tools').first()
    if not cart:
        return JsonResponse({"status": "error", "message": f"Carro con código {clean_code} no encontrado."}, status=404)

    if request.method == 'GET':
        drawers = {1: [], 2: [], 3: [], 4: [], 5: []}
        for tool in cart.tools.all().order_by('numero_gaveta', 'orden_posicion'):
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
            try:
                body = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({"status": "error", "message": "Cuerpo JSON inválido o malformado."}, status=400)

            with transaction.atomic():
                if 'nombre_carro' in body and body['nombre_carro'] is not None:
                    cart.nombre_carro = str(body['nombre_carro']).strip()
                if 'categoria' in body and body['categoria'] is not None:
                    cat = str(body['categoria']).strip().upper()
                    if cat in ['TURNO', 'MECANICO', 'ELECTRICO', 'MECATRONICO']:
                        cart.categoria = cat
                if 'area' in body and body['area'] is not None:
                    cart.area = str(body['area']).strip()
                if 'supervisor_responsable' in body and body['supervisor_responsable'] is not None:
                    cart.supervisor_responsable = str(body['supervisor_responsable']).strip()
                if 'ubicacion_especifica' in body and body['ubicacion_especifica'] is not None:
                    cart.ubicacion_especifica = str(body['ubicacion_especifica']).strip()
                if 'foto_ubicacion_url' in body:
                    cart.foto_ubicacion_url = body['foto_ubicacion_url']
                if 'drawerPhotos' in body:
                    cart.fotos_gavetas_json = json.dumps(body['drawerPhotos'])
                if 'estado_general' in body and body['estado_general'] is not None:
                    cart.estado_general = str(body['estado_general']).strip()

                cart.save()

            return JsonResponse({"status": "success", "message": f"Carro {cart.codigo_carro} actualizado correctamente."})
        except Exception as e:
            return _generic_server_error('Error al actualizar carro', e)

    elif request.method == 'DELETE':
        try:
            with transaction.atomic():
                code = cart.codigo_carro
                cart_name = cart.nombre_carro
                cart.delete()
            return JsonResponse({"status": "success", "message": f"Carro {cart_name} ({code}) eliminado correctamente."})
        except Exception as e:
            return _generic_server_error('Error al eliminar carro', e)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


@staff_required_for_methods('POST')
def api_cart_drawer_tools(request, cart_id, drawer_num):
    """
    POST: Actualiza el listado completo de herramientas de una gaveta específica (1 a 5) de forma atómica.
    """
    if request.method == 'POST':
        if drawer_num < 1 or drawer_num > 5:
            return JsonResponse({"status": "error", "message": f"Número de gaveta inválido ({drawer_num}). Debe ser entre 1 y 5."}, status=400)

        clean_code = str(cart_id).strip().upper()
        cart = ToolCart.objects.filter(codigo_carro=clean_code).first()
        if not cart:
            return JsonResponse({"status": "error", "message": f"Carro {clean_code} no encontrado."}, status=404)

        try:
            try:
                body = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({"status": "error", "message": "Cuerpo JSON inválido o malformado."}, status=400)

            tools_list = body.get('tools', [])
            if not isinstance(tools_list, list):
                return JsonResponse({"status": "error", "message": "El campo 'tools' debe ser una lista."}, status=400)

            with transaction.atomic():
                # Eliminar herramientas actuales de esta gaveta
                cart.tools.filter(numero_gaveta=drawer_num).delete()

                # Preparar e insertar en masa las nuevas herramientas
                tools_to_create = []
                for idx, tool_name in enumerate(tools_list, start=1):
                    clean_name = str(tool_name).strip()
                    if clean_name:
                        tools_to_create.append(
                            DrawerTool(
                                cart=cart,
                                numero_gaveta=drawer_num,
                                nombre_herramienta=clean_name,
                                orden_posicion=idx
                            )
                        )

                if tools_to_create:
                    DrawerTool.objects.bulk_create(tools_to_create)

                cart.recalculate_tool_count()

            return JsonResponse({
                "status": "success",
                "message": f"Gaveta {drawer_num} del carro {cart.codigo_carro} actualizada con {len(tools_to_create)} herramientas.",
                "total_herramientas": cart.total_herramientas,
                "estado_general": cart.estado_general
            })
        except Exception as e:
            return _generic_server_error('Error al guardar herramientas', e)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


@staff_required_for_methods('POST')
def api_inspections_list_create(request):
    """
    GET: Listado histórico de inspecciones 5S realizadas (optimizado con select_related).
    POST: Registro transaccional de una nueva inspección 5S (con firmas digitales y faltantes).
    """
    if request.method == 'GET':
        try:
            page, page_size = _pagination(request)
            paginator = Paginator(
                Inspection5S.objects.select_related('cart').all().order_by('-fecha_inspeccion'),
                page_size,
            )
            try:
                inspections = paginator.page(page)
            except EmptyPage:
                return JsonResponse(
                    {"status": "error", "message": "Página fuera de rango."},
                    status=404,
                )
            is_admin = (
                request.session.get('portal_admin_authenticated') is True
                or request.user.is_staff
            )
            data = []
            for insp in inspections:
                item = {
                    "folio": insp.folio,
                    "date": insp.fecha_inspeccion.strftime('%d/%m/%Y %H:%M'),
                    "cartId": insp.codigo_carro,
                    "cartName": insp.cart.nombre_carro if insp.cart else insp.codigo_carro,
                    "cartArea": insp.area,
                    "status": insp.estado_dictamen,
                    "totalChecked": insp.total_verificadas,
                    "totalTools": insp.total_herramientas,
                    "missingCount": max(0, insp.total_herramientas - insp.total_verificadas) if (insp.total_herramientas > insp.total_verificadas) else 0,
                }
                if is_admin:
                    item.update({
                        "auditor": insp.nombre_auditor,
                        "responsible": insp.responsable_carro_auditado,
                        "supervisor": insp.supervisor_responsable,
                        "missingDetails": insp.detalles_faltantes,
                        "comments": insp.comentarios_auditor,
                        "auditorSign": insp.firma_auditor_base64,
                        "respSign": insp.firma_responsable_base64,
                        "ldapAuditor": insp.ldap_auditor_id,
                        "ldapResp": insp.ldap_responsable_id,
                    })
                data.append(item)
            return JsonResponse({
                "status": "success",
                "count": paginator.count,
                "inspections": data,
                "pagination": {
                    "page": inspections.number,
                    "page_size": page_size,
                    "total_pages": paginator.num_pages,
                },
            })
        except Exception as e:
            return _generic_server_error('Error al obtener inspecciones', e)

    elif request.method == 'POST':
        try:
            try:
                body = json.loads(request.body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({"status": "error", "message": "Cuerpo JSON inválido o malformado."}, status=400)

            cart_code = _bounded_text(body.get('cartId'), 'cartId', 50, required=True).upper()
            cart = ToolCart.objects.filter(codigo_carro=cart_code).first()
            if not cart:
                return JsonResponse({"status": "error", "message": "Carro no encontrado."}, status=404)

            folio = body.get('folio')
            if not folio or not str(folio).strip():
                from datetime import datetime
                folio = f"INS-GY-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
            else:
                folio = _bounded_text(folio, 'folio', 50)

            auditor = _bounded_text(body.get('auditor', 'Inspector Goodyear'), 'auditor', 150, required=True)
            responsible = _bounded_text(body.get('responsible', 'Mecánico de Turno'), 'responsible', 150, required=True)
            supervisor = _bounded_text(body.get('supervisor', cart.supervisor_responsable), 'supervisor', 150)
            area = _bounded_text(body.get('cartArea', cart.area), 'cartArea', 150, required=True)
            status = _bounded_text(body.get('status', 'CONFORME 100%'), 'status', 100, required=True)

            try:
                total_checked = int(body.get('totalChecked', 0))
            except (ValueError, TypeError):
                return JsonResponse({"status": "error", "message": "totalChecked debe ser un entero."}, status=400)

            try:
                total_tools = int(body.get('totalTools', 0))
            except (ValueError, TypeError):
                return JsonResponse({"status": "error", "message": "totalTools debe ser un entero."}, status=400)
            if total_checked < 0 or total_tools < 0 or total_checked > total_tools:
                return JsonResponse({"status": "error", "message": "Los totales de inspección no son válidos."}, status=400)

            missing_details = _bounded_text(body.get('missingDetails'), 'missingDetails', 5000)
            comments = _bounded_text(body.get('comments'), 'comments', 5000)
            auditor_sign = body.get('auditorSign')
            resp_sign = body.get('respSign')
            for field, value in (('auditorSign', auditor_sign), ('respSign', resp_sign)):
                if value is not None and (not isinstance(value, str) or len(value) > 500000):
                    return JsonResponse({"status": "error", "message": f"{field} no es válido."}, status=400)
            ldap_auditor = _bounded_text(body.get('ldapAuditor'), 'ldapAuditor', 50)
            ldap_resp = _bounded_text(body.get('ldapResp'), 'ldapResp', 50)

            missing_items = body.get('missingItemsList', [])
            if not isinstance(missing_items, list) or len(missing_items) > 500:
                return JsonResponse({"status": "error", "message": "missingItemsList no es válido."}, status=400)
            missing_item_data = []
            for item in missing_items:
                if not isinstance(item, dict):
                    return JsonResponse({"status": "error", "message": "Detalle de faltante inválido."}, status=400)
                try:
                    d_num = int(item.get('drawer', 1))
                except (ValueError, TypeError):
                    return JsonResponse({"status": "error", "message": "Gaveta inválida."}, status=400)
                if d_num < 1 or d_num > 5:
                    return JsonResponse({"status": "error", "message": "La gaveta debe estar entre 1 y 5."}, status=400)
                t_name = _bounded_text(item.get('tool'), 'tool', 200)
                if t_name:
                    missing_item_data.append((d_num, t_name))

            with transaction.atomic():
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

                missing_objs = [
                    InspectionMissingItem(
                        inspection=insp,
                        numero_gaveta=d_num,
                        nombre_herramienta_faltante=t_name,
                    )
                    for d_num, t_name in missing_item_data
                ]
                if missing_objs:
                    InspectionMissingItem.objects.bulk_create(missing_objs)

            return JsonResponse({
                "status": "success",
                "message": f"Inspección {folio} registrada exitosamente.",
                "folio": folio
            }, status=201)

        except ValueError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
        except Exception as e:
            return _generic_server_error('Error al registrar inspección', e)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


def api_dashboard_stats(request):
    """
    GET: Estadísticas consolidadas para KPIs y gráficos del Dashboard (optimizado con agregaciones SQL).
    """
    try:
        total_carts = ToolCart.objects.count()
        total_audits = Inspection5S.objects.count()

        # Filtrar conformes utilizando Q or
        compliant_count = Inspection5S.objects.filter(
            Q(estado_dictamen__icontains='100%') | Q(estado_dictamen__icontains='CONFORME')
        ).count()

        missing_count = max(0, total_audits - compliant_count)

        # Distribución por áreas usando agregación SQL directa
        areas = {}
        cart_areas = ToolCart.objects.values('area').annotate(carts_count=Count('id'))
        for item in cart_areas:
            area_name = item['area'] or 'Planta Goodyear'
            if area_name not in areas:
                areas[area_name] = {"carts": 0, "audits": 0}
            areas[area_name]["carts"] = item['carts_count']

        audit_areas = Inspection5S.objects.values('area').annotate(audits_count=Count('id'))
        for item in audit_areas:
            area_name = item['area'] or 'Planta Goodyear'
            if area_name not in areas:
                areas[area_name] = {"carts": 0, "audits": 0}
            areas[area_name]["audits"] = item['audits_count']

        pass_rate = round((compliant_count / total_audits) * 100) if total_audits > 0 else 0

        return JsonResponse({
            "status": "success",
            "totalCarts": total_carts,
            "totalAudits": total_audits,
            "compliantAudits": compliant_count,
            "missingAudits": missing_count,
            "passRate": pass_rate,
            "areas": areas
        })
    except Exception as e:
        return _generic_server_error('Error al calcular estadísticas', e)


@staff_required_for_methods('POST')
def api_reset_factory(request):
    """
    POST: Restablece todos los carros y herramientas al estado inicial de fábrica (28 carros oficiales).
    """
    if request.method == 'POST':
        try:
            with transaction.atomic():
                ToolCart.objects.all().delete()
                from django.core.management import call_command
                call_command('seed_data')

            return JsonResponse({
                "status": "success",
                "message": f"Base de datos restablecida al estándar oficial de fábrica Goodyear ({ToolCart.objects.count()} carros cargados)."
            })
        except Exception as e:
            return _generic_server_error('Error al restablecer valores de fábrica', e)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)


def api_download_excel_template(request):
    """
    GET: Genera y descarga un archivo Excel (.xlsx) con la plantilla oficial Goodyear simplificada.
    """
    if not HAS_OPENPYXL:
        return JsonResponse({"status": "error", "message": "openpyxl no está instalado en el servidor."}, status=500)

    try:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Plantilla Carros 5S"

        headers = [
            "tipo_carro",
            "turno_o_numero",
            "area",
            "supervisor",
            "ubicacion_especifica",
            "gaveta_1_herramientas",
            "gaveta_2_herramientas",
            "gaveta_3_herramientas",
            "gaveta_4_herramientas",
            "gaveta_5_herramientas",
            "codigo_carro_opcional"
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

        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        sample_rows = [
            [
                "TURNO",
                "A",
                "ASRS",
                "Juanito Arias",
                "Pasillo Principal Bahía 1",
                "Juego Llaves Combinadas 8-24mm, Chicharra 1/2\", Dados de Impacto 17-21mm",
                "Destornillador Paleta 6x100mm, Destornillador Cruz PH2, Alicate Universal 8\"",
                "Martillo de Bola 500g, Martillo de Goma, Cincel Plano, Cepillo de Acero",
                "Cinta Métrica 5m, Flexómetro de Trabajo, Manguera Neumática, Pistola de Aire",
                "Candados LOTO Rojos (2 un), Pinza Bloqueo, Tarjeta 5S, Gafas de Seguridad",
                ""
            ],
            [
                "MECANICO",
                "01",
                "Construcción",
                "Juanito Arias",
                "Bahía Mantenimiento Construcción",
                "Juego Dados 1/2\" Heavy Duty (8-32mm), Chicharra Pesada 1/2\", Palanca de Fuerza",
                "Extractor de Rodamientos 3 Patas, Llaves Corona 10-24mm, Llave Ajustable 12\"",
                "Arco de Sierra Profesional, Cinceles Planos, Limas de Ajuste, Llave Stilson 14\"",
                "Pistola Neumática de Impacto 1/2\", Manómetro Digital, Aceite Lubricante",
                "Torquímetro Calibrado 1/2\" (20-200 Nm), Pie de Metro Digital, Kit LOTO",
                ""
            ],
            [
                "ELECTRICO",
                "01",
                "Final Finish",
                "Juanito Arias",
                "Bahía Eléctrica Final Finish",
                "Juego Destornilladores 1000V VDE (PH0-PH3, SL3-SL6), Pelacables Automático",
                "Multímetro Digital Fluke Calibrado, Pinza Amperimétrica True RMS",
                "Crimpador Terminales Eléctricos, Alicate de Punta VDE, Cautín 60W",
                "Guantes Dieléctricos Clase 0 (1000V), Detector de Tensión Sin Contacto",
                "Candados LOTO Dieléctricos, Tarjetas de Advertencia Eléctrica, Lentes",
                ""
            ]
        ]

        for row in sample_rows:
            ws.append(row)

        for row in ws.iter_rows(min_row=2, max_row=len(sample_rows)+1):
            for cell in row:
                cell.font = Font(name="Segoe UI", size=10)
                cell.border = thin_border
                cell.alignment = Alignment(vertical="center", wrap_text=True)

        column_widths = [16, 16, 20, 20, 28, 42, 42, 42, 42, 42, 24]
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
    except Exception as e:
        return _generic_server_error('Error al generar plantilla', e)


@staff_required_for_methods('POST')
def api_import_excel(request):
    """
    POST: Importa carros y herramientas desde un archivo Excel (.xlsx) o CSV subido en multipart/form-data (transaccional).
    Autogenera códigos y nombres normalizados según nomenclatura Goodyear.
    """
    if request.method == 'POST':
        if 'file' not in request.FILES:
            return JsonResponse({"status": "error", "message": "No se ha subido ningún archivo."}, status=400)

        uploaded_file = request.FILES['file']
        file_name = uploaded_file.name.lower()
        max_upload_size = getattr(settings, 'IMPORT_MAX_FILE_SIZE', 10 * 1024 * 1024)
        if uploaded_file.size > max_upload_size:
            return JsonResponse({"status": "error", "message": "El archivo supera el tamaño máximo permitido."}, status=400)

        try:
            if file_name.endswith('.xlsx'):
                if not HAS_OPENPYXL:
                    return JsonResponse({"status": "error", "message": "openpyxl no está instalado en el servidor."}, status=500)
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

            if len(data_rows) > getattr(settings, 'IMPORT_MAX_ROWS', 5000):
                return JsonResponse({"status": "error", "message": "El archivo supera el número máximo de filas permitido."}, status=400)

            col_map = {}
            for idx, raw_col in enumerate(header):
                col = str(raw_col).replace('_', ' ').replace('-', ' ').strip().lower()
                if 'tipo' in col or 'categor' in col:
                    col_map['tipo'] = idx
                elif 'turno' in col or 'numero' in col or 'número' in col or 'nro' in col:
                    col_map['turno_num'] = idx
                elif 'codigo' in col or 'código' in col or 'id' in col:
                    col_map['codigo'] = idx
                elif 'nombre' in col:
                    col_map['nombre'] = idx
                elif 'area' in col or 'área' in col:
                    col_map['area'] = idx
                elif 'superv' in col or 'responsable' in col:
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

            if 'tipo' not in col_map and 'codigo' not in col_map and 'area' not in col_map:
                return JsonResponse({"status": "error", "message": "No se encontraron columnas requeridas ('tipo_carro', 'area' o 'codigo_carro') en el archivo."}, status=400)

            imported_carts = 0
            imported_tools = 0

            with transaction.atomic():
                for row in data_rows:
                    if not any(row):
                        continue

                    raw_tipo = str(row[col_map['tipo']]).strip() if col_map.get('tipo') is not None and row[col_map['tipo']] else 'TURNO'
                    raw_turno_num = str(row[col_map['turno_num']]).strip() if col_map.get('turno_num') is not None and row[col_map['turno_num']] else 'A'
                    raw_area = str(row[col_map['area']]).strip() if col_map.get('area') is not None and row[col_map['area']] else 'Planta'
                    manual_codigo = str(row[col_map['codigo']]).strip() if col_map.get('codigo') is not None and row[col_map['codigo']] else None
                    manual_nombre = str(row[col_map['nombre']]).strip() if col_map.get('nombre') is not None and row[col_map['nombre']] else None

                    cart_meta = generate_cart_code_and_name(
                        tipo_carro=raw_tipo,
                        turno_o_numero=raw_turno_num,
                        area_input=raw_area,
                        manual_codigo=manual_codigo,
                        manual_nombre=manual_nombre
                    )

                    codigo = cart_meta['codigo_carro']
                    nombre = cart_meta['nombre_carro']
                    categoria = cart_meta['categoria']
                    area_final = cart_meta['area']

                    if not codigo or codigo.lower() in ['none', 'null']:
                        continue

                    supervisor = str(row[col_map.get('supervisor', 0)]).strip() if col_map.get('supervisor') is not None and row[col_map.get('supervisor')] else 'Juanito Arias'
                    ubicacion = str(row[col_map.get('ubicacion', 0)]).strip() if col_map.get('ubicacion') is not None and row[col_map.get('ubicacion')] else 'Bahía de Mantenimiento'

                    cart, created = ToolCart.objects.update_or_create(
                        codigo_carro=codigo,
                        defaults={
                            'nombre_carro': nombre,
                            'categoria': categoria,
                            'especialidad_tipo': f"Carro {categoria}",
                            'area': area_final,
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

            return JsonResponse({
                "status": "success",
                "message": f"¡Importación completada! Se procesaron {imported_carts} carros y {imported_tools} herramientas.",
                "imported_carts": imported_carts,
                "imported_tools": imported_tools,
                "total_carts_db": ToolCart.objects.count()
            })

        except UnicodeDecodeError:
            return JsonResponse({"status": "error", "message": "El archivo CSV debe usar codificación UTF-8."}, status=400)
        except Exception as e:
            return _generic_server_error('Error procesando archivo', e)

    return JsonResponse({"status": "error", "message": "Método no permitido."}, status=405)
