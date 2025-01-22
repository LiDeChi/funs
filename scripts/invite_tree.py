#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent.parent
script_dir = project_root / "01_Script"
sys.path.append(str(project_root))
sys.path.append(str(script_dir))
from fetch_metabase import main as fetch_main

def main():
    """
    主函数: 执行充值分析流程
    """
    # 设置参数并调用fetch_metabase.py的main函数
    sql_file = str(project_root / "02_Query" / "recharge_analysis.sql")
    sys.argv = [sys.argv[0], sql_file, "1"]  # 从第1行开始查找SQL
    fetch_main()

if __name__ == '__main__':
    main()
