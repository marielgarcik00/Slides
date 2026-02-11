"""
Contiene las 2 funciones principales:
1. extract_slide_ids() - Extrae los identificadores de slides (con signo $)
2. get_slide_components() - Obtiene los componentes dinámicos de una slide (con signo #)

Estructura esperada en Google Slides:
- Identificadores de slides: $slide_id_1, $slide_id_2, etc.
- Componentes dinámicos: #component_name, #title, #content, etc.
"""

import re #Librería para buscar patrones de texto como # y $
from typing import List, Dict, Set  #Define tipos de datos para listas y diccionarios
from google.oauth2 import service_account #Gestiona la key de la Service Account
from googleapiclient.discovery import build #Crea la conexión con la API de Google
import logging #Registra eventos y errores del sistema

# Configurar logging para seguimiento de operaciones
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleSlidesAutomation:
    """ Extracción de metadatos y etiquetas dinámicas en Google Slides.
    Requiere la ruta de un archivo JSON de credenciales de cuenta de servicio. """
    def __init__(self, credentials_path: str):
        """ Constructor que establece la ruta de credenciales e inicializa la conexión con la API."""
        self.credentials_path = credentials_path
        self.service = self._initialize_service()
    
    def _initialize_service(self):
        """ Establece la conexión con Google Slides API usando credenciales de Service Account.
        Scopes utilizados:
        - https://www.googleapis.com/auth/presentations: Acceso completo a presentaciones
        - https://www.googleapis.com/auth/drive: Acceso a Google Drive (para leer metadatos) """
        try:
            # Define los permisos que necesita el Service Account
            SCOPES = [
                'https://www.googleapis.com/auth/presentations',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Carga las credenciales desde el archivo credentials.json
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path, scopes=SCOPES
            )
            
            # Crea el servicio de Google Slides
            service = build('slides', 'v1', credentials=credentials)
            logger.info("✓ Conexión exitosa con Google Slides API")
            return service
        
        except FileNotFoundError:
            logger.error(f"✗ Archivo de credenciales no encontrado: {self.credentials_path}")
            raise
        except Exception as e:
            logger.error(f"✗ Error inicializando Google Slides API: {str(e)}")
            raise
    
    def extract_slide_ids(self, presentation_url: str) -> Dict[int, list]:
        """
        Escanea la presentación completa para identificar etiquetas de tipo estructura ($).
        Retorna un diccionario mapeando el índice de la diapositiva con sus identificadores.
        """
        try:
            # Extrae el ID de la presentación desde la URL
            presentation_id = self._extract_presentation_id(presentation_url)
            logger.info(f"Procesando presentación: {presentation_id}")
            
            # Obtiene todos los datos de la presentación
            presentation = self.service.presentations().get(
                presentationId=presentation_id
            ).execute()
            
            slide_identifiers = {}

            # Itera por cada slide de la presentación
            for slide_index, slide in enumerate(presentation.get('slides', [])):
                # Buscar todos los identificadores que empiecen con '$'
                ids = self._find_all_components_in_slide(slide, '$')

                if ids:
                    # Guardar como lista
                    slide_identifiers[slide_index] = list(ids)
                    logger.info(f"Slide {slide_index}: encontrados {len(ids)} identificadores")
                else:
                    logger.debug(f"Slide {slide_index}: sin identificador")
            
            logger.info(f"✓ Total de slides con identificadores: {len(slide_identifiers)}")
            return slide_identifiers
        
        except Exception as e:
            logger.error(f"✗ Error extrayendo IDs de slides: {str(e)}")
            raise
    
    def get_slide_components(self, presentation_url: str, slide_index: int) -> List[str]:
        """
        Localiza todos los campos de datos dinámicos (#) dentro de una diapositiva específica.
        Requiere la URL y el índice de la diapositiva a inspeccionar.
        """
        try:
            # Extrae el ID de la presentación
            presentation_id = self._extract_presentation_id(presentation_url)
            
            # Obtiene la presentación
            presentation = self.service.presentations().get(
                presentationId=presentation_id
            ).execute()
            
            slides = presentation.get('slides', [])
            
            # Validación: verifica que el índice sea válido
            if slide_index >= len(slides):
                logger.error(f"✗ Slide index {slide_index} no existe. Total de slides: {len(slides)}")
                return []
            
            slide = slides[slide_index]
            logger.info(f"Procesando slide {slide_index}...")
            
            # Encuentra todos los componentes en la slide
            components = self._find_all_components_in_slide(slide, '#')
            
            if components:
                logger.info(f"✓ Slide {slide_index}: encontrados {len(components)} componentes")
                for component in components:
                    logger.debug(f"  - {component}")
            else:
                logger.info(f"Slide {slide_index}: sin componentes dinámicos")
            
            return list(components)  # Convierte a lista para serializar en JSON
        
        except Exception as e:
            logger.error(f"✗ Error obteniendo componentes de slide: {str(e)}")
            raise
    
 
    
    @staticmethod
    def _extract_presentation_id(url: str) -> str:
        """
        Método estático que aísla el ID de la presentación contenido en la cadena de la URL.
        """
        match = re.search(r'/presentation/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        raise ValueError(f"No se pudo extraer ID de presentación de: {url}")
    
    @staticmethod
    def _find_identifier_in_slide(slide: Dict, marker: str = '$') -> str:
        """
        Busca en una slide identificadores que contenga el marcador ($).  
        """
        for element in slide.get('pageElements', []):
            # Las shapes pueden contener texto
            if 'shape' in element and 'text' in element['shape']:
                text_frame = element['shape']['text']
                
                # Itera por párrafos dentro del elemento de texto
                for paragraph in text_frame.get('textElements', []):
                    text = paragraph.get('textRun', {}).get('content', '')
                    
                    # Busca el patrón del marcador en el texto
                    match = re.search(rf'\{marker}\w+', text)
                    if match:
                        return match.group()
        
        return ""
    
    @staticmethod
    def _find_all_components_in_slide(slide: Dict, marker: str = '#') -> Set[str]:
        """
        Busca en una slide los componentes que contengan el marcador (#).
        """
        components = set()
        
        for element in slide.get('pageElements', []):
            # Procesa elementos de tipo shape (que contienen texto)
            if 'shape' in element and 'text' in element['shape']:
                text_frame = element['shape']['text']
                
                # Itera por párrafos
                for paragraph in text_frame.get('textElements', []):
                    text = paragraph.get('textRun', {}).get('content', '')
                    
                    # Busca TODOS los patrones que coincidan con el marcador
                    matches = re.findall(rf'\{marker}\w+', text)
                    components.update(matches)
            
            # También procesa tablas que puedan contener texto dinámico
            if 'table' in element:
                table = element['table']
                for row in table.get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        cell_text = cell.get('text', {})
                        for paragraph in cell_text.get('textElements', []):
                            text = paragraph.get('textRun', {}).get('content', '')
                            matches = re.findall(rf'\{marker}\w+', text)
                            components.update(matches)
        
        return components

