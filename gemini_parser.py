# gemini_parser.py — mandar texto a Gemini y obtener interpretación o JSON por tipo de slide.

import json
import os
import re
from typing import Any, Dict, List, Optional

DEFAULT_SLIDE_INDEX = 0


def ask_gemini(text: str, instruction: str = "Qué entiendes de este texto?", model: str = None) -> str:
    """Envía texto a la IA y devuelve su respuesta en texto plano."""
    if not (text and text.strip()):
        return ""
    model = model or os.getenv("GEMINI_MODEL") or "gemini-3.1-flash-lite-preview"
    from google import genai
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = f"{instruction}\n\nTexto:\n{text.strip()}"
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"temperature": 0.0},
    )
    return (response.text or "").strip()


def _parse_json_from_response(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    return {}


# Tipos de contenido que la IA puede detectar (alineados con context.json y escalables)
CONTENT_TYPES = (
    "comparacion",      # dos o más temas comparados (ej. A vs B, columnas)
    "descripcion",      # un solo concepto: título + cuerpo/desarrollo
    "lista_items",      # varios ítems o puntos (ej. 1. X 2. Y 3. Z, cada uno con título/descripción)
    "portada",          # título principal + pie/footer o aviso
    "capitulo",         # número de capítulo/sección + título de sección
    "otro",             # otro tipo (usar content_type_note para aclarar)
)

# Normaliza el JSON que devuelve Gemini a la estructura esperada
def _normalize_interpretation(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza el JSON que devuelve Gemini a la estructura esperada."""
    out = {
        "content_type": "",
        "content_type_note": "",
        "main_title": "",
        "has_subtitles": False,
        "subtitles": [],
    }
    if not parsed:
        return out
    # content_type
    ct = (parsed.get("content_type") or parsed.get("tipo_contenido") or parsed.get("tipo") or "").strip().lower()
    if ct in CONTENT_TYPES:
        out["content_type"] = ct
    elif ct:
        out["content_type"] = "otro"
        out["content_type_note"] = ct[:300]
    # content_type_note (cuando es "otro" o aclaración)
    note = (parsed.get("content_type_note") or parsed.get("nota_tipo") or "").strip()[:300]
    if note:
        out["content_type_note"] = note
    # main_title
    main = parsed.get("main_title") or parsed.get("titulo") or ""
    out["main_title"] = (main if isinstance(main, str) else str(main)).strip()[:500]
    # has_subtitles
    sub = parsed.get("subtitles") or parsed.get("subtitulos") or parsed.get("items") or []
    if isinstance(sub, list):
        out["has_subtitles"] = len(sub) > 0
        for item in sub[:20]:
            if isinstance(item, dict):
                title = (item.get("title") or item.get("titulo") or item.get("name") or "").strip()[:500]
                desc = (item.get("description") or item.get("descripcion") or "").strip()[:1500]
                out["subtitles"].append({"title": title, "description": desc})
            elif isinstance(item, str):
                out["subtitles"].append({"title": item[:500], "description": ""})
    return out

# Pide a Gemini que INTERPRETE el texto: tipo de contenido (comparación, descripción, lista de ítems, etc.), si hay título, subtítulos y descripciones. Estructura escalable.
def ask_gemini_title_and_subtitles(text: str, model: str = None) -> Dict[str, Any]:
    if not (text and text.strip()):
        return {"content_type": "", "content_type_note": "", "main_title": "", "has_subtitles": False, "subtitles": []}
    instruction = (
        "Interpretá el siguiente texto y clasificá su contenido. Devolvé ÚNICAMENTE un JSON (en español) con:\n"
        "- content_type: uno de estos valores según lo que sea el texto:\n"
        "  • comparacion = dos o más temas/opciones comparados (ej. A: algo. B: algo; columnas).\n"
        "  • descripcion = un solo concepto desarrollado (título + cuerpo o párrafo).\n"
        "  • lista_items = varios ítems o puntos (ej. 1. X: texto. 2. Y: texto. 3. Z: texto).\n"
        "  • portada = título principal y/o pie/footer, aviso legal.\n"
        "  • capitulo = número de capítulo o sección + título de sección.\n"
        "  • otro = no encaja arriba (opcionalmente usá content_type_note para aclarar).\n"
        "- content_type_note: (opcional) una frase corta que aclare el tipo si es 'otro' o para matizar.\n"
        "- main_title: título o tema general si hay; si no, string vacío.\n"
        "- has_subtitles: true si hay subtemas, ítems o secciones claras (ej. nombres seguidos de descripción); false si es un solo bloque.\n"
        "- subtitles: lista de objetos con 'title' y 'description'. Cada ítem o tema del texto es un elemento. Si has_subtitles es false, lista vacía [].\n"
        "No inventes contenido; solo extraé y clasificá lo que está en el texto.\n"
        "Ejemplo comparación: {\"content_type\": \"comparacion\", \"content_type_note\": \"\", \"main_title\": \"Bebidas energéticas\", \"has_subtitles\": true, \"subtitles\": [{\"title\": \"Monster\", \"description\": \"...\"}, {\"title\": \"Red bull\", \"description\": \"...\"}]}.\n"
        "Ejemplo descripción: {\"content_type\": \"descripcion\", \"main_title\": \"Resumen del proyecto\", \"has_subtitles\": false, \"subtitles\": []}.\n"
        "Ejemplo lista: {\"content_type\": \"lista_items\", \"main_title\": \"Herramientas\", \"has_subtitles\": true, \"subtitles\": [{\"title\": \"GTM\", \"description\": \"...\"}, {\"title\": \"GA4\", \"description\": \"...\"}]}."
    )
    raw = ask_gemini(text, instruction=instruction, model=model)
    parsed = _parse_json_from_response(raw)
    return _normalize_interpretation(parsed)

#Construye la instrucción para Gemini según los placeholders y el template de context.json.
def _build_instruction_for_slide(placeholders: List[str], context_template: Optional[Dict[str, Any]]) -> str:
    if context_template:
        parts = [
            "Interpretá el siguiente texto y devolvé ÚNICAMENTE un JSON con estas claves (en español).",
            context_template.get("instrucciones", ""),
        ]
        marcadores = context_template.get("marcadores") or {}
        marcadores_norm = {k.lstrip("#").lower(): v for k, v in marcadores.items()}
        for p in placeholders:
            desc = marcadores_norm.get(p) or marcadores.get(f"#{p}") or marcadores.get(p) or "valor que corresponda"
            parts.append(f"- {p}: {desc}")
        if context_template.get("few_shot_ejemplo"):
            parts.append("\nEjemplo: " + context_template["few_shot_ejemplo"])
        if context_template.get("ejemplo_incorrecto"):
            parts.append("\n" + context_template["ejemplo_incorrecto"])
        parts.append("\nNo agregues texto fuera del JSON. Cada clave = un fragmento distinto; no repitas el mismo texto en varias claves.")
        return "\n".join(parts)
    # Sin template: instrucción genérica
    keys_str = ", ".join(placeholders)
    return (
        f"Interpretá el texto y devolvé ÚNICAMENTE un JSON con exactamente estas claves: {keys_str}. "
        "Asigná a cada clave el fragmento de texto que corresponda por significado. "
        "No repitas el mismo texto en varias claves. Respuesta = solo el objeto JSON."
    )

#     Dado un texto, la lista de placeholders de una slide y opcionalmente el template de context.json, pide a Gemini que devuelva un JSON con esas claves rellenadas según el significado de cada una.
def ask_gemini_for_slide(
    text: str,
    placeholders: List[str],
    context_template: Optional[Dict[str, Any]] = None,
    model: str = None,
) -> Dict[str, str]:
    if not (text and text.strip()):
        return {p: "" for p in placeholders}
    placeholders = [p.lstrip("#").lower() for p in placeholders if (p or "").strip()]
    if not placeholders:
        return {}
    instruction = _build_instruction_for_slide(placeholders, context_template)
    raw = ask_gemini(text, instruction=instruction, model=model)
    out = {p: "" for p in placeholders}
    parsed = _parse_json_from_response(raw)
    # Normalizar claves del JSON (pueden venir con otro casing)
    parsed_lower = {k.lower(): v for k, v in parsed.items() if isinstance(k, str)}
    for key in out:
        if key in parsed_lower and isinstance(parsed_lower[key], str):
            out[key] = parsed_lower[key].strip()[:1500]
        elif key in parsed_lower:
            out[key] = str(parsed_lower[key]).strip()[:1500]
    return out
