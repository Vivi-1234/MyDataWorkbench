# 文件路径: MyDataWorkbench/tools/文案翻译/tool.py

import streamlit as st
import json
import pandas as pd
import io
import os
from zipfile import ZipFile
import requests

# ----------------- 工具的私有函数 -----------------

@st.cache_data
def _load_base_files_from_disk(base_path):
    """从本地加载基准JSON文件。"""
    if not os.path.exists(base_path):
        return None, f"错误：基准文件夹 '{base_path}' 不存在。"
    
    base_files_content = {}
    try:
        for filename in os.listdir(base_path):
            if filename.endswith('.json'):
                filepath = os.path.join(base_path, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    base_files_content[filename] = json.load(f)
        if not base_files_content:
            return None, "错误：在基准文件夹中没有找到任何.json文件。"
        return base_files_content, None
    except Exception as e:
        return None, f"读取基准文件时出错: {e}"

def _ai_assisted_translation(model_to_use, page_name, base_text, original_translation, target_lang):
    """
    调用本地Ollama API，使用精简的提示词，并对结果进行强制格式化清洗。
    """
    # ★★★ 最终精简版提示词 ★★★
    if original_translation is None or original_translation == "【缺失】":
        prompt = f"""
TARGET LANGUAGE: {target_lang}
PAGE CONTEXT: {page_name}
SOURCE (English): "{base_text}"
"""
    else:
        prompt = f"""
TARGET LANGUAGE: {target_lang}
PAGE CONTEXT: {page_name}
SOURCE (English): "{base_text}"
CURRENT ({target_lang}): "{original_translation}"
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model_to_use, 
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        ai_result = response.json()['message']['content']

    except requests.exceptions.RequestException as e:
        st.error(f"调用本地AI失败: {e}。请确认Ollama服务正在后台运行，并且模型 '{model_to_use}' 已经下载。")
        ai_result = "【AI调用失败】"

    print(f"--- PROMPT SENT TO AI ({model_to_use}) ---\n{prompt}\n--- AI RESULT (raw) ---\n{ai_result}\n-----------------------")
    
    # ★★★ 保留最关键的、100%可靠的代码层格式清洗 ★★★
    cleaned_result = ai_result.strip()
    if len(cleaned_result) > 1 and cleaned_result.startswith('"') and cleaned_result.endswith('"'):
        cleaned_result = cleaned_result[1:-1]
    if len(cleaned_result) > 1 and cleaned_result.startswith("'") and cleaned_result.endswith("'"):
        cleaned_result = cleaned_result[1:-1]
    
    print(f"--- CLEANED RESULT ---\n{cleaned_result}\n-----------------------")
    return cleaned_result

# ----------------- 工具的公开入口函数 -----------------
def run():
    st.subheader("文案优化工具")
    st.info("本工具以本地EN文件夹为基准，利用AI优化和修正您上传的目标语言文件夹中的文案。")
    
    tool_dir = os.path.dirname(__file__)
    base_data_path = os.path.join(tool_dir, "data", "EN")
    base_files_content, error_msg = _load_base_files_from_disk(base_data_path)
    if error_msg:
        st.error(error_msg)
        return
    st.success(f"已成功从本地加载 {len(base_files_content)} 个基准 (EN) 文件！")
    st.markdown("---")

    st.markdown("#### 1. 请指定您要优化的目标语言")
    target_lang_name = st.text_input(
        "请输入目标语言的全称（例如: German, French, Spanish, Japanese, Chinese）:",
        value="Chinese", 
        help="AI将会把英文文案优化成这个语言。"
    )
    st.markdown("---")


    st.markdown(f"#### 2. 请上传待优化的 **{target_lang_name}** 语言文件夹中的所有文件")
    target_files = st.file_uploader(
        "点击按钮后，进入文件夹并按 Ctrl+A 全选所有文件", 
        type=['json'], 
        key="target_uploader",
        accept_multiple_files=True
    )
    st.markdown("---")

    if target_files:
        target_files_dict = {f.name: f for f in target_files}
        common_filenames = sorted(list(base_files_content.keys() & target_files_dict.keys()))
        
        if not common_filenames:
            st.warning("上传的文件中没有找到与基准文件同名的JSON文件。")
            return

        st.info(f"文件匹配成功！共找到 {len(common_filenames)} 个同名文件可供处理。")
        
        with st.expander("📝 预览与执行面板", expanded=True):
            selected_file = st.selectbox("选择要预览内容的文件:", common_filenames)
            
            if selected_file:
                try:
                    base_data = base_files_content[selected_file]
                    target_files_dict[selected_file].seek(0)
                    target_data = json.load(target_files_dict[selected_file])
                    
                    df = pd.DataFrame([
                        {"Key": key, "基准文案 (EN)": base_value, f"当前文案 ({target_lang_name})": target_data.get(key, "【缺失】")}
                        for key, base_value in base_data.items()
                    ])
                    st.markdown(f"**文件 `'{selected_file}'` 内容预览**")
                    st.dataframe(df, use_container_width=True, height=300)

                except Exception as e:
                    st.error(f"处理文件 '{selected_file}' 时出错: {e}")


            if st.button("🚀 使用AI批量优化所有匹配的文件", use_container_width=True, type="primary"):
                current_model = st.session_state.get("selected_model", "mulebuy-optimizer") 
                st.info(f"正在使用模型: **{current_model}** 进行处理...")

                st.session_state.ai_results = {} 
                
                with st.spinner('正在调用AI进行批量优化...这可能需要一些时间...'):
                    all_optimized_data = {}
                    for filename in common_filenames:
                        base_data = base_files_content[filename]
                        target_files_dict[filename].seek(0)
                        target_data = json.load(target_files_dict[filename])
                        
                        optimized_file_content = {}
                        for key, base_value in base_data.items():
                            original_translation = target_data.get(key)
                            optimized_text = _ai_assisted_translation(current_model, filename, base_value, original_translation, target_lang_name)
                            optimized_file_content[key] = optimized_text
                        
                        all_optimized_data[filename] = optimized_file_content
                
                st.session_state.ai_results = all_optimized_data
                st.success("AI优化完成！请在下方审查结果。")

    if 'ai_results' in st.session_state and st.session_state.ai_results:
        st.markdown("---")
        st.header("🔬 AI优化结果审查")

        results = st.session_state.ai_results
        
        tab_filenames = list(results.keys())
        if tab_filenames:
            tab_list = st.tabs(tab_filenames)
            
            for i, filename in enumerate(tab_filenames):
                with tab_list[i]:
                    st.markdown(f"#### `{filename}` 的优化结果")
                    
                    base_data = base_files_content[filename]
                    target_files_dict[filename].seek(0)
                    target_data = json.load(target_files_dict[filename])
                    optimized_data = results[filename]

                    comparison_df = pd.DataFrame([
                        {
                            "Key": key,
                            "基准 (EN)": base_value,
                            f"原始 ({target_lang_name})": target_data.get(key, "【缺失】"),
                            f"AI优化后 ({target_lang_name})": optimized_data.get(key)
                        } for key, base_value in base_data.items()
                    ])
                    st.dataframe(comparison_df, use_container_width=True)

            zip_buffer = io.BytesIO()
            with ZipFile(zip_buffer, 'w') as zip_file:
                for filename, content_dict in results.items():
                    zip_file.writestr(filename, json.dumps(content_dict, ensure_ascii=False, indent=4))
            
            st.download_button(
                label="📥 确认无误，下载包含所有优化后文件的 .zip 包",
                data=zip_buffer.getvalue(),
                file_name=f"optimized_{target_lang_name}_files.zip",
                mime="application/zip",
                use_container_width=True
            )