import streamlit as st
import pandas as pd
import sys
from pathlib import Path
import importlib.util
from datetime import datetime
import networkx as nx
import plotly.graph_objects as go

# 设置页面配置
st.set_page_config(
    page_title="邀请关系分析",
    page_icon="🤝",
    layout="wide"
)

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 导入配置
from config import capture_output

# 动态导入invite_tree模块
invite_tree_path = project_root / "scripts" / "invite_tree.py"
spec = importlib.util.spec_from_file_location("invite_tree", invite_tree_path)
invite_tree = importlib.util.module_from_spec(spec)
spec.loader.exec_module(invite_tree)

def load_invite_data():
    """加载邀请关系数据"""
    try:
        output_dir = project_root / "data" / "merged_data"
        output_dir.mkdir(parents=True, exist_ok=True)
        files = list(output_dir.glob("invite_tree_*.csv"))
        if not files:
            return None
            
        latest_file = max(files, key=lambda x: x.stat().st_mtime)
        df = pd.read_csv(latest_file)
        return df, latest_file.name
    except Exception as e:
        st.error(f"加载数据失败: {str(e)}")
        return None, None

def create_invite_network(df, max_depth=3):
    """创建邀请关系网络图"""
    G = nx.DiGraph()
    
    # 添加节点和边
    for _, row in df.iterrows():
        inviter = row['inviter_user_id']
        invitee = row['user_id']
        depth = row['depth'] if 'depth' in df.columns else 1
        
        if depth <= max_depth:
            G.add_node(inviter, size=10)
            G.add_node(invitee, size=5)
            G.add_edge(inviter, invitee)
    
    # 使用spring_layout布局
    pos = nx.spring_layout(G)
    
    # 创建节点跟踪
    node_trace = go.Scatter(
        x=[],
        y=[],
        text=[],
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            colorscale='YlGnBu',
            size=10,
            colorbar=dict(
                thickness=15,
                title='节点连接数',
                xanchor='left',
                titleside='right'
            )
        )
    )
    
    # 添加节点位置
    for node in G.nodes():
        x, y = pos[node]
        node_trace['x'] += tuple([x])
        node_trace['y'] += tuple([y])
        node_trace['text'] += tuple([f'用户ID: {node}<br>邀请数: {len(list(G.neighbors(node)))}'])
    
    # 创建边跟踪
    edge_trace = go.Scatter(
        x=[],
        y=[],
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # 添加边
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace['x'] += tuple([x0, x1, None])
        edge_trace['y'] += tuple([y0, y1, None])
    
    # 创建图形
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       title='邀请关系网络图',
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=20,l=5,r=5,t=40),
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                   ))
    
    return fig

def main():
    st.title("🤝 邀请关系分析")
    
    # 添加刷新按钮
    if st.button("🔄 刷新数据"):
        with st.spinner("正在更新数据..."):
            try:
                invite_tree.main()
                st.success("数据更新成功！")
            except Exception as e:
                st.error(f"数据更新失败: {str(e)}")
                return
    
    # 加载最新数据
    result = load_invite_data()
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
        total_inviters = df['inviter_user_id'].nunique()
        st.metric("总邀请人数", total_inviters)
    with col2:
        total_invitees = df['user_id'].nunique()
        st.metric("总被邀请人数", total_invitees)
    with col3:
        avg_invites = len(df) / total_inviters if total_inviters > 0 else 0
        st.metric("平均邀请人数", f"{avg_invites:.2f}")
    
    # 邀请关系网络图
    st.header("邀请关系网络图")
    depth = st.slider("选择显示深度", 1, 5, 3)
    network_fig = create_invite_network(df, max_depth=depth)
    st.plotly_chart(network_fig, use_container_width=True)
    
    # 邀请者排行
    st.header("邀请者排行")
    top_inviters = df.groupby('inviter_user_id').agg({
        'user_id': 'count',
    }).reset_index()
    top_inviters.columns = ['邀请者ID', '邀请人数']
    top_inviters = top_inviters.sort_values('邀请人数', ascending=False)
    
    st.dataframe(
        top_inviters.head(20),
        column_config={
            "邀请者ID": st.column_config.TextColumn(),
            "邀请人数": st.column_config.NumberColumn(format="%d")
        },
        hide_index=True
    )
    
    # 下载数据
    st.download_button(
        "📥 下载数据",
        df.to_csv(index=False).encode("utf-8"),
        "invite_analysis.csv",
        "text/csv",
        key='download-csv'
    )

if __name__ == "__main__":
    main() 