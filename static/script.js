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
// FUNCIÓN 4: RELLENAR PRESENTACIÓN CON JSON
// ========================================================================

async function fillWithJson() {
    const presentationUrl = document.getElementById('url-upload').value.trim();
    const folder = document.getElementById('folder-upload').value.trim();
    const newName = document.getElementById('name-upload').value.trim();
    const jsonText = document.getElementById('json-upload').value.trim();

    if (!presentationUrl || !presentationUrl.includes('docs.google.com/presentation')) {
        showError('upload', 'Ingresa una URL de presentación válida.');
        return;
    }
    if (!jsonText) {
        showError('upload', 'Pega un JSON con los valores.');
        return;
    }

    try {
        JSON.parse(jsonText);
    } catch (e) {
        showError('upload', 'JSON inválido: ' + e.message);
        return;
    }

    try {
        setUIState('upload', 'loading');
        setButtonState('btn-upload-fill', true);

        const formData = new FormData();
        formData.append('presentation_url', presentationUrl);
        formData.append('folder_url_or_id', folder);
        formData.append('new_name', newName);
        formData.append('data_json', jsonText);
        formData.append('remove_identifiers', 'true');

        const response = await fetch(`${API_BASE_URL}/api/fill-from-json`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || data.message || 'Error al rellenar presentación.');
        }

        showUploadResult(data);
        showResult('upload');
    } catch (error) {
        console.error('Error:', error);
        showError('upload', error.message);
    } finally {
        setButtonState('btn-upload-fill', false);
    }
}

function showUploadResult(data) {
    const outputDiv = document.getElementById('output-upload');
    const identifiers = (data.replaced || []).join(', ');
    outputDiv.innerHTML = `
        Marcadores reemplazados: <strong>${identifiers || 'N/D'}</strong><br>
        <a href="${data.new_presentation_url || data.presentation_url}" target="_blank" style="font-weight:bold; color:#2e7d32;">Abrir presentación</a><br>
        <span style="font-size:0.85em; color:#666;">Solo se reemplazaron los marcadores presentes en el JSON. Los $ fueron limpiados.</span>
    `;
}

// ========================================================================
// GEMINI: PROBAR SOLO LA IA
// ========================================================================

async function askGeminiOnly() {
    const text = document.getElementById('ask-gemini-text').value.trim();
    if (!text) {
        showError('ask-gemini', 'Escribí o pegá un texto.');
        return;
    }
    try {
        setUIState('ask-gemini', 'loading');
        setButtonState('btn-ask-gemini', true);
        const data = await apiFetch('/api/ask-gemini', { text: text });
        document.getElementById('output-ask-gemini').textContent = data.response || '(vacío)';
        showResult('ask-gemini');
    } catch (error) {
        showError('ask-gemini', error.message);
    } finally {
        setButtonState('btn-ask-gemini', false);
    }
}

async function askGeminiStructure() {
    const text = document.getElementById('ask-gemini-text').value.trim();
    if (!text) {
        showError('ask-gemini', 'Escribí o pegá un texto antes de estructurar.');
        return;
    }
    try {
        setButtonState('btn-ask-gemini-structure', true);
        document.getElementById('error-ask-gemini').style.display = 'none';
        document.getElementById('result-ask-gemini-structure').style.display = 'block';
        document.getElementById('output-ask-gemini-structure').innerHTML = '<p>Obteniendo estructura...</p>';
        const data = await apiFetch('/api/ask-gemini-structure', { text: text });
        const s = data.structured || {};
        const typeLabels = { comparacion: 'Comparación', descripcion: 'Descripción', lista_items: 'Lista de ítems', portada: 'Portada', capitulo: 'Capítulo', otro: 'Otro' };
        let html = '<p><strong>Tipo de contenido:</strong> ' + escapeHtml(typeLabels[s.content_type] || s.content_type || '—');
        if (s.content_type_note) html += ' <span style="color:#555;">(' + escapeHtml(s.content_type_note) + ')</span>';
        html += '</p>';
        html += '<p><strong>Título general:</strong> ' + escapeHtml(s.main_title || '—') + '</p>';
        html += '<p><strong>¿Tiene subtítulos/ítems?</strong> ' + (s.has_subtitles ? 'Sí' : 'No') + '</p>';
        if (s.subtitles && s.subtitles.length > 0) {
            html += '<p><strong>Subtítulos / ítems y descripciones:</strong></p>';
            s.subtitles.forEach(function(item, i) {
                html += '<p style="margin-left:12px;">' + (i + 1) + '. <strong>' + escapeHtml(item.title || '—') + '</strong>: ' + escapeHtml(item.description || '—') + '</p>';
            });
        }
        html += '<pre class="output-text" style="margin-top:12px; font-size:0.85rem;">' + escapeHtml(JSON.stringify(s, null, 2)) + '</pre>';
        document.getElementById('output-ask-gemini-structure').innerHTML = html;
    } catch (error) {
        document.getElementById('result-ask-gemini-structure').style.display = 'none';
        showError('ask-gemini', error.message);
    } finally {
        setButtonState('btn-ask-gemini-structure', false);
    }
}

