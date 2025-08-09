function updateIpProgress(step, percent) { /* ... */ }
function updateIpStatus(step, message) { /* ... */ }
function onAiTranslationFinished(resultStr) { /* ... */ }

document.addEventListener('DOMContentLoaded', () => {
    const toolListContainer = document.getElementById('tool-list');
    const mainContentContainer = document.getElementById('main-content');

    // --- State ---
    let MULEBUY_IMAGE_DATA, TRANSLATOR_BASE_FILES, TRANSLATOR_TARGET_FILES, TRANSLATOR_AI_RESULTS;

    // --- WebChannel Init ---
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
    function renderToolList() { /* ... */ }
    function renderAiModelSelector() { /* ... */ }

    async function loadTool(toolId) {
        mainContentContainer.innerHTML = `<div class="text-center text-slate-500">正在加载...</div>`;
        const html = await pyBackend.get_tool_html(toolId);
        mainContentContainer.innerHTML = html;
        if (toolId === 'mulebuy_pics') await initializeMulebuyPics();
        if (toolId === 'translator') await initializeTranslator();
    }

    // --- Event Delegation ---
    document.addEventListener('click', async (e) => {
        const target = e.target.closest('button');
        if (!target) return;
        const id = target.id;
        if (target.matches('.tool-btn')) await loadTool(target.dataset.toolId);
        // Affiliate Data
        if (id === 'generate-report-btn') await handleGenerateReportClick(target);
        // Mulebuy Pics
        if (id === 'upload-images-btn') await handleMulebuyUpload();
        // ... other handlers
    });

    // --- Tool Logic ---
    async function handleGenerateReportClick(btn) {
        const affiliateId = document.getElementById('affiliate-id').value;
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        const result = await pyBackend.generate_affiliate_report(parseInt(affiliateId), startDate, endDate);
        // ... render result
    }

    async function initializeMulebuyPics() {
        const dataStr = await pyBackend.get_mulebuy_image_data();
        MULEBUY_IMAGE_DATA = JSON.parse(dataStr);
        // ... render UI
    }

    async function handleMulebuyUpload() {
        const pathsStr = await pyBackend.open_image_file_dialog();
        const paths = JSON.parse(pathsStr);
        // ... call backend to copy
        await initializeMulebuyPics(); // refresh
    }

    // ... all other functions
});
