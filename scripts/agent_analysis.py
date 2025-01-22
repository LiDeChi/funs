#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
from pathlib import Path
import sys
import time
from io import StringIO
from datetime import datetime

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent.parent
script_dir = project_root / "01_Script"
sys.path.append(str(project_root))
sys.path.append(str(script_dir))
from fetch_metabase import load_config, get_data_as_csv

def get_base_user_data(metabase, db_id):
    """获取基础用户数据"""
    query = """
    SELECT DISTINCT
        t.agent_id,
        au.game_user_id,
        au.username,
        t.user_id,
        t.inviter_user_id,
        DATE(t.create_time) as create_time,
        DATE(t.update_time) as update_time
    FROM tg_user t
    LEFT JOIN admin_user au ON t.agent_id = au.admin_user_id
    WHERE t.enable_flag = 1
    """
    return get_data_as_csv(
        metabase["base_url"],
        metabase["session_id"],
        metabase["device_id"],
        db_id,
        query
    )

def get_charge_data(metabase, db_id):
    """获取充值数据"""
    query = """
    SELECT 
        t.user_id,
        t.agent_id,
        g.amount,
        g.status,
        g.pay_type,
        g.created_at
    FROM tg_user t
    JOIN game_charges g ON t.user_id = g.user_id
    WHERE 
        t.enable_flag = 1
        AND g.created_at >= '2024-11-01'
        AND g.status = true
    """
    return get_data_as_csv(
        metabase["base_url"],
        metabase["session_id"],
        metabase["device_id"],
        db_id,
        query
    )

def get_game_data(metabase, db_id):
    """获取游戏数据"""
    query = """
    SELECT 
        t.user_id,
        COUNT(*) as game_count
    FROM tg_user t
    JOIN transaction_record tr ON t.user_id = tr.user_id
    WHERE 
        t.invitation_code IS NOT NULL 
        AND t.invitation_code != ''
        AND t.enable_flag = 1
        AND tr.business_type = 6
    GROUP BY t.user_id
    """
    return get_data_as_csv(
        metabase["base_url"],
        metabase["session_id"],
        metabase["device_id"],
        db_id,
        query
    )

def get_invite_data(metabase, db_id):
    """获取邀请记录数据"""
    query = """
    WITH agent_users AS (
        -- 找出所有代理的game_user_id
        SELECT DISTINCT game_user_id
        FROM admin_user
        WHERE game_user_id IS NOT NULL
    ),
    inviter_stats AS (
        -- 统计每个非代理用户邀请的人数
        SELECT 
            t1.agent_id,
            t1.user_id,
            COUNT(DISTINCT t2.user_id) as invite_count
        FROM tg_user t1
        LEFT JOIN tg_user t2 ON t1.user_id = t2.inviter_user_id
        LEFT JOIN agent_users au ON t1.user_id = au.game_user_id
        WHERE 
            t1.enable_flag = 1
            AND t2.enable_flag = 1
            AND t2.user_id != t2.inviter_user_id  -- 排除自己邀请自己
            AND au.game_user_id IS NULL  -- 排除代理用户
        GROUP BY t1.agent_id, t1.user_id
        HAVING COUNT(DISTINCT t2.user_id) > 0  -- 只保留有邀请的记录
    )
    -- 找出每个代理下邀请人数最多的记录
    SELECT 
        agent_id,
        user_id as inviter_user_id,
        invite_count
    FROM inviter_stats i1
    WHERE invite_count = (
        SELECT MAX(invite_count)
        FROM inviter_stats i2
        WHERE i2.agent_id = i1.agent_id
    )
    """
    return get_data_as_csv(
        metabase["base_url"],
        metabase["session_id"],
        metabase["device_id"],
        db_id,
        query
    )

