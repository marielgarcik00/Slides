/**
 * SCRIPT PRINCIPAL - Google Slides Automation Tool
 * 
 * Este archivo contiene las funciones JavaScript que se ejecutan en el navegador.
 * Se comunica con la API FastAPI en el backend para procesar las solicitudes.
 */

// ========================================================================
// CONFIGURACIÓN BASE
// ========================================================================

// URL base de la API (se conecta al servidor FastAPI)
// En desarrollo: http://localhost:8000
// En producción: se actualizaría al dominio real
const API_BASE_URL = 'http://localhost:8000';

// ========================================================================
// FUNCIÓN 1: EXTRAER IDENTIFICADORES DE SLIDES
// ========================================================================

/**
 * Extrae los identificadores ($) de todas las slides de la presentación.
 * 
 * Pasos:
 * 1. Obtiene la URL del input HTML
 * 2. Valida que la URL sea válida
 * 3. Envía una solicitud POST a la API
 * 4. Procesa la respuesta y la muestra en pantalla
 */
async function extractSlideIds() {
    // Obtener valores del formulario
    const presentationUrl = document.getElementById('url-extract').value.trim();
    
    // Validación: URL vacía
    if (!presentationUrl) {
        showError('extract', 'Por favor, ingresa una URL de presentación válida');
        return;
    }
    
    // Validación: URL debe ser de Google Slides
    if (!presentationUrl.includes('docs.google.com/presentation')) {
        showError('extract', 'La URL debe ser de una presentación de Google Slides');
        return;
    }
    
    try {
        // Mostrar loading y ocultar resultados previos
        document.getElementById('loading-extract-ids').style.display = 'block';
        document.getElementById('result-extract-ids').style.display = 'none';
        document.getElementById('error-extract-ids').style.display = 'none';
        document.getElementById('btn-extract-ids').disabled = true;
        
        // Crear el payload de la solicitud
        const payload = {
            presentation_url: presentationUrl
        };
        
        console.log('Enviando solicitud:', payload);
        
        // Enviar solicitud POST al endpoint /api/extract-slide-ids
        const response = await fetch(`${API_BASE_URL}/api/extract-slide-ids`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        // Parsear respuesta JSON
        const data = await response.json();
        
        console.log('Respuesta recibida:', data);
        
        // Validar respuesta exitosa
        if (!response.ok) {
            throw new Error(data.detail || 'Error en la solicitud');
        }
        
        // Mostrar resultados
        showExtractIdsResult(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError('extract', error.message || 'Error al procesar la solicitud');
    } finally {
        // Ocultar loading y habilitar botón
        document.getElementById('loading-extract-ids').style.display = 'none';
        document.getElementById('btn-extract-ids').disabled = false;
    }
}

/**
 * Muestra los resultados de la extracción de identificadores en la pantalla.
 */
function showExtractIdsResult(data) {
    const resultContainer = document.getElementById('result-extract-ids');
    const outputDiv = document.getElementById('output-extract-ids');
    
    // Formatear los resultados de forma legible
    let output = '';
    
    if (Object.keys(data.slide_identifiers).length === 0) {
        output = 'No se encontraron identificadores ($) en la presentación.';
    } else {
        output = 'Identificadores encontrados por slide:\n';
        output += '═════════════════════════════════════\n\n';
        
        // Iterar sobre cada slide identificada
        for (const [slideIndex, identifier] of Object.entries(data.slide_identifiers)) {
            // identifier puede ser un string o una lista de strings
            if (Array.isArray(identifier)) {
                output += `📄 Slide ${slideIndex}: ${identifier.join(', ')}\n`;
            } else {
                output += `📄 Slide ${slideIndex}: ${identifier}\n`;
            }
        }
        
        output += `\n═════════════════════════════════════\n`;
        output += `Total: ${Object.keys(data.slide_identifiers).length} slides con identificadores`;
    }
    
    // Establecer el contenido y mostrar el contenedor
    outputDiv.textContent = output;
    resultContainer.style.display = 'block';
}

// ========================================================================
// FUNCIÓN 2: OBTENER COMPONENTES DE UNA SLIDE
// ========================================================================

/**
 * Obtiene los componentes (#) de una slide específica.
 * 
 * Pasos:
 * 1. Obtiene URL y índice de slide del formulario
 * 2. Valida los datos
 * 3. Envía solicitud POST a /api/get-slide-components
 * 4. Muestra los componentes encontrados
 */
async function getSlideComponents() {
    // Obtener valores del formulario
    const presentationUrl = document.getElementById('url-components').value.trim();
    const slideIndexInput = document.getElementById('slide-index').value.trim();
    
    // Validaciones
    if (!presentationUrl) {
        showError('components', 'Por favor, ingresa una URL de presentación válida');
        return;
    }
    
    if (!presentationUrl.includes('docs.google.com/presentation')) {
        showError('components', 'La URL debe ser de una presentación de Google Slides');
        return;
    }
    
    // Convertir índice a número y validar
    const slideIndex = parseInt(slideIndexInput);
    if (isNaN(slideIndex) || slideIndex < 0) {
        showError('components', 'Por favor, ingresa un índice de slide válido (número >= 0)');
        return;
    }
    
    try {
        // Mostrar loading
        document.getElementById('loading-components').style.display = 'block';
        document.getElementById('result-components').style.display = 'none';
        document.getElementById('error-components').style.display = 'none';
        document.getElementById('btn-get-components').disabled = true;
        
        // Crear payload
        const payload = {
            presentation_url: presentationUrl,
            slide_index: slideIndex
        };
        
        console.log('Enviando solicitud:', payload);
        
        // Enviar solicitud POST al endpoint /api/get-slide-components
        const response = await fetch(`${API_BASE_URL}/api/get-slide-components`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        // Parsear respuesta
        const data = await response.json();
        
        console.log('Respuesta recibida:', data);
        
        // Validar respuesta
        if (!response.ok) {
            throw new Error(data.detail || 'Error en la solicitud');
        }
        
        // Mostrar resultados
        showComponentsResult(data);
        
    } catch (error) {
        console.error('Error:', error);
        showError('components', error.message || 'Error al procesar la solicitud');
    } finally {
        // Ocultar loading
        document.getElementById('loading-components').style.display = 'none';
        document.getElementById('btn-get-components').disabled = false;
    }
}

/**
 * Muestra los componentes encontrados en la pantalla.
 */
function showComponentsResult(data) {
    const resultContainer = document.getElementById('result-components');
    const outputDiv = document.getElementById('output-components');
    
    // Formatear resultados
    let output = '';
    
    if (data.components.length === 0) {
        output = `La slide ${data.slide_index} no contiene componentes dinámicos (#).`;
    } else {
        output = `Componentes encontrados en Slide ${data.slide_index}:\n`;
        output += '═════════════════════════════════════\n\n';
        
        // Listar cada componente
        data.components.forEach((component, index) => {
            output += `${index + 1}. ${component}\n`;
        });
        
        output += `\n═════════════════════════════════════\n`;
        output += `Total: ${data.components.length} componentes dinámicos`;
    }
    
    // Mostrar resultado
    outputDiv.textContent = output;
    resultContainer.style.display = 'block';
}

// ========================================================================
// FUNCIÓN 3: VERIFICAR ESTADO DEL SERVICIO
// ========================================================================

/**
 * Verifica el estado del servicio API.
 * 
 * Útil para confirmar que:
 * - El servidor está corriendo
 * - Las credenciales de GCP están configuradas
 */
async function checkHealth() {
    try {
        // Enviar solicitud GET al endpoint /api/health
        const response = await fetch(`${API_BASE_URL}/api/health`);
        const data = await response.json();
        
        console.log('Health check:', data);
        
        // Mostrar resultado
        const healthStatus = document.getElementById('health-status');
        const healthOutput = document.getElementById('health-output');
        
        let output = `Estado del servicio: ${data.status.toUpperCase()}\n`;
        output += `Mensaje: ${data.message}\n`;
        
        // Si hay advertencias, mostrarlas
        if (data.status === 'warning') {
            output += '\n⚠️  ADVERTENCIA:\n';
            output += 'El archivo de credenciales no está configurado.\n';
            output += 'Debes pasar las credenciales JSON de tu Service Account de GCP.';
        }
        
        healthOutput.textContent = output;
        healthStatus.style.display = 'block';
        
    } catch (error) {
        console.error('Error checking health:', error);
        
        // Mostrar error de conexión
        const healthStatus = document.getElementById('health-status');
        const healthOutput = document.getElementById('health-output');
        
        const output = `❌ ERROR DE CONEXIÓN\n\n` +
                      `No se pudo conectar al servidor API.\n` +
                      `Asegúrate de que:\n` +
                      `1. El servidor está corriendo (python app.py)\n` +
                      `2. La URL correcta es: ${API_BASE_URL}\n` +
                      `3. No hay firewall bloqueando las conexiones\n\n` +
                      `Error: ${error.message}`;
        
        healthOutput.textContent = output;
        healthStatus.style.display = 'block';
    }
}

// ========================================================================
// FUNCIONES AUXILIARES
// ========================================================================

/**
 * Muestra un mensaje de error en la pantalla.
 * 
 * @param {string} section - 'extract' o 'components'
 * @param {string} message - Mensaje de error
 */
function showError(section, message) {
    if (section === 'extract') {
        document.getElementById('error-extract-ids').style.display = 'block';
        document.getElementById('error-text-extract-ids').textContent = message;
        document.getElementById('result-extract-ids').style.display = 'none';
    } else if (section === 'components') {
        document.getElementById('error-components').style.display = 'block';
        document.getElementById('error-text-components').textContent = message;
        document.getElementById('result-components').style.display = 'none';
    }
}

/**
 * Formatea un objeto JavaScript como JSON con indentación.
 * Útil para mostrar datos en formato legible.
 */
function formatJSON(obj) {
    return JSON.stringify(obj, null, 2);
}

// ========================================================================
// EVENTOS Y INICIALIZACIÓN
// ========================================================================

// Permitir enviar formularios con Enter en los inputs
document.addEventListener('DOMContentLoaded', function() {
    // Extraer IDs al presionar Enter en el input
    document.getElementById('url-extract')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') extractSlideIds();
    });
    
    // Obtener componentes al presionar Enter en los inputs
    document.getElementById('url-components')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') getSlideComponents();
    });
    
    document.getElementById('slide-index')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') getSlideComponents();
    });
    
    console.log('✓ Google Slides Automation Tool cargado correctamente');
});
