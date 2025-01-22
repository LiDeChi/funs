# 数据分析平台

这是一个基于Streamlit的数据分析平台，集成了代理商分析、充值分析和邀请关系分析等功能。

## 功能特点

1. 📈 **代理商分析**
   - 查看代理商的用户数据
   - 分析代理商的业务表现
   - 支持数据筛选和排序

2. 💰 **充值分析**
   - 分析用户充值行为
   - 计算关键充值指标
   - 可视化充值趋势

3. 🤝 **邀请关系分析**
   - 查看用户邀请关系
   - 分析邀请效果
   - 邀请关系网络图展示

## 安装说明

1. 克隆项目到本地：
   ```bash
   git clone <repository_url>
   cd streamlit_analysis
   ```

2. 创建并激活虚拟环境：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   .\venv\Scripts\activate  # Windows
   ```

3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 使用说明

1. 启动应用：
   ```bash
   streamlit run Home.py
   ```

2. 在浏览器中访问应用（默认地址：http://localhost:8501）

3. 使用左侧导航栏切换不同的分析功能

4. 点击各页面的"刷新数据"按钮更新数据

## 数据更新

- 数据每日自动更新
- 可以手动点击"刷新数据"按钮更新数据
- 更新时间显示在各分析页面

## 注意事项

1. 确保已正确配置数据库连接信息
2. 数据更新可能需要一定时间
3. 建议定期备份数据

## 技术支持

如有问题或建议，请联系技术支持。 