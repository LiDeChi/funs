import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import importlib.util
from datetime import datetime

# 设置页面配置
st.set_page_config(
    page_title="代理商分析",
    page_icon="📈",
    layout="wide"
)

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# 导入配置
from streamlit_analysis.config import capture_output

# 动态导入agent_analysis模块
agent_analysis_path = project_root / "01_Script" / "fun" / "agent_analysis.py"
spec = importlib.util.spec_from_file_location("agent_analysis", agent_analysis_path)
agent_analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_analysis)

def load_latest_analysis():
    """加载最新的分析结果"""
    try:
        output_dir = project_root / "03_Data" / "merged_data"
        files = list(output_dir.glob("agent_analysis_*.csv"))
        if not files:
            return None
            
        latest_file = max(files, key=lambda x: x.stat().st_mtime)
        df = pd.read_csv(latest_file)
        return df, latest_file.name
    except Exception as e:
        st.error(f"加载数据失败: {str(e)}")
        return None, None

def main():
    st.title("📈 代理商分析")
    
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
                    agent_analysis.main()
                    
                progress_container.success("数据更新成功！")
            except Exception as e:
                progress_container.error(f"数据更新失败: {str(e)}")
                return
    
    # 加载最新数据
    result = load_latest_analysis()
    if result is None:
        st.warning("未找到分析数据，请点击刷新按钮更新数据。")
        return
        
    df, filename = result
    
    # 显示最后更新时间
    st.info(f"最后更新时间: {filename.split('_')[2].split('.')[0]}")
    
    # 数据概览
    st.header("数据概览")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总代理数", len(df))
    with col2:
        st.metric("总用户数", df["总用户数"].sum())
    with col3:
        st.metric("总充值金额", f"¥{df['总充值金额'].sum():,.2f}")
    
    # 代理商筛选
    st.header("代理商详情")
    agent_filter = st.text_input("🔍 搜索代理商", "")
    if agent_filter:
        df = df[df["username"].str.contains(agent_filter, case=False, na=False)]
    
    # 排序选项
    sort_col = st.selectbox(
        "排序依据",
        ["总用户数", "总充值金额", "付费用户数", "游戏玩家数", "活跃天数"],
        index=0
    )
    df = df.sort_values(sort_col, ascending=False)
    
    # 显示详细数据
    st.dataframe(
        df,
        column_config={
            "username": "代理商名称",
            "总用户数": st.column_config.NumberColumn(format="%d"),
            "总充值金额": st.column_config.NumberColumn(format="¥%.2f"),
            "付费率": st.column_config.TextColumn(),
            "人均充值": st.column_config.NumberColumn(format="¥%.2f"),
            "活跃天数": st.column_config.NumberColumn(format="%d")
        },
        hide_index=True
    )
    
    # 下载数据
    st.download_button(
        "📥 下载数据",
        df.to_csv(index=False).encode("utf-8"),
        "agent_analysis.csv",
        "text/csv",
        key='download-csv'
    )

if __name__ == "__main__":
    main() 