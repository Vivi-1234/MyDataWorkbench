document.addEventListener('DOMContentLoaded', () => {
    // --- Globals & State ---
    const toolListContainer = document.getElementById('tool-list');
    const mainContentContainer = document.getElementById('main-content');
    let MULEBUY_IMAGE_DATA, TRANSLATOR_BASE_FILES, TRANSLATOR_TARGET_FILES, TRANSLATOR_AI_RESULTS;

    // --- All Handler & Helper Functions ---
    const renderToolList = () => { /* ... */ };
    const renderAiModelSelector = () => { /* ... */ };
    const loadTool = async (toolId) => { /* ... */ };
    const handleGenerateReportClick = async (btn) => { /* ... */ };
    const renderReport = (data) => { /* ... */ };
    const initializeMulebuyPics = async () => { /* ... */ };
    const initializeTranslator = async () => { /* ... */ };
    // ... all other functions for all tools ...

    // --- Main Execution ---
    new QWebChannel(qt.webChannelTransport, (channel) => {
        window.pyBackend = channel.objects.pyBackend;
        renderToolList();
        renderAiModelSelector();
        loadTool('affiliate_data'); // Load initial tool
    });

    // --- Main Event Listener ---
    document.addEventListener('click', async (e) => {
        const target = e.target.closest('button');
        if (!target) return;
        if (target.matches('.tool-btn')) await loadTool(target.dataset.toolId);
        switch (target.id) {
            case 'generate-report-btn': await handleGenerateReportClick(target); break;
            // ... other cases
        }
    });
});
