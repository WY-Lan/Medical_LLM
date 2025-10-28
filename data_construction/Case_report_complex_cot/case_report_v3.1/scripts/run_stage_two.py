#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二阶段运行脚本：使用AI API生成数据集
优化版本：使用配置文件和新的AI客户端
"""

import os
import sys
import yaml
import argparse
import logging
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.four_o_client import FourOClient
from src.stage_two.content_extractor import ContentExtractor

def load_config(config_path):
    """加载YAML配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logging.error(f"加载配置文件时出错: {str(e)}")
        raise

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='运行第二阶段: 使用AI API生成数据集')
    
    parser.add_argument('--config', default='config/default.yaml', help='配置文件路径')
    parser.add_argument('--input-dir', help='输入目录路径，包含JSON文件（覆盖配置文件）')
    parser.add_argument('--output-dir', help='输出目录路径，存储生成的数据集（覆盖配置文件）')
    parser.add_argument('--mapping-dir', help='映射目录路径（覆盖配置文件）')
    parser.add_argument('--max-workers', type=int, help='最大线程数（覆盖配置文件）')
    parser.add_argument('--max-items', type=int, help='最大处理文件数（覆盖配置文件）')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别（覆盖配置文件）')
    
    # 添加响应保存目录参数
    parser.add_argument('--response-dir', type=str, default='logs/api_responses',
                        help='API请求和响应保存目录')
    parser.add_argument('--save-responses', action='store_true',
                        help='是否保存API请求和响应')
    
    return parser.parse_args()

def setup_logging(log_dir='logs/stage_two', log_level='INFO'):
    """设置日志记录"""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 配置日志
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'{log_dir}/run.log', mode='a')
        ]
    )
    
    logging.info(f"日志级别设置为: {log_level}")

