import os
import subprocess
import pandas as pd
from datetime import datetime, timedelta

def get_user_registration_data():
    """
    获取用户注册信息（2024-11-01 之后注册）
    - tg_user表：user_id, agent_id, create_time
    - admin_user表：admin_user_id, username（代理名称）
    """
    # SQL 查询：获取 2024-11-01 之后注册的用户
    sql = """SELECT 
        t.user_id, 
        CASE 
            WHEN t.agent_id IS NULL THEN '官方'
            ELSE t.agent_id 
        END as agent_id,
        IFNULL(a.username, '未知代理') AS agent_username,
        DATE(t.create_time) AS registration_date
    FROM tg_user t
    LEFT JOIN admin_user a 
        ON t.agent_id = a.admin_user_id
    WHERE t.create_time >= '2024-11-01'
    ORDER BY t.agent_id, t.create_time, t.user_id;
    """

    temp_sql_file = '02_Query/temp_user_registration.sql'
    os.makedirs('02_Query', exist_ok=True)
    with open(temp_sql_file, 'w', encoding='utf-8') as f:
        f.write(sql)

    try:
        # 运行 fetch_metabase.py
        subprocess.run(['python', '01_Script/fetch_metabase.py', temp_sql_file, '1'], check=True)

        # 获取 CSV
        output_dir = '03_Data/merged_data'
        files = [f for f in os.listdir(output_dir) if f.startswith('tg_user_') or f.startswith('user_')]
        if not files:
            raise Exception("未找到用户注册数据文件。")

        latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
        df_user = pd.read_csv(
            os.path.join(output_dir, latest_file),
            dtype={'agent_id': str, 'user_id': str},
            encoding='utf-8'
        )

        # 删除临时 SQL
        os.remove(temp_sql_file)

        # 基本检查
        expected_cols = ['user_id', 'agent_id', 'agent_username', 'registration_date']
        for col in expected_cols:
            if col not in df_user.columns:
                raise Exception(f"缺少必要列: {col}")

        # 去除多余空格
        df_user['user_id'] = df_user['user_id'].astype(str).str.strip()
        df_user['agent_id'] = df_user['agent_id'].astype(str).str.strip()

        # 重命名列
        df_user = df_user.rename(columns={'registration_date': '注册日期'})

        # 打印部分用户注册数据以验证
        print("\n示例用户注册数据:")
        print(df_user.head())

        return df_user

    except Exception as e:
        if os.path.exists(temp_sql_file):
            os.remove(temp_sql_file)
        raise

def get_recharge_data():
    """
    获取充值数据（2024-11-01 之后的订单），并计算 adjusted_amount
    规则：
    - status=1 才算成功
    - pay_type 为空时视为 0
    - pay_type=0 => amount * 5
    - pay_type=1 => amount / 50
    - pay_type 其他值按 0 处理
    - 只保留 status=1 的记录
    - 添加 agent_username 列
    """
    sql = """SELECT 
        r.user_id AS user_id,
        DATE(r.create_time) AS recharge_date,
        COALESCE(r.pay_type, 0) AS pay_type,
        r.amount,
        CASE 
            WHEN r.status = 1 AND COALESCE(r.pay_type, 0) = 0 THEN r.amount * 5
            WHEN r.status = 1 AND COALESCE(r.pay_type, 0) = 1 THEN r.amount / 50
            ELSE 0 
        END AS adjusted_amount,
        r.status,
        IFNULL(a.username, '未知代理') AS agent_username
    FROM game_charges r
    LEFT JOIN tg_user t ON r.user_id = t.user_id
    LEFT JOIN admin_user a ON t.agent_id = a.admin_user_id
    WHERE r.create_time >= '2024-11-01' AND r.status = 1
    ORDER BY r.user_id, r.create_time;
    """

    temp_sql_file = '02_Query/temp_agent_recharge.sql'
    os.makedirs('02_Query', exist_ok=True)
    with open(temp_sql_file, 'w', encoding='utf-8') as f:
        f.write(sql)

    try:
        subprocess.run(['python', '01_Script/fetch_metabase.py', temp_sql_file, '1'], check=True)

        output_dir = '03_Data/merged_data'
        files = [f for f in os.listdir(output_dir) if f.startswith('game_charges_')]
        if not files:
            raise Exception("未找到充值数据文件。")

        latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
        df_recharge = pd.read_csv(
            os.path.join(output_dir, latest_file),
            dtype={'user_id': str},
            encoding='utf-8'
        )

        # 删除临时 SQL
        os.remove(temp_sql_file)

        # 去除多余空格
        df_recharge['user_id'] = df_recharge['user_id'].astype(str).str.strip()

        # 重命名列
        df_recharge = df_recharge.rename(columns={
            'recharge_date': '充值日期',
            'adjusted_amount': '调整后金额'
        })

        # 确保 'status' 是整数，1 表示成功
        if df_recharge['status'].dtype == object:
            # 处理不同形式的 TRUE/FALSE
            df_recharge['status'] = df_recharge['status'].str.upper().map({'TRUE': 1, 'FALSE': 0})
            df_recharge['status'] = pd.to_numeric(df_recharge['status'], errors='coerce').fillna(0).astype(int)
        else:
            df_recharge['status'] = df_recharge['status'].astype(int)

        # 处理 pay_type 非 0/1 的情况，按 0 处理
        df_recharge['pay_type'] = df_recharge['pay_type'].apply(lambda x: x if x in [0,1] else 0)

        # 打印部分充值数据以验证
        print("\n示例充值数据:")
        print(df_recharge.head())

        # 打印唯一的 pay_type 值以确认
        print("\n充值数据中 pay_type 的唯一值:")
        print(df_recharge['pay_type'].unique())

        # 打印唯一的 status 值以确认
        print("\n充值数据中 status 的唯一值:")
        print(df_recharge['status'].unique())

        return df_recharge

    except Exception as e:
        if os.path.exists(temp_sql_file):
            os.remove(temp_sql_file)
        raise

