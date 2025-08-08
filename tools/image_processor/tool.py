# 文件路径: MyDataWorkbench/tools/image_processor/tool.py

import streamlit as st
import os
import cv2
import shutil
import time
import requests
import numpy as np
import json
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from collections import Counter

# --- 全局配置 ---
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

class Config:
    INPUT_DIR = os.path.join(BASE_PATH, 'input')
    OUTPUT_DIR = os.path.join(BASE_PATH, 'output')
    TEMPLATE_DIR = os.path.join(BASE_PATH, 'templates')
    
    URL_FILE_PATH = os.path.join(INPUT_DIR, 'qc.txt')
    STATE_FILE_PATH = os.path.join(INPUT_DIR, 'state.json') # 新增：状态文件
    PROCESSED_FOLDER = os.path.join(OUTPUT_DIR, 'processed_images')
    UNPROCESSED_FOLDER = os.path.join(OUTPUT_DIR, 'unprocessed_images')

    MATCH_THRESHOLD = 0.8
    NUM_WORKERS = max(1, os.cpu_count() - 1)

    LOWER_RED1, UPPER_RED1 = np.array([0, 80, 80]), np.array([10, 255, 255])
    LOWER_RED2, UPPER_RED2 = np.array([160, 80, 80]), np.array([179, 255, 255])
    LOWER_WHITE, UPPER_WHITE = np.array([0, 0, 180]), np.array([179, 40, 255])
    MIN_RED_TO_WHITE_RATIO = 0.01
    MIN_TOTAL_AREA_RATIO = 0.0001 # 示例值，需要调整
    MIN_ASPECT_RATIO = 0.5       # 示例值，需要调整
    MAX_ASPECT_RATIO = 5.0       # 示例值，需要调整

# --- 全局模板变量 ---
templates_g = []

def init_template_worker():
    """初始化每个工作进程，加载模板"""
    global templates_g
    templates_g.clear()
    if not os.path.exists(Config.TEMPLATE_DIR):
        return
    for f in os.listdir(Config.TEMPLATE_DIR):
        if f.lower().endswith(('.png', '.jpg')):
            img = cv2.imread(os.path.join(Config.TEMPLATE_DIR, f), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                templates_g.append(img)

# -------------------- 核心功能函数 --------------------

def download_image(url):
    """下载单个图片并返回状态"""
    try:
        path_parts = urlparse(url).path.strip('/').split('/')
        if len(path_parts) < 3:
            return "url_error"
        
        dir_path = os.path.join(Config.UNPROCESSED_FOLDER, *path_parts[-3:-1])
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, path_parts[-1])

        if os.path.exists(file_path):
            return "skipped"

        response = requests.get(url, stream=True, timeout=20, verify=True)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return "success"
        else:
            return f"http_error_{response.status_code}"
    except requests.exceptions.SSLError:
        return "ssl_error"
    except Exception:
        return "error"

