import streamlit as st
import sys
from pathlib import Path
from config import APP_CONFIG, load_config

# 设置页面配置
st.set_page_config(**APP_CONFIG)

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def main():
    # 检查配置
    config = load_config()
    if config is None:
        st.error("无法加载配置文件，请确保 config/database_config.json 文件存在且格式正确。")
        return
        
    st.title("📊 数据分析平台")
    
    st.markdown("""
    ### 👋 欢迎使用数据分析平台
    
    本平台集成了以下分析功能：
    
    1. 📈 **代理商分析**
       - 查看代理商的用户数据
       - 分析代理商的业务表现
       
    2. 💰 **充值分析**
       - 分析用户充值行为
       - 计算关键充值指标
       
    3. 🤝 **邀请关系分析**
       - 查看用户邀请关系
       - 分析邀请效果
    
    ### 使用说明
    
    - 在左侧边栏选择需要的分析功能
    - 根据页面提示输入必要参数
    - 查看分析结果和可视化图表
    
    ### 数据更新频率
    
    - 数据每日更新
    - 最后更新时间显示在各分析页面
    """)
    
    # 添加页脚
    st.markdown("---")
    st.markdown("### 📫 联系方式")
    st.info("如有问题或建议，请联系技术支持。")

if __name__ == "__main__":
    main() 