def process_data(base_df, charge_df, game_df, invite_df):
    """处理数据并计算统计指标"""
    try:
        # 检查数据是否为空
        if base_df.empty:
            print("警告: 基础数据为空")
            return pd.DataFrame()
            
        # 清理数据：删除所有列都是NaN的行
        base_df = base_df.dropna(how='all')
        
        # 打印列名和前几行数据，用于调试
        print("基础数据列名:", base_df.columns.tolist())
        print("\n基础数据前5行:")
        print(base_df.head())
        print("\n基础数据信息:")
        print(base_df.info())
        
        # 确保所有必需的列都存在
        required_columns = ['agent_id', 'game_user_id', 'username', 'user_id', 'inviter_user_id', 'create_time', 'update_time']
        missing_columns = [col for col in required_columns if col not in base_df.columns]
        if missing_columns:
            print(f"警告: 基础数据缺少以下列: {missing_columns}")
            return pd.DataFrame()
            
        # 处理agent_id为空的情况（官方账号）
        base_df['agent_id'] = base_df['agent_id'].fillna('NULL')
        base_df['game_user_id'] = pd.to_numeric(base_df['game_user_id'], errors='coerce').fillna(0)
        base_df['username'] = base_df['username'].fillna('官方')
        base_df['user_id'] = pd.to_numeric(base_df['user_id'], errors='coerce')
        base_df['inviter_user_id'] = pd.to_numeric(base_df['inviter_user_id'], errors='coerce')
        
        # 确保所有数据中的agent_id都是相同类型（字符串）
        def convert_agent_id(df):
            if df is None or df.empty:
                return pd.DataFrame()
            if 'agent_id' in df.columns:
                df['agent_id'] = df['agent_id'].fillna('NULL')
                df['agent_id'] = df['agent_id'].astype(str)
            return df
            
        # 转换所有DataFrame中的agent_id类型
        base_df = convert_agent_id(base_df)
        charge_df = convert_agent_id(charge_df) if not charge_df.empty else pd.DataFrame()
        game_df = convert_agent_id(game_df) if not game_df.empty else pd.DataFrame()
        invite_df = convert_agent_id(invite_df) if not invite_df.empty else pd.DataFrame()
        
        # 打印数据统计信息
        print("\n数据统计:")
        print(f"基础用户数: {len(base_df)}")
        print(f"充值记录数: {len(charge_df)}")
        print(f"游戏记录数: {len(game_df)}")
        print(f"邀请记录数: {len(invite_df)}")
        print(f"\n空值统计:")
        print(base_df.isnull().sum())
        
        # 按代理分组的基础统计
        result = base_df.groupby(['agent_id', 'game_user_id', 'username']).agg({
            'user_id': 'nunique'  # 总用户数
        }).reset_index()
        
        # 重命名总用户数列（提前重命名）
        result = result.rename(columns={
            'user_id': '总用户数'
        })
        
        # 计算直属用户数
        direct_users = base_df[
            (base_df['inviter_user_id'] == base_df['game_user_id']) | 
            (base_df['inviter_user_id'].isna())
        ].groupby(['agent_id'])['user_id'].nunique()
        result = result.merge(
            direct_users.reset_index().rename(columns={'user_id': '直属用户数'}),
            on='agent_id',
            how='left'
        )
        
        # 计算最大邀请人数（使用邀请记录表）
        if not invite_df.empty:
            print("\n邀请数据:")
            print(invite_df)
            print("\n邀请数据类型:")
            print(invite_df.dtypes)
            
            # 确保邀请数据的类型正确
            invite_df['invite_count'] = pd.to_numeric(invite_df['invite_count'], errors='coerce')
            invite_df['inviter_user_id'] = pd.to_numeric(invite_df['inviter_user_id'], errors='coerce')
            invite_df['agent_id'] = invite_df['agent_id'].fillna('NULL')
            invite_df['agent_id'] = invite_df['agent_id'].astype(str)
            
            # 直接使用SQL查询返回的最大邀请数
            result = result.merge(
                invite_df[['agent_id', 'invite_count']].rename(columns={'invite_count': '最大邀请人数'}),
                on='agent_id',
                how='left'
            )
            
            # 打印邀请统计信息
            print("\n邀请统计信息:")
            print("每个代理的邀请人数统计:")
            print(invite_df.groupby('agent_id')['invite_count'].describe())
            print("\n最大邀请人数:")
            print(invite_df.sort_values('invite_count', ascending=False))
        else:
            result['最大邀请人数'] = 0
        
        # 计算充值相关指标
        if not charge_df.empty:
            # 确保充值数据的类型正确
            charge_df['amount'] = pd.to_numeric(charge_df['amount'], errors='coerce')
            charge_df['pay_type'] = pd.to_numeric(charge_df['pay_type'], errors='coerce')
            
            # 计算实际充值金额
            charge_df['real_amount'] = np.where(
                charge_df['pay_type'] == 0,
                charge_df['amount'] * 5,  # pay_type = 0 时，金额乘以5
                np.where(charge_df['pay_type'] == 1, charge_df['amount'] / 50, 0)  # pay_type = 1 时，金额除以50
            )
            
            # 按代理和用户汇总充值金额
            charge_stats = charge_df.groupby(['agent_id', 'user_id'])['real_amount'].sum().reset_index()
            
            # 只保留有实际充值的记录（real_amount > 0）
            charge_stats = charge_stats[charge_stats['real_amount'] > 0]
            
            # 计算每个代理的充值统计
            charge_by_agent = charge_stats.groupby('agent_id').agg({
                'real_amount': 'sum',  # 总充值金额
                'user_id': 'nunique'  # 付费用户数（只统计实际有充值的用户）
            }).reset_index()
            
            charge_by_agent.columns = ['agent_id', '总充值金额', '付费用户数']
            
            # 确保agent_id类型一致
            charge_by_agent = convert_agent_id(charge_by_agent)
            
            # 合并到结果中
            result = result.merge(charge_by_agent, on='agent_id', how='left')
        else:
            result['总充值金额'] = 0
            result['付费用户数'] = 0
            
        # 计算游戏相关指标
        if not game_df.empty:
            # 确保游戏数据的类型正确
            game_df['game_count'] = pd.to_numeric(game_df['game_count'], errors='coerce')
            game_df['user_id'] = pd.to_numeric(game_df['user_id'], errors='coerce')
            
            # 找出游戏次数大于5的玩家
            game_players = game_df[game_df['game_count'] > 5]['user_id'].unique()
            
            # 统计每个代理的游戏玩家数
            game_stats = base_df[base_df['user_id'].isin(game_players)].groupby('agent_id')['user_id'].nunique()
            result = result.merge(
                game_stats.reset_index().rename(columns={'user_id': '游戏玩家数'}),
                on='agent_id',
                how='left'
            )
        else:
            # 如果没有游戏数据，添加空列
            result['游戏玩家数'] = 0
        
        # 填充空值
        result = result.fillna({
            '总用户数': 0,
            '直属用户数': 0,
            '最大邀请人数': 0,
            '总充值金额': 0,
            '付费用户数': 0,
            '游戏玩家数': 0
        })
        
        # 计算比率和平均值（避免除以零）
        result['直属用户占比'] = result.apply(
            lambda row: f"{(row['直属用户数'] / row['总用户数'] * 100):.2f}%" if row['总用户数'] > 0 else "0%",
            axis=1
        )
        
        result['游戏玩家占比'] = result.apply(
            lambda row: f"{(row['游戏玩家数'] / row['总用户数'] * 100):.2f}%" if row['总用户数'] > 0 else "0%",
            axis=1
        )
        
        result['付费率'] = result.apply(
            lambda row: f"{(row['付费用户数'] / row['总用户数'] * 100):.2f}%" if row['总用户数'] > 0 else "0%",
            axis=1
        )
        
        # 计算ARPPU和人均指标（避免除以零）
        result['付费用户平均充值'] = result.apply(
            lambda row: round(row['总充值金额'] / row['付费用户数'], 4) if row['付费用户数'] > 0 else 0,
            axis=1
        )
        
        result['人均充值'] = result.apply(
            lambda row: round(row['总充值金额'] / row['总用户数'], 4) if row['总用户数'] > 0 else 0,
            axis=1
        )
        
        # 计算活跃时间相关指标
        def get_date_range(group):
            try:
                # 确保日期时间格式正确
                create_dates = pd.to_datetime(group['create_time']).dt.date
                update_dates = pd.to_datetime(group['update_time']).dt.date
                
                # 过滤掉无效的日期（NaT）
                create_dates = create_dates[pd.notna(create_dates)]
                update_dates = update_dates[pd.notna(update_dates)]
                
                # 合并所有日期并转换为列表
                all_dates = pd.concat([
                    pd.Series(create_dates),
                    pd.Series(update_dates)
                ]).dropna().tolist()
                
                if not all_dates:  # 如果没有有效日期
                    return pd.DataFrame({
                        '首次活跃日期': [None],
                        '最后活跃日期': [None],
                        '活跃天数': [0]
                    })
                    
                # 计算统计数据
                return pd.DataFrame({
                    '首次活跃日期': [min(all_dates)],
                    '最后活跃日期': [max(all_dates)],
                    '活跃天数': [len(set(all_dates))]
                })
            except Exception as e:
                print(f"日期处理错误: {str(e)}")
                return pd.DataFrame({
                    '首次活跃日期': [None],
                    '最后活跃日期': [None],
                    '活跃天数': [0]
                })
            
        date_stats = base_df.groupby('agent_id').apply(get_date_range).reset_index()
        date_stats.columns = ['agent_id', 'level_1'] + list(date_stats.columns[2:])
        date_stats = date_stats.drop('level_1', axis=1)
        
        # 合并日期统计
        result = result.merge(date_stats, on='agent_id', how='left')
        
        # 计算人均日充值（避免除以零）
        result['人均日充值'] = result.apply(
            lambda row: round(row['总充值金额'] / row['总用户数'] / row['活跃天数'], 4) 
            if row['总用户数'] > 0 and row['活跃天数'] > 0 else 0,
            axis=1
        )
        
        # 确保数值列为整数类型
        int_columns = ['总用户数', '直属用户数', '最大邀请人数', '付费用户数', '游戏玩家数', '活跃天数']
        for col in int_columns:
            if col in result.columns:
                result[col] = result[col].fillna(0).astype(int)
        
        # 确保金额列为浮点数类型，保留4位小数
        float_columns = ['总充值金额', '付费用户平均充值', '人均充值', '人均日充值']
        for col in float_columns:
            if col in result.columns:
                result[col] = result[col].fillna(0).round(4)
        
        # 按总用户数排序
        result = result.sort_values('总用户数', ascending=False)
        
        return result
        
    except Exception as e:
        print(f"数据处理错误: {str(e)}")
        print("错误详情:", e.__class__.__name__)
        import traceback
        print(traceback.format_exc())
        return pd.DataFrame()  # 返回空DataFrame