def check_for_logo_in_roi(hsv, roi_ratio):
    """在指定的ROI内检查是否存在logo，存在则返回True"""
    cfg = Config
    height, width, _ = hsv.shape
    
    y1, y2 = int(height * roi_ratio[0]), int(height * roi_ratio[1])
    x1, x2 = int(width * roi_ratio[2]), int(width * roi_ratio[3])

    red_mask = cv2.bitwise_or(cv2.inRange(hsv, cfg.LOWER_RED1, cfg.UPPER_RED1),
                              cv2.inRange(hsv, cfg.LOWER_RED2, cfg.UPPER_RED2))
    white_mask = cv2.inRange(hsv, cfg.LOWER_WHITE, cfg.UPPER_WHITE)
    
    roi_isolated = np.zeros_like(red_mask)
    roi_isolated[y1:y2, x1:x2] = 255
    red_mask_roi = cv2.bitwise_and(red_mask, roi_isolated)
    white_mask_roi = cv2.bitwise_and(white_mask, roi_isolated)
    
    red_area_in_roi = cv2.countNonZero(red_mask_roi)
    white_area_in_roi = cv2.countNonZero(white_mask_roi)
    if white_area_in_roi == 0 or (red_area_in_roi / white_area_in_roi < cfg.MIN_RED_TO_WHITE_RATIO):
        return False

    logo_mask = cv2.bitwise_or(red_mask_roi, white_mask_roi)
    contours, _ = cv2.findContours(logo_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return False

    max_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(max_contour)
    _, _, bw, bh = cv2.boundingRect(max_contour)
    
    if (area / (height * width) < cfg.MIN_TOTAL_AREA_RATIO or
        (bh > 0 and (bw / bh < cfg.MIN_ASPECT_RATIO or bw / bh > cfg.MAX_ASPECT_RATIO))):
        return False
        
    return True

def identify_and_move_task(source_path):
    """识别图片，如果没有logo则移动它"""
    try:
        img = cv2.imread(source_path)
        if img is None:
            return "load_fail"
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        roi_bl = (0.75, 1.0, 0.0, 0.4)
        roi_tr = (0.0, 0.25, 0.6, 1.0)
        
        logo_found = check_for_logo_in_roi(hsv, roi_bl) or check_for_logo_in_roi(hsv, roi_tr)
            
        if not logo_found:
            dest_path = source_path.replace(Config.UNPROCESSED_FOLDER, Config.PROCESSED_FOLDER, 1)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.move(source_path, dest_path)
            return "no_logo_moved"
        else:
            return "logo_found_stay"
    except Exception:
        return "error_stay"

def match_and_cover(image, threshold):
    """在图片的左下角和右上角区域寻找模板并覆盖"""
    global templates_g
    h, w = image.shape[:2]
    
    rois_to_check = [(0, h // 2, w // 2, h), (w // 2, 0, w, h // 2)]

    for x1, y1, x2, y2 in rois_to_check:
        roi = image[y1:y2, x1:x2]
        if roi.shape[0] == 0 or roi.shape[1] == 0: continue
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        for template in templates_g:
            th, tw = template.shape
            for scale in [1.2, 1.0, 0.8]:
                w_s, h_s = int(tw * scale), int(th * scale)
                if h_s > gray_roi.shape[0] or w_s > gray_roi.shape[1]: continue
                
                res = cv2.matchTemplate(gray_roi, cv2.resize(template, (w_s, h_s)), cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)

                if max_val >= threshold:
                    top_left = (max_loc[0] + x1, max_loc[1] + y1)
                    bottom_right = (top_left[0] + w_s, top_left[1] + h_s)
                    cv2.rectangle(image, top_left, bottom_right, (0, 128, 0), -1)
                    return image, True

    return image, False

def process_template_task(args):
    """处理单张图片的模板匹配任务"""
    source_path, threshold = args
    processed_path = source_path.replace(Config.UNPROCESSED_FOLDER, Config.PROCESSED_FOLDER, 1)
    try:
        image = cv2.imread(source_path)
        if image is None: return "load_fail"
        processed_image, matched = match_and_cover(image, threshold)
        if matched:
            os.makedirs(os.path.dirname(processed_path), exist_ok=True)
            cv2.imwrite(processed_path, processed_image)
            os.remove(source_path)
            return "processed"
        else:
            return "unmatched"
    except Exception:
        return "error"

# --- 状态管理 ---
def save_state():
    """保存 session state 到文件"""
    state = {
        'current_step': st.session_state.get('current_step', 1),
        'match_threshold': st.session_state.get('match_threshold', 0.8)
    }
    with open(Config.STATE_FILE_PATH, 'w') as f:
        json.dump(state, f)

def load_state():
    """从文件加载 session state"""
    if os.path.exists(Config.STATE_FILE_PATH):
        try:
            with open(Config.STATE_FILE_PATH, 'r') as f:
                state = json.load(f)
                st.session_state.current_step = state.get('current_step', 1)
                st.session_state.match_threshold = state.get('match_threshold', 0.8)
        except (json.JSONDecodeError, FileNotFoundError):
            initialize_state()
    else:
        initialize_state()

def initialize_state(force=False):
    """初始化或重置 session_state"""
    if force or 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if force or 'match_threshold' not in st.session_state:
        st.session_state.match_threshold = 0.8
    if force:
        save_state()

# --- UI 渲染函数 ---

def render_step_1():
    """渲染步骤1的UI：上传与下载"""
    st.subheader("步骤 1: 上传 `qc.txt` 并下载图片")
    uploaded_file = st.file_uploader("请上传包含URL列表的 qc.txt 文件:", type=['txt'])
    
    if uploaded_file is not None:
        with open(Config.URL_FILE_PATH, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"'qc.txt' 已成功上传。")
        
        if st.button("🚀 开始下载", key="start_download"):
            with st.spinner("准备下载..."):
                with open(Config.URL_FILE_PATH, 'r') as f:
                    urls = [line.strip() for line in f if line.strip()]
                for folder in [Config.PROCESSED_FOLDER, Config.UNPROCESSED_FOLDER]:
                    if os.path.exists(folder): shutil.rmtree(folder)
                    os.makedirs(folder)

            progress_bar = st.progress(0)
            status_text = st.empty()
            results_counter = Counter()
            
            with ThreadPoolExecutor(max_workers=Config.NUM_WORKERS * 2) as executor:
                futures = {executor.submit(download_image, url) for url in urls}
                for i, future in enumerate(as_completed(futures)):
                    result = future.result()
                    results_counter[result] += 1
                    
                    progress = (i + 1) / len(urls)
                    progress_bar.progress(progress)
                    status_text.info(f"""
                    **下载进度: {i+1}/{len(urls)}**
                    - ✅ **成功**: {results_counter['success']}
                    - ⏩ **跳过**: {results_counter['skipped']}
                    - ❌ **失败 (HTTP/网络)**: {sum(v for k, v in results_counter.items() if k.startswith('http_error') or k == 'error')}
                    - 🔒 **失败 (SSL证书问题)**: {results_counter['ssl_error']}
                    """)
            
            st.success("下载任务完成！")
            st.markdown("---")
            st.subheader("下载报告总结")
            st.write(f"✅ **成功下载:** {results_counter['success']} 张")
            st.write(f"⏩ **跳过 (文件已存在):** {results_counter['skipped']} 张")
            st.write(f"❌ **下载失败 (HTTP或网络错误):** {sum(v for k, v in results_counter.items() if k.startswith('http_error') or k == 'error')} 张")
            if results_counter['ssl_error'] > 0:
                st.error(f"🔒 **SSL证书错误:** {results_counter['ssl_error']} 张. 这通常由公司网络防火墙或代理引起。")
            
            st.session_state.current_step = 2
            save_state()
            st.rerun()

def render_step_2():
    """渲染步骤2的UI：自动筛选"""
    st.subheader("步骤 2: 自动筛选无Logo图片")
    st.write("此步骤将使用颜色识别算法，将明显没有logo的图片从`unprocessed_images`移动到`processed_images`。")
    if st.button("🤖 开始自动筛选", key="start_filter"):
        tasks = [os.path.join(dp, f) for dp, _, fn in os.walk(Config.UNPROCESSED_FOLDER) for f in fn if f.lower().endswith(('.jpg','.png'))]
        if not tasks:
            st.warning("'unprocessed_images' 文件夹为空，无需筛选。")
            st.session_state.current_step = 3
            save_state()
            st.rerun()
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_counter = Counter()

            with ProcessPoolExecutor(max_workers=Config.NUM_WORKERS) as executor:
                futures = {executor.submit(identify_and_move_task, task) for task in tasks}
                for i, future in enumerate(as_completed(futures)):
                    result = future.result()
                    results_counter[result] += 1
                    progress = (i + 1) / len(tasks)
                    progress_bar.progress(progress)
                    status_text.info(f"""
                    **筛选进度: {i+1}/{len(tasks)}**
                    - ➡️ **已移动 (无Logo)**: {results_counter['no_logo_moved']}
                    - ✅ **已保留 (有Logo)**: {results_counter['logo_found_stay']}
                    - ❌ **处理失败**: {results_counter['error_stay'] + results_counter['load_fail']}
                    """)

            st.success("自动筛选完成！")
            st.markdown("---")
            st.subheader("筛选报告总结")
            st.write(f"➡️ **移动到 'processed' 的图片:** {results_counter['no_logo_moved']} 张")
            st.write(f"✅ **保留在 'unprocessed' 的图片:** {results_counter['logo_found_stay']} 张")
            st.write(f"❌ **处理失败:** {results_counter['error_stay'] + results_counter['load_fail']} 张")

            st.session_state.current_step = 3
            save_state()
            st.rerun()

def render_step_3():
    """渲染步骤3的UI：模板匹配"""
    st.subheader("步骤 3: 使用模板迭代处理")

    st.markdown("**模板管理**")
    template_files = [f for f in os.listdir(Config.TEMPLATE_DIR) if f.lower().endswith(('.png','.jpg'))]
    st.info(f"当前模板: {', '.join(template_files) if template_files else '无'}")

    uploaded_templates = st.file_uploader("上传新模板:", type=['png', 'jpg'], accept_multiple_files=True, key="template_uploader")
    if uploaded_templates:
        for uploaded_template in uploaded_templates:
            with open(os.path.join(Config.TEMPLATE_DIR, uploaded_template.name), "wb") as f:
                f.write(uploaded_template.getbuffer())
        st.success("模板上传成功！请在下面开始处理。")
        # 移除了 st.rerun() 以确保UI稳定性

    if template_files:
        col1, col2 = st.columns([3, 1])
        with col1:
            template_to_delete = st.selectbox("或选择要删除的模板:", [""] + template_files, key="template_selector")
        with col2:
            st.write("") # 占位
            st.write("") # 占位
            if template_to_delete and st.button("删除所选", key="delete_template"):
                os.remove(os.path.join(Config.TEMPLATE_DIR, template_to_delete))
                st.warning(f"模板 '{template_to_delete}' 已删除。")
                st.rerun()

    st.markdown("**参数调整**")
    st.session_state.match_threshold = st.slider(
        "设置匹配阈值:",
        min_value=0.5, max_value=0.95,
        value= st.session_state.get('match_threshold', 0.8),
        step=0.01,
        on_change=save_state # 拖动时自动保存
    )

    st.markdown("---")

    remaining_files_count = sum([len(files) for r, d, files in os.walk(Config.UNPROCESSED_FOLDER)])
    st.write(f"当前 `unprocessed_images` 文件夹中还有 **{remaining_files_count}** 张图片待处理。")

    # 按钮的 disabled 状态现在依赖于重新计算的 template_files 列表
    current_templates = [f for f in os.listdir(Config.TEMPLATE_DIR) if f.lower().endswith(('.png','.jpg'))]
    disable_button = (remaining_files_count == 0 or not current_templates)

    if st.button("🔥 使用当前模板和阈值开始处理", key="start_processing", disabled=disable_button):
        tasks = [os.path.join(dp, f) for dp,_,fn in os.walk(Config.UNPROCESSED_FOLDER) for f in fn if f.lower().endswith(('.jpg','.png'))]
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_counter = Counter()

        with ProcessPoolExecutor(max_workers=Config.NUM_WORKERS, initializer=init_template_worker) as executor:
            args = [(task, st.session_state.match_threshold) for task in tasks]
            futures = {executor.submit(process_template_task, arg) for arg in args}
            for i, future in enumerate(as_completed(futures)):
                result = future.result()
                results_counter[result] += 1
                progress_bar.progress((i + 1) / len(tasks))
                status_text.info(f"""
                **处理进度: {i+1}/{len(tasks)}**
                - ✅ **已处理覆盖**: {results_counter['processed']}
                - ⏩ **未匹配跳过**: {results_counter['unmatched']}
                - ❌ **处理失败**: {results_counter['error'] + results_counter['load_fail']}
                """)
        status_text.success("本轮处理完成！")
        st.rerun()

def render_reset_ui():
    """渲染重置按钮的UI"""
    st.sidebar.markdown("---")
    st.sidebar.subheader("重置操作")
    if st.sidebar.button("🗑️ 全部重置并从头开始", type="primary"):
        # 删除状态文件
        if os.path.exists(Config.STATE_FILE_PATH):
            os.remove(Config.STATE_FILE_PATH)
        # 清理文件夹
        for folder in [Config.PROCESSED_FOLDER, Config.UNPROCESSED_FOLDER]:
            if os.path.exists(folder):
                shutil.rmtree(folder)
        # 清理session state并重新运行
        initialize_state(force=True)
        st.success("所有进度和文件已重置！")
        time.sleep(1) # 短暂显示消息
        st.rerun()

# --- 主入口函数 ---
def run():
    """这是被 app.py 调用的主入口函数，用于构建Streamlit界面。"""
    # 确保关键目录存在
    for dir_path in [Config.INPUT_DIR, Config.OUTPUT_DIR, Config.TEMPLATE_DIR, Config.PROCESSED_FOLDER, Config.UNPROCESSED_FOLDER]:
        os.makedirs(dir_path, exist_ok=True)
        
    # 加载或初始化状态
    if 'current_step' not in st.session_state:
        load_state()

    st.header("🖼️ 图片批量处理器")
    st.info("本工具将引导您完成从下载到处理的全过程。刷新页面可恢复进度。")

    # 渲染重置按钮
    render_reset_ui()

    # 根据当前步骤渲染对应的UI
    if st.session_state.current_step == 1:
        render_step_1()
    elif st.session_state.current_step == 2:
        render_step_2()
    elif st.session_state.current_step == 3:
        render_step_3()