async function askGeminiForSlide() {
    const text = document.getElementById('ask-gemini-text').value.trim();
    const url = (document.getElementById('ask-gemini-preso-url') && document.getElementById('ask-gemini-preso-url').value) ? document.getElementById('ask-gemini-preso-url').value.trim() : '';
    const slideInput = document.getElementById('ask-gemini-slide-index');
    const slideIndex = slideInput ? parseInt(slideInput.value, 10) : 0;
    if (!text) {
        showError('ask-gemini', 'Escribí o pegá un texto.');
        return;
    }
    if (!url || !url.includes('docs.google.com/presentation') || !url.includes('/d/')) {
        showError('ask-gemini', 'Para «Ponelo en la slide» necesitás la URL de la presentación (Google Slides).');
        return;
    }
    const idx = isNaN(slideIndex) || slideIndex < 0 ? 0 : slideIndex;
    try {
        document.getElementById('error-ask-gemini').style.display = 'none';
        const resultDiv = document.getElementById('result-ask-gemini-for-slide');
        const outDiv = document.getElementById('output-ask-gemini-for-slide');
        resultDiv.style.display = 'block';
        setButtonState('btn-ask-gemini-for-slide', true);
        outDiv.innerHTML = '<p>Obteniendo placeholders de la slide y generando JSON...</p>';
        const data = await apiFetch('/api/ask-gemini-for-slide', { text: text, presentation_url: url, slide_index: idx });
        const s = data.structured || {};
        const lines = Object.keys(s).map(function(k) {
            return '<p><strong>' + escapeHtml(k) + ':</strong> ' + escapeHtml(s[k] || '—') + '</p>';
        }).join('');
        outDiv.innerHTML = '<p style="font-size:0.9rem; color:#555;">Slide ' + idx + ', placeholders: ' + escapeHtml((data.placeholders || []).join(', ')) + (data.template_matched ? ' (plantilla de context.json aplicada)' : '') + '</p>' + lines + '<pre class="output-text" style="margin-top:12px; font-size:0.85rem;">' + escapeHtml(JSON.stringify(s, null, 2)) + '</pre>';
    } catch (error) {
        document.getElementById('result-ask-gemini-for-slide').style.display = 'none';
        showError('ask-gemini', error.message);
    } finally {
        setButtonState('btn-ask-gemini-for-slide', false);
    }
}

// GEMINI: PARSEAR TEXTO Y RELLENAR SLIDE
// ========================================================================

/**
 * Solo parsear: pide URL de plantilla + índice de slide, llama a Gemini y muestra el prompt que se mandó y el JSON que devolvió.
 * Guarda el resultado en window.lastParseResult para que "Crear copia con este resultado" lo reutilice.
 */
async function parseTextOnly() {
    const text = document.getElementById('gemini-text').value.trim();
    const url = document.getElementById('gemini-parse-url').value.trim().replace(/,\s*$/, '');
    const slideInput = document.getElementById('gemini-parse-slide');
    const slideIndex = slideInput ? parseInt(slideInput.value, 10) : 0;
    if (!text) {
        showError('gemini', 'Escribí algo en el cuadro de texto.');
        return;
    }
    if (!url || !url.includes('docs.google.com/presentation') || !url.includes('/d/')) {
        showError('gemini', 'Para probar el parseo necesitás la URL de la plantilla (Google Slides) y el índice de la slide.');
        return;
    }
    try {
        setUIState('gemini', 'loading');
        setButtonState('btn-parse-text', true);
        const payload = {
            text: text,
            presentation_url: url,
            slide_index: isNaN(slideIndex) || slideIndex < 0 ? 0 : slideIndex
        };
        const data = await apiFetch('/api/parse-text', payload);
        window.lastParseResult = {
            presentation_url: url,
            slide_index: isNaN(slideIndex) || slideIndex < 0 ? 0 : slideIndex,
            parsed: data.parsed || {},
            placeholders: data.placeholders || []
        };
        const out = document.getElementById('output-gemini');
        const promptBlock = data.prompt_sent
            ? `<details open><summary><strong>Prompt que se le envió a Gemini</strong></summary><pre style="background:#f0f4f8; padding:12px; border-radius:6px; overflow:auto; font-size:0.8rem; margin-top:6px; white-space:pre-wrap; max-height:280px;">${escapeHtml(data.prompt_sent)}</pre></details>`
            : '';
        const jsonBlock = data.parsed && Object.keys(data.parsed).length > 0
            ? `<p style="margin-top:12px;"><strong>JSON que devolvió Gemini</strong></p><pre style="background:#f5f5f5; padding:12px; border-radius:6px; overflow:auto; font-size:0.85rem;">${escapeHtml(JSON.stringify(data.parsed, null, 2))}</pre>`
            : '';
        out.innerHTML = `
            ${promptBlock}
            ${jsonBlock}
            <p style="margin-top:14px; font-size:0.9rem; color:#555;">Si este resultado está bien, indicá la carpeta de Drive abajo y usá <strong>«Crear copia y rellenar con este resultado»</strong> para no volver a llamar a Gemini.</p>
            <button type="button" id="btn-fill-with-result" class="btn btn-primary" style="margin-top:8px;">Crear copia y rellenar con este resultado</button>
        `;
        document.getElementById('btn-fill-with-result').onclick = fillWithLastParseResult;
        showResult('gemini');
    } catch (error) {
        console.error('Error:', error);
        showError('gemini', error.message);
    } finally {
        setButtonState('btn-parse-text', false);
    }
}