def calculate_rolling_recharge(df_user, df_recharge):
    """
    计算需求：
    1) 不要 total_orders, attempt_users, success_orders, success_user_rate 这类当天指标
    2) success = status=1
    3) 统计注册日期到查询时的相差天数
    4) 3/7/15/30天的 累积充值(包括前面天数)，并计算：
       - 3/7/15/30 天的人均充值（总金额 / 注册人数）
       - 3/7/15/30 天的付费用户的人均充值（成功用户的总金额 / 付费用户数）
    5) success_users, attempt_user_rate, success_user_rate 是指累积到查询时刻，不是仅注册当天
    6) 字段名字用中文
    7) 增加累积总充值
    """
    try:
        # 转换日期类型
        df_user['注册日期'] = pd.to_datetime(df_user['注册日期'])
        df_recharge['充值日期'] = pd.to_datetime(df_recharge['充值日期'])

        # ---------------------------
        # 第一步：计算"距查询时刻相差天数"
        # ---------------------------
        # 以脚本运行时的日期为查询时刻
        query_time = pd.to_datetime(datetime.now().date())
        df_user['距查询时天数'] = (query_time - df_user['注册日期']).dt.days

        # ---------------------------
        # 第二步：计算注册人数（按天）
        # ---------------------------
        # 每天每个代理有多少新注册
        daily_users = df_user.groupby(['agent_id', 'agent_username', '注册日期']).agg(
            注册人数=('user_id', 'nunique')
        ).reset_index()

        # ---------------------------
        # 第三步：合并充值 & 注册信息，使用内连接
        # ---------------------------
        merged = pd.merge(
            df_recharge,
            df_user[['user_id', 'agent_id', 'agent_username', '注册日期']],
            on=['user_id'],
            how='inner',
            suffixes=('_charge', '')  # 保留df_user中的agent_username
        )

        # 计算距离注册多少天进行的充值
        merged['自注册起天数'] = (merged['充值日期'] - merged['注册日期']).dt.days

        # ---------------------------
        # 第四步：为每条充值计算 3/7/15/30天窗口内的金额
        # ---------------------------
        # 使用向量化操作代替 apply，提高性能
        merged['金额_3天'] = merged['调整后金额'].where(merged['自注册起天数'] <= 3, 0)
        merged['金额_7天'] = merged['调整后金额'].where(merged['自注册起天数'] <= 7, 0)
        merged['金额_15天'] = merged['调整后金额'].where(merged['自注册起天数'] <= 15, 0)
        merged['金额_30天'] = merged['调整后金额'].where(merged['自注册起天数'] <= 30, 0)
        merged['金额_total'] = merged['调整后金额']  # 累积总充值

        # 打印列名用于调试
        print("\n合并后的数据列名:", merged.columns.tolist())

        # ---------------------------
        # 第五步：分组聚合 - 求累积充值
        # ---------------------------
        rolling = merged.groupby(['agent_id', 'agent_username', '注册日期']).agg(
            累积充值_3天=('金额_3天', 'sum'),
            累积充值_7天=('金额_7天', 'sum'),
            累积充值_15天=('金额_15天', 'sum'),
            累积充值_30天=('金额_30天', 'sum'),
            累积充值_total=('金额_total', 'sum'),
            付费用户数_3天=('user_id', lambda x: x.loc[x.index].nunique()),
            付费用户数_7天=('user_id', lambda x: x.loc[x.index].nunique()),
            付费用户数_15天=('user_id', lambda x: x.loc[x.index].nunique()),
            付费用户数_30天=('user_id', lambda x: x.loc[x.index].nunique())
        ).reset_index()

        # ---------------------------
        # 第六步：合并回注册人数
        # ---------------------------
        df_final = pd.merge(
            daily_users,
            rolling,
            on=['agent_id', 'agent_username', '注册日期'],
            how='left'
        ).fillna(0)

        # ---------------------------
        # 第七步：计算人均充值 / 付费人均充值
        # ---------------------------
        # 3/7/15/30 天人均充值 = 累积充值 / 注册人数
        df_final['3天ARPU'] = (df_final['累积充值_3天'] / df_final['注册人数']).round(3).fillna(0)
        df_final['7天ARPU'] = (df_final['累积充值_7天'] / df_final['注册人数']).round(3).fillna(0)
        df_final['15天ARPU'] = (df_final['累积充值_15天'] / df_final['注册人数']).round(3).fillna(0)
        df_final['30天ARPU'] = (df_final['累积充值_30天'] / df_final['注册人数']).round(3).fillna(0)
        df_final['总充值ARPU'] = (df_final['累积充值_total'] / df_final['注册人数']).round(3).fillna(0)

        # 3/7/15/30 天付费人均充值 = 累积充值 / 付费用户数
        df_final['3天ARPPU'] = (df_final['累积充值_3天'] / df_final['付费用户数_3天']).round(3).fillna(0)
        df_final['7天ARPPU'] = (df_final['累积充值_7天'] / df_final['付费用户数_7天']).round(3).fillna(0)
        df_final['15天ARPPU'] = (df_final['累积充值_15天'] / df_final['付费用户数_15天']).round(3).fillna(0)
        df_final['30天ARPPU'] = (df_final['累积充值_30天'] / df_final['付费用户数_30天']).round(3).fillna(0)
        df_final['总充值ARPPU'] = (df_final['累积充值_total'] / df_final['付费用户数_30天']).round(3).fillna(0)

        # ---------------------------
        # 第八步：充值用户累积、充值率累积
        # 这里指"累积到查询时刻"
        # ---------------------------
        # 充值用户累积 = 累积成功用户数
        df_success = merged.groupby(['agent_id', 'agent_username', '注册日期'])['user_id'].nunique().reset_index(name='充值用户累积')
        df_final = pd.merge(df_final, df_success, on=['agent_id', 'agent_username', '注册日期'], how='left').fillna(0)
        df_final['充值率累积'] = df_final.apply(
            lambda row: f"{round(row['充值用户累积'] / row['注册人数'] * 100, 2)}%" if row['注册人数'] > 0 else '0%',
            axis=1
        )

        # ---------------------------
        # 第九步：计算过去天数
        # ---------------------------
        query_date = pd.to_datetime(datetime.now().date())
        df_final['过去天数'] = (query_date - df_final['注册日期']).dt.days

        # ---------------------------
        # 第十步：排序、重命名列等操作
        # ---------------------------
        df_final = df_final.sort_values(['注册日期', 'agent_id'], ascending=[True, True]).reset_index(drop=True)

        # 打印最终数据示例
        print("\n示例最终合并后的数据:")
        print(df_final.head())

        return df_final
    except Exception as e:
        print(f"计算滚动充值时发生错误: {str(e)}")
        raise

def main():
    try:
        print("获取用户注册数据...")
        df_user = get_user_registration_data()

        print("获取充值数据...")
        df_recharge = get_recharge_data()

        print("开始计算滚动充值与相关指标...")
        df_result = calculate_rolling_recharge(df_user, df_recharge)

        # 保存结果
        output_dir = '03_Data/merged_data'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 保存综合分析结果
        output_file_result = f'agent_recharge_analysis_{timestamp}.csv'
        output_path_result = os.path.join(output_dir, output_file_result)
        df_result.to_csv(output_path_result, index=False, encoding='utf-8')
        print(f"综合分析结果已保存：{output_path_result}")

    except Exception as e:
        print(f"执行出错：{str(e)}")
        raise

if __name__ == "__main__":
    main()
