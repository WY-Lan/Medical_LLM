#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多进程处理脚本：处理PMC数据集
"""

import os
import sys
import yaml
import argparse
import logging
import glob
import time
import multiprocessing
import traceback
from pathlib import Path
from functools import partial
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.stage_one.html_to_json import HTMLToJSONConverter
from src.stage_one.html_parser import HTMLParser
from src.stage_two.content_extractor import ContentExtractor
from src.stage_three.cot_generator import CoTGenerator
from src.api.four_o_client import FourOClient

# 创建日志目录
os.makedirs('logs', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/process_multi.log', mode='a')
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

def sanitize_filename(filename):
    """清理文件名，替换/移除特殊字符"""
    # 替换Windows/Unix系统不允许的特殊字符
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def process_single_file(html_file, output_base_dir, mapping_dir, four_o_client):
    """处理单个文件的完整流程（三个阶段）"""
    html_file = Path(html_file)
    file_id = html_file.stem
    
    try:
        # 阶段一：解析HTML并保存为JSON
        stage_one_output = Path(output_base_dir) / "stage_one"
        os.makedirs(stage_one_output, exist_ok=True)
        
        # 清理文件名中的特殊字符
        sanitized_file_id = sanitize_filename(file_id)
        stage_one_output_file = stage_one_output / f"{sanitized_file_id}.json"
        
        # 如果阶段一输出已存在，就跳过阶段一
        if not stage_one_output_file.exists():
            try:
                # 直接使用HTMLParser而不是初始化不需要路径的HTMLToJSONConverter
                parser = HTMLParser()
                
                with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                    html_content = f.read()
                
                # 解析HTML内容
                parsed_data = parser.parse_html(html_content)
                
                if parsed_data:
                    with open(stage_one_output_file, 'w', encoding='utf-8') as f:
                        f.write(json.dumps(parsed_data, ensure_ascii=False, indent=2))
                else:
                    logger.warning(f"文件{file_id}的HTML内容解析结果为空")
                    return False, file_id, "阶段一解析失败：解析结果为空"
            except Exception as e:
                logger.error(f"阶段一处理文件{file_id}时出错: {str(e)}")
                return False, file_id, f"阶段一处理出错: {str(e)}"
        
        # 阶段二：提取信息
        stage_two_output = Path(output_base_dir) / "stage_two"
        os.makedirs(stage_two_output, exist_ok=True)
        
        stage_two_output_file = stage_two_output / f"{sanitized_file_id}_processed.json"
        
        # 如果阶段二输出已存在，就跳过阶段二
        if not stage_two_output_file.exists():
            try:
                if not stage_one_output_file.exists():
                    logger.error(f"阶段二处理时，阶段一的输出文件不存在: {stage_one_output_file}")
                    return False, file_id, "阶段二处理失败：阶段一输出文件不存在"
                
                # 创建内容提取器
                content_extractor = ContentExtractor(
                    api_client=four_o_client,
                    mapping_dir=mapping_dir
                )
                
                # 读取阶段一的输出文件
                with open(stage_one_output_file, 'r', encoding='utf-8') as f:
                    article_data = json.load(f)
                
                # 处理文章
                processed_data = content_extractor.process_article(article_data)
                
                # 保存处理结果，不做严格验证
                with open(stage_two_output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed_data, f, ensure_ascii=False, indent=2)
                    
            except Exception as e:
                logger.error(f"阶段二处理文件{file_id}时出错: {str(e)}")
                return False, file_id, f"阶段二处理出错: {str(e)}"
        
        # 阶段三：生成CoT
        stage_three_output = Path(output_base_dir) / "stage_three"
        os.makedirs(stage_three_output, exist_ok=True)
        
        stage_three_output_file = stage_three_output / f"{sanitized_file_id}_cot.json"
        
        # 如果阶段三输出已存在，就跳过阶段三
        if not stage_three_output_file.exists():
            try:
                if not stage_two_output_file.exists():
                    logger.error(f"阶段三处理时，阶段二的输出文件不存在: {stage_two_output_file}")
                    return False, file_id, "阶段三处理失败：阶段二输出文件不存在"
                
                # 读取阶段二输出文件
                with open(stage_two_output_file, 'r', encoding='utf-8') as f:
                    stage_two_data = json.load(f)
                
                # 简化检查逻辑
                cases = stage_two_data.get("cases", {})
                if not cases:
                    logger.warning(f"阶段三处理时，阶段二输出文件缺少cases字段: {stage_two_output_file}")
                    # 创建空的cases以允许继续处理
                    stage_two_data["cases"] = {"case_1": {}}
                
                cot_generator = CoTGenerator(
                    four_o_client=four_o_client,
                    output_dir=stage_three_output
                )
                
                # 处理单个文件
                result = cot_generator.process_file(stage_two_output_file)
                if not result:
                    logger.warning(f"阶段三处理文件{file_id}可能部分失败，但仍继续处理")
            except Exception as e:
                logger.error(f"阶段三处理文件{file_id}时出错: {str(e)}")
                return False, file_id, f"阶段三处理出错: {str(e)}"
        
        return True, file_id, "处理成功"
    
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"处理文件{file_id}时出错: {str(e)}\n{error_details}")
        return False, file_id, f"处理出错: {str(e)}"

def process_dataset(input_dir, output_base_dir, mapping_dir, api_endpoint, api_key, 
                    max_files=1000, num_processes=None, set_prefix="set_", set_numbers=None,
                    save_responses=False, response_dir='logs/api_responses', config=None):
    """处理指定的数据集"""
    # 设置进程数，默认为CPU核心数的75%
    if num_processes is None:
        num_processes = max(1, int(multiprocessing.cpu_count() * 0.75))
    
    logger.info(f"使用进程数: {num_processes}")
    
    # 创建api客户端
    api_config = config['stage_two']['api'] if config else {}
    
    four_o_client = FourOClient(
        api_endpoint=api_endpoint,
        api_key=api_key,
        timeout=api_config.get('timeout', 60),
        retry_attempts=api_config.get('retry_attempts', 3),
        retry_delay=api_config.get('retry_delay', 5),
        model=api_config.get('model', 'gpt-4.1-mini-2025-04-14'),
        save_responses=save_responses,
        response_dir=response_dir
    )
    
    logger.info(f"使用模型: {four_o_client.model}")
    
    # 处理各个set目录
    results = {"success": 0, "failure": 0}
    all_failure_details = {}  # 收集所有失败的详细情况
    
    # 如果未指定set_numbers，则使用默认的1-5
    if not set_numbers:
        set_numbers = list(range(1, 6))  # set_1到set_5
    
    for set_num in set_numbers:
        set_dir = os.path.join(input_dir, f"{set_prefix}{set_num}")
        if not os.path.exists(set_dir):
            logger.warning(f"目录不存在: {set_dir}")
            continue
        
        logger.info(f"处理目录: {set_dir}")
        
        # 获取HTML文件列表
        html_files = sorted(glob.glob(os.path.join(set_dir, "*.html")))
        if not html_files:
            logger.warning(f"在目录 {set_dir} 中未找到HTML文件")
            continue
        
        # 限制处理文件数量，-1表示处理全部文件
        if max_files > 0 and len(html_files) > max_files:
            logger.info(f"限制处理文件数为 {max_files} (共找到 {len(html_files)} 个文件)")
            html_files = html_files[:max_files]
        else:
            logger.info(f"找到 {len(html_files)} 个HTML文件，将处理全部文件")
        
        # 为当前set创建输出目录
        set_output_dir = os.path.join(output_base_dir, f"{set_prefix}{set_num}")
        os.makedirs(set_output_dir, exist_ok=True)
        
        # 多进程处理
        process_func = partial(
            process_single_file, 
            output_base_dir=set_output_dir,
            mapping_dir=mapping_dir,
            four_o_client=four_o_client
        )
        
        set_failure_details = {}  # 收集当前set的失败详情
        
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = [executor.submit(process_func, file) for file in html_files]
            
            # 使用tqdm显示进度
            set_success = 0
            set_failure = 0
            
            for future in tqdm(futures, total=len(futures), desc=f"处理{set_prefix}{set_num}"):
                try:
                    success, file_id, message = future.result()
                    if success:
                        set_success += 1
                        results["success"] += 1
                    else:
                        set_failure += 1
                        results["failure"] += 1
                        logger.warning(f"文件{file_id}处理失败: {message}")
                        # 保存失败详情
                        set_failure_details[file_id] = message
                        all_failure_details[f"{set_prefix}{set_num}:{file_id}"] = message
                except Exception as e:
                    set_failure += 1
                    results["failure"] += 1
                    error_msg = f"获取任务结果时出错: {str(e)}"
                    logger.error(error_msg)
                    # 保存异常详情
                    if "unknown_error" not in set_failure_details:
                        set_failure_details["unknown_error"] = []
                    set_failure_details["unknown_error"].append(error_msg)
                    all_failure_details[f"{set_prefix}{set_num}:unknown_error"] = error_msg
        
        # 保存当前set的失败详情
        if set_failure_details:
            failure_log_file = os.path.join(set_output_dir, "failure_details.json")
            with open(failure_log_file, 'w', encoding='utf-8') as f:
                json.dump(set_failure_details, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存{set_prefix}{set_num}的失败详情到: {failure_log_file}")
        
        logger.info(f"{set_prefix}{set_num}处理完成. 成功: {set_success}, 失败: {set_failure}")
    
    # 保存所有失败详情
    if all_failure_details:
        all_failures_file = os.path.join(output_base_dir, "all_failures_summary.json")
        with open(all_failures_file, 'w', encoding='utf-8') as f:
            json.dump(all_failure_details, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存所有失败详情到: {all_failures_file}")
    
    return results

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='多进程处理PMC数据集')
    
    parser.add_argument('--config', default='config/default.yaml', help='配置文件路径')
    parser.add_argument('--input_dir', default='/ai/data-container/lwy/pmc_data/1-15/1-15',
                        help='输入目录路径，包含set1-5目录')
    parser.add_argument('--output_dir', default='output/pmc_data',
                        help='输出根目录')
    parser.add_argument('--mapping_dir', default='config/mapping',
                        help='映射目录')
    parser.add_argument('--api_endpoint', default=None,
                        help='4o API端点')
    parser.add_argument('--api_key', default=None,
                        help='4o API密钥')
    parser.add_argument('--max_files', type=int, default=-1,
                        help='每个set的最大处理文件数，设置为-1表示处理全部文件')
    parser.add_argument('--num_processes', type=int, default=192,
                        help='使用的进程数，默认为CPU核心数的75%')
    parser.add_argument('--set_prefix', default='set_',
                        help='数据集目录前缀')
    parser.add_argument('--sets', type=str, default='4',
                        help='要处理的set编号，用逗号分隔，例如"1,3,5"表示处理set_1,set_3,set_5')
    # 添加响应保存相关参数
    parser.add_argument('--save_responses', action='store_true',
                        help='是否保存API请求和响应')
    parser.add_argument('--response_dir', type=str, default=None,
                        help='API响应保存目录')
    # 添加模型相关参数
    parser.add_argument('--model', default='gpt-4.1-mini-2025-04-14',
                        help='使用的模型名称')
    
    args = parser.parse_args()
    
    # 加载配置文件
    config = load_config(args.config)
    
    # 从配置文件获取默认值
    default_api_config = config['stage_two']['api']
    
    # API配置
    api_endpoint = args.api_endpoint or default_api_config['endpoint']
    api_key = args.api_key or default_api_config['key']
    
    # 处理环境变量形式的API密钥
    if api_key and api_key.startswith('${') and api_key.endswith('}'):
        env_var = api_key[2:-1]
        api_key = os.environ.get(env_var)
        if not api_key:
            logger.error(f"环境变量 {env_var} 未设置或为空")
            return 1
    
    if not api_key:
        logger.error("未提供API密钥，请通过--api_key参数或配置文件设置")
        return 1
    
    # 其他配置
    save_responses = args.save_responses or default_api_config.get('save_responses', False)
    response_dir = args.response_dir or os.path.join(config['paths'].get('log_dir', 'logs'), 'api_responses')
    num_processes = args.num_processes or config['general'].get('max_workers', 192)
    
    # 解析要处理的set编号
    try:
        set_numbers = [int(s.strip()) for s in args.sets.split(',') if s.strip()]
        if not set_numbers:
            logger.error("未指定要处理的set编号")
            return 1
        logger.info(f"将处理以下set: {set_numbers}")
    except ValueError:
        logger.error(f"无效的set编号格式: {args.sets}，应为逗号分隔的数字")
        return 1
    
    start_time = time.time()
    
    try:
        results = process_dataset(
            input_dir=args.input_dir,
            output_base_dir=args.output_dir,
            mapping_dir=args.mapping_dir,
            api_endpoint=api_endpoint,
            api_key=api_key,
            max_files=args.max_files,
            num_processes=num_processes,
            set_prefix=args.set_prefix,
            set_numbers=set_numbers,
            save_responses=save_responses,
            response_dir=response_dir,
            config=config
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"处理完成. 总计成功: {results['success']}, 失败: {results['failure']}")
        logger.info(f"总耗时: {duration:.2f}秒 ({duration/60:.2f}分钟)")
        
        return 0 if results["failure"] == 0 else 1
        
    except Exception as e:
        logger.error(f"处理过程中出错: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
