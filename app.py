""" Este archivo crea un servidor FastAPI que expone las funciones principales como endpoints HTTP. """

from fastapi import FastAPI, HTTPException, UploadFile, File, Form  # File para parse-and-fill/upload
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
import os
import io
import json
import tempfile
from dotenv import load_dotenv
import logging
from PyPDF2 import PdfReader
from docx import Document

# Importa el módulo con las funciones principales
from slides_automation import GoogleSlidesAutomation
from gemini_parser import ask_gemini, ask_gemini_title_and_subtitles, ask_gemini_for_slide, DEFAULT_SLIDE_INDEX

# Carga variables de entorno desde .env
load_dotenv()
# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ruta base del proyecto (carpeta donde está app.py)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Contexto de slides (context.json) para enriquecer el prompt de Gemini
CONTEXT_PATH = os.path.join(PROJECT_ROOT, "context.json")


def _load_context_json() -> dict:
    """Carga context.json completo."""
    if not os.path.exists(CONTEXT_PATH):
        return {}
    try:
        with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_slide_context_for_identifiers(identifiers: List[str]):
    """Carga context.json y devuelve finalidad + marcadores para el primer $ que exista en el contexto."""
    if not identifiers:
        return None
    data = _load_context_json()
    slides_context = data.get("slides_context") or {}
    for ident in identifiers:
        key = ident if ident.startswith("$") else f"${ident}"
        if key in slides_context:
            return slides_context[key]
        if ident.lower() in {k.lower().lstrip("$") for k in slides_context}:
            for k in slides_context:
                if k.lower().lstrip("$") == ident.lower():
                    return slides_context[k]
    return None


def get_slide_context_by_placeholders(placeholders: List[str]):
    """
    Dada la lista de placeholders de una slide (ej. main_title, column_1_title, ...),
    devuelve el template de context.json cuyos marcadores coinciden exactamente.
    placeholders puede venir con o sin # (se normaliza a sin # y lower).
    """
    data = _load_context_json()
    slides_context = data.get("slides_context") or {}
    want = {p.lstrip("#").lower() for p in placeholders if (p or "").strip()}
    if not want:
        return None
    for _key, template in slides_context.items():
        marcadores = template.get("marcadores") or {}
        have = {k.lstrip("#").lower() for k in marcadores}
        if have == want:
            return template
    return None

#Obtiene la ruta del archivo de credenciales
def get_credentials_path() -> str:
    path = os.getenv('GOOGLE_CREDENTIALS_PATH', './credentials.json')
    if not os.path.isabs(path):
        path = os.path.normpath(os.path.join(PROJECT_ROOT, path))
    return path

#Valida que exista el archivo de credenciales y lo devuelve
def validate_credentials() -> str:
    creds_path = get_credentials_path()
    if not os.path.exists(creds_path):
        raise HTTPException(
            status_code=400,
            detail=f"Archivo de credenciales no encontrado: {creds_path}"
        )
    return creds_path

# crea instancia de automatización
def create_automation(credentials_path: str) -> GoogleSlidesAutomation:
    return GoogleSlidesAutomation(credentials_path)

#Helper para loguear y re-lanzar errores de API 
def handle_api_error(context: str, error: Exception) -> None:
    logger.error(f"✗ Error {context}: {str(error)}")
    if isinstance(error, ValueError):
        raise HTTPException(status_code=400, detail=str(error))
    raise HTTPException(status_code=500, detail=f"Error al procesar: {str(error)}")

# ===== Helpers de parsing de archivos =====
def _extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts).strip()


def _extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text]
    return "\n".join(paragraphs).strip()


