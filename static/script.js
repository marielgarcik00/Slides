/**
 * SCRIPT PRINCIPAL - Google Slides Automation Tool
 * Funciones para comunicarse con la API FastAPI del backend
 */

// ========================================================================
// CONFIGURACIÓN
// ========================================================================

const API_BASE_URL = 'http://localhost:8000';

// ========================================================================
// HELPERS - Funciones reutilizables para UI
// ========================================================================

/**
 * Muestra o oculta elementos de loading, resultado y error
 */
function setUIState(section, state) {
    const loadingId = `loading-${section}`;
    const resultId = `result-${section}`;
    const errorId = `error-${section}`;
    
    const loading = document.getElementById(loadingId);
    const result = document.getElementById(resultId);
    const error = document.getElementById(errorId);
    
    if (state === 'loading') {
        loading && (loading.style.display = 'block');
        result && (result.style.display = 'none');
        error && (error.style.display = 'none');
    } else if (state === 'result') {
        loading && (loading.style.display = 'none');
        result && (result.style.display = 'block');
        error && (error.style.display = 'none');
    } else if (state === 'error') {
        loading && (loading.style.display = 'none');
        result && (result.style.display = 'none');
        error && (error.style.display = 'block');
    } else if (state === 'hidden') {
        loading && (loading.style.display = 'none');
        result && (result.style.display = 'none');
        error && (error.style.display = 'none');
    }
}

/**
 * Muestra error en la UI
 */
function showError(section, message) {
    const errorTextId = `error-text-${section}`;
    const errorTextEl = document.getElementById(errorTextId);
    
    if (errorTextEl) {
        errorTextEl.textContent = message;
    }
    setUIState(section, 'error');
}

/**
 * Muestra resultado en la UI
 */
function showResult(section) {
    setUIState(section, 'result');
}

/**
 * Habilita/deshabilita botón
 */
function setButtonState(buttonId, disabled) {
    const btn = document.getElementById(buttonId);
    if (btn) {
        btn.disabled = disabled;
    }
}

/**
 * Realiza fetch con manejo de errores centralizado
 */
async function apiFetch(endpoint, data) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (!response.ok) {
        throw new Error(result.detail || result.message || 'Error desconocido');
    }
    
    return result;
}

// ========================================================================
// FUNCIÓN 1: EXTRAER IDENTIFICADORES DE SLIDES
// ========================================================================

/**
 * Extrae los identificadores ($) de todas las slides
 */
async function extractSlideIds() {
    const presentationUrl = document.getElementById('url-extract').value.trim();

    if (!presentationUrl) {
        showError('extract-ids', 'Por favor, ingresa una URL válida');
        return;
    }

    if (!presentationUrl.includes('docs.google.com/presentation')) {
        showError('extract-ids', 'La URL debe ser de una presentación de Google Slides');
        return;
    }

    try {
        setUIState('extract-ids', 'loading');
        setButtonState('btn-extract-ids', true);

        const data = await apiFetch('/api/extract-slide-ids', {
            presentation_url: presentationUrl
        });

        showExtractIdsResult(data);
        showResult('extract-ids');
    } catch (error) {
        console.error('Error:', error);
        showError('extract-ids', error.message);
    } finally {
        setButtonState('btn-extract-ids', false);
    }
}

/**
 * Muestra resultados de extracción de IDs
 */
function showExtractIdsResult(data) {
    const outputDiv = document.getElementById('output-extract-ids');
    let output = '';

    if (Object.keys(data.slide_identifiers).length === 0) {
        output = 'No se encontraron identificadores ($) en la presentación.';
    } else {
        output = 'Identificadores encontrados por slide:\n';
        output += '═════════════════════════════════════\n\n';

        for (const [slideIndex, identifier] of Object.entries(data.slide_identifiers)) {
            const identifierStr = Array.isArray(identifier) ? identifier.join(', ') : identifier;
            output += `📄 Slide ${slideIndex}: ${identifierStr}\n`;
        }

        output += `\n═════════════════════════════════════\n`;
        output += `Total: ${Object.keys(data.slide_identifiers).length} slides con identificadores`;
    }

    outputDiv.textContent = output;
}

// ========================================================================
// FUNCIÓN 2: OBTENER COMPONENTES DE UNA SLIDE
// ========================================================================

/**
 * Obtiene los componentes (#) de una slide específica
 */
async function getSlideComponents() {
    const presentationUrl = document.getElementById('url-components').value.trim();
    const slideIndexInput = document.getElementById('slide-index').value.trim();

    if (!presentationUrl) {
        showError('components', 'Por favor, ingresa una URL válida');
        return;
    }

    if (!presentationUrl.includes('docs.google.com/presentation')) {
        showError('components', 'La URL debe ser de una presentación de Google Slides');
        return;
    }

    let slideIndex = slideIndexInput === '' ? 0 : parseInt(slideIndexInput);

    if (isNaN(slideIndex) || slideIndex < 0) {
        showError('components', 'Por favor, ingresa un índice válido (número >= 0)');
        return;
    }

    try {
        setUIState('components', 'loading');
        setButtonState('btn-get-components', true);

        const data = await apiFetch('/api/get-slide-components', {
            presentation_url: presentationUrl,
            slide_index: slideIndex
        });

        showComponentsResult(data);
        showResult('components');
    } catch (error) {
        console.error('Error:', error);
        showError('components', error.message);
    } finally {
        setButtonState('btn-get-components', false);
    }
}

