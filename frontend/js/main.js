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
    alert("AI 优化完成！");
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
        window.pyBackend = channel.objects.pyBackend;
        window.pyIpBackend = channel.objects.pyIpBackend;
        window.pyTranslatorBackend = channel.objects.pyTranslatorBackend;

        renderToolList();
        renderAiModelSelector(); // This was the missing function call's target
    });

    const tools = [
        { id: 'affiliate_data', name: '联盟数据' },
        { id: 'image_processor', name: '图片批量处理器' },
        { id: 'mulebuy_pics', name: 'Mulebuy图片' },
        { id: 'translator', name: '文案优化' }
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

    function renderAiModelSelector() {
        const container = document.getElementById('ai-model-selector-container');
        if (!container) return;
        const models = ["mulebuy-optimizer", "llama3.1:latest", "qwen3:8b", "gemma3:4b", "gpt-oss:20b"];
        container.innerHTML = `
            <label for="ai-model-selector" class="block text-sm font-medium text-gray-400 mb-1">🧠 AI模型选择:</label>
            <select id="ai-model-selector" class="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-pink-500">
                ${models.map(m => `<option value="${m}">${m}</option>`).join('')}
            </select>
        `;
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

    // Main event listener
    document.addEventListener('click', async (event) => {
        const target = event.target.closest('button');
        if (!target) return;
        if (target.matches('.tool-btn')) await loadTool(target.dataset.toolId);
        // ... other event handlers
    });

    // ... all other tool-specific handlers go here
});
