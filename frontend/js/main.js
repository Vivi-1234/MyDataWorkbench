document.addEventListener('DOMContentLoaded', () => {
    const toolListContainer = document.getElementById('tool-list');
    const mainContentContainer = document.getElementById('main-content');
    let pyBackend;

    const tools = [
        { id: 'affiliate_data', name: '联盟数据' },
        { id: 'image_processor', name: '图片批量处理器' },
        { id: 'mulebuy_pics', name: 'Mulebuy图片' },
        { id: 'translator', name: '文案优化' }
    ];

    new QWebChannel(qt.webChannelTransport, (channel) => {
        pyBackend = channel.objects.pyBackend;

        // 1. Render tool list
        renderToolList();

        // 2. Add AI Model Selector (as an example of JS->HTML)
        renderAiModelSelector();
    });

    function renderToolList() {
        if (!toolListContainer) return;

        const ul = document.createElement('ul');
        ul.className = 'space-y-2';

        tools.forEach(tool => {
            const li = document.createElement('li');
            const button = document.createElement('button');
            button.textContent = tool.name;
            button.className = 'w-full text-left px-4 py-2 rounded-md transition-colors duration-200 hover:bg-pink-500 hover:text-white focus:outline-none focus:ring-2 focus:ring-pink-400';
            button.addEventListener('click', () => loadTool(tool.id));
            li.appendChild(button);
            ul.appendChild(li);
        });

        toolListContainer.appendChild(ul);
    }

    async function loadTool(toolId) {
        if (!mainContentContainer || !pyBackend) return;

        try {
            mainContentContainer.innerHTML = '<div class="text-center text-gray-500">正在加载...</div>';
            const toolHtml = await pyBackend.get_tool_html(toolId);
            mainContentContainer.innerHTML = toolHtml;

            // If the mulebuy pics tool is loaded, initialize it
            if (toolId === 'mulebuy_pics') {
                await initializeMulebuyPics();
            }
            // If the translator tool is loaded, initialize it
            else if (toolId === 'translator') {
                await initializeTranslator();
            }
        } catch (error) {
            console.error('Error loading tool:', error);
            mainContentContainer.innerHTML = `<div class="text-red-500">加载工具 ${toolId} 时出错: ${error}</div>`;
        }
    }

// --- Global functions callable from Python ---
function updateIpProgress(step, percent) {
    const progress_bar = document.getElementById(`ip-${step}-progress`);
    if (progress_bar) {
        progress_bar.style.width = `${percent}%`;
    }
}

function updateIpStatus(step, message) {
    const status_div = document.getElementById(`ip-${step}-status`);
    if (status_div) {
        status_div.innerHTML = message.replace(/\n/g, '<br>');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const toolListContainer = document.getElementById('tool-list');
    const mainContentContainer = document.getElementById('main-content');
    let pyBackend;

    const tools = [
        { id: 'affiliate_data', name: '联盟数据' },
        { id: 'image_processor', name: '图片批量处理器' },
        { id: 'mulebuy_pics', name: 'Mulebuy图片' },
        { id: 'translator', name: '文案优化' }
    ];

    new QWebChannel(qt.webChannelTransport, (channel) => {
        window.pyBackend = channel.objects.pyBackend;
        window.pyIpBackend = channel.objects.pyIpBackend;
        window.pyTranslatorBackend = channel.objects.pyTranslatorBackend;

        // 1. Render tool list
        renderToolList();

        // 2. Add AI Model Selector (as an example of JS->HTML)
        renderAiModelSelector();
    });

    function renderToolList() {
        if (!toolListContainer) return;

        const ul = document.createElement('ul');
        ul.className = 'space-y-2';

        tools.forEach(tool => {
            const li = document.createElement('li');
            const button = document.createElement('button');
            button.textContent = tool.name;
            button.className = 'w-full text-left px-4 py-2 rounded-md transition-colors duration-200 hover:bg-pink-500 hover:text-white focus:outline-none focus:ring-2 focus:ring-pink-400';
            button.addEventListener('click', () => loadTool(tool.id));
            li.appendChild(button);
            ul.appendChild(li);
        });

        toolListContainer.appendChild(ul);
    }

    async function loadTool(toolId) {
        if (!mainContentContainer || !pyBackend) return;

        try {
            mainContentContainer.innerHTML = '<div class="text-center text-gray-500">正在加载...</div>';
            const toolHtml = await pyBackend.get_tool_html(toolId);
            mainContentContainer.innerHTML = toolHtml;

            // If the mulebuy pics tool is loaded, initialize it
            if (toolId === 'mulebuy_pics') {
                await initializeMulebuyPics();
            }
        } catch (error) {
            console.error('Error loading tool:', error);
            mainContentContainer.innerHTML = `<div class="text-red-500">加载工具 ${toolId} 时出错: ${error}</div>`;
        }
    }

    // --- Event Delegation for dynamically loaded content ---
    document.addEventListener('click', async (event) => {
        const target = event.target;
        if (!target) return;

        // Affiliate Data Tool
        if (target.id === 'generate-report-btn') {
            handleGenerateReportClick(target);
        }
        // Image Processor Tool
        else if (target.id === 'ip-select-qc-btn') {
            const fileName = await window.pyIpBackend.open_qc_file_dialog();
            if (fileName) {
                document.getElementById('ip-qc-file-label').textContent = fileName;
            }
        }
        else if (target.id === 'ip-start-download-btn') {
            window.pyIpBackend.start_download();
        }
        // Mulebuy Pics Tool
        else if (target.id === 'create-category-btn') {
            await handleMulebuyCreateCategory();
        } else if (target.id === 'rename-category-btn') {
            await handleMulebuyRenameCategory();
        } else if (target.id === 'delete-category-btn') {
            await handleMulebuyDeleteCategory();
        } else if (target.id === 'upload-images-btn') {
            await handleMulebuyUploadImages();
        } else if (target.id === 'bulk-delete-btn') {
            await handleMulebuyBulkDelete();
        } else if (target.id === 'bulk-move-btn') {
            await handleMulebuyBulkMove();
        } else if (target.id === 'select-all-checkbox') {
            handleMulebuySelectAll(target.checked);
        }
    });

    // --- Mulebuy Pics specific logic ---
    let MULEBUY_IMAGE_DATA = null;

    async function initializeMulebuyPics() {
        try {
            const resultStr = await pyBackend.get_mulebuy_image_data();
            MULEBUY_IMAGE_DATA = JSON.parse(resultStr);
            if (MULEBUY_IMAGE_DATA.error) {
                document.getElementById('gallery-content').innerHTML = `<p class="text-red-500">${MULEBUY_IMAGE_DATA.error}</p>`;
                return;
            }
            renderMulebuyUI();
        } catch(e) {
            console.error("Error initializing Mulebuy Pics", e);
        }
    }

    function renderMulebuyUI() {
        renderMulebuySidebar();
        renderMulebuyTabs();
        // Initial tab content
        if (MULEBUY_IMAGE_DATA.uncategorized || MULEBUY_IMAGE_DATA.categorized.length > 0) {
            const initialTabName = MULEBUY_IMAGE_DATA.uncategorized.images.length > 0 ? '未分类' : MULEBUY_IMAGE_DATA.categorized[0].name;
            renderMulebuyGallery(initialTabName);
        }
    }

    function renderMulebuySidebar() {
        const categories = ["未分类", ...MULEBUY_IMAGE_DATA.categories];
        const uploadSelect = document.getElementById('upload-category-select');
        const manageSelect = document.getElementById('manage-category-select');

        uploadSelect.innerHTML = categories.map(c => `<option value="${c}">${c}</option>`).join('');
        manageSelect.innerHTML = MULEBUY_IMAGE_DATA.categories.map(c => `<option value="${c}">${c}</option>`).join('');
    }

    function renderMulebuyTabs() {
        const tabsContainer = document.getElementById('gallery-tabs');
        tabsContainer.innerHTML = ''; // Clear existing tabs

        const createTab = (name) => {
            const button = document.createElement('button');
            button.className = 'px-4 py-2 text-sm font-medium text-gray-400 border-b-2 border-transparent hover:text-pink-400 hover:border-pink-400';
            button.textContent = name;
            button.dataset.tabName = name;
            button.addEventListener('click', () => renderMulebuyGallery(name));
            return button;
        };

        if (MULEBUY_IMAGE_DATA.uncategorized.images.length > 0) {
            tabsContainer.appendChild(createTab('未分类'));
        }
        MULEBUY_IMAGE_DATA.categorized.forEach(cat => {
            tabsContainer.appendChild(createTab(cat.name));
        });
    }

    function renderMulebuyGallery(categoryName) {
        const contentContainer = document.getElementById('gallery-content');
        const toolbar = document.getElementById('gallery-toolbar');

        let data;
        if (categoryName === '未分类') {
            data = MULEBUY_IMAGE_DATA.uncategorized;
        } else {
            data = MULEBUY_IMAGE_DATA.categorized.find(c => c.name === categoryName);
        }

        if (!data || data.images.length === 0) {
            contentContainer.innerHTML = '<p class="text-gray-500 text-center mt-8">这个分类下还没有图片。</p>';
            toolbar.classList.add('hidden');
            return;
        }

        toolbar.classList.remove('hidden');
        // Populate move dropdown
        const moveSelect = document.getElementById('bulk-move-select');
        const moveCategories = ["未分类", ...MULEBUY_IMAGE_DATA.categories].filter(c => c !== categoryName);
        moveSelect.innerHTML = moveCategories.map(c => `<option value="${c}">${c}</option>`).join('');


        let gridHtml = '<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">';
        data.images.forEach(imgPath => {
            gridHtml += `
                <div class="relative group bg-gray-900 rounded-lg overflow-hidden border-2 border-transparent hover:border-pink-500 transition-all">
                    <img src="${imgPath}" loading="lazy" class="w-full h-40 object-cover">
                    <div class="absolute top-2 left-2">
                        <input type="checkbox" data-path="${imgPath}" class="mulebuy-img-checkbox h-5 w-5 bg-gray-700 border-gray-500 text-pink-500 focus:ring-pink-500 rounded">
                    </div>
                </div>
            `;
        });
        gridHtml += '</div>';
        contentContainer.innerHTML = gridHtml;
    }

    function handleMulebuySelectAll(isChecked) {
        document.querySelectorAll('.mulebuy-img-checkbox').forEach(cb => cb.checked = isChecked);
    }

    function getSelectedImagePaths() {
        const selected = [];
        document.querySelectorAll('.mulebuy-img-checkbox:checked').forEach(cb => {
            selected.push(cb.dataset.path);
        });
        return selected;
    }

    async function handleMulebuyBulkDelete() {
        const paths = getSelectedImagePaths();
        if (paths.length === 0) return;
        if (!confirm(`确定要永久删除选中的 ${paths.length} 张图片吗？`)) return;

        await pyBackend.delete_mulebuy_images(JSON.stringify(paths));
        await initializeMulebuyPics();
    }

    async function handleMulebuyBulkMove() {
        const paths = getSelectedImagePaths();
        const destination = document.getElementById('bulk-move-select').value;
        if (paths.length === 0 || !destination) return;

        await pyBackend.move_mulebuy_images(JSON.stringify(paths), destination);
        await initializeMulebuyPics();
    }

    async function handleMulebuyCreateCategory() {
        const input = document.getElementById('new-category-name');
        if (!input || !input.value) return;
        await pyBackend.create_mulebuy_category(input.value);
        input.value = '';
        await initializeMulebuyPics(); // Refresh everything
    }

    async function handleMulebuyUploadImages() {
        const filePathsStr = await pyBackend.open_image_file_dialog();
        const filePaths = JSON.parse(filePathsStr);
        if (filePaths.length === 0) return;

        const targetCategory = document.getElementById('upload-category-select').value;
        await pyBackend.upload_mulebuy_images(filePaths, targetCategory);
        await initializeMulebuyPics(); // Refresh everything
    }

    async function handleMulebuyRenameCategory() {
        const oldName = document.getElementById('manage-category-select').value;
        const newName = document.getElementById('rename-category-input').value;
        if (!oldName || !newName || oldName === newName) return;
        await pyBackend.rename_mulebuy_category(oldName, newName);
        await initializeMulebuyPics();
    }

    async function handleMulebuyDeleteCategory() {
        const name = document.getElementById('manage-category-select').value;
        if (!name) return;
        const resultStr = await pyBackend.delete_mulebuy_category(name);
        const result = JSON.parse(resultStr);
        if (!result.success) {
            alert(result.error); // Simple alert for now
        }
        await initializeMulebuyPics();
    }

    async function handleGenerateReportClick(button) {
        const affiliateId = document.getElementById('affiliate-id').value;
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        const reportContainer = document.getElementById('report-container');

        if (!affiliateId || !startDate || !endDate) {
            reportContainer.innerHTML = '<p class="text-yellow-400 text-center">请填写所有参数。</p>';
            return;
        }

        button.disabled = true;
        button.textContent = '正在生成...';
        reportContainer.innerHTML = '<p class="text-gray-500 text-center">正在计算...</p>';

        try {
            const resultStr = await pyBackend.generate_affiliate_report(parseInt(affiliateId), startDate, endDate);
            const result = JSON.parse(resultStr);

            if (result.error) {
                reportContainer.innerHTML = `<p class="text-red-500 text-center">${result.error}</p>`;
            } else {
                renderReport(result);
            }
        } catch (e) {
            console.error(e);
            reportContainer.innerHTML = `<p class="text-red-500 text-center">生成报告时发生未知错误。</p>`;
        } finally {
            button.disabled = false;
            button.textContent = '🚀 生成分析报告';
        }
    }

    function renderReport(data) {
        const container = document.getElementById('report-container');
        const displayOrder = ['注册用户数', '激活用户数', '活跃人数', '下单人数', '下单数量', '下单总金额', '提包人数', '提包数量', '提包总金额', '收单总金额'];

        let content = '<div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">';
        displayOrder.forEach(key => {
            const value = data[key];
            const formattedValue = Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
            content += `
                <div class="flex justify-between items-baseline border-b border-gray-700 py-2">
                    <span class="text-gray-300 font-medium">${key}:</span>
                    <span class="text-pink-400 font-bold text-lg">${formattedValue}</span>
                </div>
            `;
        });
        content += '</div>';

        container.innerHTML = content;
    }

    function renderAiModelSelector() {
        const container = document.getElementById('ai-model-selector-container');
        if (!container) return;

        const label = document.createElement('label');
        label.textContent = '🧠 AI模型选择:';
        label.className = 'block text-sm font-medium text-gray-400 mb-1';

        const select = document.createElement('select');
        select.id = 'ai-model-selector';
        select.className = 'w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-pink-500';

        const models = ["mulebuy-optimizer", "llama3.1:latest", "qwen3:8b", "gemma3:4b", "gpt-oss:20b"];
        models.forEach(modelName => {
            const option = document.createElement('option');
            option.value = modelName;
            option.textContent = modelName;
            select.appendChild(option);
        });

        container.appendChild(label);
        container.appendChild(select);
    }
});
