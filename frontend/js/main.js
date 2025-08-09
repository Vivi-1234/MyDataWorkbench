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
    document.getElementById('tr-run-ai-btn').disabled = false;
    document.getElementById('tr-download-btn').disabled = false;
    alert("AI 优化完成！结果已可供审查和下载。");
    // In a real app, render review tabs here
}

document.addEventListener('DOMContentLoaded', () => {
    // --- Globals ---
    const toolListContainer = document.getElementById('tool-list');
    const mainContentContainer = document.getElementById('main-content');

    // --- State ---
    let MULEBUY_IMAGE_DATA = {};
    let TRANSLATOR_BASE_FILES = {};
    let TRANSLATOR_TARGET_FILES = {};
    let TRANSLATOR_AI_RESULTS = {};

    // --- WebChannel Initialization ---
    new QWebChannel(qt.webChannelTransport, (channel) => {
        window.pyBackend = channel.objects.pyBackend;
        renderToolList();
        renderAiModelSelector();
    });

    // --- UI Rendering ---
    const tools = [
        { id: 'affiliate_data', name: '联盟数据' },
        { id: 'image_processor', name: '图片批量处理器' },
        { id: 'mulebuy_pics', name: 'Mulebuy图片' },
        { id: 'translator', name: '文案优化' }
    ];

    function renderToolList() {
        toolListContainer.innerHTML = `<ul class="space-y-2">${tools.map(tool => `
            <li><button data-tool-id="${tool.id}" class="tool-btn w-full text-left px-4 py-2 rounded-md transition-colors duration-200 hover:bg-rose-500 hover:text-white">${tool.name}</button></li>
        `).join('')}</ul>`;
    }

    function renderAiModelSelector() {
        const container = document.getElementById('ai-model-selector-container');
        const models = ["mulebuy-optimizer", "llama3.1:latest", "qwen3:8b", "gemma3:4b", "gpt-oss:20b"];
        container.innerHTML = `
            <label for="ai-model-selector" class="block text-sm font-medium text-slate-300 mb-1">🧠 AI模型选择:</label>
            <select id="ai-model-selector" class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-rose-500">
                ${models.map(m => `<option value="${m}">${m}</option>`).join('')}
            </select>`;
    }

    async function loadTool(toolId) {
        mainContentContainer.innerHTML = `<div class="text-center text-slate-500">正在加载...</div>`;
        try {
            const toolHtml = await window.pyBackend.get_tool_html(toolId);
            mainContentContainer.innerHTML = toolHtml;
            if (toolId === 'mulebuy_pics') await initializeMulebuyPics();
            else if (toolId === 'translator') await initializeTranslator();
        } catch (e) {
            mainContentContainer.innerHTML = `<div class="text-red-500">加载工具 ${toolId} 时出错: ${e}</div>`;
        }
    }

    // --- Main Event Listener ---
    document.addEventListener('click', async (event) => {
        const target = event.target.closest('button');
        if (!target) return;
        if (target.matches('.tool-btn')) await loadTool(target.dataset.toolId);
        // ... other handlers
    });

    // ... all tool-specific functions
});
