# Referencia: Template "Monks – General Slides"

Estructura del template base (según el PDF exportado) para usar con **`POST /api/build-from-spec`**.

---

## Slides del template (índices 0–4)

| Posición | Identificadores `$` (type en el spec) | Placeholders `#` (content en el spec) |
|----------|----------------------------------------|----------------------------------------|
| **1** (slide_1) | `$cover`, `$presentation` | `#footer_context`, `#main_title` |
| **2** (slide_2) | `$chapter`, `$cover` | `#section_title`, `#chapter`, `#_number` |
| **3** (slide_3) | `$descriptive`, `$presentation` | `#main_title`, `#description` |
| **4** (slide_4) | `$three`, `$items`, `$list` | `#item_1_title`, `#item_1_description`, `#item_2_title`, `#item_2_description`, `#item_3_title`, `#item_3_description` |
| **5** (slide_5) | `$comparative`, `$two`, `$differences` | `#main_title`, `#column_1_title`, `#column_1_description`, `#column_2_title`, `#column_2_description` |

---

## Cómo armar el `spec` para este template

- **`slide_n`**: posición en la presentación final (1 = primera diapositiva).
- **`type`**: uno de los identificadores `$` de la fila. Si varios comparten slide, usa cualquiera de ellos (ej. para la portada: `"cover"` o `"presentation"`; para la de 3 ítems: `"three"`, `"items"` o `"list"`).
- **`content`**: objeto con las claves de los `#` que quieras reemplazar (con o sin `#`). Ejemplos:
  - Portada: `{"main_title": "Título", "footer_context": "Pie opcional"}`
  - Capítulo: `{"section_title": "Sección", "chapter": "Capítulo 1", "_number": "1"}`
  - Descriptiva: `{"main_title": "Título", "description": "Texto..."}`
  - Tres ítems: `{"item_1_title": "...", "item_1_description": "...", "item_2_title": "...", ...}`
  - Comparativa: `{"main_title": "...", "column_1_title": "...", "column_1_description": "...", "column_2_title": "...", "column_2_description": "..."}`

---

## Ejemplo de body para `/api/build-from-spec`

```json
{
  "presentation_url": "https://docs.google.com/presentation/d/TU_ID_DEL_TEMPLATE/edit",
  "folder_url_or_id": "https://drive.google.com/.../folders/TU_FOLDER_ID",
  "new_name": "Presentación Monks - Ejemplo",
  "spec": {
    "slide_1": {
      "type": "cover",
      "content": {
        "main_title": "Presentación de testeo",
        "footer_context": "Contexto opcional"
      }
    },
    "slide_2": {
      "type": "chapter",
      "content": {
        "section_title": "Introducción",
        "chapter": "Capítulo 1",
        "_number": "1"
      }
    },
    "slide_3": {
      "type": "descriptive",
      "content": {
        "main_title": "Resumen ejecutivo",
        "description": "Texto descriptivo largo..."
      }
    },
    "slide_4": {
      "type": "three",
      "content": {
        "item_1_title": "Ítem 1",
        "item_1_description": "Descripción 1",
        "item_2_title": "Ítem 2",
        "item_2_description": "Descripción 2",
        "item_3_title": "Ítem 3",
        "item_3_description": "Descripción 3"
      }
    },
    "slide_5": {
      "type": "comparative",
      "content": {
        "main_title": "Comparativa",
        "column_1_title": "Opción A",
        "column_1_description": "Detalle A",
        "column_2_title": "Opción B",
        "column_2_description": "Detalle B"
      }
    }
  }
}
```

---

**Nota:** El PDF que compartiste es una exportación; la URL que uses en `presentation_url` debe ser la del **archivo de Google Slides** del template (no del PDF).
