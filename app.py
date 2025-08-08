# 文件路径: MyDataWorkbench/app.py

import streamlit as st
import os
import importlib

# --- 1. 页面基础配置 ---
st.set_page_config(
    layout="wide", 
    page_title="Allen工作台",
    page_icon="✅"
)

# --- 2. 注入CSS ---
# ... (这部分代码保持不变) ...
st.markdown("""
<style>
    div[data-testid="stNumberInput"] button {
        display: none;
    }
    [data-testid="stSidebar"] .stButton button {
        text-align: left;
        padding-left: 20px;
    }
</style>
""", unsafe_allow_html=True)


# --- 3. 动态工具发现与加载 ---
def get_tools():
    """扫描 'tools' 文件夹，找到所有可用的工具。"""
    tools_dir = "tools"
    if not os.path.exists(tools_dir):
        return []
    return [d for d in os.listdir(tools_dir) if os.path.isdir(os.path.join(tools_dir, d)) and os.path.exists(os.path.join(tools_dir, d, '__init__.py'))]

# --- 4. 使用 Session State 管理状态 ---
available_tools = get_tools()

if 'selected_tool' not in st.session_state:
    st.session_state.selected_tool = available_tools[0] if available_tools else None

# ★★★★★ 新增：在这里定义您留下的模型列表 ★★★★★
available_models = [
    "mulebuy-optimizer",
    "llama3.1:latest",  # 默认主力模型
    "qwen3:8b",
    "gemma3:4b",
    "gpt-oss:20b"
]

if 'selected_model' not in st.session_state:
    st.session_state.selected_model = available_models[0] # 默认选择第一个

# --- 应用主标题 ---
st.title("✅ Allen工作台")

# --- 5. 侧边栏导航 ---
st.sidebar.title("工具箱")

# ★★★★★ 新增：在这里添加模型选择的下拉菜单 ★★★★★
st.session_state.selected_model = st.sidebar.selectbox(
    "🧠 请选择要调用的AI模型:",
    options=available_models,
    index=available_models.index(st.session_state.selected_model), # 保持上次的选择
    help="您的选择会立即生效，并应用于所有AI工具。"
)
st.sidebar.info(f"当前激活: **{st.session_state.selected_model}**")
st.sidebar.markdown("---")


# 定义工具的显示名称映射
tool_display_names = {
    "MulebuyPics": "Mulebuy图片",
    "Affiliate_data": "联盟数据",
    "Translator": "文案优化"
}

for tool_name in available_tools:
    # 获取显示名称，如果找不到映射，则使用原始文件夹名
    display_name = tool_display_names.get(tool_name, tool_name)
    if st.sidebar.button(display_name, use_container_width=True):
        st.session_state.selected_tool = tool_name
        st.rerun()
st.sidebar.markdown("---")

# --- 6. 主界面 ---
selected_tool_name = st.session_state.selected_tool

if not selected_tool_name:
    st.error("在 'tools' 文件夹中未发现任何可用工具。")
else:
    display_name = tool_display_names.get(selected_tool_name, selected_tool_name)
    st.caption(f"当前工具: {display_name}")
    st.markdown("---")
    
    # 动态加载并执行选中的工具
    try:
        tool_module = importlib.import_module(f"tools.{selected_tool_name}.tool")
        tool_module.run()
    except ImportError as e:
        st.error(f"加载工具 '{selected_tool_name}' 失败: {e}. 请确保该文件夹下有 'tool.py' 文件。")
    except AttributeError:
        st.error(f"工具 '{selected_tool_name}' 的 'tool.py' 文件中缺少一个名为 run() 的入口函数。")