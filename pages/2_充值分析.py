import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import importlib.util
from datetime import datetime
import plotly.express as px

# 设置页面配置
st.set_page_config(
    page_title="充值分析",
    page_icon="💰",
    layout="wide"
)

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# 导入配置
from streamlit_analysis.config import capture_output

# 动态导入accumulate_recharge模块
recharge_analysis_path = project_root / "01_Script" / "fun" / "accumulate_recharge.py"
spec = importlib.util.spec_from_file_location("accumulate_recharge", recharge_analysis_path)
accumulate_recharge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accumulate_recharge)

def load_latest_recharge():
    """加载最新的充值分析结果"""
    try:
        output_dir = project_root / "03_Data" / "merged_data"
        files = list(output_dir.glob("agent_recharge_analysis_*.csv"))
        if not files:
            return None
            
        latest_file = max(files, key=lambda x: x.stat().st_mtime)
        df = pd.read_csv(latest_file)
        return df, latest_file.name
    except Exception as e:
        st.error(f"加载数据失败: {str(e)}")
        return None, None

def plot_recharge_trend(df):
    """绘制充值趋势图"""
    df['注册日期'] = pd.to_datetime(df['注册日期'])
    daily_stats = df.groupby('注册日期').agg({
        '累积充值_3天': 'sum',
        '累积充值_7天': 'sum',
        '累积充值_15天': 'sum',
        '累积充值_30天': 'sum',
        '注册人数': 'sum'
    }).reset_index()
    
    # 计算人均充值
    for period in [3, 7, 15, 30]:
        daily_stats[f'{period}天人均充值'] = daily_stats[f'累积充值_{period}天'] / daily_stats['注册人数']
    
    # 创建趋势图
    fig = px.line(
        daily_stats,
        x='注册日期',
        y=['3天人均充值', '7天人均充值', '15天人均充值', '30天人均充值'],
        title='各时间段人均充值趋势',
        labels={'value': '人均充值金额', 'variable': '时间段'}
    )
    return fig

def main():
    st.title("💰 充值分析")
    
    # 创建日志容器
    log_container = st.empty()
    
    # 添加刷新按钮
    if st.button("🔄 刷新数据"):
        with st.spinner("正在更新数据..."):
            try:
                # 创建进度显示区域
                progress_container = st.empty()
                progress_container.info("开始更新数据...")
                
                # 捕获并显示日志
                with capture_output(log_container):
                    accumulate_recharge.main()
                    
                progress_container.success("数据更新成功！")
            except Exception as e:
                progress_container.error(f"数据更新失败: {str(e)}")
                return
    
    # 加载最新数据
    result = load_latest_recharge()
    if result is None:
        st.warning("未找到分析数据，请点击刷新按钮更新数据。")
        return
        
    df, filename = result
    
    # 显示最后更新时间
    st.info(f"最后更新时间: {filename.split('_')[3].split('.')[0]}")
    
    # 数据概览
    st.header("数据概览")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总注册人数", df["注册人数"].sum())
    with col2:
        total_recharge = df["累积充值_total"].sum()
        st.metric("总充值金额", f"¥{total_recharge:,.2f}")
    with col3:
        avg_recharge = total_recharge / df["注册人数"].sum() if df["注册人数"].sum() > 0 else 0
        st.metric("整体人均充值", f"¥{avg_recharge:.2f}")
    with col4:
        paying_users = df[df["付费用户数_30天"] > 0]["付费用户数_30天"].sum()
        st.metric("30天付费用户数", paying_users)
    
    # 充值趋势分析
    st.header("充值趋势分析")
    trend_fig = plot_recharge_trend(df)
    st.plotly_chart(trend_fig, use_container_width=True)
    
    # 代理商筛选
    st.header("代理商详情")
    agent_filter = st.text_input("🔍 搜索代理商", "")
    if agent_filter:
        df = df[df["agent_username"].str.contains(agent_filter, case=False, na=False)]
    
    # 排序选项
    sort_col = st.selectbox(
        "排序依据",
        ["注册人数", "累积充值_total", "付费用户数_30天", "30天ARPU", "30天ARPPU"],
        index=0
    )
    df = df.sort_values(sort_col, ascending=False)
    
    # 显示详细数据
    st.dataframe(
        df,
        column_config={
            "agent_username": "代理商名称",
            "注册人数": st.column_config.NumberColumn(format="%d"),
            "累积充值_total": st.column_config.NumberColumn(format="¥%.2f"),
            "30天ARPU": st.column_config.NumberColumn(format="¥%.2f"),
            "30天ARPPU": st.column_config.NumberColumn(format="¥%.2f"),
            "付费用户数_30天": st.column_config.NumberColumn(format="%d")
        },
        hide_index=True
    )
    
    # 下载数据
    st.download_button(
        "📥 下载数据",
        df.to_csv(index=False).encode("utf-8"),
        "recharge_analysis.csv",
        "text/csv",
        key='download-csv'
    )

if __name__ == "__main__":
    main() 