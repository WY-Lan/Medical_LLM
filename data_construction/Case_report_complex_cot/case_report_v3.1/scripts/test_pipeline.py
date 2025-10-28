#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：测试前两个阶段的流程处理
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.stage_one.html_parser import HTMLParser
from src.stage_one.html_to_json import HTMLToJSONConverter
from src.stage_two.mapping_manager import MappingManager
from src.stage_two.api_generator import APIGenerator
from src.api.four_o_client import FourOClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/test_pipeline.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)

def test_stage_one(input_dir, output_dir, max_files=20, max_workers=4):
    """测试第一阶段：HTML到JSON转换"""
    logger.info(f"开始测试第一阶段，处理目录: {input_dir}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有HTML文件
    html_files = list(Path(input_dir).glob("*.html"))
    if not html_files:
        logger.error(f"在目录 {input_dir} 中未找到HTML文件")
        return False
    
    # 限制处理文件数量
    if max_files and len(html_files) > max_files:
        logger.info(f"限制处理文件数为 {max_files} (共找到 {len(html_files)} 个文件)")
        html_files = html_files[:max_files]
    else:
        logger.info(f"找到 {len(html_files)} 个HTML文件")
    
    # 创建转换器并处理文件
    converter = HTMLToJSONConverter(
        input_dir=input_dir,
        output_dir=output_dir,
        max_workers=max_workers,
        max_items=max_files
    )
    
    success_count, failure_count = converter.run()
    
    logger.info(f"第一阶段处理结果: 成功 {success_count}, 失败 {failure_count}")
    return output_dir

def test_stage_two(input_dir, output_dir, mapping_dir, api_endpoint, api_key, max_files=20, max_workers=4, save_llm_output=False, llm_output_dir=None):
    """测试第二阶段：内容提取和数据集生成"""
    logger.info(f"开始测试第二阶段，处理目录: {input_dir}")
    
    # 确保目录存在
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(mapping_dir, exist_ok=True)
    
    # 如果需要保存LLM输出，确保输出目录存在
    if save_llm_output and llm_output_dir:
        os.makedirs(llm_output_dir, exist_ok=True)
        logger.info(f"将保存大模型输出到: {llm_output_dir}")
    
    # 获取所有JSON文件
    json_files = list(Path(input_dir).glob("*.json"))
    if not json_files:
        logger.error(f"在目录 {input_dir} 中未找到JSON文件")
        return False
    
    # 限制处理文件数量
    if max_files and len(json_files) > max_files:
        logger.info(f"限制处理文件数为 {max_files} (共找到 {len(json_files)} 个文件)")
        json_files = json_files[:max_files]
    else:
        logger.info(f"找到 {len(json_files)} 个JSON文件")
    
    # 创建组件
    mapping_manager = MappingManager(mapping_dir)
    four_o_client = FourOClient(
        api_endpoint=api_endpoint,
        api_key=api_key,
        timeout=60,
        retry_attempts=3,
        retry_delay=5,
        model="gpt-4o",
        save_responses=save_llm_output,
        response_dir=llm_output_dir
    )
    
    api_generator = APIGenerator(
        mapping_manager=mapping_manager,
        four_o_client=four_o_client,
        max_workers=max_workers
    )
    
    # 处理文件
    success_count, failure_count = api_generator.process_batch(json_files, Path(output_dir))
    
    logger.info(f"第二阶段处理结果: 成功 {success_count}, 失败 {failure_count}")
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='测试处理流程')
    parser.add_argument('--input_dir', type=str, default='/ai/home/jcw/Project/case_report_cot_v2.0/data/raw',
                        help='输入目录，包含HTML文件')
    parser.add_argument('--output_dir', type=str, default='output',
                        help='输出根目录')
    parser.add_argument('--stage_one_output', type=str, default='output/stage_one',
                        help='第一阶段输出目录')
    parser.add_argument('--stage_two_output', type=str, default='output/stage_two',
                        help='第二阶段输出目录')
    parser.add_argument('--mapping_dir', type=str, default='config/mapping',
                        help='映射目录')
    parser.add_argument('--api_endpoint', type=str, default='https://yunwu.ai',
                        help='4o API端点')
    parser.add_argument('--api_key', type=str, default='sk-846vAFyXMjPEEDUyU4iSifp6BMfq0OlqBlAo7yXbK1yRN1V4',
                        help='4o API密钥')
    parser.add_argument('--max_files', type=int, default=20,
                        help='最大处理文件数')
    parser.add_argument('--max_workers', type=int, default=4,
                        help='最大线程数')
    parser.add_argument('--stages', type=str, nargs='+', default=['stage_one', 'stage_two'],
                        help='要运行的阶段 (stage_one, stage_two)')
    parser.add_argument('--save_llm_output', action='store_true',
                        help='是否保存大模型的输出')
    parser.add_argument('--llm_output_dir', type=str, default='output/llms_res',
                        help='大模型输出保存目录')
    
    args = parser.parse_args()
    
    # 创建日志目录
    os.makedirs('logs', exist_ok=True)
    
    try:
        # 运行第一阶段
        if 'stage_one' in args.stages:
            logger.info("开始运行第一阶段...")
            os.makedirs(args.stage_one_output, exist_ok=True)
            stage_one_result = test_stage_one(
                args.input_dir, 
                args.stage_one_output,
                args.max_files,
                args.max_workers
            )
            if not stage_one_result:
                logger.error("第一阶段失败，终止测试")
                return 1
            logger.info(f"第一阶段完成，输出目录: {args.stage_one_output}")
        
        # 运行第二阶段
        if 'stage_two' in args.stages:
            logger.info("开始运行第二阶段...")
            os.makedirs(args.stage_two_output, exist_ok=True)
            stage_two_result = test_stage_two(
                args.stage_one_output, 
                args.stage_two_output,
                args.mapping_dir,
                args.api_endpoint,
                args.api_key,
                args.max_files,
                args.max_workers,
                args.save_llm_output,
                args.llm_output_dir
            )
            if not stage_two_result:
                logger.error("第二阶段失败，终止测试")
                return 1
            logger.info(f"第二阶段完成，输出目录: {args.stage_two_output}")
        
        logger.info("测试流程成功完成")
        return 0
        
    except Exception as e:
        logger.error(f"测试过程中出错: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
