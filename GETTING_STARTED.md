# 🚀 Guía de Inicio Rápido

Sigue estos pasos para tener el proyecto funcionando en 15 minutos.

---

## 1️⃣ Configurar Google Cloud Platform (GCP)

### Crear Service Account

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto llamado `Google Slides Automation`
3. Ve a **APIs y servicios** → **Biblioteca**
4. Habilita:
   - **Google Slides API**
   - **Google Drive API**
5. Ve a **IAM y administración** → **Cuentas de servicio**
6. Crea una cuenta de servicio:
   - Nombre: `google-slides-automation`
   - Rol: `Editor`
7. En la cuenta creada, ve a **Claves** → **Agregar clave** → **JSON**
8. Se descargará `credentials.json` — cópialo a la raíz del proyecto

### Compartir la presentación

1. Abre tu presentación de Google Slides
2. Haz clic en **Compartir**
3. En `credentials.json`, busca el campo `"client_email"`
4. Pega ese email en Compartir y dale permisos de **Edición**

---

## 2️⃣ Instalar dependencias

```bash
# Desde la carpeta del proyecto
cd "/Users/marielgarcik/Desktop/Test Slides"

# Crear virtual environment
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## 3️⃣ Ejecutar el servidor

```bash
# Activa el venv si aún no lo hiciste
source venv/bin/activate

# Ejecutar en la carpeta del proyecto
python app.py
```

El servidor estará disponible en: **http://localhost:8000**

---

## 4️⃣ Usar la aplicación

### Opción A: Frontend Web
1. Abre http://localhost:8000 en tu navegador
2. Pega la URL de tu presentación
3. Clickea en los botones para extraer identificadores ($) o componentes (#)

### Opción B: API REST

#### Extraer identificadores ($)
```bash
curl -X POST http://localhost:8000/api/extract-slide-ids \
  -H "Content-Type: application/json" \
  -d '{"presentation_url":"https://docs.google.com/presentation/d/YOUR_ID/edit"}'
```

Respuesta:
```json
{
  "success": true,
  "slide_identifiers": {
    "0": ["$portada"],
    "1": ["$contenido_principal"],
    "2": ["$cierre"]
  },
  "message": "Se encontraron 3 slides con identificadores"
}
```

#### Obtener componentes (#) de una slide
```bash
curl -X POST http://localhost:8000/api/get-slide-components \
  -H "Content-Type: application/json" \
  -d '{
    "presentation_url":"https://docs.google.com/presentation/d/YOUR_ID/edit",
    "slide_index": 0
  }'
```

Respuesta:
```json
{
  "success": true,
  "slide_index": 0,
  "components": ["#titulo", "#subtitulo", "#fecha"],
  "message": "Se encontraron 3 componentes en la slide 0"
}
```

### Opción C: Python directo
```python
from slides_automation import GoogleSlidesAutomation

automation = GoogleSlidesAutomation("./credentials.json")

# Extraer IDs
slide_ids = automation.extract_slide_ids(
    "https://docs.google.com/presentation/d/YOUR_ID/edit"
)
print(slide_ids)  # {0: ['$portada'], 1: ['$contenido'], ...}

# Obtener componentes
components = automation.get_slide_components(
    "https://docs.google.com/presentation/d/YOUR_ID/edit",
    slide_index=0
)
print(components)  # ['#titulo', '#subtitulo', '#fecha']
```

---

## 📌 Estructura del proyecto

```
Test Slides/
├── app.py                  # FastAPI server
├── slides_automation.py    # Funciones principales
├── requirements.txt        # Dependencias Python
├── .gitignore              # Archivos ignorados en Git
├── README.md               # Documentación general
├── GETTING_STARTED.md      # Esta guía
├── credentials.json        # Tu JSON de GCP (no subir a GitHub)
├── static/
│   ├── index.html          # Frontend
│   ├── styles.css          # Estilos
│   └── script.js           # Lógica del cliente
└── venv/                   # Virtual environment
```

---

## 🐛 Solución de problemas

### "The caller does not have permission" (403)
- La presentación **no está compartida** con el Service Account
- Ve a la presentación → Compartir → añade el email de `credentials.json`
- Espera 30-60 segundos y vuelve a probar

### "No se encuentran identificadores/componentes"
- Los marcadores (`$` y `#`) **deben estar en elementos de TEXTO**
- Sintaxis: `$identificador` y `#componente` (sin espacios)
- No pueden estar en imágenes o formas
- Ejemplo válido: `"Esta es mi portada $portada"`

### "Puerto 8000 ocupado"
```bash
# Mata los procesos usando el puerto
kill -9 $(lsof -t -i tcp:8000)

# O arranca en otro puerto
PORT=8001 python app.py
```

---

## 📖 Información adicional

- **app.py**: Servidor FastAPI con endpoints REST
- **slides_automation.py**: Lógica de integración con Google Slides API
- **requirements.txt**: Dependencias (FastAPI, google-api-python-client, etc.)

Para preguntas o issues, consulta el README.md
