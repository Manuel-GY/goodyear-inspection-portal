# 🏭 Portal de Inspección de Carros de Herramientas 5S — Goodyear

![Goodyear Logo](logo-goodyear.png)

Sistema integral web de gestión, auditoría 5S y control centralizado de inventario de carros de herramientas industriales en la Planta Goodyear (**ASRS, Construcción, Final Finish y demás áreas operativas**), con **Backend Django**, base de datos relacional y soporte multidispositivo (PC Desktop, Celulares e inspectores con pistolas **Datalogic Falcon X4**).

---

## 🚀 Características Principales

- **Backend Centralizado en Django + Base de Datos Relacional**:
  - 🌐 Sincronización en tiempo real entre todos los dispositivos (Pistolas Falcon, Celulares y PCs de supervisión).
  - 💾 Base de datos unificada (`db.sqlite3` / PostgreSQL / SQL Server) para auditorías, flota de carros, gavetas y fotos 5S.
  - 📡 REST APIs para carros (`/api/carts/`), gavetas (`/api/carts/<id>/drawers/<num>/tools/`), auditorías (`/api/inspections/`) y estadísticas (`/api/dashboard/stats/`).
  - 📴 Capacidad de trabajo Offline/Caché local con re-sincronización automática.
- **Flota Oficial de 28 Carros de Herramientas**:
  - 🏭 **Área ASRS (12 Carros)**: Carros de Turno (A, B, C, D), Mecánicos (M01, M02) y Mecatrónicos (MT01 a MT06) (Supervisor: Juanito Arias).
  - 🏗️ **Área Construcción (12 Carros)**: Carros de Turno (A, B, C, D) y Mecatrónicos (MT01 a MT08) (Supervisor: Juanito Arias).
  - 🏁 **Área Final Finish (4 Carros)**: Carros de Turno (A, B), Mecánico (M01) y Mecatrónico (MT01) (Supervisor: Juanito Arias).
  - ➕ Creación y eliminación dinámica de nuevos carros desde el panel administrador o directamente desde las tarjetas de flota.
- **Escanear QR y Códigos Únicos por Carro (28 Carros)**:
  - 📷 **Acceso Directo por QR**: Cada uno de los 28 carros cuenta con un código QR único que redirige inmediatamente a su lista de verificación de inspección (`?cart=CH-ASRS-TA`).
  - 🖨️ **Impresión de Stickers QR en Módulo Admin**: Generador e impresor individual de sticker por carro con logo Goodyear y botón de **Impresión por Lote (28 Stickers en Hoja de Etiquetas)** para rotular toda la planta de una sola vez.
  - 📄 **Manifiesto Oficial 5S Imprimible**: Botón en cada carro y modal de gavetas para imprimir el **Manifiesto de Herramientas** completo en formato hoja de control (con datos de planta, código QR, foto de ubicación, fotos de referencia 5S gaveta por gaveta, tabla de inventario numerada y sección de firmas).
- **Detección Automática Multiplataforma**:
  - 🖥️ **Modo PC Desktop**: Vista integral de supervisión con **Dashboard analítico 5S**, KPIs, gráficos de cumplimiento, inventario de la flota completa, historial detallado y módulo de administración.
  - 📱 **Modo Celular Corporativo**: Vista **exclusiva de inspección** sin distracciones. Al ingresar, solicita de inmediato el escaneo del código QR con la cámara. Al completar una auditoría, solicita inmediatamente el siguiente QR.
  - 🔫 **Modo Datalogic Falcon X4 (Windows Embedded Compact / CE)**: Vista **exclusiva de inspección ultraligera**. Carga inmediata para escaneo con gatillo láser, interfaz de alto contraste y exclusión de fotos pesadas para máximo rendimiento en la memoria del terminal.
- **Validación de Identidad por LDAP Corporativo y Doble Firma Digital**:
  - 👤 **Identificación LDAP**: Registro de ID de usuario y nombre tanto del auditor como del responsable auditado.
  - ✍️ **Firma Digital Manual**: Lienzo interactivo para firma manual táctil o con cursor, estampada en el comprobante y registro de auditoría.
- **Notificaciones Automáticas a Microsoft Teams**:
  - Integración nativa mediante Webhook de Power Automate y **Adaptive Cards v1.2**.

---

## 🛠️ Estructura del Proyecto

```text
goodyear-inspection-portal/
├── goodyear_portal/           # Configuración del proyecto Django (settings, urls, asgi, wsgi)
├── inspections/               # App de Django (modelos, vistas API, admin, seed_data)
│   ├── management/commands/   # Comando de siembra inicial (seed_data)
│   ├── models.py              # Modelos: ToolCart, DrawerTool, Inspection5S, InspectionMissingItem
│   ├── views.py               # Vistas y APIs REST
│   └── urls.py                # Rutas de endpoints
├── static/                    # Archivos estáticos (logo-goodyear.png, assets)
├── index.html                 # Frontend Single Page Application optimizado
├── manage.py                  # CLI de Django
├── requirements.txt           # Dependencias Python
└── README.md                  # Documentación
```

---

## ⚙️ Instalación y Puesta en Marcha (Django)

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/Manuel-GY/goodyear-inspection-portal.git
   cd goodyear-inspection-portal
   ```

2. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar migraciones y sembrar los 28 carros oficiales**:
   ```bash
   python manage.py migrate
   python manage.py seed_data
   ```

4. **Crear superusuario para Django Admin (Opcional)**:
   ```bash
   python manage.py createsuperuser
   ```

5. **Iniciar el Servidor (Accesible desde toda la red de la planta)**:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

6. **Acceso desde cualquier dispositivo**:
   - Desde PC: `http://localhost:8000` o `http://<IP_SERVIDOR>:8000`
   - Desde Celulares / Pistolas Falcon X4: `http://<IP_SERVIDOR>:8000`
   - Panel de Administración Django: `http://<IP_SERVIDOR>:8000/admin`

---

© 2026 The Goodyear Tire & Rubber Company. Confidential & Proprietary.