def _split_title_description(text: str) -> Dict[str, str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return {"title": "Sin título", "description": "Sin contenido disponible"}

    title = lines[0][:140]
    description_text = " ".join(lines[1:]) if len(lines) > 1 else ""
    description = (description_text or " ".join(lines)).strip()
    # Limitar tamaño para evitar errores de Slides
    description = description[:1500]
    return {"title": title, "description": description}

# CONFIGURACIÓN APP
app = FastAPI(
    title="Google Slides Automation API",
    description="API para automatizar Google Slides con identificadores y componentes dinámicos",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MODELOS DE DATOS (Pydantic)
#Solicitud para extraer identificadores de slides
class ExtractSlideIdsRequest(BaseModel):
    presentation_url: str

#Solicitud para obtener componentes de una slide específica"
class GetSlideComponentsRequest(BaseModel):
    presentation_url: str
    slide_index: int

#Solicitud para copiar una presentación completa
class CopyPresentationRequest(BaseModel):
    presentation_url: str
    folder_url_or_id: str
    new_name: str = None

#Solicitud para listar slides de una presentación
class ListSlidesRequest(BaseModel):
    presentation_url: str

#Solicitud para copia con reordenamiento
class CustomCopyRequest(BaseModel):
    presentation_url: str
    folder_url_or_id: str
    new_name: str = None
    slide_counts: Dict[int, int] = None
    slide_sequence: List[int] = None

# Solicitud para generar presentación desde especificación (slide_n → type $, content #)
class BuildFromSpecRequest(BaseModel):
    presentation_url: str
    folder_url_or_id: str
    new_name: str = None
    spec: Dict  # ej. {"slide_1": {"type": "cover", "content": {"title": "..."}}, ...}

# Solicitud para parsear texto con Gemini y rellenar slide (sobre una copia)
# Si se envía parsed_replacements (JSON ya generado), se usa ese y no se llama a Gemini
class ParseAndFillRequest(BaseModel):
    presentation_url: str
    folder_url_or_id: str
    new_name: str = None
    text: str = ""
    slide_index: int = 0
    parsed_replacements: Dict = None  # Opcional: si viene del "Solo parsear", reutilizamos y no llamamos a Gemini

# Solo texto; opcionalmente URL + slide_index para ver el JSON que generaría Gemini para esa slide
class ParseTextRequest(BaseModel):
    text: str
    presentation_url: str = None
    slide_index: int = 0

# Probar solo la IA: mandar texto y que devuelva lo que entiende
class AskGeminiRequest(BaseModel):
    text: str


# Ponelo en la slide N: texto + URL + índice → JSON con placeholders de esa slide
class AskGeminiForSlideRequest(BaseModel):
    text: str
    presentation_url: str
    slide_index: int = 0

#Respuesta con los identificadores de slides
class ExtractSlideIdsResponse(BaseModel):
    success: bool
    slide_identifiers: Dict[int, List[str]]
    message: str

#Respuesta con lista de slides
class ListSlidesResponse(BaseModel):
    success: bool
    slides: List[Dict]
    message: str

#Respuesta con los componentes de una slide
class GetSlideComponentsResponse(BaseModel):
    success: bool
    slide_index: int
    components: List[str]
    message: str

#Respuesta que indica el estado del servicio
class HealthResponse(BaseModel):
    status: str
    message: str

# ENDPOINTS
@app.get("/", tags=["Frontend"])
async def root():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    
    return {
        "service": "Google Slides Automation API",
        "version": "1.0.0",
        "message": "Archivo frontend no encontrado",
        "endpoints": {
            "extract_ids": "POST /api/extract-slide-ids",
            "get_components": "POST /api/get-slide-components",
            "build_from_spec": "POST /api/build-from-spec",
            "parse_text": "POST /api/parse-text (solo Gemini, para probar)",
            "parse_and_fill": "POST /api/parse-and-fill",
            "parse_and_fill_upload": "POST /api/parse-and-fill/upload",
            "health": "GET /api/health"
        }
    }

@app.post("/api/ask-gemini", tags=["Gemini"])
async def ask_gemini_endpoint(request: AskGeminiRequest):
    """Envía texto a la IA y devuelve solo lo que interpreta (texto en bruto)."""
    try:
        text = (request.text or "").strip()
        if not text:
            raise ValueError("El texto no puede estar vacío.")
        response = ask_gemini(text)
        return {"success": True, "response": response or "(La IA no devolvió texto)"}
    except Exception as e:
        err = str(e).upper()
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "QUOTA" in err:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Límite de uso de la API alcanzado. "
                    "Esperá ~1 minuto y probá de nuevo, o creá otra API key en https://aistudio.google.com/apikey (cada key tiene su propia cuota). "
                    "Cuotas: https://ai.google.dev/gemini-api/docs/rate-limits"
                ),
            )
        handle_api_error("ask-gemini", e)


