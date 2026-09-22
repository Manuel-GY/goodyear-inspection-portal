# 🏭 Portal de Inspección de Carros de Herramientas 5S — Goodyear

![Goodyear Logo](logo-goodyear.png)

Sistema integral web de gestión, auditoría 5S y control centralizado de inventario de carros de herramientas industriales en la Planta Goodyear (**ASRS, Construcción, Final Finish y demás áreas operativas**), con **Backend Django**, base de datos relacional y soporte multidispositivo (PC Desktop, Celulares e inspectores con pistolas **Datalogic Falcon X4**).

---

## 🔑 Credenciales de Acceso

| Tipo de Acceso | URL | Usuario / Rol | Contraseña |
| :--- | :--- | :--- | :--- |
| **Portal Principal 5S** | `http://localhost:8000` | Operadores / Inspectores | *Acceso Libre* |
| **Módulo Admin en Portal** | Pestaña **Administrador** | `ac17157` / `aa09876` | *Validación LDAP* |
| **Django Admin Backoffice** | `http://localhost:8000/admin` | **`admin`** | **`Goodyear5S2026!`** |

---

## 🚀 Puesta en Marcha Rápida (3 Comandos)

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Aplicar migraciones y cargar los 28 carros oficiales de Goodyear**:
   ```bash
   python manage.py migrate
   python manage.py seed_data
   ```

3. **Iniciar el servidor para toda la red de la planta**:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

---

## 📱 Acceso por Dispositivo en la Red de la Planta

- 🖥️ **PCs de Supervisión y Oficina**:
  - `http://localhost:8000` (Local)
  - `http://10.107.202.76:8000` o `http://<IP_DE_TU_PC>:8000`
- 📱 **Celulares Corporativos e Inspectores en Terreno**:
  - `http://10.107.202.76:8000` (Abre directamente el escáner QR de cámara).
- 🔫 **Pistolas Láser Datalogic Falcon X4 (Windows CE)**:
  - `http://10.107.202.76:8000` (Modo ultraligero sin gráficos pesados).

---

## 📊 Migración e Importación Masiva desde Excel / CSV

El sistema permite importar y actualizar masivamente carros y herramientas de gavetas desde archivos Excel (`.xlsx`) o CSV.

### Método 1: Desde la Interfaz Web (Recomendado)
1. En la pestaña **Flota de Carros** o en el **Editor de Gavetas**, haz clic en el botón verde **`📥 Importar Excel / CSV`**.
2. Haz clic en **`Descargar Plantilla .xlsx`** para obtener el archivo modelo con columnas y ejemplos de Goodyear.
3. Completa los datos en Excel, selecciona el archivo y presiona **`Iniciar Importación`**.

### Método 2: Desde la Terminal (Línea de Comandos)
```bash
# 1. Generar la plantilla Excel con formato Goodyear
python manage.py export_template

# 2. Importar un archivo Excel o CSV directamente a la base de datos
python manage.py import_excel plantilla_carros_goodyear.xlsx
```

### 📋 Estructura de Columnas de la Plantilla Excel:
- `codigo_carro`: Identificador único (ej: `CH-ASRS-TA`, `CH-CST-M01`).
- `nombre_carro`: Nombre descriptivo (ej: `Carro Turno A (ASRS)`).
- `categoria`: `TURNO`, `MECANICO`, `ELECTRICO` o `MECATRONICO`.
- `area`: `Área ASRS`, `Área Construcción`, `Área Final Finish`, etc.
- `supervisor`: Nombre del supervisor responsable (ej: `Juanito Arias`).
- `ubicacion_especifica`: Ubicación en la planta (ej: `Bahía 1 Pasillo Principal`).
- `gaveta_1_herramientas`: Listado de herramientas separadas por comas (`,`) o punto y coma (`;`).
- `gaveta_2_herramientas`: Herramientas de Gaveta 2.
- `gaveta_3_herramientas`: Herramientas de Gaveta 3.
- `gaveta_4_herramientas`: Herramientas de Gaveta 4.
- `gaveta_5_herramientas`: Herramientas de Gaveta 5.

---

## 🛠️ Estructura del Proyecto

```text
goodyear-inspection-portal/
├── goodyear_portal/                 # Configuración del proyecto Django (settings, urls, wsgi, asgi)
├── inspections/                     # Aplicación Django principal
│   ├── management/commands/
│   │   ├── seed_data.py             # Carga inicial de 28 carros oficiales
│   │   ├── import_excel.py          # Importador de archivos Excel y CSV
│   │   └── export_template.py       # Generador de plantilla Excel
│   ├── models.py                    # Modelos: ToolCart, DrawerTool, Inspection5S, InspectionMissingItem
│   ├── views.py                     # Vistas y APIs REST (Carros, Inspecciones, Excel, Stats)
│   └── urls.py                      # Rutas de endpoints
├── static/                          # Archivos estáticos (logo-goodyear.png, assets)
├── index.html                       # Frontend Single Page Application optimizado
├── plantilla_carros_goodyear.xlsx   # Plantilla Excel modelo lista para usar
├── manage.py                        # CLI de Django
├── requirements.txt                 # Dependencias Python
└── README.md                        # Documentación oficial
```

---

## 🖨️ Funcionalidades Especiales de Impresión

- **`Imprimir Todos los QR (28 Carros)`**: Genera automáticamente una hoja de etiquetas con los 28 códigos QR oficiales listos para recortar y pegar en cada carro de la planta.
- **`Imprimir Manifiesto (Listado + Fotos)`**: Genera la ficha técnica oficial 5S del carro con foto de ubicación, estándares fotográficos de las 5 gavetas y tabla de inventario numerada para auditorías.

---

© 2026 The Goodyear Tire & Rubber Company. Confidential & Proprietary.
