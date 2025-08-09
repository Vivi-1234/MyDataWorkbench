// --- Global functions callable from Python ---
function updateIpProgress(step, percent) {
    const progressBar = document.getElementById(`ip-${step}-progress`);
    if (progressBar) progressBar.style.width = `${percent}%`;
}
function updateIpStatus(step, message) {
    const statusDiv = document.getElementById(`ip-${step}-status`);
    if (statusDiv) statusDiv.innerHTML = message.replace(/\n/g, '<br>');
}
function onAiTranslationFinished(resultStr) {
    window.TRANSLATOR_AI_RESULTS = JSON.parse(resultStr);
    alert("AI 优化完成！"); // Placeholder
    // In a real app, render review tabs here
}

document.addEventListener('DOMContentLoaded', () => {
    const toolListContainer = document.getElementById('tool-list');
    const mainContentContainer = document.getElementById('main-content');

    // --- State ---
    window.TRANSLATOR_BASE_FILES = {};
    window.TRANSLATOR_TARGET_FILES = {};
    window.TRANSLATOR_AI_RESULTS = {};
    let MULEBUY_IMAGE_DATA = null;

    new QWebChannel(qt.webChannelTransport, (channel) => {
        // Make backend objects globally accessible
        window.pyBackend = channel.objects.pyBackend;
        window.pyIpBackend = channel.objects.pyIpBackend;
        window.pyTranslatorBackend = channel.objects.pyTranslatorBackend;

        renderToolList();
        renderAiModelSelector();
    });

    const tools = [
        { id: 'affiliate_data', name: '联盟数据' }, { id: 'image_processor', name: '图片批量处理器' },
        { id: 'mulebuy_pics', name: 'Mulebuy图片' }, { id: 'translator', name: '文案优化' }
    ];

    function renderToolList() {
        toolListContainer.innerHTML = `<ul class="space-y-2">${tools.map(tool => `
            <li>
                <button data-tool-id="${tool.id}" class="tool-btn w-full text-left px-4 py-2 rounded-md transition-colors duration-200 hover:bg-pink-500 hover:text-white focus:outline-none focus:ring-2 focus:ring-pink-400">
                    ${tool.name}
                </button>
            </li>
        `).join('')}</ul>`;
    }

    async function loadTool(toolId) {
        mainContentContainer.innerHTML = '<div class="text-center text-gray-500">正在加载...</div>';
        try {
            const toolHtml = await window.pyBackend.get_tool_html(toolId);
            mainContentContainer.innerHTML = toolHtml;
            if (toolId === 'mulebuy_pics') await initializeMulebuyPics();
            else if (toolId === 'translator') await initializeTranslator();
        } catch (e) {
            mainContentContainer.innerHTML = `<div class="text-red-500">加载工具 ${toolId} 时出错: ${e}</div>`;
        }
    }

    // --- Main Event Listener (Delegation) ---
    document.addEventListener('click', async (event) => {
        const target = event.target.closest('button, input[type=checkbox]');
        if (!target) return;

        if (target.matches('.tool-btn')) await loadTool(target.dataset.toolId);
        // Affiliate Data
        else if (target.id === 'generate-report-btn') await handleGenerateReportClick(target);
        // Image Processor
        else if (target.id === 'ip-select-qc-btn') {
            const fileName = await window.pyIpBackend.open_qc_file_dialog();
            if (fileName) document.getElementById('ip-qc-file-label').textContent = fileName;
        }
        else if (target.id === 'ip-start-download-btn') window.pyIpBackend.start_download();
        // ... other IP buttons
        // Mulebuy Pics
        // ... (all mulebuy handlers)
        // Translator
        else if (target.id === 'tr-upload-btn') await handleTranslatorUpload();
        else if (target.id === 'tr-run-ai-btn') await handleTranslatorRunAi();
    });

    // --- Tool Specific Functions ---
    async function handleGenerateReportClick(button) { /* ... implementation ... */ }
    function renderReport(data) { /* ... implementation ... */ }
    async function initializeMulebuyPics() { /* ... implementation ... */ }
    // ... all other functions from before
    async function initializeTranslator() {
        const baseFilesStr = await window.pyTranslatorBackend.get_base_files();
        window.TRANSLATOR_BASE_FILES = JSON.parse(baseFilesStr);
        document.getElementById('tr-file-select').addEventListener('change', (e) => renderTranslatorPreview(e.target.value));
    }
    async function handleTranslatorUpload() {
        const targetFilesStr = await window.pyTranslatorBackend.open_translation_files();
        window.TRANSLATOR_TARGET_FILES = JSON.parse(targetFilesStr);
        const commonFiles = Object.keys(window.TRANSLATOR_BASE_FILES).filter(k => k in window.TRANSLATOR_TARGET_FILES);
        const select = document.getElementById('tr-file-select');
        select.innerHTML = commonFiles.map(f => `<option value="${f}">${f}</option>`).join('');
        if (commonFiles.length > 0) renderTranslatorPreview(commonFiles[0]);
    }
    function renderTranslatorPreview(filename) { /* ... implementation ... */ }
    async function handleTranslatorRunAi() {
        const lang = document.getElementById('tr-lang-input').value;
        const model = document.getElementById('ai-model-selector').value;
        window.pyTranslatorBackend.start_translation(lang, model, JSON.stringify(window.TRANSLATOR_BASE_FILES), JSON.stringify(window.TRANSLATOR_TARGET_FILES));
    }
});