@app.post("/api/ask-gemini-structure", tags=["Gemini"])
async def ask_gemini_structure_endpoint(request: AskGeminiRequest):
    """Devuelve título, 2 subtítulos y descripciones a partir del texto."""
    try:
        text = (request.text or "").strip()
        if not text:
            raise ValueError("El texto no puede estar vacío.")
        structured = ask_gemini_title_and_subtitles(text)
        return {"success": True, "structured": structured}
    except Exception as e:
        err = str(e).upper()
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "QUOTA" in err:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Límite de uso de la API alcanzado. "
                    "Esperá ~1 minuto y probá de nuevo, o creá otra API key en https://aistudio.google.com/apikey (cada key tiene su propia cuota). "
                    "Cuotas: https://ai.google.dev/gemini-api/docs/rate-limits"
                ),
            )
        handle_api_error("ask-gemini-structure", e)


@app.post("/api/ask-gemini-for-slide", tags=["Gemini"])
async def ask_gemini_for_slide_endpoint(request: AskGeminiForSlideRequest):
    """
    Obtiene los placeholders de la slide indicada, busca el template en context.json
    y devuelve el JSON que Gemini genera para rellenar esa slide con el texto dado.
    """
    try:
        text = (request.text or "").strip()
        if not text:
            raise ValueError("El texto no puede estar vacío.")
        url = (request.presentation_url or "").strip()
        if not url or "docs.google.com/presentation" not in url or "/d/" not in url:
            raise ValueError("Se necesita la URL de la presentación (Google Slides) para saber qué placeholders tiene la slide.")
        slide_index = request.slide_index if request.slide_index >= 0 else 0
        automation = create_automation(validate_credentials())
        components = automation.get_slide_components(url, slide_index)
        if not components:
            raise ValueError(
                f"En la slide {slide_index} no hay ningún marcador #. "
                "Agregá placeholders (ej. #main_title, #description) en esa slide."
            )
        placeholders = [c.lstrip("#").lower() for c in components]
        context_template = get_slide_context_by_placeholders(placeholders)
        structured = ask_gemini_for_slide(text, placeholders, context_template)
        return {
            "success": True,
            "slide_index": slide_index,
            "placeholders": placeholders,
            "template_matched": context_template is not None,
            "structured": structured,
        }
    except Exception as e:
        err = str(e).upper()
        if "429" in err or "RESOURCE_EXHAUSTED" in err or "QUOTA" in err:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Límite de uso de la API alcanzado. "
                    "Esperá ~1 minuto y probá de nuevo, o creá otra API key en https://aistudio.google.com/apikey. "
                    "Cuotas: https://ai.google.dev/gemini-api/docs/rate-limits"
                ),
            )
        handle_api_error("ask-gemini-for-slide", e)


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
#Verificar estado del servicio y archivo de credenciales
async def health_check():
    try:
        validate_credentials()
        return HealthResponse(
            status="healthy",
            message="Servicio activo y listo"
        )
    except HTTPException as e:
        logger.warning("⚠ Credenciales no encontradas")
        return HealthResponse(
            status="warning",
            message="Archivo de credenciales no configurado"
        )

# Montar carpeta de recursos estáticos
if os.path.exists('./static'):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/api/extract-slide-ids", response_model=ExtractSlideIdsResponse, tags=["Slides"])
#Extrae identificadores ($) de todas las slides
async def extract_slide_ids(request: ExtractSlideIdsRequest):
    try:
        automation = create_automation(validate_credentials())
        slide_identifiers = automation.extract_slide_ids(request.presentation_url)
        
        logger.info(f"✓ Se extrajeron {len(slide_identifiers)} identificadores")
        return ExtractSlideIdsResponse(
            success=True,
            slide_identifiers=slide_identifiers,
            message=f"Se encontraron {len(slide_identifiers)} slides con identificadores"
        )
    except Exception as e:
        handle_api_error("extrayendo IDs de slides", e)

