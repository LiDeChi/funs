import os
from pathlib import Path
import json
import streamlit as st
from datetime import datetime
import sys
from contextlib import contextmanager
from io import StringIO

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
LOCAL_ROOT = Path(__file__).parent

# 日志处理
class StreamlitLogger:
    def __init__(self):
        self._log_container = None
        self.log_buffer = StringIO()
    
    def set_container(self, container):
        self._log_container = container
        
    def write(self, text):
        if self._log_container is not None:
            if text.strip():  # 只显示非空内容
                timestamp = datetime.now().strftime("%H:%M:%S")
                self._log_container.write(f"[{timestamp}] {text}")
        self.log_buffer.write(text)
        
    def flush(self):
        pass

@contextmanager
def capture_output(container):
    """捕获输出并重定向到Streamlit容器"""
    logger = StreamlitLogger()
    logger.set_container(container)
    
    # 保存原始的stdout和stderr
    old_stdout, old_stderr = sys.stdout, sys.stderr
    
    try:
        # 重定向stdout和stderr到logger
        sys.stdout = logger
        sys.stderr = logger
        yield logger
    finally:
        # 恢复原始的stdout和stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

def load_config():
    """加载配置文件，优先使用本地配置"""
    try:
        # 首先尝试加载本地配置
        local_config_path = LOCAL_ROOT / "config" / "database_config.json"
        if local_config_path.exists():
            with open(local_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        # 如果本地配置不存在，尝试加载项目根目录的配置
        project_config_path = PROJECT_ROOT / "config" / "database_config.json"
        if project_config_path.exists():
            with open(project_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        st.error("配置文件不存在！")
        return None
    except Exception as e:
        st.error(f"加载配置失败: {str(e)}")
        return None

def get_metabase_config():
    """获取Metabase配置"""
    config = load_config()
    if config and "metabase" in config:
        return config["metabase"]
    return None

def get_target_databases():
    """获取目标数据库列表"""
    config = load_config()
    if config and "target_databases" in config:
        return config["target_databases"]
    return []

def get_output_dir():
    """获取输出目录"""
    config = load_config()
    if config and "output_dir" in config:
        # 优先使用本地路径
        output_dir = LOCAL_ROOT / config["output_dir"].replace("...", "")
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    return LOCAL_ROOT / "03_Data" / "merged_data"

# Streamlit 应用配置
APP_CONFIG = {
    "page_title": "数据分析平台",
    "page_icon": "📊",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# 缓存配置
CACHE_TTL = 3600  # 缓存过期时间（秒）

# 图表配置
CHART_CONFIG = {
    "theme": "streamlit",
    "color_discrete_sequence": ["#FF4B4B", "#0068C9", "#FF8C37", "#6AD551", "#37C2FF"],
    "template": "plotly_white"
} 