/**
 * Crea una copia de la plantilla y rellena la slide usando el JSON del último "Solo parsear" (reutiliza, no llama a Gemini).
 */
async function fillWithLastParseResult() {
    const last = window.lastParseResult;
    if (!last || !last.parsed || Object.keys(last.parsed).length === 0) {
        showError('gemini', 'Primero hacé «Solo parsear» y esperá a que devuelva el JSON.');
        return;
    }
    const folderUrl = document.getElementById('gemini-folder').value.trim().replace(/,\s*$/, '');
    const newName = document.getElementById('gemini-name').value.trim();
    if (!folderUrl) {
        showError('gemini', 'Indicá la carpeta de Drive donde crear la copia.');
        return;
    }
    try {
        setUIState('gemini', 'loading');
        setButtonState('btn-fill-with-result', true);
        const data = await apiFetch('/api/parse-and-fill', {
            presentation_url: last.presentation_url,
            folder_url_or_id: folderUrl,
            new_name: newName || null,
            slide_index: last.slide_index,
            parsed_replacements: last.parsed
        });
        const out = document.getElementById('output-gemini');
        const link = data.new_presentation_url || `https://docs.google.com/presentation/d/${data.presentation_id}/edit`;
        out.innerHTML = `
            <strong>Copia creada</strong> usando el JSON que habías parseado (no se llamó a Gemini de nuevo).<br>
            Slide ${data.slide_index} rellenada. Reemplazados: ${(data.replaced || []).join(', ')}.<br>
            <a href="${escapeHtml(link)}" target="_blank" style="font-weight:bold; color:#2e7d32;">Abrir presentación (copia)</a>
        `;
        showResult('gemini');
    } catch (error) {
        console.error('Error:', error);
        showError('gemini', error.message);
    } finally {
        const btn = document.getElementById('btn-fill-with-result');
        if (btn) setButtonState('btn-fill-with-result', false);
    }
}

/**
 * Crea una copia de la plantilla en la carpeta indicada, Gemini completa los # de la slide 0.
 * La plantilla original NUNCA se modifica.
 */
async function parseAndFill() {
    const text = document.getElementById('gemini-text').value.trim();
    const presentationUrl = document.getElementById('gemini-url').value.trim().replace(/,\s*$/, '');
    const folderUrl = document.getElementById('gemini-folder').value.trim().replace(/,\s*$/, '');
    const newName = document.getElementById('gemini-name').value.trim();
    const slideIndexInput = document.getElementById('gemini-slide-index');
    const slideIndex = slideIndexInput ? parseInt(slideIndexInput.value, 10) : 0;
    if (!text) {
        showError('gemini', 'Escribí algo en el cuadro de texto.');
        return;
    }
    if (!presentationUrl || !presentationUrl.includes('docs.google.com/presentation') || !presentationUrl.includes('/d/')) {
        showError('gemini', 'La URL de la plantilla tiene que ser de Google Slides (ej: https://docs.google.com/presentation/d/ID/edit).');
        return;
    }
    if (!folderUrl) {
        showError('gemini', 'Indicá la carpeta de Drive donde crear la copia. La plantilla nunca se modifica.');
        return;
    }
    try {
        setUIState('gemini', 'loading');
        setButtonState('btn-parse-fill', true);
        const data = await apiFetch('/api/parse-and-fill', {
            presentation_url: presentationUrl,
            folder_url_or_id: folderUrl,
            new_name: newName || null,
            slide_index: isNaN(slideIndex) || slideIndex < 0 ? 0 : slideIndex,
            text: text
        });
        const parsedLines = data.parsed && typeof data.parsed === 'object'
            ? Object.entries(data.parsed).map(([k, v]) => `<strong>#${k}:</strong> ${escapeHtml(String(v).substring(0, 200))}${String(v).length > 200 ? '…' : ''}`).join('<br>')
            : '';
        const out = document.getElementById('output-gemini');
        const link = data.new_presentation_url || `https://docs.google.com/presentation/d/${data.presentation_id}/edit`;
        out.innerHTML = `
            <strong>Gemini completó estos placeholders:</strong><br>${parsedLines || '—'}<br><br>
            <strong>Copia creada.</strong> Slide ${data.slide_index} rellenada. Reemplazados: ${(data.replaced || []).join(', ')}. La plantilla no fue modificada.<br>
            <a href="${escapeHtml(link)}" target="_blank" style="font-weight:bold; color:#2e7d32;">Abrir presentación (copia)</a>
        `;
        showResult('gemini');
    } catch (error) {
        console.error('Error:', error);
        showError('gemini', error.message);
    } finally {
        setButtonState('btn-parse-fill', false);
    }
}