@app.post("/api/get-slide-components", response_model=GetSlideComponentsResponse, tags=["Slides"])
# Obtiene componentes (#) de una slide específica
async def get_slide_components(request: GetSlideComponentsRequest):
    try:
        if request.slide_index < 0:
            raise ValueError("El índice de slide debe ser >= 0")
        
        automation = create_automation(validate_credentials())
        components = automation.get_slide_components(
            request.presentation_url,
            request.slide_index
        )
        
        logger.info(f"✓ Se extrajeron {len(components)} componentes de slide {request.slide_index}")
        return GetSlideComponentsResponse(
            success=True,
            slide_index=request.slide_index,
            components=components,
            message=f"Se encontraron {len(components)} componentes en la slide {request.slide_index}"
        )
    except Exception as e:
        handle_api_error("obteniendo componentes", e)


@app.post("/api/copy-presentation", tags=["Slides"])
#Copia una presentación completa a una carpeta de Drive
async def copy_presentation(request: CopyPresentationRequest):
    try:
        automation = create_automation(validate_credentials())
        new_id = automation.copy_presentation_to_folder(
            request.presentation_url,
            request.folder_url_or_id,
            request.new_name
        )
        new_url = f"https://docs.google.com/presentation/d/{new_id}/edit"
        return {
            "success": True,
            "new_presentation_id": new_id,
            "new_presentation_url": new_url,
            "message": "Copia completa creada correctamente"
        }
    except Exception as e:
        handle_api_error("copiando presentación", e)

@app.post("/api/list-slides", response_model=ListSlidesResponse, tags=["Slides"])
# Lista todas las slides de una presentación
async def list_slides(request: ListSlidesRequest):
    try:
        automation = create_automation(validate_credentials())
        slides = automation.get_presentation_slides(request.presentation_url)
        return {
            "success": True,
            "slides": slides,
            "message": f"Se encontraron {len(slides)} slides"
        }
    except Exception as e:
        handle_api_error("listando slides", e)

@app.post("/api/copy-custom", tags=["Slides"])
# Copia avanzada con reordenamiento - slide_sequence tiene prioridad sobre slide_counts
async def copy_custom(request: CustomCopyRequest):
    try:
        automation = create_automation(validate_credentials())
        slide_counts = request.slide_counts if request.slide_counts else {}
        
        new_id = automation.copy_presentation_advanced(
            request.presentation_url,
            slide_counts,
            request.folder_url_or_id,
            request.new_name,
            request.slide_sequence
        )
        
        new_url = f"https://docs.google.com/presentation/d/{new_id}/edit"
        return {
            "success": True,
            "new_presentation_id": new_id,
            "new_presentation_url": new_url,
            "message": "Copia personalizada creada correctamente"
        }
    except Exception as e:
        handle_api_error("copiando presentación personalizada", e)


@app.post("/api/fill-from-json", tags=["Slides"])
async def fill_from_json(
    presentation_url: str = Form(...),
    folder_url_or_id: str = Form(""),
    new_name: str = Form(None),
    data_json: str = Form(...),
    remove_identifiers: bool = Form(True)
):
    """
    Recibe un JSON con pares clave-valor para marcadores # y llena toda la presentación.
    Si se pasa carpeta o nombre, primero crea una copia; de lo contrario, edita la presentación indicada.
    """
    try:
        if not presentation_url or 'docs.google.com/presentation' not in presentation_url:
            raise ValueError("URL de presentación inválida.")

        try:
            data = json.loads(data_json)
        except Exception as e:
            raise ValueError(f"JSON inválido: {e}")

        automation = create_automation(validate_credentials())
        result = automation.fill_presentation_from_json(
            presentation_url=presentation_url,
            data=data,
            folder_url_or_id=folder_url_or_id,
            new_name=new_name,
            remove_identifiers=bool(remove_identifiers)
        )

        new_url = f"https://docs.google.com/presentation/d/{result['presentation_id']}/edit"
        return {
            "success": True,
            "message": "Presentación actualizada",
            "new_presentation_id": result['presentation_id'],
            "new_presentation_url": new_url,
            **result
        }
    except Exception as e:
        handle_api_error("rellenando presentación con JSON", e)


