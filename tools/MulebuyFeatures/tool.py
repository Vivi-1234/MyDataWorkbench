import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import time

def setup_firebase():
    """Sets up Firebase connection using Streamlit secrets."""
    try:
        if not firebase_admin._apps:
            firebase_creds = st.secrets["firebase"]
            cred = credentials.Certificate(dict(firebase_creds))
            firebase_admin.initialize_app(cred)
        st.session_state['db'] = firestore.client()
        return True
    except Exception as e:
        st.error("Firebase 连接失败，请检查您的 Streamlit Secrets 配置。")
        st.info("请在项目根目录的 .streamlit/secrets.toml 文件中添加您的 Firebase 服务账户凭证。")
        st.code("""
[firebase]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "your-private-key"
client_email = "your-client-email"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-client-x509-cert-url"
        """, language="toml")
        return False

def init_session_state():
    """Initialize session state variables."""
    for key in ['features', 'selected_feature_id', 'edit_mode', 'new_feature', 'sort_option']:
        if key not in st.session_state:
            if key == 'features':
                st.session_state[key] = []
            elif key == 'selected_feature_id':
                st.session_state[key] = None
            elif key in ['edit_mode', 'new_feature']:
                st.session_state[key] = False
            elif key == 'sort_option':
                st.session_state[key] = 'created_at'

@st.cache_data(ttl=60)
def load_features(sort_by='created_at', order='desc'):
    """Load features from Firestore."""
    db = st.session_state['db']
    try:
        direction = firestore.Query.DESCENDING if order == 'desc' else firestore.Query.ASCENDING

        # 为查询添加10秒的超时
        features_ref = db.collection('prototypes').order_by(sort_by, direction=direction).stream(timeout=10)
        features = [{'id': doc.id, **doc.to_dict()} for doc in features_ref]
        
        return features
    except Exception as e:
        st.error(f"从 Firestore 加载数据时出错: {e}")
        st.info("这可能是由于网络问题或防火墙限制。请检查您的网络连接是否能访问 Google Cloud 服务。")
        return []

def render_sidebar():
    """Render the sidebar with feature list and controls."""
    with st.sidebar:
        st.header("Mulebuy 功能原型")
        if st.button("✨ 新增功能原型", use_container_width=True):
            st.session_state.edit_mode = True
            st.session_state.new_feature = True
            st.session_state.selected_feature_id = None
            st.rerun()

        st.selectbox(
            "排序方式",
            options=['created_at', 'title'],
            format_func=lambda x: '按创建时间' if x == 'created_at' else '按标题排序',
            key='sort_option'
        )

        st.write("---")

        order = 'desc' if st.session_state.sort_option == 'created_at' else 'asc'
        st.session_state.features = load_features(sort_by=st.session_state.sort_option, order=order)

        if not st.session_state.features:
            st.info("还没有原型，点击上方按钮新增一个吧！")
        else:
            for feature in st.session_state.features:
                item_label = f"{'📌 ' if feature.get('published') else ''}{feature.get('title', '未命名原型')}"
                col1, col2 = st.columns([0.8, 0.2])
                if col1.button(item_label, key=f"select_{feature['id']}", use_container_width=True):
                    st.session_state.selected_feature_id = feature['id']
                    st.session_state.edit_mode = False
                    st.session_state.new_feature = False
                    st.rerun()
                if col2.button("🗑️", key=f"delete_{feature['id']}", help="删除原型"):
                    delete_feature(feature['id'])
                    st.rerun()

def render_main_panel():
    """Render the main panel for feature preview or editing."""
    if st.session_state.edit_mode or st.session_state.new_feature:
        render_edit_form()
    elif st.session_state.selected_feature_id:
        render_preview()
    else:
        render_placeholder()

def render_placeholder():
    st.markdown("""
    <div style="text-align: center; padding: 5rem; color: #64748b;">
        <svg xmlns="http://www.w3.org/2000/svg" style="width: 64px; height: 64px; color: #cbd5e1;" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" /></svg>
        <h3 style="margin-top: 1rem; font-size: 1.25rem; color: #1e293b;">没有选中的原型</h3>
        <p style="margin-top: 0.25rem;">请从左侧选择一个原型，或新增一个。</p>
    </div>
    """, unsafe_allow_html=True)

def render_preview():
    feature = next((f for f in st.session_state.features if f['id'] == st.session_state.selected_feature_id), None)
    if not feature:
        st.error("无法找到所选功能。")
        st.session_state.selected_feature_id = None
        st.rerun()
        return
    st.header(feature.get('title', '未命名原型'))
    if st.button("✏️ 编辑"):
        st.session_state.edit_mode = True
        st.rerun()
    st.markdown(f"<p style='font-style: italic; color: #64748b;'>{feature.get('description', '无描述')}</p>", unsafe_allow_html=True)
    st.components.v1.html(feature.get('htmlCode', ''), height=600, scrolling=True)

def render_edit_form():
    feature_data = next((f for f in st.session_state.features if f['id'] == st.session_state.selected_feature_id), {}) if not st.session_state.new_feature else {}
    form_title = "✨ 新增功能原型" if st.session_state.new_feature else "✏️ 编辑原型"
    st.header(form_title)

    with st.form(key="feature_form"):
        title = st.text_input("功能标题", value=feature_data.get('title', ''))
        description = st.text_area("功能描述", value=feature_data.get('description', ''))
        html_code = st.text_area("HTML 原型代码", value=feature_data.get('htmlCode', '<!DOCTYPE html>\n<html>\n<head>\n  <title>新原型</title>\n</head>\n<body>\n  <h1>在此处开始构建...</h1>\n</body>\n</html>'), height=300)
        published = st.checkbox("标记为已发布", value=feature_data.get('published', False))

        submitted = st.form_submit_button("💾 保存")
        if submitted:
            save_feature(title, description, html_code, published)

    if st.button("❌ 取消"):
        st.session_state.edit_mode = False
        st.session_state.new_feature = False
        st.rerun()

def save_feature(title, description, html_code, published):
    db = st.session_state['db']
    data = {'title': title, 'description': description, 'htmlCode': html_code, 'published': published}
    try:
        if st.session_state.new_feature:
            data['created_at'] = firestore.SERVER_TIMESTAMP
            _, doc_ref = db.collection('prototypes').add(data)
            st.session_state.selected_feature_id = doc_ref.id
            st.toast("原型创建成功！", icon="🎉")
        else:
            db.collection('prototypes').document(st.session_state.selected_feature_id).update(data)
            st.toast("原型更新成功！", icon="✅")

        st.session_state.edit_mode = False
        st.session_state.new_feature = False
        load_features.clear()
        st.rerun()
    except Exception as e:
        st.error(f"保存失败: {e}")

def delete_feature(feature_id):
    db = st.session_state['db']
    try:
        db.collection('prototypes').document(feature_id).delete()
        st.toast("原型删除成功！", icon="🗑️")
        if st.session_state.selected_feature_id == feature_id:
            st.session_state.selected_feature_id = None
        load_features.clear()
    except Exception as e:
        st.error(f"删除失败: {e}")

def run():
    st.set_page_config(layout="wide", page_title="Mulebuy 功能原型")
    if 'db' not in st.session_state:
        if not setup_firebase():
            st.stop()
    init_session_state()
    render_sidebar()
    render_main_panel()