function escapeHtml(str) {
    if (str == null) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ========================================================================
// FUNCIÓN 5: GENERAR DESDE SPEC
// ========================================================================

const SPEC_EXAMPLE = {
  slide_1: {
    type: "cover",
    content: {
      main_title: "Presentación de testeo",
      footer_context: "Contexto opcional"
    }
  },
  slide_2: {
    type: "chapter",
    content: {
      section_title: "Introducción",
      chapter: "Capítulo 1",
      _number: "1"
    }
  },
  slide_3: {
    type: "descriptive",
    content: {
      main_title: "Resumen ejecutivo",
      description: "Este es el texto descriptivo de la diapositiva. Podés poner todo el contenido que necesites para probar el reemplazo de los marcadores."
    }
  },
  slide_4: {
    type: "three",
    content: {
      item_1_title: "Primer ítem",
      item_1_description: "Descripción del primer punto.",
      item_2_title: "Segundo ítem",
      item_2_description: "Descripción del segundo punto.",
      item_3_title: "Tercer ítem",
      item_3_description: "Descripción del tercer punto."
    }
  },
  slide_5: {
    type: "comparative",
    content: {
      main_title: "Comparativa",
      column_1_title: "Opción A",
      column_1_description: "Detalle de la opción A.",
      column_2_title: "Opción B",
      column_2_description: "Detalle de la opción B."
    }
  }
};

function loadSpecExample() {
  document.getElementById('name-spec').value = 'Presentación Monks - Test';
  document.getElementById('json-spec').value = JSON.stringify(SPEC_EXAMPLE, null, 2);
}

async function buildFromSpec() {
  const presentationUrl = document.getElementById('url-spec').value.trim();
  const folderUrl = document.getElementById('folder-spec').value.trim();
  const newName = document.getElementById('name-spec').value.trim();
  const jsonSpec = document.getElementById('json-spec').value.trim();

  if (!presentationUrl || !presentationUrl.includes('docs.google.com/presentation')) {
    showError('spec', 'Ingresá la URL del template (Google Slides).');
    return;
  }
  if (!folderUrl) {
    showError('spec', 'Ingresá la carpeta de destino (URL o ID de Drive).');
    return;
  }
  if (!jsonSpec) {
    showError('spec', 'Ingresá el JSON del spec (o usá "Cargar ejemplo").');
    return;
  }

  let spec;
  try {
    spec = JSON.parse(jsonSpec);
  } catch (e) {
    showError('spec', 'JSON inválido: ' + e.message);
    return;
  }

  try {
    setUIState('spec', 'loading');
    setButtonState('btn-build-spec', true);

    const data = await apiFetch('/api/build-from-spec', {
      presentation_url: presentationUrl,
      folder_url_or_id: folderUrl,
      new_name: newName || null,
      spec: spec
    });

    const output = document.getElementById('output-spec');
    output.innerHTML = `
      <a href="${data.new_presentation_url}" target="_blank" style="font-weight:bold; color:#2e7d32;">Abrir presentación</a><br>
      <span style="font-size:0.85em; color:#666;">Slides: ${data.slides_count} · ID: ${data.new_presentation_id}</span>
    `;
    showResult('spec');
  } catch (error) {
    console.error('Error:', error);
    showError('spec', error.message);
  } finally {
    setButtonState('btn-build-spec', false);
  }
}

// ========================================================================
// FUNCIÓN 6: VERIFICAR ESTADO DEL SERVICIO
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

    document.getElementById('url-spec')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') buildFromSpec();
    });
    document.getElementById('folder-spec')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') buildFromSpec();
    });

    console.log('✓ Google Slides Automation Tool cargado');
});
