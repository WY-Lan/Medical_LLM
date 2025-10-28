#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合运行脚本：多线程执行所有阶段
- 第一阶段：HTML转JSON
- 第二阶段：使用AI API生成数据集
- 第三阶段：生成CoT
"""

import os
import sys
import yaml
import argparse
import logging
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Dict, Any, List, Optional
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入各阶段所需组件
from src.stage_one.html_to_json import HTMLToJSONConverter
from src.api.four_o_client import FourOClient
from src.stage_two.content_extractor import ContentExtractor
from src.stage_three.cot_generator import CoTGenerator

# 创建日志目录
os.makedirs('logs/all_stages', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/all_stages/run.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)

def load_config(config_path: str) -> dict:
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
    parser = argparse.ArgumentParser(description='运行所有阶段')
    
    # 基本配置
    parser.add_argument('--config', default='config/default.yaml', help='配置文件路径')
    parser.add_argument('--max-workers', type=int, help='最大线程数（覆盖配置文件）')
    parser.add_argument('--max-items', type=int, help='最大处理文件数（覆盖配置文件）')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='日志级别')
    
    # 阶段选择
    parser.add_argument('--start-stage', type=int, choices=[1, 2, 3], default=1, help='起始阶段（1, 2, 或 3）')
    parser.add_argument('--end-stage', type=int, choices=[1, 2, 3], default=3, help='结束阶段（1, 2, 或 3）')
    
    # 目录配置
    parser.add_argument('--input-dir', help='第一阶段输入目录（HTML文件）')
    parser.add_argument('--mapping-dir', help='映射目录路径')
    parser.add_argument('--output-base-dir', help='输出基础目录')
    
    # API配置
    parser.add_argument('--api-endpoint', help='4o API端点（覆盖配置文件）')
    parser.add_argument('--api-key', help='4o API密钥（覆盖配置文件）')
    parser.add_argument('--model', help='使用的模型名称（覆盖配置文件）')
    parser.add_argument('--save-responses', action='store_true', help='保存API请求和响应')
    parser.add_argument('--response-dir', type=str, help='API响应保存目录')
    
    return parser.parse_args()

def setup_logging(log_level: str) -> None:
    """设置日志级别"""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    for handler in logging.root.handlers:
        handler.setLevel(numeric_level)
    logging.root.setLevel(numeric_level)
    logger.info(f"日志级别设置为: {log_level}")

# ==== 第一阶段函数 ====
def run_stage_one(config: dict, args) -> Tuple[int, int]:
    """运行第一阶段：HTML转JSON"""
    logger.info("====== 开始运行第一阶段：HTML转JSON ======")
    
    try:
        # 从配置创建转换器
        converter = HTMLToJSONConverter.from_config_file(args.config)
        
        # 如果命令行有覆盖参数，更新配置
        if args.input_dir:
            converter.input_dir = args.input_dir
        if args.output_base_dir:
            converter.output_dir = os.path.join(args.output_base_dir, 'stage_one')
        if args.max_workers:
            converter.max_workers = args.max_workers
        if args.max_items:
            converter.max_items = args.max_items
            
        # 打印运行信息
        logger.info(f"输入目录: {converter.input_dir}")
        logger.info(f"输出目录: {converter.output_dir}")
        logger.info(f"最大线程数: {converter.max_workers}")
        logger.info(f"最大处理文件数: {converter.max_items if converter.max_items else '不限'}")
    
        # 运行转换
        success_count, failure_count = converter.run()
        
        # 输出处理结果
        logger.info(f"第一阶段完成. 成功: {success_count}, 失败: {failure_count}")
        
        return success_count, failure_count
        
    except Exception as e:
        logger.error(f"运行第一阶段时出错: {str(e)}")
        return 0, sys.maxsize  # 返回最大错误数，表示整个阶段失败

# ==== 第二阶段函数 ====
def process_file_stage_two(file_path: Path, content_extractor: ContentExtractor, output_dir: Path) -> Tuple[bool, str, dict]:
    """
    处理单个文件（第二阶段）
    
    参数:
        file_path: 输入文件路径
        content_extractor: 内容提取器实例
        output_dir: 输出目录
        
    返回:
        (是否成功, 错误信息, token使用统计)
    """
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

def run_stage_two(config: dict, args, stage_one_output: str) -> Tuple[int, int, dict]:
    """运行第二阶段：使用AI API生成数据集"""
    logger.info("====== 开始运行第二阶段：使用AI API生成数据集 ======")
    
    try:
        # 设置输入/输出目录
        input_dir = stage_one_output
        output_base_dir = args.output_base_dir or config['paths']['output_dir']
        output_dir = os.path.join(output_base_dir, 'stage_two')
        mapping_dir = args.mapping_dir or config['paths']['mapping_dir']
        max_workers = args.max_workers or config['general']['max_workers']
        max_items = args.max_items or config.get('general', {}).get('max_items')
        
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
        api_endpoint = args.api_endpoint or api_config['endpoint']
        api_key = args.api_key or api_config['key']
        api_key = os.environ.get(api_key[2:-1]) if api_key.startswith('${') and api_key.endswith('}') else api_key
        model = args.model or api_config.get('model', 'qwq-plus')
        response_dir = args.response_dir or os.path.join(config['paths'].get('log_dir', 'logs'), 'api_responses')
        
        api_client = FourOClient(
            api_endpoint=api_endpoint,
            api_key=api_key,
            timeout=api_config.get('timeout', 60),
            retry_attempts=api_config.get('retry_attempts', 3),
            retry_delay=api_config.get('retry_delay', 5),
            model=model,
            save_responses=args.save_responses if args.save_responses is not None else api_config.get('save_responses', False),
            response_dir=response_dir
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
            return 0, 0, {}
        
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
                executor.submit(process_file_stage_two, file_path, content_extractor, Path(output_dir)): file_path
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
        
        return success_count, failure_count, {"output_dir": output_dir, "token_usage": total_token_usage, "requests": total_requests}
        
    except Exception as e:
        logger.error(f"运行第二阶段时出错: {str(e)}", exc_info=True)
        return 0, sys.maxsize, {}  # 返回最大错误数，表示整个阶段失败

# ==== 第三阶段函数 ====
def process_file_stage_three(file_path: Path, cot_generator: CoTGenerator, output_dir: str) -> Tuple[bool, str, dict]:
    """
    处理单个文件（第三阶段）
    
    参数:
        file_path: 输入文件路径
        cot_generator: CoT生成器实例
        output_dir: 输出目录
        
    返回:
        (成功状态, 错误信息, token使用统计)
    """
    try:
        # 添加调试信息
        logger.debug(f"开始处理文件: {file_path}")
        
        # 检查case_main字段是否存在且有内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
            
            cases = input_data.get("cases", {})
            if not cases:
                error_msg = f"输入文件缺少cases字段: {file_path.name}"
                logger.error(error_msg)
                return False, error_msg, {}
                
        except json.JSONDecodeError as e:
            error_msg = f"无法解析JSON文件: {file_path.name}, 错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {}
            
        except Exception as e:
            error_msg = f"检查case_main字段时出错: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, {}
        
        # 重置token使用统计
        cot_generator.four_o_client.reset_token_usage()
        
        # 处理文件
        success = cot_generator.process_file(file_path)
        
        # 获取token使用统计
        token_usage = cot_generator.four_o_client.get_token_usage()
        
        if not success:
            logger.warning(f"CoT生成器处理文件返回失败: {file_path.name}")
            return False, "CoT生成器处理失败", token_usage
        
        logger.info(f"文件处理成功: {file_path.name}")
        
        return True, "", token_usage
        
    except Exception as e:
        logger.error(f"处理文件 {file_path.name} 时出错: {str(e)}")
        return False, str(e), {}

def run_stage_three(config: dict, args, stage_two_output: str) -> Tuple[int, int, dict]:
    """运行第三阶段：生成CoT"""
    logger.info("====== 开始运行第三阶段：生成CoT ======")
    
    try:
        # 设置输入/输出目录
        input_dir = stage_two_output
        output_base_dir = args.output_base_dir or config['paths']['output_dir']
        output_dir = os.path.join(output_base_dir, 'stage_three')
        max_items = args.max_items or config.get('general', {}).get('max_items')
        max_workers = args.max_workers or config['general']['max_workers']
        
        # API配置
        api_config = config['stage_three']['api']
        api_endpoint = args.api_endpoint or api_config['endpoint']
        api_key = args.api_key or api_config['key']
        api_key = os.environ.get(api_key[2:-1]) if api_key.startswith('${') and api_key.endswith('}') else api_key
        model = args.model or api_config.get('model', 'gpt-4o')
        response_dir = args.response_dir or os.path.join(config['paths'].get('log_dir', 'logs'), 'api_responses')
        
        logger.info(f"输入目录: {input_dir}")
        logger.info(f"输出目录: {output_dir}")
        logger.info(f"4o API端点: {api_endpoint}")
        logger.info(f"模型: {model}")
        logger.info(f"最大处理文件数: {max_items if max_items else '不限'}")
        logger.info(f"最大线程数: {max_workers}")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建四天客户端
        four_o_client = FourOClient(
            api_endpoint=api_endpoint,
            api_key=api_key,
            timeout=api_config.get('timeout', 60),
            retry_attempts=api_config.get('retry_attempts', 3),
            retry_delay=api_config.get('retry_delay', 5),
            model=model,
            save_responses=args.save_responses if args.save_responses is not None else api_config.get('save_responses', False),
            response_dir=response_dir
        )
        
        # 创建CoT生成器
        cot_generator = CoTGenerator(
            four_o_client=four_o_client,
            output_dir=output_dir
        )
        
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
            return 0, 0, {}
            
        # 批量处理文件（多线程）
        success_count = 0
        failure_count = 0
        case_main_failure_count = 0
        total_token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        total_requests = 0
        failure_details = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(process_file_stage_three, file_path, cot_generator, output_dir): file_path
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
                        # 记录失败详情
                        failure_details[file_path.name] = error
                        logger.error(f"处理文件失败: {file_path.name}, 错误: {error}")
                        
                        # 检查是否为case_main相关错误
                        if "case_main" in error.lower():
                            case_main_failure_count += 1
                            logger.warning(f"检测到case_main相关错误: {file_path.name}")
                except Exception as e:
                    failure_count += 1
                    failure_details[file_path.name] = str(e)
                    logger.error(f"处理文件时发生异常: {file_path.name}, 错误: {str(e)}")
        
        # 输出处理结果
        logger.info(f"第三阶段完成. 成功: {success_count}, 失败: {failure_count}")
        if case_main_failure_count > 0:
            logger.info(f"其中 {case_main_failure_count} 个失败是由于case_main字段缺失或为空")
            
        # 保存失败详情
        if failure_count > 0:
            failure_log_file = os.path.join(output_dir, 'failure_details.json')
            with open(failure_log_file, 'w', encoding='utf-8') as f:
                json.dump(failure_details, f, ensure_ascii=False, indent=2)
            logger.info(f"已保存失败详情到: {failure_log_file}")
        
        # 输出token使用汇总
        avg_tokens_per_file = total_token_usage["total_tokens"] / success_count if success_count > 0 else 0
        avg_requests_per_file = total_requests / success_count if success_count > 0 else 0
        logger.info(f"API Token使用统计:")
        logger.info(f"  - 总请求次数: {total_requests}")
        logger.info(f"  - Prompt Tokens: {total_token_usage['prompt_tokens']}")
        logger.info(f"  - Completion Tokens: {total_token_usage['completion_tokens']}")
        logger.info(f"  - 总Tokens: {total_token_usage['total_tokens']}")
        logger.info(f"  - 平均每个文件: {avg_tokens_per_file:.1f} tokens, {avg_requests_per_file:.1f} 请求")
        
        return success_count, failure_count, {"token_usage": total_token_usage, "requests": total_requests}
        
    except Exception as e:
        logger.error(f"运行第三阶段时出错: {str(e)}")
        return 0, sys.maxsize, {}  # 返回最大错误数，表示整个阶段失败

def main():
    """主函数"""
    start_time = time.time()
    
    # 解析命令行参数
    args = parse_args()
    
    # 加载配置文件
    config = load_config(args.config)
    
    # 设置日志级别
    log_level = args.log_level or config.get('general', {}).get('log_level', 'INFO')
    setup_logging(log_level)
    
    # 打印开始信息
    logger.info("========== 开始综合运行脚本 ==========")
    logger.info(f"配置文件: {args.config}")
    logger.info(f"起始阶段: {args.start_stage}")
    logger.info(f"结束阶段: {args.end_stage}")
    
    # 阶段结果存储
    stage_results = {
        "stage_one": {"success": 0, "failure": 0, "output_dir": ""},
        "stage_two": {"success": 0, "failure": 0, "output_dir": "", "token_usage": {}, "requests": 0},
        "stage_three": {"success": 0, "failure": 0, "token_usage": {}, "requests": 0}
    }
    
    # 设置输出基础目录
    output_base_dir = args.output_base_dir or config['paths']['output_dir']
    
    # 预设阶段输出目录
    stage_one_output_dir = os.path.join(output_base_dir, 'stage_one')
    stage_two_output_dir = os.path.join(output_base_dir, 'stage_two')
    
    # === 第一阶段：HTML转JSON ===
    if args.start_stage <= 1 <= args.end_stage:
        success_count, failure_count = run_stage_one(config, args)
        stage_results["stage_one"]["success"] = success_count
        stage_results["stage_one"]["failure"] = failure_count
        stage_results["stage_one"]["output_dir"] = stage_one_output_dir
        
        if failure_count > 0 and success_count == 0:
            logger.error("第一阶段完全失败，无法继续执行后续阶段")
            return 1
    else:
        logger.info("跳过第一阶段")
    
    # === 第二阶段：使用AI API生成数据集 ===
    if args.start_stage <= 2 <= args.end_stage:
        # 如果没有运行第一阶段或第一阶段失败，使用预设目录
        input_dir = stage_results["stage_one"]["output_dir"] if args.start_stage <= 1 else stage_one_output_dir
        
        success_count, failure_count, extra_info = run_stage_two(config, args, input_dir)
        stage_results["stage_two"]["success"] = success_count
        stage_results["stage_two"]["failure"] = failure_count
        
        if extra_info:
            stage_results["stage_two"]["output_dir"] = extra_info.get("output_dir", stage_two_output_dir)
            stage_results["stage_two"]["token_usage"] = extra_info.get("token_usage", {})
            stage_results["stage_two"]["requests"] = extra_info.get("requests", 0)
        
        if failure_count > 0 and success_count == 0:
            logger.error("第二阶段完全失败，无法继续执行后续阶段")
            return 1
    else:
        logger.info("跳过第二阶段")
    
    # === 第三阶段：生成CoT ===
    if args.start_stage <= 3 <= args.end_stage:
        # 如果没有运行第二阶段或第二阶段失败，使用预设目录
        input_dir = stage_results["stage_two"]["output_dir"] if args.start_stage <= 2 and stage_results["stage_two"]["success"] > 0 else stage_two_output_dir
        
        success_count, failure_count, extra_info = run_stage_three(config, args, input_dir)
        stage_results["stage_three"]["success"] = success_count
        stage_results["stage_three"]["failure"] = failure_count
        
        if extra_info:
            stage_results["stage_three"]["token_usage"] = extra_info.get("token_usage", {})
            stage_results["stage_three"]["requests"] = extra_info.get("requests", 0)
    else:
        logger.info("跳过第三阶段")
    
    # 计算总运行时间
    elapsed_time = time.time() - start_time
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # 输出总结
    logger.info("========== 综合运行完成 ==========")
    logger.info(f"总运行时间: {int(hours)}小时 {int(minutes)}分钟 {seconds:.2f}秒")
    logger.info("各阶段结果:")
    
    # 第一阶段结果
    if args.start_stage <= 1 <= args.end_stage:
        logger.info(f"  - 第一阶段: 成功={stage_results['stage_one']['success']}, 失败={stage_results['stage_one']['failure']}")
    
    # 第二阶段结果
    if args.start_stage <= 2 <= args.end_stage:
        logger.info(f"  - 第二阶段: 成功={stage_results['stage_two']['success']}, 失败={stage_results['stage_two']['failure']}")
        token_usage = stage_results["stage_two"].get("token_usage", {})
        if token_usage:
            logger.info(f"    * API请求: {stage_results['stage_two']['requests']}")
            logger.info(f"    * 总Token: {token_usage.get('total_tokens', 0)}")
    
    # 第三阶段结果
    if args.start_stage <= 3 <= args.end_stage:
        logger.info(f"  - 第三阶段: 成功={stage_results['stage_three']['success']}, 失败={stage_results['stage_three']['failure']}")
        token_usage = stage_results["stage_three"].get("token_usage", {})
        if token_usage:
            logger.info(f"    * API请求: {stage_results['stage_three']['requests']}")
            logger.info(f"    * 总Token: {token_usage.get('total_tokens', 0)}")
    
    # 计算总成功和失败数
    total_success = sum([stage_results[f"stage_{i}"]["success"] for i in range(1, 4) if args.start_stage <= i <= args.end_stage])
    total_failure = sum([stage_results[f"stage_{i}"]["failure"] for i in range(1, 4) if args.start_stage <= i <= args.end_stage])
    
    # 计算总API使用
    total_api_requests = stage_results["stage_two"].get("requests", 0) + stage_results["stage_three"].get("requests", 0)
    total_api_tokens = 0
    stage_two_tokens = stage_results["stage_two"].get("token_usage", {}).get("total_tokens", 0)
    stage_three_tokens = stage_results["stage_three"].get("token_usage", {}).get("total_tokens", 0)
    total_api_tokens = stage_two_tokens + stage_three_tokens
    
    logger.info(f"总计: 成功={total_success}, 失败={total_failure}")
    if args.start_stage <= 2 or args.end_stage >= 3:  # 如果包含使用API的阶段
        logger.info(f"总API使用: {total_api_requests}请求, {total_api_tokens}tokens")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 