/**
 * Muestra los componentes encontrados en una slide
 */
function showComponentsResult(data) {
    const outputDiv = document.getElementById('output-components');
    let output = '';

    if (data.components.length === 0) {
        output = `No se encontraron componentes (#) en la slide ${data.slide_index}.`;
    } else {
        output = `Componentes encontrados en Slide ${data.slide_index}:\n`;
        output += '═════════════════════════════════════\n\n';

        data.components.forEach(comp => {
            output += `🔹 ${comp}\n`;
        });

        output += `\n═════════════════════════════════════\n`;
        output += `Total: ${data.components.length} componentes`;
    }

    outputDiv.textContent = output;
}

// ========================================================================
// FUNCIÓN 3: COPIA AVANZADA
// ========================================================================

/**
 * Carga las slides para configurar la copia avanzada
 */
async function previewSlides() {
    const presentationUrl = document.getElementById('url-advanced').value.trim();

    if (!presentationUrl || !presentationUrl.includes('docs.google.com/presentation')) {
        showErrorAdvanced('Por favor, ingresa una URL válida');
        return;
    }

    try {
        const btn = document.getElementById('btn-preview-advanced');
        btn.disabled = true;
        btn.textContent = '⏳ Cargando Slides...';

        document.getElementById('advanced-config-container').style.display = 'none';
        document.getElementById('error-advanced').style.display = 'none';
        document.getElementById('result-advanced').style.display = 'none';

        const data = await apiFetch('/api/list-slides', {
            presentation_url: presentationUrl
        });

        renderAdvancedSlidesList(data.slides);

    } catch (error) {
        console.error('Error:', error);
        showErrorAdvanced(error.message);
    } finally {
        const btn = document.getElementById('btn-preview-advanced');
        btn.disabled = false;
        btn.textContent = '📥 Previsualizar / Configurar Slides';
    }
}

/**
 * Ejecuta la copia con la configuración actual
 */
async function executeAdvancedCopy() {
    const presentationUrl = document.getElementById('url-advanced').value.trim();
    const folderUrl = document.getElementById('folder-advanced').value.trim();
    const newName = document.getElementById('name-advanced').value.trim();

    if (!folderUrl) {
        showErrorAdvanced('Por favor, ingresa la carpeta de destino');
        return;
    }

    if (STATE.targetSequence.length === 0) {
        showErrorAdvanced('La presentación destino no puede estar vacía');
        return;
    }

    const sequenceIndices = STATE.targetSequence.map(item => item.index);

    try {
        setUIState('advanced', 'loading');
        setButtonState('btn-execute-advanced', true);
        setButtonState('btn-preview-advanced', true);

        const data = await apiFetch('/api/copy-custom', {
            presentation_url: presentationUrl,
            folder_url_or_id: folderUrl,
            new_name: newName || null,
            slide_sequence: sequenceIndices
        });

        showAdvancedResult(data);
        showResult('advanced');

    } catch (error) {
        console.error('Error:', error);
        showErrorAdvanced(error.message);
    } finally {
        setButtonState('btn-execute-advanced', false);
        setButtonState('btn-preview-advanced', false);
    }
}

// Estado global para la playlist
let STATE = {
    sourceSlides: [], // [{index, objectId, identifiers}]
    targetSequence: [] // [{index, objectId, identifiers, uuid}]
};

/**
 * Renderiza la lista de slides DISPONIBLES (Izquierda) e inicializa el Target.
 */
function renderAdvancedSlidesList(slides) {
    STATE.sourceSlides = slides;
    STATE.targetSequence = []; // Reset target on load

    // Auto-populate target with 1 copy of each slide initially (optional but friendly)
    slides.forEach(slide => {
        addToTargetList(slide, false); // false = don't render yet
    });

    renderSourcePanel();
    renderTargetPanel();

    document.getElementById('advanced-config-container').style.display = 'block';
}

function renderSourcePanel() {
    const container = document.getElementById('source-list');
    container.innerHTML = '';

    const countBadge = document.getElementById('source-count');
    if (countBadge) countBadge.textContent = STATE.sourceSlides.length;

    STATE.sourceSlides.forEach(slide => {
        const item = document.createElement('div');
        item.className = 'source-slide-item';
        item.onclick = () => addToTarget(slide.index); // Click anywhere adds

        let tagsHtml = '';
        if (slide.identifiers && slide.identifiers.length > 0) {
            tagsHtml = slide.identifiers.map(tag =>
                `<span class="tag-badge" style="font-size:0.75rem; margin-right:4px;">${tag}</span>`
            ).join('');
        }

        item.innerHTML = `
            <div class="slide-mini-index">#${slide.index}</div>
            <div class="source-slide-info">
                ${tagsHtml}
                <div style="font-size:0.8rem; color:#999; margin-top:2px;">ID: ${slide.objectId.substring(0, 8)}...</div>
            </div>
            <div class="btn-add-slide" title="Agregar">+</div>
        `;

        container.appendChild(item);
    });
}