@app.post("/api/build-from-spec", tags=["Slides"])
# Genera una presentación: URL plantilla + carpeta destino + JSON spec (slide_n → type $, content #)
async def build_from_spec(request: BuildFromSpecRequest):
    """
    Crea una presentación a partir de una plantilla, carpeta de destino y un JSON de especificación.

    - **presentation_url**: URL de la presentación plantilla (con slides identificadas con $).
    - **folder_url_or_id**: URL o ID de la carpeta de Drive donde guardar la copia.
    - **spec**: JSON con claves slide_1, slide_2, ... slide_n. Cada valor tiene:
      - **type**: identificador de la diapo plantilla (ej. "cover", "chapter") → busca la slide con $cover, $chapter.
      - **content**: dict de reemplazos para los marcadores # (ej. {"title": "Título", "description": "..."}).
    - **new_name**: nombre opcional de la nueva presentación.

    Las diapos se ordenan según slide_1, slide_2, ... y se rellenan con su content.
    """
    try:
        automation = create_automation(validate_credentials())
        result = automation.build_presentation_from_spec(
            presentation_url=request.presentation_url,
            folder_url_or_id=request.folder_url_or_id,
            spec=request.spec,
            new_name=request.new_name,
            remove_identifiers=True
        )
        return {
            "success": True,
            "message": "Presentación generada desde especificación",
            "new_presentation_id": result["presentation_id"],
            "new_presentation_url": result["presentation_url"],
            "slides_count": result["slides_count"],
            "slide_sequence": result["slide_sequence"],
        }
    except Exception as e:
        handle_api_error("generando presentación desde spec", e)


@app.post("/api/verify-access", tags=["Slides"])
# Verifica si el Service Account tiene acceso a una presentación
async def verify_access(request: ExtractSlideIdsRequest):
    try:
        automation = create_automation(validate_credentials())
        access_info = automation.verify_presentation_access(request.presentation_url)

        return {
            "success": True,
            **access_info,
            "message": "Acceso verificado" if access_info['overall_access'] else "⚠ Acceso limitado"
        }
    except Exception as e:
        handle_api_error("verificando acceso", e)

# Prueba Gemini: requiere URL de plantilla + índice de slide. Devuelve el prompt que se mandó a Gemini y el JSON que devolvió.
@app.post("/api/parse-text", tags=["Gemini"])
async def parse_text_only(request: ParseTextRequest):
    try:
        text = (request.text or "").strip()
        if not text:
            raise ValueError("Se requiere el campo 'text'.")
        url = (request.presentation_url or "").strip()
        slide_index = request.slide_index if request.slide_index >= 0 else 0
        if not url or "docs.google.com/presentation" not in url or "/d/" not in url:
            raise ValueError("Para probar el parseo con placeholders se necesita URL de la plantilla (Google Slides) e índice de la slide.")

        automation = create_automation(validate_credentials())
        components = automation.get_slide_components(url, slide_index)
        if not components:
            raise ValueError(
                f"En la slide {slide_index} no hay ningún marcador #. Elegí otra slide."
            )
        placeholders = [c.lstrip("#").lower() for c in components]
        slide_ids = automation.extract_slide_ids(url)
        identifiers = slide_ids.get(slide_index, []) or []
        slide_context = _load_slide_context_for_identifiers(identifiers)
        response_raw = ask_gemini(text) if text else ""
        parsed = {p: "" for p in placeholders}
        return {
            "success": True,
            "message": f"Respuesta de Gemini (slide {slide_index}). Por ahora solo se muestra lo que entiende; no hay segmentación a placeholders.",
            "slide_index": slide_index,
            "placeholders": placeholders,
            "prompt_sent": "",
            "response_raw": response_raw,
            "parsed": parsed,
        }
    except Exception as e:
        handle_api_error("parseando texto con Gemini", e)

