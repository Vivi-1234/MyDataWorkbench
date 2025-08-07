# 文件路径: MyDataWorkbench/tools/Firebase数据看板/tool.py

import streamlit as st
import os

def run():
    """
    这是“Firebase数据看板”工具的唯一入口函数。
    它负责读取并展示同目录下的 index.html 文件。
    """

    # st.set_page_config(layout="wide") # 这一行通常在主app.py中设置，这里不需要

    # 获取当前文件(tool.py)所在的目录
    tool_dir = os.path.dirname(__file__)
    # 构建 index.html 的完整路径
    html_path = os.path.join(tool_dir, "index.html")

    try:
        # 读取HTML文件的全部内容
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 使用Streamlit的组件来渲染HTML
        # 我们设置一个合适的高度，并允许滚动
        st.components.v1.html(html_content, height=800, scrolling=True)

    except FileNotFoundError:
        st.error(f"错误：在工具文件夹中没有找到 'index.html' 文件。请确保它与 'tool.py' 放在一起。")
    except Exception as e:
        st.error(f"加载HTML文件时出错: {e}")