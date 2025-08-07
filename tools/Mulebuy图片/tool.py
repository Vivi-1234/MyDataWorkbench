# 文件路径: MyDataWorkbench/tools/Mulebuy图片/tool.py

import streamlit as st
import os
import shutil

def run():
    """这是“Mulebuy图片”工具的最终版入口函数。"""

    st.subheader("Mulebuy 视觉资产管理器 (DAM)")
    
    # --- 1. 初始化路径和分类 ---
    tool_dir = os.path.dirname(__file__)
    data_path = os.path.join(tool_dir, "data")
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    
    try:
        categories = sorted([d for d in os.listdir(data_path) if os.path.isdir(os.path.join(data_path, d))])
        supported_formats = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
        uncategorized_images = sorted([f for f in os.listdir(data_path) if os.path.isfile(os.path.join(data_path, f)) and f.lower().endswith(supported_formats)])
    except Exception as e:
        st.error(f"扫描文件夹时出错: {e}")
        return

    # --- 2. 侧边栏：管理中心 ---
    with st.sidebar:
        st.title("管理中心")
        with st.expander("📁 上传新图片", expanded=True):
            upload_options = ["未分类"] + categories
            upload_target = st.selectbox("选择上传目标:", upload_options, key="upload_select")
            uploaded_files = st.file_uploader(
                label=f"上传到 '{upload_target}' (支持拖拽)",
                accept_multiple_files=True,
                key="native_uploader"
            )
            if uploaded_files:
                save_path = data_path if upload_target == "未分类" else os.path.join(data_path, upload_target)
                for uploaded_file in uploaded_files:
                    with open(os.path.join(save_path, uploaded_file.name), "wb") as f:
                        f.write(uploaded_file.getbuffer())
                st.success(f"成功上传 {len(uploaded_files)} 个文件到 '{upload_target}'！")
                st.rerun()
        
        with st.expander("🗂️ 分类管理", expanded=False):
            st.subheader("创建新分类")
            new_category_name = st.text_input("输入新分类名称:", key="new_cat_name")
            if st.button("创建"):
                if new_category_name and new_category_name not in categories:
                    os.makedirs(os.path.join(data_path, new_category_name))
                    st.success(f"分类 '{new_category_name}' 创建成功！")
                    st.rerun()
                else:
                    st.warning("请输入分类名称或该分类已存在。")
            st.markdown("---")
            st.subheader("重命名/删除分类")
            if not categories:
                st.info("当前没有可管理的分类。")
            else:
                selected_cat_to_manage = st.selectbox("选择要管理的分类:", categories, key="manage_select")
                new_name = st.text_input("输入新名称:", value=selected_cat_to_manage, key=f"rename_{selected_cat_to_manage}")
                if st.button("重命名"):
                    if new_name and new_name != selected_cat_to_manage:
                        os.rename(os.path.join(data_path, selected_cat_to_manage), os.path.join(data_path, new_name))
                        st.success(f"已将 '{selected_cat_to_manage}' 重命名为 '{new_name}'")
                        st.rerun()
                if st.button("删除分类", type="primary"):
                    cat_path = os.path.join(data_path, selected_cat_to_manage)
                    if not os.listdir(cat_path):
                        shutil.rmtree(cat_path)
                        st.success(f"分类 '{selected_cat_to_manage}' 已被删除。")
                        st.rerun()
                    else:
                        st.error("无法删除：该分类下仍有图片，请先将图片移出或删除。")

    # --- 3. 主界面：图片画廊 ---
    tab_titles = []
    if uncategorized_images:
        tab_titles.append(f"未分类 ({len(uncategorized_images)})")
    if categories:
        tab_titles.extend(categories)

    if not tab_titles:
        st.info("您的图片库还是空的。")
        st.stop()

    tab_list = st.tabs(tab_titles)
    tab_index = 0

    if uncategorized_images:
        with tab_list[tab_index]:
            render_image_gallery(data_path, uncategorized_images, "未分类", categories, data_path)
        tab_index += 1
    
    for category in categories:
        with tab_list[tab_index]:
            category_path = os.path.join(data_path, category)
            image_files = sorted([f for f in os.listdir(category_path) if f.lower().endswith(supported_formats)])
            render_image_gallery(category_path, image_files, category, categories, data_path)
        tab_index += 1

def render_image_gallery(current_path, image_files, current_category, all_categories, data_path):
    """渲染图片画廊和批量操作UI。"""
    
    if not image_files:
        st.info("这个分类下还没有图片。")
        return

    if f"select_all_{current_category}" not in st.session_state:
        st.session_state[f"select_all_{current_category}"] = False
    
    selected_images = []
    
    # --- 关键改动：将“全选”和批量操作栏都放在图片画廊的上方 ---
    header_cols = st.columns([1, 4]) # 定义列的比例
    with header_cols[0]:
        st.checkbox("全选", key=f"select_all_{current_category}")

    # 渲染图片画廊，并收集被选中的图片
    num_columns = 4
    cols = st.columns(num_columns)
    
    for index, image_file in enumerate(image_files):
        with cols[index % num_columns]:
            image_path = os.path.join(current_path, image_file)
            
            with st.container(border=True):
                is_selected = st.checkbox("", key=f"select_{current_category}_{image_file}", value=st.session_state[f"select_all_{current_category}"])
                if is_selected:
                    selected_images.append(image_path)
                
                st.image(image_path, use_container_width=True)

    # 只有当有图片被选中时，才在 header_cols 的第二列中显示批量操作按钮
    with header_cols[1]:
        if selected_images:
            action_cols = st.columns(3) # 删除[1], 移动[2], 执行[1]
            
            with action_cols[0]:
                @st.dialog("批量删除确认")
                def confirm_bulk_delete(images_to_delete):
                    st.write(f"确定要永久删除选中的 {len(images_to_delete)} 张图片吗？")
                    st.write("此操作无法撤销。")
                    if st.button("确认删除", type="primary"):
                        for img_path in images_to_delete:
                            os.remove(img_path)
                        st.rerun()
                
                if st.button(f"🗑️ 删除 ({len(selected_images)})", use_container_width=True, type="primary"):
                    confirm_bulk_delete(selected_images)

            with action_cols[1]:
                move_options = ["--移动到--"] + [cat for cat in all_categories if cat != current_category]
                if current_category != "未分类":
                    move_options.insert(1, "未分类")
                selected_target = st.selectbox("移动到:", options=move_options, key=f"bulk_move_{current_category}", label_visibility="collapsed")

            with action_cols[2]:
                 if st.button("执行移动", use_container_width=True):
                    if selected_target != "--移动到--":
                        target_path = data_path if selected_target == "未分类" else os.path.join(data_path, selected_target)
                        for img_path in selected_images:
                            shutil.move(img_path, os.path.join(target_path, os.path.basename(img_path)))
                        st.success(f"成功移动 {len(selected_images)} 张图片到 '{selected_target}'")
                        st.rerun()