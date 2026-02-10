"""
MÓDULO PRINCIPAL DE AUTOMATIZACIÓN DE GOOGLE SLIDES
===================================================

Este módulo contiene las 2 funciones principales:
1. extract_slide_ids() - Extrae los identificadores de slides (con signo $)
2. get_slide_components() - Obtiene los componentes dinámicos de una slide (con signo #)

Estructura esperada en Google Slides:
- Identificadores de slides: $slide_id_1, $slide_id_2, etc.
- Componentes dinámicos: #component_name, #title, #content, etc.
"""

import re
from typing import List, Dict, Set
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

# Configurar logging para seguimiento de operaciones
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleSlidesAutomation:
    """
    Clase para interactuar con Google Slides API y procesar identificadores
    y componentes dinámicos.
    
    Args:
        credentials_path (str): Ruta al archivo JSON de credenciales del Service Account
    """
    
    def __init__(self, credentials_path: str):
        """
        Inicializa la conexión con Google Slides API usando Service Account.
        
        El Service Account es una cuenta de servicio que actúa como una aplicación,
        permitiendo acceso programático a Google Slides sin intervención del usuario.
        """
        self.credentials_path = credentials_path
        self.service = self._initialize_service()
    
    def _initialize_service(self):
        """
        Establece la conexión con Google Slides API usando credenciales de Service Account.
        
        Scopes utilizados:
        - https://www.googleapis.com/auth/presentations: Acceso completo a presentaciones
        - https://www.googleapis.com/auth/drive: Acceso a Google Drive (para leer metadatos)
        """
        try:
            # Define los permisos que necesita el Service Account
            SCOPES = [
                'https://www.googleapis.com/auth/presentations',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Carga las credenciales desde el archivo JSON
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
        FUNCIÓN 1: Extrae los identificadores únicos de cada slide.
        
        Busca patrones de texto que contengan $ (por ej: $slide_id_1, $portada, etc.)
        en TODAS las slides de la presentación.
        
        Args:
            presentation_url (str): URL de la presentación de Google Slides
                                   Ejemplo: https://docs.google.com/presentation/d/1ABC...
        
        Returns:
            Dict[int, str]: Diccionario con estructura:
                           {
                               0: "$slide_id_1",
                               1: "$main_slide", 
                               2: "$chart_slide",
                               ...
                           }
        
        Ejemplo de uso:
            >>> automation = GoogleSlidesAutomation('credentials.json')
            >>> ids = automation.extract_slide_ids('https://docs.google.com/presentation/d/...')
            >>> print(ids)
            {0: '$slide_id_1', 1: '$main_content', 2: '$report_data'}
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
                # Los elementos dentro de una slide pueden ser texto, imágenes, shapes, etc.
                # Buscar todos los identificadores que empiecen con '$'
                ids = self._find_all_components_in_slide(slide, '$')

                if ids:
                    # Guardar como lista (el método devuelve un set)
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
        FUNCIÓN 2: Obtiene todos los componentes dinámicos de una slide específica.
        
        Busca patrones de texto que contengan # (por ej: #title, #content, #table_data, etc.)
        SOLO en la slide especificada por su índice.
        
        Args:
            presentation_url (str): URL de la presentación
            slide_index (int): Índice de la slide (0-based)
                              Nota: Puedes obtener el slide_index usando extract_slide_ids()
        
        Returns:
            List[str]: Lista de componentes encontrados
                      Ejemplo: ['#title', '#subtitle', '#content', '#footer']
        
        Ejemplo de uso:
            >>> components = automation.get_slide_components(
            ...     'https://docs.google.com/presentation/d/...',
            ...     slide_index=0
            ... )
            >>> print(components)
            ['#title', '#description', '#image_placeholder', '#date']
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
    
    # ============================================================================
    # MÉTODOS PRIVADOS (uso interno)
    # ============================================================================
    
    @staticmethod
    def _extract_presentation_id(url: str) -> str:
        """
        Extrae el ID único de la presentación desde la URL.
        
        La URL de Google Slides tiene este formato:
        https://docs.google.com/presentation/d/{ID}/edit?...
        
        Este método extrae el {ID}.
        """
        match = re.search(r'/presentation/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        raise ValueError(f"No se pudo extraer ID de presentación de: {url}")
    
    @staticmethod
    def _find_identifier_in_slide(slide: Dict, marker: str = '$') -> str:
        """
        Busca en una slide un ÚNICO identificador que contenga el marcador ($).
        
        Busca en todos los elementos de texto de la slide (shapes, text boxes, etc.)
        y retorna el primer identificador encontrado.
        
        Args:
            slide (Dict): Datos de la slide del API
            marker (str): El carácter buscado ('$' para identificadores)
        
        Returns:
            str: El identificador encontrado o vacío si no hay
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
        Busca en una slide TODOS los componentes que contengan el marcador (#).
        
        A diferencia de _find_identifier_in_slide, esta función busca y retorna
        TODOS los componentes encontrados en la slide.
        
        Args:
            slide (Dict): Datos de la slide del API
            marker (str): El carácter buscado ('#' para componentes dinámicos)
        
        Returns:
            Set[str]: Conjunto de componentes únicos encontrados
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


# ============================================================================
# FUNCIONES AUXILIARES DE ACCESO RÁPIDO
# ============================================================================

def extract_slide_ids_from_presentation(presentation_url: str, credentials_path: str) -> Dict[int, str]:
    """
    Función simplificada para extraer IDs sin instanciar la clase.
    
    Útil para implementaciones rápidas o pruebas.
    """
    automation = GoogleSlidesAutomation(credentials_path)
    return automation.extract_slide_ids(presentation_url)


def get_components_from_slide(presentation_url: str, slide_index: int, credentials_path: str) -> List[str]:
    """
    Función simplificada para obtener componentes sin instanciar la clase.
    """
    automation = GoogleSlidesAutomation(credentials_path)
    return automation.get_slide_components(presentation_url, slide_index)
