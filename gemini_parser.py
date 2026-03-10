# Parsear texto con la API de Gemini y extraer contenido. Apto para componentes (#) de una slide.

import json
import logging
import os
import re
from typing import Dict, List, Optional
logger = logging.getLogger(__name__)

# Slide y componente por defecto cuando no se usa "por placeholders"
DEFAULT_SLIDE_INDEX = 0
DEFAULT_COMPONENT_MARKER = "#description"


def parse_text_with_gemini_for_placeholders(
    text: str,
    placeholders: List[str],
    api_key: Optional[str] = None,
) -> Dict[str, str]:
    """
    Pide a Gemini que lea el texto y asigne a cada placeholder el contenido que mejor encaje.
    Los nombres de los placeholders pueden ser en español o inglés (titulo, descripcion, fecha,
    autor, etc.) y Gemini interpreta a qué se refiere cada uno.

    Args:
        text: Texto crudo (ej. resumen de reunión, noticia).
        placeholders: Lista de nombres sin # (ej. ["titulo", "descripcion", "fecha"]).
        api_key: Opcional; si no se pasa, usa GEMINI_API_KEY.

    Returns:
        Dict con una clave por placeholder y el texto asignado por Gemini.
    """
    # Busca la API Key. Si no hay usa el fallback (plan B sin IA)
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or not text or not text.strip():
        return _fallback_for_placeholders(text or "", placeholders)
    if not placeholders:
        return {}

    # Convierte los placeholders a minúsculas y elimina los espacios
    placeholders = [p.strip().lower() for p in placeholders if p and str(p).strip()]
    if not placeholders:
        return {}

    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        placeholders_str = ", ".join(placeholders)
        prompt = (
            "Tenés un texto y una lista de placeholders de una diapositiva. "
            "Cada placeholder es un nombre que indica qué tipo de contenido debe llevar (ej. titulo, descripcion, fecha, autor, resumen). "
            "Leé el texto y asigná a cada placeholder el contenido que mejor encaje. Interpretá el significado de cada nombre "
            "(titulo/title = título breve, descripcion/description = texto más largo, fecha = fecha si aparece, etc.).\n\n"
            f"Placeholders a completar (devolvé un JSON con exactamente estas claves): {placeholders_str}\n\n"
            "Texto:\n"
            f"{text.strip()}\n\n"
            "Respondé ÚNICAMENTE con un JSON válido, sin markdown ni texto extra. "
            "Usá las mismas claves que los placeholders. Si no hay información para un campo, usá cadena vacía o un valor por defecto razonable. "
            "Para campos tipo título: una línea corta. Para descripción/resumen: texto más largo si aplica."
        )

        response = model.generate_content(prompt)
        if not response or not response.text:
            return _fallback_for_placeholders(text, placeholders)

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```\s*$", "", raw)
        parsed = json.loads(raw)

        #Crea un diccionario vacío donde guardaremos los datos finales
        result: Dict[str, str] = {}
        # Itera sobre los placeholders y asigna el valor correspondiente
        for p in placeholders:
            # Busca el valor en el diccionario parsed. Si no lo encuentra, busca en minúsculas.
            val = parsed.get(p) or parsed.get(p.lower())
            # Si no se encuentra el valor, busca en minúsculas.
            if val is None:
                for k, v in parsed.items():
                    if k.lower() == p.lower():
                        val = v
                        break
            # Asigna el valor al diccionario result
            result[p] = (str(val).strip() if val is not None else "")[:1500]
        logger.info("✓ Gemini completó %s placeholders a partir del texto", len(result))
        return result
    except Exception as e:
        logger.warning("Gemini no disponible o error al completar placeholders: %s. Usando fallback.", e)
        return _fallback_for_placeholders(text, placeholders)

# Asigna contenido básico cuando Gemini no está disponible.
def _fallback_for_placeholders(text: str, placeholders: List[str]) -> Dict[str, str]:

    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    first_line = lines[0][:200] if lines else ""
    rest = " ".join(lines[1:])[:1500] if len(lines) > 1 else first_line
    result: Dict[str, str] = {}
    title_like = {"title", "titulo", "heading", "main", "nombre"}
    desc_like = {"description", "descripcion", "body", "texto", "resumen", "desc"}
    for p in placeholders:
        pl = p.lower()
        if pl in title_like or any(t in pl for t in ("titulo", "title", "nombre")):
            result[p] = first_line
        elif pl in desc_like or any(d in pl for d in ("descripcion", "description", "body", "texto")):
            result[p] = rest
        else:
            result[p] = rest if len(rest) > len(first_line) else first_line
    return result

# Envía el texto a Gemini y devuelve un diccionario con 'title' y 'description' listos para rellenar una slide. Si la API falla o no está configurada, devuelve un parseo local simple (primera línea = título, resto = descripción).

def parse_text_with_gemini(text: str, api_key: Optional[str] = None) -> Dict[str, str]:
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or not text or not text.strip():
        return _fallback_parse(text or "")

    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "Dado el siguiente texto, extrae un título breve (máximo 1 línea, para una diapositiva) "
            "y una descripción o resumen (texto corrido, adecuado para una slide). "
            "Responde ÚNICAMENTE con un JSON válido, sin markdown ni texto extra, con las claves "
            '"title" y "description". Ejemplo: {"title": "Mi título", "description": "Texto de la descripción."}\n\n'
            "Texto:\n"
            f"{text.strip()}"
        )
        response = model.generate_content(prompt)
        if not response or not response.text:
            return _fallback_parse(text)

        raw = response.text.strip()
        # Quitar posibles bloques de código markdown
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```\s*$", "", raw)
        # Carga el JSON generado por Gemini
        parsed = json.loads(raw)
        # Extrae el título y la descripción
        title = (parsed.get("title") or "").strip() or "Sin título"
        description = (parsed.get("description") or "").strip() or _fallback_parse(text)["description"]
        # Limitar longitud para Slides 
        title = title[:140]
        description = description[:1500]
        logger.info("✓ Gemini parseó el texto correctamente")
        return {"title": title, "description": description}
    except Exception as e:
        # Si hay un error, usa el fallback
        logger.warning("Gemini no disponible o error al parsear: %s. Usando fallback.", e)
        return _fallback_parse(text)

# Parseo local cuando Gemini no está disponible
def _fallback_parse(text: str) -> Dict[str, str]:

    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    if not lines:
        return {"title": "Sin título", "description": "Sin contenido disponible"}
    title = lines[0][:140]
    description = " ".join(lines[1:]) if len(lines) > 1 else lines[0]
    description = (description or " ").strip()[:1500]
    return {"title": title, "description": description}
