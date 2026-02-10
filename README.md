# Google Slides Automation - Guía Completa

## Descripción del Proyecto
Este proyecto automatiza la extracción de **identificadores** y **componentes dinámicos** de presentaciones de Google Slides usando Python, FastAPI y Google Slides API.

### Características principales:
- **Función 1 - Extraer Identificadores ($)**: 
  - Busca en TODAS las slides de la presentación
  - Encuentra elementos que contienen el marcador `$` (ej: `$portada`, `$contenido_principal`)
  - Retorna un diccionario con el índice de cada slide y su identificador

- **Función 2 - Obtener Componentes (#)**:
  - Busca en una slide ESPECÍFICA
  - Encuentra elementos que contienen el marcador `#` (ej: `#titulo`, `#descripcion`, `#fecha`)
  - Retorna una lista de todos los componentes encontrados

- **Frontend**: 
  - HTML/CSS/JS 
  - Interfaz para probar ambas funciones

## 🏗️ Estructura del Proyecto

```
Test Slides/
├── requirements.txt              # Dependencias Python
├── .env.example                  # Ejemplo de variables de entorno
├── .env                          # Variables de entorno (crear manualmente)
├── credentials.json              # Credenciales GCP 
├── slides_automation.py          # FUNCIONES PRINCIPALES
├── app.py                        # API FastAPI
└── static/
    ├── index.html               # Frontend HTML
    ├── styles.css               # Estilos CSS
    └── script.js                # Lógica JavaScript
```

## 🔑 Paso 1: Configurar Service Account de GCP

### ¿Qué es un Service Account?
Un **Service Account** es una cuenta especial en Google Cloud que actúa como una aplicación. Permite acceso programático a Google Slides sin necesidad de intervención manual del usuario.

### Pasos para crear el Service Account:

1. **Ir a Google Cloud Console**
   - Abre https://console.cloud.google.com/
   - Asegúrate de estar en tu proyecto

2. **Crear el Service Account**
   - Ve a "IAM y administración" → "Cuentas de servicio"
   - Haz clic en "Crear cuenta de servicio"
   - Dale un nombre: `google-slides-automation`
   - Haz clic en "Crear y continuar"

3. **Asignar permisos**
   - Selecciona el rol "Editor" (para testing; en producción usa permisos más específicos)
   - Haz clic en "Continuar" → "Listo"

4. **Crear clave JSON**
   - Haz clic en la cuenta de servicio que acabas de crear
   - Ve a la pestaña "Claves"
   - Haz clic en "Agregar clave" → "Crear clave nueva"
   - Selecciona "JSON"
   - Se descargará automáticamente el archivo `credentials.json`

5. **Copiar el archivo**
   - Copia el archivo `credentials.json` descargado
   - Pégalo en la carpeta raíz del proyecto (donde está `app.py`)

6. **Compartir presentación con Service Account**
   - Abre tu presentación de Google Slides
   - Haz clic en "Compartir"
   - En el archivo `credentials.json`, busca el campo `client_email`
   - Comparte la presentación con ese email, dándole permisos de edición

### Validar credenciales
Si todo está correcto, verás:
```json
{
  "type": "service_account",
  "project_id": "tu-proyecto",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "google-slides-automation@...",
  "client_id": "...",
  ...
}
```

## 💻 Paso 2: Instalar dependencias Python

```bash
# Ir a la carpeta del proyecto
cd /Users/marielgarcik/Desktop/Test\ Slides

# Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## 🚀 Paso 3: Ejecutar la aplicación

```bash
# Asegúrate de estar en el directorio del proyecto
cd /Users/marielgarcik/Desktop/Test\ Slides

# Ejecutar el servidor FastAPI
python app.py
```

Verás algo como:
```
╔════════════════════════════════════════╗
║  Google Slides Automation API          ║
║  Servidor iniciando en puerto 8000...   ║
║  http://localhost:8000                 ║
╚════════════════════════════════════════╝
```

## 🌐 Paso 4: Acceder al Frontend

1. Abre tu navegador
2. Ve a: `http://localhost:8000`
3. ¡Ya puedes usar la herramienta!

## 📚 Uso de las funciones

### Función 1: Extraer Identificadores

```
URL: https://docs.google.com/presentation/d/1Q1PtD0eAKaNlWA6fDev4naT1bzNsxZbQRsdbnTGA2D8/edit
```

**Respuesta esperada:**
```
Identificadores encontrados por slide:
═════════════════════════════════════

📄 Slide 0: $portada
📄 Slide 1: $contenido_principal
📄 Slide 2: $cierre

═════════════════════════════════════
Total: 3 slides con identificadores
```

### Función 2: Obtener Componentes

```
URL: https://docs.google.com/presentation/d/1Q1PtD0eAKaNlWA6fDev4naT1bzNsxZbQRsdbnTGA2D8/edit
Índice de Slide: 0
```

**Respuesta esperada:**
```
Componentes encontrados en Slide 0:
═════════════════════════════════════

1. #titulo
2. #subtitulo
3. #fecha

═════════════════════════════════════
Total: 3 componentes dinámicos
```

## 🔍 Explicación técnica de las funciones

### `extract_slide_ids(presentation_url)`

**¿Qué hace?**
1. Extrae el ID de la presentación desde la URL
2. Obtiene todos los datos de la presentación vía Google Slides API
3. Itera por cada slide (índice 0, 1, 2, ...)
4. Busca en elementos de texto valores que contengan `$` (regex: `\$\w+`)
5. Retorna un diccionario: `{slide_index: identifier}`

**Ejemplo de búsqueda:**
```
Texto dentro de shape: "Esta es la portada $portada"
Match encontrado: "$portada"
Agregado a resultados con índice 0
```

### `get_slide_components(presentation_url, slide_index)`

**¿Qué hace?**
1. Extrae el ID de la presentación
2. Obtiene el dato de la slide específica por índice
3. Busca en TODOS los elementos de la slide (shapes, tablas, etc.)
4. Busca valores que contengan `#` (regex: `\#\w+`)
5. Retorna un SET de componentes únicos (evita duplicados)

**Ejemplo de búsqueda:**
```
Slide 0 contiene:
  - Shape 1: "Título: #titulo"
  - Shape 2: "Fecha: #fecha"
  - Shape 3: "Autor: #titulo" (duplicado)

Resultado: ["#titulo", "#fecha"]
```

## 🐛 Solución de problemas

### Error: "Archivo de credenciales no encontrado"
**Solución:**
- Verifica que `credentials.json` esté en la carpeta raíz
- Revisa la variable `GOOGLE_CREDENTIALS_PATH` en `.env`

### Error: "No se pudo extraer ID de presentación"
**Solución:**
- La URL debe ser como: `https://docs.google.com/presentation/d/{ID}/edit`
- No uses URLs acortadas o con parámetros extras innecesarios

### Error de conexión al servidor
**Solución:**
```bash
# Verifica que el servidor está corriendo
# En otra terminal, prueba:
curl http://localhost:8000/api/health

# Si obtienes un error, reinicia el servidor:
python app.py
```

### "Permission denied" al acceder a la presentación
**Solución:**
- Comparte la presentación con el email del Service Account
- El email se encuentra en el archivo `credentials.json` bajo `client_email`

## 🔐 Seguridad

⚠️ **IMPORTANTE:**
- **NUNCA** subas `credentials.json` a un repositorio público
- Agrega `credentials.json` a `.gitignore`
- En producción, usa variables de entorno para las credenciales

Archivo `.gitignore` recomendado:
```
credentials.json
.env
__pycache__/
venv/
*.pyc
```

## 🎯 Próximos pasos (para el objetivo final)

Este proyecto es la base para la automatización completa. El flujo sería:

1. **Usuario sube PDF** ← (Función futura)
2. **Sistema extrae datos del PDF** ← (Función futura)
3. **Sistema obtiene estructura de slide** ← (Función 1: `extract_slide_ids()`)
4. **Sistema obtiene componentes** ← (Función 2: `get_slide_components()`)
5. **Sistema llena componentes con datos del PDF** ← (Función futura)
6. **Sistema duplica slide según necesidad** ← (Función futura)
7. **Presentación automatizada completada** ✅

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs en la terminal del servidor
2. Comprueba que `credentials.json` está correcto
3. Verifica que la presentación está compartida con el Service Account
4. Consulta la [documentación oficial de Google Slides API](https://developers.google.com/slides/api)

---

**Creado con ❤️ para automatizar Google Slides**
