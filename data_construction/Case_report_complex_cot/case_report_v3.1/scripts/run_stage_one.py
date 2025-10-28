#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一阶段运行脚本：HTML转JSON
优化版本：使用配置文件，关注h2标题特别是class="pmc_sec_title"
"""

import os
import sys
import yaml
import argparse
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.stage_one.html_to_json import HTMLToJSONConverter

# 创建日志目录
os.makedirs('logs/stage_one', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/stage_one/run.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)

def load_config(config_path):
    """加载YAML配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置文件时出错: {str(e)}")
        raise

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='运行第一阶段: HTML转JSON')
    
    parser.add_argument('--config', default='config/default.yaml', help='配置文件路径')
    parser.add_argument('--input-dir', help='输入目录路径，包含HTML文件（覆盖配置文件）')
    parser.add_argument('--output-dir', help='输出目录路径，存储JSON结果（覆盖配置文件）')
    parser.add_argument('--max-workers', type=int, help='最大线程数（覆盖配置文件）')
    parser.add_argument('--max-items', type=int, help='最大处理文件数（覆盖配置文件）')
    
    return parser.parse_args()

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 加载配置文件
    config = load_config(args.config)
    
    # 合并配置和命令行参数
    if args.input_dir:
        config['paths']['input_dir'] = args.input_dir
    if args.output_dir:
        config['stage_one']['output_dir'] = args.output_dir
    if args.max_workers:
        config['general']['max_workers'] = args.max_workers
    if args.max_items:
        config['general']['max_items'] = args.max_items
    
    try:
        # 从配置创建转换器
        converter = HTMLToJSONConverter.from_config_file(args.config)
        
        # 打印运行信息
        logger.info(f"运行第一阶段: HTML转JSON (优化版)")
        logger.info(f"输入目录: {converter.input_dir}")
        logger.info(f"输出目录: {converter.output_dir}")
        logger.info(f"最大线程数: {converter.max_workers}")
        logger.info(f"最大处理文件数: {converter.max_items if converter.max_items else '不限'}")
    
        # 运行转换
        success_count, failure_count = converter.run()
        
        # 输出处理结果
        logger.info(f"第一阶段完成. 成功: {success_count}, 失败: {failure_count}")
        
        return 0 if failure_count == 0 else 1
        
    except Exception as e:
        logger.error(f"运行第一阶段时出错: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
