# 文件路径: MyDataWorkbench/tools/网红数据报告/tool.py

import streamlit as st
import pandas as pd
from datetime import datetime
import os

@st.cache_data
def _load_data_from_disk(data_path):
    """一个私有的数据加载函数。"""
    try:
        users_path = os.path.join(data_path, 'wp_users_affilate_tmp.csv')
        orders_path = os.path.join(data_path, 'wp_erp_order_tmp.csv')
        packages_path = os.path.join(data_path, 'wp_erp_packeage_tmp.csv')
        return pd.read_csv(users_path, encoding='gb18030'), pd.read_csv(orders_path, encoding='gb18030'), pd.read_csv(packages_path, encoding='gb18030')
    except FileNotFoundError:
        return None, None, None

def _calculate_metrics(users_df, orders_df, packages_df, start_date, end_date):
    """私有的核心计算逻辑。"""
    users_reg = users_df[(users_df['reg_time'] >= start_date) & (users_df['reg_time'] <= end_date)]
    users_verified = users_df[(users_df['verified_time'] >= start_date) & (users_df['verified_time'] <= end_date)]
    users_active = users_df[(users_df['activate_time'] >= start_date) & (users_df['activate_time'] <= end_date)]
    orders = orders_df[(orders_df['create_time'] >= start_date) & (orders_df['create_time'] <= end_date)]
    packages = packages_df[(packages_df['create_time'] >= start_date) & (packages_df['create_time'] <= end_date)]
    
    metrics = {
        "注册用户数": len(users_reg), "激活用户数": len(users_verified), "活跃人数": len(users_active),
        "下单人数": orders['uid'].nunique(), "下单数量": len(orders), "下单总金额 (CNY)": orders['total_cny'].sum(),
        "提包人数": packages['uid'].nunique(), "提包数量": len(packages), "提包总金额 (CNY)": packages['total_cny'].sum(),
    }
    metrics["收单总金额 (CNY)"] = metrics["下单总金额 (CNY)"] + metrics["提包总金额 (CNY)"]
    return metrics

def run():
    """本工具的唯一入口函数，包含了所有的UI元素和业务逻辑。"""
    
    tool_dir = os.path.dirname(__file__)
    data_path = os.path.join(tool_dir, "data")
    
    df_users_full, df_orders_full, df_packages_full = _load_data_from_disk(data_path)

    if df_users_full is None:
        st.error(f"错误：未在 'tools/网红数据报告/data/' 文件夹中找到必需的CSV文件。")
        return

    st.sidebar.success("数据源已加载！")
    if st.sidebar.button("刷新数据源"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("参数设置")
    affiliate_id = st.sidebar.number_input("输入网红ID:", min_value=1, step=1, format="%d")
    today = datetime.now()
    start_date = st.sidebar.date_input("选择开始日期", today)
    end_date = st.sidebar.date_input("选择结束日期", today)
    
    if st.sidebar.button("🚀 生成分析报告", type="primary", use_container_width=True):
        with st.spinner('正在分析数据...'):
            df_users = df_users_full[df_users_full['affilate'] == affiliate_id].copy()
            df_orders = df_orders_full[df_orders_full['affilate'] == affiliate_id].copy()
            df_packages = df_packages_full[df_packages_full['affilate'] == affiliate_id].copy()

            if df_users.empty and df_orders.empty and df_packages.empty:
                st.warning(f"在数据源中找不到网红ID {affiliate_id} 的任何记录。")
            else:
                for col in ['reg_time', 'verified_time', 'activate_time']: 
                    df_users[col] = pd.to_datetime(df_users[col], errors='coerce')
                for col in ['create_time']:
                    df_orders[col] = pd.to_datetime(df_orders[col], errors='coerce')
                    df_packages[col] = pd.to_datetime(df_packages[col], errors='coerce')
                
                start_datetime = pd.to_datetime(f"{start_date} 00:00:00")
                end_datetime = pd.to_datetime(f"{end_date} 23:59:59")
                
                final_metrics = _calculate_metrics(df_users, df_orders, df_packages, start_datetime, end_datetime)

                title = f"网红 {int(affiliate_id)} 数据报告 ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
                st.markdown(f"##### {title}")
                display_order = ['注册用户数', '激活用户数', '活跃人数', '下单人数', '下单数量', '下单总金额 (CNY)', '提包人数', '提包数量', '提包总金额 (CNY)', '收单总金额 (CNY)']
                summary_list = [f"**{key.replace(' (CNY)', '')}:** {final_metrics.get(key, 0):,}" if isinstance(final_metrics.get(key, 0), int) else f"**{key.replace(' (CNY)', '')}:** {final_metrics.get(key, 0):,.2f}" for key in display_order]
                report_col1, report_col2 = st.columns(2)
                with report_col1:
                    for item in summary_list[::2]: st.markdown(item)
                with report_col2:
                    for item in summary_list[1::2]: st.markdown(item)
                st.success("报告生成完毕！")
    else:
        st.info("请在左侧面板设置参数后点击按钮生成报告。")