# Crea una copia en la carpeta indicada y rellena la slide. Si viene parsed_replacements (del "Solo parsear"), reutiliza ese JSON y no llama a Gemini.
@app.post("/api/parse-and-fill", tags=["Slides", "Gemini"])
async def parse_and_fill(request: ParseAndFillRequest):
    try:
        if not (request.folder_url_or_id or request.folder_url_or_id.strip()):
            raise ValueError("Se requiere 'folder_url_or_id' para crear la copia. La plantilla original NUNCA se modifica.")

        automation = create_automation(validate_credentials())
        copy_id = automation.copy_presentation_to_folder(
            request.presentation_url,
            request.folder_url_or_id.strip(),
            request.new_name or None,
        )
        copy_url = f"https://docs.google.com/presentation/d/{copy_id}/edit"
        slide_index = request.slide_index if request.slide_index >= 0 else 0

        components = automation.get_slide_components(copy_url, slide_index)
        if not components:
            raise ValueError(
                f"En la slide {slide_index} no hay ningún marcador #. "
                "Elegí otra slide o agregá placeholders (ej. #titulo, #descripcion) en esa slide."
            )
        placeholders = [c.lstrip("#").lower() for c in components]

        # Solo rellenamos si nos pasan el JSON (parsed_replacements). No hay segmentación automática.
        if request.parsed_replacements and isinstance(request.parsed_replacements, dict) and len(request.parsed_replacements) > 0:
            parsed = request.parsed_replacements
        else:
            raise ValueError("Se requiere 'parsed_replacements' (JSON con claves/valores para cada placeholder). La segmentación desde texto no está disponible.")

        result = automation.replace_components_in_slide_by_index(
            presentation_url=copy_url,
            slide_index=slide_index,
            replacements=parsed,
        )
        return {
            "success": True,
            "message": "Se creó una copia y se rellenaron los placeholders. La plantilla original no fue modificada.",
            "parsed": parsed,
            "placeholders": placeholders,
            "slide_index": slide_index,
            "presentation_id": copy_id,
            "new_presentation_url": copy_url,
            "replaced": result["replaced"],
        }
    except Exception as e:
        handle_api_error("parseando y rellenando slide", e)

# Igual que parse-and-fill pero con archivo (PDF/DOCX)
@app.post("/api/parse-and-fill/upload", tags=["Slides", "Gemini"])
async def parse_and_fill_upload(
    presentation_url: str = Form(...),
    folder_url_or_id: str = Form(...),
    new_name: str = Form(""),
    slide_index: int = Form(0),
    file: UploadFile = File(None),
    text: str = Form(""),
):
    try:
        raw_text = (text or "").strip()
        if file and file.filename:
            content = await file.read()
            if file.filename.lower().endswith(".pdf"):
                raw_text = _extract_text_from_pdf(content)
            elif file.filename.lower().endswith(".docx"):
                raw_text = _extract_text_from_docx(content)
            else:
                raw_text = content.decode("utf-8", errors="replace")
        if not raw_text or not raw_text.strip():
            raise ValueError("Se requiere texto o un archivo PDF/DOCX con contenido.")
        if not (folder_url_or_id or folder_url_or_id.strip()):
            raise ValueError("Se requiere 'folder_url_or_id'. La plantilla original NUNCA se modifica.")

        automation = create_automation(validate_credentials())
        copy_id = automation.copy_presentation_to_folder(
            presentation_url,
            folder_url_or_id.strip(),
            new_name.strip() or None,
        )
        copy_url = f"https://docs.google.com/presentation/d/{copy_id}/edit"

        idx = slide_index if slide_index >= 0 else 0
        slide_ids = automation.extract_slide_ids(copy_url)
        identifiers = slide_ids.get(idx, []) or []
        slide_context = _load_slide_context_for_identifiers(identifiers)

        components = automation.get_slide_components(copy_url, idx)
        if not components:
            raise ValueError(
                f"En la slide {idx} no hay ningún marcador #. Elegí otra slide o agregá placeholders."
            )
        placeholders = [c.lstrip("#").lower() for c in components]
        parsed = {p: "" for p in placeholders}

        result = automation.replace_components_in_slide_by_index(
            presentation_url=copy_url,
            slide_index=idx,
            replacements=parsed,
        )
        return {
            "success": True,
            "message": "Se creó una copia y Gemini completó los placeholders.",
            "parsed": parsed,
            "placeholders": placeholders,
            "slide_index": idx,
            "presentation_id": copy_id,
            "new_presentation_url": copy_url,
            "replaced": result["replaced"],
        }
    except Exception as e:
        handle_api_error("parseando y rellenando desde archivo", e)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    
    print(f"""
    ╔════════════════════════════════════════╗
    ║  Google Slides Automation API          ║
    ║  Servidor iniciando en puerto {port}...   ║
    ║  http://localhost:{port}                ║
    ╚════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
