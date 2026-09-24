# 🏭 Portal de Inspección de Carros de Herramientas 5S — Goodyear

![Goodyear Logo](static/logo-goodyear.png)

Sistema integral web y móvil de gestión, auditoría 5S y control centralizado de inventario de carros de herramientas industriales en la Planta Goodyear (**ASRS, Construcción, Final Finish y demás áreas operativas**), con **Backend Django**, base de datos relacional optimizada con transacciones atómicas, APIs REST y soporte multidispositivo (PC Desktop, Celulares e inspectores con pistolas **Datalogic Falcon X4** con escaneo láser por hardware).

---

## 🔑 Accesos

| Tipo de Acceso | URL | Usuario / Rol | Contraseña |
| :--- | :--- | :--- | :--- |
| **Portal Principal 5S** | `http://localhost:8000` | Operadores / Inspectores | *Acceso Libre* |
| **Módulo Admin en Portal** | Pestaña **Administrador** | Usuario staff de Django | Inicio de sesión del servidor |
| **Django Admin Backoffice** | `http://localhost:8000/admin` | Usuario staff creado por el administrador | Configurada fuera del repositorio |

El portal de inspección es público. Las operaciones de administración requieren una
sesión de usuario Django con `is_staff=True`. No se almacenan credenciales en el
repositorio; cree el primer usuario con `python manage.py createsuperuser`.

---

## 🚀 Puesta en Marcha Rápida

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar el entorno** (en producción no use los valores de desarrollo):
   ```bash
   # PowerShell
   $env:DJANGO_SECRET_KEY = "genere-una-clave-larga-y-aleatoria"
   $env:DJANGO_DEBUG = "False"
   $env:DJANGO_ALLOWED_HOSTS = "servidor-goodyear,localhost"
   $env:CORS_ALLOWED_ORIGINS = "https://servidor-goodyear"
   ```

3. **Aplicar migraciones y cargar los 28 carros oficiales de Goodyear**:
   ```bash
   python manage.py migrate
   python manage.py seed_data
   ```

4. **Crear el usuario administrativo fuera del repositorio**:
   ```bash
   python manage.py createsuperuser
   ```
   El usuario debe iniciar sesión en `/admin/`. Solo las cuentas Django con
   `is_staff=True` pueden editar la flota, importar archivos o restablecer datos.

5. **Ejecutar conjunto de pruebas automatizadas (Tests Unitarios)**:
   ```bash
   python manage.py test
   ```

6. **Iniciar el servidor para toda la red de la planta**:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

---

## 📱 Modos de Dispositivo Soportados

El sistema cuenta con un motor adaptativo para tres perfiles de hardware en planta:

- 🖥️ **Modo PC Desktop**:
  - Panel integral de control con KPIs en vivo, gráficos interactivos Chart.js, gestión de flota con 28 carros, exportación de manifiestos técnicos e historial 5S.
- 📱 **Modo Celular Móvil (HD)**:
  - Formulario ágil de inspección ergonómico con escaneo de código QR mediante cámara (Html5-QRCode), fotos de referencia por gaveta y firma táctil digital.
- 🔫 **Modo Pistola Datalogic Falcon X4 (Windows CE / Embedded)**:
  - Modo ultraligero sin animaciones pesadas ni gráficos, con captura por hardware (Keyboard Wedge Listener) de códigos de barra / QR y flujo optimizado guiado por el manifiesto impreso del carro.

---

## 🌐 Endpoints de la API REST

| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/` | Portal web Single Page Application |
| `GET` | `/api/drawer-structure/` | Estructura de gavetas estándar por categoría |
| `GET` / `POST` | `/api/carts/` | Listado de flota y creación de nuevos carros |
| `GET` / `PUT` / `DELETE` | `/api/carts/<cart_id>/` | Detalle, edición y borrado de carro |
| `POST` | `/api/carts/<cart_id>/drawers/<d>/tools/` | Guardado atómico de herramientas por gaveta (1 a 5) |
| `GET` / `POST` | `/api/inspections/` | Historial de auditorías y registro de inspección 5S |
| `GET` | `/api/dashboard/stats/` | KPIs agregados y distribución por áreas |
| `POST` | `/api/reset-factory/` | Restablecimiento de flota oficial a valores de fábrica |
| `GET` | `/api/download-excel-template/` | Descarga de plantilla Excel `.xlsx` oficial Goodyear |
| `POST` | `/api/import-excel/` | Importación masiva desde archivos `.xlsx` o `.csv` |

---

## 📊 Migración e Importación Masiva desde Excel / CSV

### Método 1: Desde la Interfaz Web

La importación y edición desde la interfaz requieren iniciar sesión como usuario
administrativo. La pestaña de administración no se muestra a visitantes públicos.
1. En la pestaña **Flota de Carros** o en el **Editor de Gavetas**, haz clic en **`📥 Importar Excel / CSV`**.
2. Haz clic en **`Descargar Plantilla .xlsx`** para obtener el archivo modelo oficial.
3. Completa los datos en Excel, selecciona el archivo y presiona **`Iniciar Importación`**.

### Método 2: Desde la Terminal
```bash
# 1. Generar la plantilla Excel con formato Goodyear
python manage.py export_template

# 2. Importar un archivo Excel o CSV directamente a la base de datos
python manage.py import_excel plantilla_carros_goodyear.xlsx
```

### 📋 Columnas de la Plantilla Excel (Asignación Automática de Códigos):
- `tipo_carro`: `TURNO`, `MECANICO`, `ELECTRICO` o `MECATRONICO`.
- `turno_o_numero`: `A`, `B`, `C`, `D` (para turnos) o `01`, `02` (para mecánicos/eléctricos/mecatrónicos).
- `area`: `ASRS`, `Construcción`, `Final Finish`, `Banbury`, `Vulcanización`, etc.
- `supervisor`: Supervisor responsable (ej: `Juanito Arias`).
- `ubicacion_especifica`: Ubicación en la planta (ej: `Bahía 1 Pasillo Principal`).
- `gaveta_1_herramientas` a `gaveta_5_herramientas`: Herramientas separadas por coma (`,`), punto y coma (`;`) o salto de línea.
- `codigo_carro_opcional`: *(Opcional)* Dejar vacío para autogenerar el código oficial Goodyear (ej: `CH-ASRS-TA`, `CH-CST-M01`).

> [!TIP]
> **Autogeneración:** El usuario no necesita calcular ni inventar los códigos `CH-...` ni el nombre del carro. El sistema los normaliza y asigna automáticamente respetando los estándares de planta Goodyear.

---

## 🖨️ Impresión y Manifiestos 5S

- **`Imprimir Todos los QR (28 Carros)`**: Genera automáticamente una hoja de etiquetas con los 28 códigos QR oficiales listos para imprimir y pegar en los carros.
- **`Imprimir Manifiesto (Listado + Fotos)`**: Ficha técnica oficial 5S del carro con foto de ubicación, estándares fotográficos de las 5 gavetas y tabla de inventario numerada para auditorías.

---

## 🧪 Pruebas Automatizadas

El proyecto incluye una suite de tests unitarios e integración en `inspections/tests.py`:
```bash
python manage.py test
```
Cobertura:
- Creación, edición, eliminación y relaciones en cascada de `ToolCart`.
- Guardado por gavetas (1 a 5), ordenamiento y recálculo automático en `DrawerTool`.
- Creación de auditorías 5S, firmas base64 y desglose de faltantes en `Inspection5S` y `InspectionMissingItem`.
- Generación de plantilla Excel y parser de importación masiva (`.xlsx` y `.csv`).
- Todos los endpoints REST con validación de estados HTTP (200, 201, 400, 404, 405).
- Comandos de gestión `seed_data`, `export_template` y `reset_factory`.

---

© 2026 The Goodyear Tire & Rubber Company. Confidential & Proprietary.
