"""
API FASTAPI - Servidor HTTP para las funciones de automatización
=================================================================

Este archivo crea un servidor FastAPI que expone las dos funciones principales
como endpoints HTTP. Permite acceder a las funciones desde el frontend o
desde cualquier cliente HTTP.

Endpoints disponibles:
- GET /                              - Información del servicio
- POST /api/extract-slide-ids        - Extrae identificadores
- POST /api/get-slide-components     - Obtiene componentes
- GET /api/health                    - Verificar estado del servicio
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
import os
from dotenv import load_dotenv
import logging

# Importa el módulo con las funciones principales
from slides_automation import GoogleSlidesAutomation

# Carga variables de entorno desde .env
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Google Slides Automation API",
    description="API para automatizar Google Slides con identificadores y componentes dinámicos",
    version="1.0.0"
)

# CONFIGURACIÓN DE CORS (Cross-Origin Resource Sharing) permite que el frontend HTML pueda realizar solicitudes a este servidor desde el navegador.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELOS DE DATOS (Pydantic)
# ============================================================================
# Estos modelos definen la estructura de datos que la API recibe y envía.
# Validación automática de tipos y documentación OpenAPI.

class ExtractSlideIdsRequest(BaseModel):
    """Solicitud para extraer identificadores de slides"""
    presentation_url: str  # URL de la presentación de Google Slides


class GetSlideComponentsRequest(BaseModel):
    """Solicitud para obtener componentes de una slide específica"""
    presentation_url: str  # URL de la presentación
    slide_index: int       # Índice de la slide (empezando en 0)


class ExtractSlideIdsResponse(BaseModel):
    """Respuesta con los identificadores de slides"""
    success: bool
    slide_identifiers: Dict[int, List[str]]  
    message: str


class GetSlideComponentsResponse(BaseModel):
    """Respuesta con los componentes de una slide"""
    success: bool
    slide_index: int
    components: List[str]  # ['#title', '#content', '#date']
    message: str


class HealthResponse(BaseModel):
    """Respuesta que indica el estado del servicio"""
    status: str
    message: str


# ENDPOINTS


@app.get("/", tags=["Frontend"])
async def root():
    """
    Sirve el archivo index.html del frontend.
    """
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    else:
        # Si no existe el archivo, retorna info del API
        return {
            "service": "Google Slides Automation API",
            "version": "1.0.0",
            "message": "Archivo frontend no encontrado. Los archivos estáticos están en /static/",
            "endpoints": {
                "extract_ids": "POST /api/extract-slide-ids",
                "get_components": "POST /api/get-slide-components",
                "health": "GET /api/health"
            }
        }

    
    # ENDPOINT: Health Check
    
    @app.get("/api/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        """
        Verificar estado del servicio.
        Comprueba que el archivo de credenciales existe.
        """
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', './credentials.json')

        if not os.path.exists(credentials_path):
            logger.warning(f"⚠ Archivo de credenciales no encontrado: {credentials_path}")
            return HealthResponse(
                status="warning",
                message=f"Archivo de credenciales no encontrado en {credentials_path}"
            )

        return HealthResponse(
            status="healthy",
            message="Servicio activo y listo"
        )


 
# Monta la carpeta `static` para servir CSS/JS/otros recursos
if os.path.exists('./static'):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.post("/api/extract-slide-ids", response_model=ExtractSlideIdsResponse, tags=["Slides"])
async def extract_slide_ids(request: ExtractSlideIdsRequest):
    # Define ruta POST para extraer identificadores estructurales
    try:
        # Obtiene la ruta del archivo de credenciales desde la variable de entorno
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', './credentials.json')
        
        # Validación: verifica que el archivo de credenciales existe
        if not os.path.exists(credentials_path):
            raise HTTPException(
                status_code=400,
                detail=f"Archivo de credenciales no encontrado: {credentials_path}"
            )
        
        # Inicializa la automatización con las credenciales
        automation = GoogleSlidesAutomation(credentials_path)
        
        # Llama extraer los identificadores
        slide_identifiers = automation.extract_slide_ids(request.presentation_url)
        
        logger.info(f"✓ Se extrajeron {len(slide_identifiers)} identificadores")
        
        return ExtractSlideIdsResponse(
            success=True,
            slide_identifiers=slide_identifiers,
            message=f"Se encontraron {len(slide_identifiers)} slides con identificadores"
        )
    
    except ValueError as e:
        logger.error(f"✗ Error de validación: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"URL inválida: {str(e)}"
        )
    except Exception as e:
        logger.error(f"✗ Error inesperado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la solicitud: {str(e)}"
        )


@app.post("/api/get-slide-components", response_model=GetSlideComponentsResponse, tags=["Slides"])
async def get_slide_components(request: GetSlideComponentsRequest):
    # Define ruta POST para obtener variables de datos #
    try:
        # Obtiene la ruta del archivo de credenciales
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', './credentials.json')
        
        # Validación: verifica que el archivo existe
        if not os.path.exists(credentials_path):
            raise HTTPException(
                status_code=400,
                detail=f"Archivo de credenciales no encontrado: {credentials_path}"
            )
        
        # Validación: verifica que el índice sea válido
        if request.slide_index < 0:
            raise HTTPException(
                status_code=400,
                detail="El índice de slide debe ser >= 0"
            )
        
        # Inicializa la automatización
        automation = GoogleSlidesAutomation(credentials_path)
        
        # Llama a obtener los componentes
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
    
    except ValueError as e:
        logger.error(f"✗ Error de validación: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"URL inválida: {str(e)}"
        )
    except Exception as e:
        logger.error(f"✗ Error inesperado: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la solicitud: {str(e)}"
         )
    


# Punto de entrada para ejecución directa del script
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
    
    # Inicia el servidor con hot-reload para desarrollo
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Recargar automáticamente si cambia algún archivo (.py)
        log_level="info"
    )