def main():
    try:
        # 记录开始时间
        start_time = time.time()
        
        # 加载配置
        config = load_config()
        metabase = config["metabase"]
        
        print(f"\n=== 开始分析代理商数据 ===")
        print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 准备输出目录
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        project_root = Path(__file__).parent.parent
        output_dir = project_root / config["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"agent_analysis_{timestamp}.csv"
        
        all_results = []
        for db_id in config["target_databases"]:
            print(f"\n处理数据库 {db_id}...")
            
            try:
                # 获取各类数据
                base_data = get_base_user_data(metabase, db_id)
                if not base_data:
                    print(f"数据库 {db_id} 基础数据获取失败")
                    continue
                    
                charge_data = get_charge_data(metabase, db_id)
                game_data = get_game_data(metabase, db_id)
                invite_data = get_invite_data(metabase, db_id)
                
                # 转换为DataFrame
                base_df = pd.read_csv(StringIO(base_data))
                charge_df = pd.read_csv(StringIO(charge_data)) if charge_data else pd.DataFrame()
                game_df = pd.read_csv(StringIO(game_data)) if game_data else pd.DataFrame()
                invite_df = pd.read_csv(StringIO(invite_data)) if invite_data else pd.DataFrame()
                
                # 处理数据
                result = process_data(base_df, charge_df, game_df, invite_df)
                if not result.empty:
                    all_results.append(result)
                    print(f"数据库 {db_id} 处理完成，获取到 {len(result)} 条记录")
                
            except Exception as e:
                print(f"处理数据库 {db_id} 时发生错误: {str(e)}")
                import traceback
                print(traceback.format_exc())
                continue
        
        # 合并所有结果
        if all_results:
            final_result = pd.concat(all_results, ignore_index=True)
            # 填充空值
            final_result = final_result.fillna({
                '总用户数': 0,
                '直属用户数': 0,
                '最大邀请人数': 0,
                '总充值金额': 0,
                '付费用户数': 0,
                '游戏玩家数': 0,
                '付费用户平均充值': 0,
                '人均充值': 0,
                '活跃天数': 0,
                '人均日充值': 0,
                '直属用户占比': '0%',
                '游戏玩家占比': '0%',
                '付费率': '0%'
            })
            final_result.to_csv(output_file, index=False, encoding='utf-8')
            print(f"\n分析完成，结果已保存到: {output_file}")
            print(f"总记录数: {len(final_result)}")
        else:
            print("\n未能获取任何有效数据")
        
        # 计算总耗时
        total_time = time.time() - start_time
        print(f"\n总耗时: {total_time:.2f} 秒")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    main() 