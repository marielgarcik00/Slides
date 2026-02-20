
import re  # Librería para buscar patrones de texto como # y $
from typing import Any, List, Dict, Set, cast  # Define tipos de datos para listas y diccionarios
from google.oauth2 import service_account  # Gestiona la key de la Service Account
from googleapiclient.discovery import build  # Crea la conexión con la API de Google
from googleapiclient.errors import HttpError  # Manejo de errores de la API
import logging  # Registra eventos y errores del sistema

# Configurar logging para seguimiento de operaciones
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleSlidesAutomation:
    # Establecemos la ruta de credenciales e inicializamos la conexión con la API
    # Necesita un archivo JSON de credenciales de cuenta de servicio.
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        self.service: Any = self._initialize_service()  # build() retorna un recurso dinámico

    # Establece la conexión con Google Slides API usando credenciales de Service Account
    def _initialize_service(self) -> Any:
        """ Scopes utilizados:
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
            
            # Guarda las credenciales para usos posteriores y crea el servicio de Slides
            self._credentials = credentials
            service = cast(Any, build('slides', 'v1', credentials=credentials))
            logger.info("✓ Conexión exitosa con Google Slides API")
            return service
        
        except FileNotFoundError:
            logger.error("✗ Archivo de credenciales no encontrado: %s", self.credentials_path)
            raise
        except Exception as e:
            logger.error("✗ Error inicializando Google Slides API: %s", e)
            raise
    
    #Escanea la presentación para buecar los identificadores que empiezan con $.
    def extract_slide_ids(self, presentation_url: str) -> Dict[int, list]:
        try:
            # Extrae el ID de la presentación desde la URL
            presentation_id = self._extract_presentation_id(presentation_url)
            logger.info("Procesando presentación: %s", presentation_id)
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
                    logger.info("Slide %s: encontrados %s identificadores", slide_index, len(ids))
                else:
                    logger.debug("Slide %s: sin identificador", slide_index)
            
            logger.info("✓ Total de slides con identificadores: %s", len(slide_identifiers))
            return slide_identifiers
        
        except Exception as e:
            logger.error("✗ Error extrayendo IDs de slides: %s", e)
            raise
    
   #Buscaa todos los datos dinámicos (#) dentro de una diapositiva.
    def get_slide_components(self, presentation_url: str, slide_index: int) -> List[str]:
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
                logger.error("✗ Slide index %s no existe. Total de slides: %s", slide_index, len(slides))
                return []
            slide = slides[slide_index]
            logger.info("Procesando slide %s...", slide_index)
            # Encuentra todos los componentes en la slide
            components = self._find_all_components_in_slide(slide, '#')
            if components:
                logger.info("✓ Slide %s: encontrados %s componentes", slide_index, len(components))
                for component in components:
                    logger.debug("  - %s", component)
            else:
                logger.info("Slide %s: sin componentes dinámicos", slide_index)
                logger.info("Slide %s: sin componentes dinámicos", slide_index)
            return list(components)  # Convierte a lista para serializar en JSON
        
        except Exception as e:
            logger.error("✗ Error obteniendo componentes de slide: %s", e)
            raise
    
    # Copia una slide individual a una carpeta de Drive
    def copy_slide_to_folder(self, presentation_url: str, slide_index: int, folder_url_or_id: str, new_name: str) -> str:
        try:
            if not new_name:
                raise ValueError("El parámetro new_name es obligatorio para copiar una slide.")
            return self.copy_presentation_advanced(
                presentation_url=presentation_url,
                slide_counts={},
                folder_url_or_id=folder_url_or_id,
                new_name=new_name,
                slide_sequence=[slide_index]
            )
        except Exception as e:
            logger.error("✗ Error copiando slide: %s", e)
            raise

    @staticmethod
    # Extrae el folder ID desde una URL de Drive o devuelve el valor si ya es un ID
    def _extract_folder_id(folder_url_or_id: str) -> str:
        if not folder_url_or_id:
            return ''
        # Si la cadena contiene 'folders/', extraemos el ID
        m = re.search(r'/folders/([a-zA-Z0-9_-]+)', folder_url_or_id)
        if m:
            return m.group(1)
        # Si es una URL con id=item, fallback
        m2 = re.search(r'id=([a-zA-Z0-9_-]+)', folder_url_or_id)
        if m2:
            return m2.group(1)
        # Si parece un id simple lo retornamos
        if re.match(r'^[a-zA-Z0-9_-]+$', folder_url_or_id):
            return folder_url_or_id
        return ''
    
    #Copia la presentación completa al folder de Drive indicado. Retorna el ID de la nueva presentación.
    def copy_presentation_to_folder(self, presentation_url: str, folder_url_or_id: str, new_name: str = None) -> str:
        try:
            src_presentation_id = self._extract_presentation_id(presentation_url)
            drive_service: Any = build('drive', 'v3', credentials=self._credentials)
            src_file = drive_service.files().get(fileId=src_presentation_id, fields='name', supportsAllDrives=True).execute()
            base_name = src_file.get('name', 'Presentation')
            target_name = new_name or f"Copy of {base_name}"
            folder_id = self._extract_folder_id(folder_url_or_id)

            copy_body = {'name': target_name}
            if folder_id:
                copy_body['parents'] = [folder_id]
            try:
                new_file = drive_service.files().copy(fileId=src_presentation_id, body=copy_body, supportsAllDrives=True).execute()
            except HttpError as e:
                logger.warning("Advertencia al copiar con parents: %s", getattr(e, 'content', str(e)))
                if 'parents' in copy_body:
                    logger.info("Reintentando copia sin carpeta padre")
                    copy_body.pop('parents', None)
                    new_file = drive_service.files().copy(fileId=src_presentation_id, body=copy_body, supportsAllDrives=True).execute()
                else:
                    raise
            new_presentation_id = new_file.get('id')
            logger.info("✓ Copia completa creada en Drive: %s", new_presentation_id)
            return new_presentation_id
        except Exception as e:
            logger.error("✗ Error copiando presentación: %s", e)
            raise
    
    # Verifica si el Service Account tiene acceso a la presentación
    def verify_presentation_access(self, presentation_url: str) -> dict:
        try:
            presentation_id = self._extract_presentation_id(presentation_url)
            logger.info("Verificando acceso a presentación: %s", presentation_id)
            # Intentar acceder via Slides API
            try:
                presentation = self.service.presentations().get(presentationId=presentation_id).execute()
                slides_access = True
                slides_error = None
                slide_count = len(presentation.get('slides', []))
            except Exception as e:
                slides_access = False
                slides_error = str(e)
                slide_count = 0
            
            # Intentar acceder via Drive API
            drive_service: Any = build('drive', 'v3', credentials=self._credentials)
            try:
                file_info = drive_service.files().get(fileId=presentation_id, fields='name,mimeType', supportsAllDrives=True).execute()
                drive_access = True
                drive_error = None
                file_name = file_info.get('name', 'Unknown')
            except Exception as e:
                drive_access = False
                drive_error = str(e)
                file_name = 'Unknown'
            
            return {
                'presentation_id': presentation_id,
                'file_name': file_name,
                'slides_api_access': slides_access,
                'slides_api_error': slides_error,
                'drive_api_access': drive_access,
                'drive_api_error': drive_error,
                'slide_count': slide_count,
                'overall_access': slides_access and drive_access
            }
        
        except ValueError as e:
            logger.error("Error al extraer ID: %s", e)
            raise
        except Exception as e:
            logger.error("Error verificando acceso: %s", e)
            raise
    
    @staticmethod
    # Aísla el ID de la presentación contenido en la cadena de la URL
    def _extract_presentation_id(url: str) -> str:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            return match.group(1)
        raise ValueError(f"No se pudo extraer ID de presentación de: {url}")
    
    @staticmethod
    # Escaneo profundo navegando por la jerarquía de formas y tablas de cada slide para extraer etiquetas
    def _extract_markers_from_element(element: Dict, marker: str) -> Set[str]:
        """Extrae marcadores de un elemento individual """
        markers = set()
        
        # Procesar shapes
        if 'shape' in element and 'text' in element['shape']:
            for paragraph in element['shape']['text'].get('textElements', []):
                text = paragraph.get('textRun', {}).get('content', '')
                markers.update(re.findall(rf'\{marker}\w+', text))
        
        # Procesar tablas
        if 'table' in element:
            for row in element['table'].get('tableRows', []):
                for cell in row.get('tableCells', []):
                    for paragraph in cell.get('text', {}).get('textElements', []):
                        text = paragraph.get('textRun', {}).get('content', '')
                        markers.update(re.findall(rf'\{marker}\w+', text))
        
        return markers
    
    @staticmethod
    #Busca todos los componentes con un marcador específico en una slide
    def _find_all_components_in_slide(slide: Dict, marker: str = '#') -> Set[str]:
        components = set()
        for element in slide.get('pageElements', []):
            components.update(GoogleSlidesAutomation._extract_markers_from_element(element, marker))
        return components

    #  Obtiene una lista de todas las slides con su índice y objectId y busca los identificadosres ($)
    def get_presentation_slides(self, presentation_url: str) -> List[Dict]:
        try:
            presentation_id = self._extract_presentation_id(presentation_url)
            presentation = self.service.presentations().get(presentationId=presentation_id).execute()
            slides = presentation.get('slides', [])
            
            result = []
            for i, slide in enumerate(slides):
                identifiers = list(self._find_all_components_in_slide(slide, '$'))
                result.append({
                    'index': i,
                    'objectId': slide['objectId'],
                    'identifiers': identifiers,
                    'pageElements': len(slide.get('pageElements', []))
                })
            return result
        except Exception as e:
            logger.error(f"Error obteniendo slides: {str(e)}")
            raise

    # Usa extract_slide_ids para ubicar el índice de la slide que contenga TODOS los identificadores $ solicitados.
    def _find_slide_index_by_identifiers(self, presentation_url: str, required_identifiers: List[str]) -> int:
        if not required_identifiers:
            return -1

        normalized_ids = {i.lower() for i in required_identifiers}
        slide_map = self.extract_slide_ids(presentation_url)
        for idx, ids in slide_map.items():
            ids_lower = {i.lower() for i in ids}
            if normalized_ids.issubset(ids_lower):
                return idx
        return -1

    def replace_components_in_slide(
        self,
        presentation_url: str,
        slide_identifiers: List[str],
        replacements: Dict[str, str],
        require_all_markers: bool = False
    ) -> Dict[str, Any]:
        normalized_ids = self._normalize_slide_identifiers(slide_identifiers)
        if not replacements:
            raise ValueError("El diccionario de reemplazos está vacío.")

        presentation_id, target_slide, target_index = self._get_target_slide(
            presentation_url,
            normalized_ids
        )

        target_slide_id = target_slide['objectId']
        target_slide_identifiers = {m.lower() for m in self._find_all_components_in_slide(target_slide, '$')}
        target_slide_components = {m.lower() for m in self._find_all_components_in_slide(target_slide, '#')}

        normalized_replacements, semantic = self._normalize_replacements(replacements)
        self._validate_required_markers(target_slide_components, normalized_replacements, require_all_markers)

        replacement_requests, applied = self._build_component_requests(
            target_slide_id,
            target_slide_components,
            normalized_replacements,
            semantic
        )
        cleanup_requests = self._build_identifier_cleanup_requests(target_slide_id, target_slide_identifiers)

        requests = replacement_requests + cleanup_requests
        if not requests:
            raise ValueError("No se encontraron en la slide los marcadores a reemplazar.")

        self.service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={'requests': requests}
        ).execute()

        logger.info(
            "✓ Reemplazados %s componentes en slide con IDs %s",
            len(requests),
            ", ".join(normalized_ids)
        )
        return {
            'presentation_id': presentation_id,
            'slide_identifier': ", ".join(normalized_ids),
            'replaced': applied,
            'slide_index': target_index
        }

    def _normalize_slide_identifiers(self, slide_identifiers: List[str]) -> List[str]:
        """Asegura formato $ident y limpieza básica de los IDs de slide."""
        if not slide_identifiers:
            raise ValueError("Se requiere al menos un identificador de slide (ej: $descriptive).")

        normalized = [
            ident if ident.startswith('$') else f"${ident}"
            for ident in slide_identifiers
        ]
        normalized = [i.lower() for i in normalized if i and i.strip()]
        if not normalized:
            raise ValueError("No se proporcionaron identificadores válidos.")
        return normalized

    def _get_target_slide(self, presentation_url: str, normalized_ids: List[str]):
        """Obtiene la slide que contiene todos los identificadores solicitados."""
        target_index = self._find_slide_index_by_identifiers(presentation_url, normalized_ids)
        if target_index < 0:
            raise ValueError(
                f"No se encontró una slide que contenga los identificadores: {', '.join(normalized_ids)}"
            )

        presentation_id = self._extract_presentation_id(presentation_url)
        presentation = self.service.presentations().get(presentationId=presentation_id).execute()
        slides = presentation.get('slides', [])
        if target_index >= len(slides):
            raise ValueError("Índice de slide fuera de rango tras la búsqueda de identificadores.")

        return presentation_id, slides[target_index], target_index

    def _normalize_replacements(self, replacements: Dict[str, str]):
        """Normaliza claves de reemplazo y detecta valores semánticos comunes."""
        normalized: Dict[str, str] = {}
        semantic = {'title': None, 'description': None}

        for key, value in replacements.items():
            if value is None:
                continue
            base = (key[1:] if key.startswith('#') else key).lower()
            normalized[base] = value
            if any(tag in base for tag in ['title', 'titulo', 'heading', 'main']):
                semantic['title'] = semantic['title'] or value
            if any(tag in base for tag in ['description', 'descripcion', 'body', 'texto']):
                semantic['description'] = semantic['description'] or value

        return normalized, semantic

    def _validate_required_markers(self, target_components: Set[str], normalized_replacements: Dict[str, str], require_all: bool):
        if not require_all:
            return
        missing = [f"#{k}" for k in normalized_replacements.keys() if f"#{k}" not in target_components]
        if missing:
            raise ValueError(f"Faltan en la slide los marcadores: {', '.join(missing)}")

    def _build_component_requests(
        self,
        slide_id: str,
        target_components: Set[str],
        normalized_replacements: Dict[str, str],
        semantic: Dict[str, str]
    ) -> (List[Dict], List[str]):
        """Crea solicitudes de reemplazo para los marcadores # de la slide."""
        requests: List[Dict] = []
        applied: List[str] = []

        for marker in target_components:
            base = marker.lstrip('#').lower()
            value = None
            if any(tag in base for tag in ['title', 'titulo', 'heading', 'main']):
                value = semantic.get('title') or normalized_replacements.get(base)
            elif any(tag in base for tag in ['description', 'descripcion', 'body', 'texto']):
                value = semantic.get('description') or normalized_replacements.get(base)
            elif base in normalized_replacements:
                value = normalized_replacements[base]
            else:
                value = semantic.get('description') or semantic.get('title')

            if value:
                requests.append({
                    'replaceAllText': {
                        'containsText': {'text': marker, 'matchCase': False},
                        'replaceText': value,
                        'pageObjectIds': [slide_id]
                    }
                })
                applied.append(marker)

        return requests, applied

    def _build_identifier_cleanup_requests(self, slide_id: str, identifiers: Set[str]) -> List[Dict]:
        """Genera solicitudes para eliminar identificadores $ una vez usados."""
        requests: List[Dict] = []
        for ident in identifiers:
            requests.append({
                'replaceAllText': {
                    'containsText': {'text': ident, 'matchCase': False},
                    'replaceText': '',
                    'pageObjectIds': [slide_id]
                }
            })
        return requests


    #Dependiendo de los requerimientos del usuario, ya sea que necesite ajustar cantidades o realizar un reordenamiento total de la presentación, el sistema define automáticamente qué función ejecutar
    def copy_presentation_advanced(self, presentation_url: str, slide_counts: Dict[int, int], folder_url_or_id: str, new_name: str = None, slide_sequence: List[int] = None) -> str:
        try:
            # Crear copia de la presentación
            new_presentation_id = self.copy_presentation_to_folder(presentation_url, folder_url_or_id, new_name)
            
            # Si hay secuencia, reordenar. Si no, aplicar conteos legacy.
            if slide_sequence is not None:
                self._reorder_slides_by_sequence(new_presentation_id, slide_sequence)
            elif slide_counts:
                self._apply_slide_counts(new_presentation_id, slide_counts)
            
            return new_presentation_id

        except Exception as e:
            logger.error(f"Error en copia avanzada: {str(e)}")
            raise

    #Duplica o borra slides según el conteo indicado en el map (dccionario) {slide_index: count}
    # Función de tipo "legacy", se usa cuando solo te interesa ajustar las cantidades, manteniendo la estructura básica de la plantilla
    def _apply_slide_counts(self, presentation_id: str, slide_counts: Dict[int, int]):
        presentation = self.service.presentations().get(presentationId=presentation_id).execute()
        slides = presentation.get('slides', [])
        
        # Validar índice maximo base, si lo superamos generamos un diccionario (mapa)
        max_index = len(slides) - 1
        for idx in slide_counts.keys():
            if idx > max_index:
                logger.warning(f"Índice {idx} fuera de rango (máx {max_index}). Se ignorará.")
        
        requests = []
        original_slides_map = {i: slide['objectId'] for i, slide in enumerate(slides)}
        
        # Duplicar slides (count > 1)
        for idx, count in slide_counts.items():
            if idx in original_slides_map and count > 1:
                slide_id = original_slides_map[idx]
                for _ in range(count - 1):
                    requests.append({'duplicateObject': {'objectId': slide_id}})
        
        # Eliminar slides (count == 0)
        for idx, count in slide_counts.items():
            if idx in original_slides_map and count == 0:
                requests.append({'deleteObject': {'objectId': original_slides_map[idx]}})

        if requests:
            self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            logger.info(f"✓ Conteos aplicados: {len(requests)} operaciones")


    #Reconstruye la presentación siguiendo lo indicado
    def _reorder_slides_by_sequence(self, presentation_id: str, sequence: List[int]):
        # Obtenemos las slides originales, les ponemos in id a cada una para poder manipularlas mas tarde
        presentation = self.service.presentations().get(presentationId=presentation_id).execute()
        original_slides = presentation.get('slides', [])
        
        if not original_slides:
            return

        requests = []
        import uuid
        
        original_count = len(original_slides)
        # Lista par guardas los id de las diapos que necesitamos
        requested_new_ids = []
        
        # Duplicar las slides siguiendo la secuencia
        for slide_index in sequence:
            if 0 <= slide_index < original_count:
                source_id = original_slides[slide_index]['objectId']
                new_slide_id = f"gen_slide_{uuid.uuid4().hex}"
                requests.append({
                    'duplicateObject': {
                        'objectId': source_id,
                        'objectIds': {source_id: new_slide_id}
                    }
                })
                requested_new_ids.append(new_slide_id)
            else:
                logger.warning(f"Índice de slide {slide_index} fuera de rango, se omite")

        # Ejecutamos la duplicación primero
        if requests:
            self.service.presentations().batchUpdate(
                presentationId=presentation_id, 
                body={'requests': requests}
            ).execute()
            logger.info(f"✓ Duplicadas {len(requested_new_ids)} slides según la secuencia")

        # Limpieza eliminar diapos necesarias
        delete_requests = [{
            'deleteObject': {'objectId': slide['objectId']}
        } for slide in original_slides]

        if delete_requests:
            self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': delete_requests}
            ).execute()
            logger.info(f"✓ Eliminadas {len(delete_requests)} slides originales.")

        
        # Reordenar cada nueva slide según la secuencia deseada
        reorder_requests = []
        for desired_index, slide_id in enumerate(requested_new_ids):
            reorder_requests.append({
                'updateSlidesPosition': {
                    'slideObjectIds': [slide_id],
                    'insertionIndex': desired_index
                }
            })

        if reorder_requests:
            self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': reorder_requests}
            ).execute()
            logger.info("✓ Reordenadas todas las slides nuevas según la secuencia solicitada")