function renderTargetPanel() {
    const container = document.getElementById('target-list');
    container.innerHTML = '';

    if (STATE.targetSequence.length === 0) {
        container.innerHTML = '<div class="empty-target-message">Lista vacía. La presentación resultante fallará si no tiene slides.</div>';
        return;
    }

    STATE.targetSequence.forEach((item, idx) => {
        const row = document.createElement('div');
        row.className = 'target-slide-item';

        let tagsHtml = '';
        if (item.identifiers && item.identifiers.length > 0) {
            tagsHtml = item.identifiers.map(tag =>
                `<span class="tag-badge" style="font-size:0.75rem;">${tag}</span>`
            ).join(' ');
        } else {
            tagsHtml = `<span style="font-size:0.8rem; color:#ccc;">#${item.index}</span>`;
        }

        row.innerHTML = `
            <div class="target-slide-controls">
                <div style="display:flex; flex-direction:column; gap:2px;">
                    <button class="control-btn" onclick="moveSlide(${idx}, -1); event.stopPropagation();" title="Subir">▲</button>
                    <button class="control-btn" onclick="moveSlide(${idx}, 1); event.stopPropagation();" title="Bajar">▼</button>
                </div>
            </div>
            <div class="target-slide-content">
                ${tagsHtml}
            </div>
            <button class="control-btn remove" onclick="removeFromTarget(${idx}); event.stopPropagation();" title="Quitar">✕</button>
        `;
        container.appendChild(row);
    });
}

// LOGIC HELPERS

function addToTarget(sourceIndex) {
    const slide = STATE.sourceSlides.find(s => s.index === sourceIndex);
    if (slide) {
        addToTargetList(slide, true);
    }
}

function addToTargetList(slide, render = true) {
    STATE.targetSequence.push({
        ...slide,
        _uuid: Math.random().toString(36).substr(2, 9) // Internal unique ID if needed
    });
    if (render) renderTargetPanel();
}

function removeFromTarget(index) {
    STATE.targetSequence.splice(index, 1);
    renderTargetPanel();
}

function moveSlide(index, direction) {
    if (direction === -1 && index > 0) {
        // Swap with previous
        [STATE.targetSequence[index], STATE.targetSequence[index - 1]] =
            [STATE.targetSequence[index - 1], STATE.targetSequence[index]];
        renderTargetPanel();
    } else if (direction === 1 && index < STATE.targetSequence.length - 1) {
        // Swap with next
        [STATE.targetSequence[index], STATE.targetSequence[index + 1]] =
            [STATE.targetSequence[index + 1], STATE.targetSequence[index]];
        renderTargetPanel();
    }
}

function clearTargetList() {
    STATE.targetSequence = [];
    renderTargetPanel();
}


// Helpers para la sección advanced
function showErrorAdvanced(message) {
    showError('advanced', message);
}

function showAdvancedResult(data) {
    const output = document.getElementById('output-advanced');
    output.innerHTML = `Nueva presentación creada exitosamente:<br>` +
        `<a href="${data.new_presentation_url}" target="_blank" style="font-weight:bold; color:#2e7d32;">Abrir Presentación</a><br>` +
        `<span style="font-size:0.8em; color:#666;">ID: ${data.new_presentation_id}</span>`;
}

// ========================================================================
// FUNCIÓN 4: VERIFICAR ESTADO DEL SERVICIO
// ========================================================================

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        const data = await response.json();

        const healthOutput = document.getElementById('health-output');
        let output = `Estado del servicio: ${data.status.toUpperCase()}\n`;
        output += `Mensaje: ${data.message}\n`;

        if (data.status === 'warning') {
            output += '\n⚠️  ADVERTENCIA:\n';
            output += 'El archivo de credenciales no está configurado.\n';
            output += 'Debes pasar las credenciales JSON de tu Service Account de GCP.';
        }

        healthOutput.textContent = output;
        document.getElementById('health-status').style.display = 'block';

    } catch (error) {
        console.error('Error:', error);

        const output = `❌ ERROR DE CONEXIÓN\n\n` +
            `No se pudo conectar al servidor API.\n` +
            `Asegúrate de que:\n` +
            `1. El servidor está corriendo (python app.py)\n` +
            `2. La URL es: ${API_BASE_URL}\n` +
            `3. No hay firewall bloqueando\n\n` +
            `Error: ${error.message}`;

        document.getElementById('health-output').textContent = output;
        document.getElementById('health-status').style.display = 'block';
    }
}

// ========================================================================
// INICIALIZACIÓN - Event Listeners
// ========================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Permitir Enter en los inputs principales
    document.getElementById('url-extract')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') extractSlideIds();
    });

    document.getElementById('url-components')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') getSlideComponents();
    });

    document.getElementById('slide-index')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') getSlideComponents();
    });

    document.getElementById('url-advanced')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') previewSlides();
    });

    console.log('✓ Google Slides Automation Tool cargado');
});