def process_file(file_path: Path, content_extractor: ContentExtractor, output_dir: Path) -> Tuple[bool, str, dict]:
    """
    处理单个文件
    
    参数:
        file_path: 输入文件路径
        content_extractor: 内容提取器实例
        output_dir: 输出目录
        
    返回:
        (是否成功, 错误信息, token使用统计)
    """
    logger = logging.getLogger(__name__)
    try:
        # 在处理前重置API客户端的token统计
        content_extractor.api_client.reset_token_usage()
        
        # 读取输入文件
        with open(file_path, 'r', encoding='utf-8') as f:
            article_data = json.load(f)
        
        # 处理文章
        result = content_extractor.process_article(article_data)
        
        # 获取token使用统计
        token_usage = content_extractor.api_client.get_token_usage()
        
        # 将token使用信息添加到结果中
        result["metadata"]["token_usage"] = token_usage["token_usage"]
        result["metadata"]["api_requests"] = token_usage["request_count"]
        
        # 保存结果
        output_file = output_dir / file_path.name
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return True, "", token_usage
    except json.JSONDecodeError as e:
        error_msg = f"JSON解析错误: {str(e)}"
        logger.error(f"{file_path.name}: {error_msg}")
        return False, error_msg, {}
    except (IOError, OSError) as e:
        error_msg = f"文件操作错误: {str(e)}"
        logger.error(f"{file_path.name}: {error_msg}")
        return False, error_msg, {}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"{file_path.name}: 未知错误: {error_msg}")
        return False, error_msg, {}

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    try:
        # 加载配置文件
        config = load_config(args.config)
        
        # 设置日志
        log_level = args.log_level or config.get('general', {}).get('log_level', 'INFO')
        log_dir = os.path.join(config.get('paths', {}).get('log_dir', 'logs'), 'stage_two')
        setup_logging(log_dir, log_level)
        
        # 输出版本信息
        logger = logging.getLogger(__name__)
        logger.info("运行第二阶段: 使用AI API生成数据集 (优化版本)")
        
        # 合并配置和命令行参数
        input_dir = args.input_dir or os.path.join(config['paths']['output_dir'], 'stage_one')
        output_dir = args.output_dir or os.path.join(config['paths']['output_dir'], 'stage_two')
        mapping_dir = args.mapping_dir or config['paths']['mapping_dir']
        max_workers = args.max_workers or config['general']['max_workers']
        max_items = args.max_items or config.get('general', {}).get('max_items')
        
        logger.info(f"配置文件: {args.config}")
        logger.info(f"输入目录: {input_dir}")
        logger.info(f"输出目录: {output_dir}")
        logger.info(f"映射目录: {mapping_dir}")
        logger.info(f"最大线程数: {max_workers}")
        logger.info(f"最大处理文件数: {max_items if max_items else '不限'}")
        
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(mapping_dir, exist_ok=True)
        
        # 创建API客户端
        api_config = config['stage_two']['api']
        api_client = FourOClient(
            api_endpoint=api_config['endpoint'],
            api_key=api_config['key'],
            timeout=api_config.get('timeout', 60),
            retry_attempts=api_config.get('retry_attempts', 3),
            retry_delay=api_config.get('retry_delay', 5),
            model=api_config.get('model', 'qwq-plus'),
            save_responses=args.save_responses if args.save_responses is not None else api_config.get('save_responses', False),
            response_dir=args.response_dir if args.response_dir else os.path.join(config['paths'].get('log_dir', 'logs'), 'api_responses')
        )
        
        # 创建内容提取器
        content_extractor = ContentExtractor(api_client, mapping_dir)
        logger.info("成功创建内容提取器实例")
        
        # 获取输入文件列表
        input_dir_path = Path(input_dir)
        json_files = list(input_dir_path.glob('*.json'))
        
        # 根据max_items限制处理数量
        if max_items is not None and len(json_files) > max_items:
            logger.info(f"限制处理文件数为 {max_items} (共找到 {len(json_files)} 个文件)")
            json_files = json_files[:max_items]
        else:
            logger.info(f"找到 {len(json_files)} 个JSON文件")
            
        if not json_files:
            logger.warning(f"未找到JSON文件")
            return 0
        
        # 批量处理文件
        success_count = 0
        failure_count = 0
        failure_details = {}
        total_token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        total_requests = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(process_file, file_path, content_extractor, Path(output_dir)): file_path
                for file_path in json_files
            }
            
            # 处理结果
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    success, error, token_usage = future.result()
                    if success:
                        success_count += 1
                        logger.info(f"成功处理文件: {file_path.name}")
                        
                        # 累加token使用统计
                        if token_usage:
                            file_token_usage = token_usage.get("token_usage", {})
                            total_token_usage["prompt_tokens"] += file_token_usage.get("prompt_tokens", 0)
                            total_token_usage["completion_tokens"] += file_token_usage.get("completion_tokens", 0)
                            total_token_usage["total_tokens"] += file_token_usage.get("total_tokens", 0)
                            total_requests += token_usage.get("request_count", 0)
                            
                            # 输出每个文件的token使用情况
                            logger.info(f"文件 {file_path.name} 消耗tokens: {file_token_usage.get('total_tokens', 0)}, API请求数: {token_usage.get('request_count', 0)}")
                    else:
                        failure_count += 1
                        failure_details[file_path.name] = error
                        logger.error(f"处理文件失败: {file_path.name}, 错误: {error}")
                except Exception as e:
                    failure_count += 1
                    failure_details[file_path.name] = str(e)
                    logger.error(f"处理文件时发生异常: {file_path.name}, 错误: {str(e)}")
        
        # 输出处理结果
        logger.info(f"第二阶段完成. 成功: {success_count}, 失败: {failure_count}")
        
        # 输出token使用汇总
        avg_tokens_per_file = total_token_usage["total_tokens"] / success_count if success_count > 0 else 0
        avg_requests_per_file = total_requests / success_count if success_count > 0 else 0
        logger.info(f"API Token使用统计:")
        logger.info(f"  - 总请求次数: {total_requests}")
        logger.info(f"  - Prompt Tokens: {total_token_usage['prompt_tokens']}")
        logger.info(f"  - Completion Tokens: {total_token_usage['completion_tokens']}")
        logger.info(f"  - 总Tokens: {total_token_usage['total_tokens']}")
        logger.info(f"  - 平均每个文件: {avg_tokens_per_file:.1f} tokens, {avg_requests_per_file:.1f} 请求")
        
        # 如果有失败项，记录详情
        if failure_count > 0:
            failed_files = ', '.join(list(failure_details.keys())[:5])
            if len(failure_details) > 5:
                failed_files += f"... 等 {len(failure_details)} 个文件"
            logger.warning(f"失败文件: {failed_files}")
            
            # 保存失败详情
            failure_file = os.path.join(output_dir, 'failure_details.json')
            with open(failure_file, 'w', encoding='utf-8') as f:
                json.dump(failure_details, f, ensure_ascii=False, indent=2)
            logger.info(f"详细失败信息已保存到: {failure_file}")
        
        return 0 if failure_count == 0 else 1
        
    except Exception as e:
        logging.error(f"运行第二阶段时出错: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
