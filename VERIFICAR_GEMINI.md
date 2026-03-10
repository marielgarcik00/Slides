# Cómo verificar que Gemini y parse-and-fill funcionan

## 1. Configurar la API key

Crea o edita el archivo `.env` en la raíz del proyecto:

```env
GEMINI_API_KEY=tu_api_key_de_gemini
```

(Si no tienes `.env`, copia `.env.example` y agrega la línea de arriba.)

## 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

O solo Gemini:

```bash
pip install google-generativeai
```

## 3. Probar solo Gemini (sin Google Slides)

Arranca el servidor:

```bash
python app.py
```

En otra terminal, prueba el endpoint que **solo** parsea texto (no toca presentaciones):

```bash
curl -X POST http://localhost:8000/api/parse-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Reunión de lanzamiento. Hoy presentamos el nuevo producto X con todas sus características y fechas."}'
```

Si todo va bien verás algo como:

```json
{
  "success": true,
  "message": "Texto parseado (solo Gemini, sin modificar presentación)",
  "parsed": {
    "title": "Reunión de lanzamiento",
    "description": "Hoy presentamos el nuevo producto X con todas sus características y fechas."
  }
}
```

Si la API key falla, verás un error 500 y en los logs algo como "Gemini no disponible... Usando fallback". En ese caso el `parsed` vendrá del fallback local (primera línea = título, resto = descripción).

## 4. Probar parse-and-fill (Gemini + Google Slides)

Necesitas:

- `credentials.json` de la Service Account con acceso a la presentación.
- Una presentación con la **primera slide** (índice 0) que tenga cajas de texto con los marcadores **`#title`** y **`#description`**.

Luego:

```bash
curl -X POST http://localhost:8000/api/parse-and-fill \
  -H "Content-Type: application/json" \
  -d '{
    "presentation_url": "https://docs.google.com/presentation/d/TU_PRESENTATION_ID/edit",
    "text": "Título del proyecto. Esta es la descripción larga que queremos en la slide."
  }'
```

Si funciona, la primera slide de esa presentación se actualizará con el título y la descripción que devolvió Gemini.

## 5. Documentación interactiva

Con el servidor en marcha, abre en el navegador:

- **Swagger UI:** http://localhost:8000/docs  
- **ReDoc:** http://localhost:8000/redoc  

Ahí puedes probar `POST /api/parse-text` y `POST /api/parse-and-fill` desde el navegador.
