""" Este archivo crea un servidor FastAPI que expone las funciones principales como endpoints HTTP. """

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
import os
import io
from dotenv import load_dotenv
import logging
from PyPDF2 import PdfReader
from docx import Document

# Importa el módulo con las funciones principales
from slides_automation import GoogleSlidesAutomation
# Carga variables de entorno desde .env
load_dotenv()
# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Obtiene la ruta del archivo de credenciales
def get_credentials_path() -> str:
    return os.getenv('GOOGLE_CREDENTIALS_PATH', './credentials.json')

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

#Helper para loguear y re-lanzar errores de API de manera consistente
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
            "health": "GET /api/health"
        }
    }

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


@app.post("/api/upload-and-fill", tags=["Slides"])
async def upload_and_fill(
    presentation_url: str = Form(...),
    slide_identifier: str = Form(...),
    folder_url_or_id: str = Form(""),
    new_name: str = Form(None),
    file: UploadFile = File(...)
):
    """
    Sube un PDF o DOCX, crea una copia de la presentación, extrae título/descripcion y reemplaza marcadores (#) en la slide con $identificador.
    Marcadores soportados: #title, #titulo, #description, #descripcion.
    """
    try:
        if not presentation_url or 'docs.google.com/presentation' not in presentation_url:
            raise ValueError("URL de presentación inválida.")

        ext = os.path.splitext(file.filename or "")[1].lower()
        raw_bytes = await file.read()

        if ext == ".pdf":
            text = _extract_text_from_pdf(raw_bytes)
        elif ext == ".docx":
            text = _extract_text_from_docx(raw_bytes)
        else:
            raise ValueError("Formato no soportado. Usa PDF o DOCX.")

        if not text:
            raise ValueError("No se pudo extraer texto del archivo proporcionado.")

        parts = _split_title_description(text)
        replacements = {
            "title": parts["title"],
            "description": parts["description"]
        }

        automation = create_automation(validate_credentials())
        # Crear copia primero
        new_presentation_id = automation.copy_presentation_to_folder(
            presentation_url,
            folder_url_or_id,
            new_name
        )
        new_presentation_url = f"https://docs.google.com/presentation/d/{new_presentation_id}/edit"

        identifiers_list = [token for token in slide_identifier.split() if token.strip()]
        result = automation.replace_components_in_slide(
            new_presentation_url,
            identifiers_list,
            replacements,
            require_all_markers=False
        )

        return {
            "success": True,
            "slide_identifier": slide_identifier,
            "applied_replacements": list(replacements.keys()),
            "message": "Contenido actualizado en la presentación",
            "new_presentation_id": new_presentation_id,
            "new_presentation_url": new_presentation_url,
            **result
        }

    except Exception as e:
        handle_api_error("cargando archivo y reemplazando contenido", e)

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
