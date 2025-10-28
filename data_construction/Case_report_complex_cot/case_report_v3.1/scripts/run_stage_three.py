#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三阶段运行脚本：生成CoT
"""

import os
import sys
import yaml
import argparse
import logging
from pathlib import Path
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.stage_three.cot_generator import CoTGenerator
from src.api.four_o_client import FourOClient

# 确保日志目录存在
os.makedirs('logs/stage_three', exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/stage_three/run.log', mode='a')
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
    parser = argparse.ArgumentParser(description='运行第三阶段: 生成CoT')
    
    parser.add_argument('--config', default='config/default.yaml', help='配置文件路径')
    parser.add_argument('--input-dir', help='输入目录路径，包含第二阶段生成的JSON文件（覆盖配置文件）')
    parser.add_argument('--output-dir', help='输出目录路径，存储CoT结果（覆盖配置文件）')
    parser.add_argument('--api-endpoint', help='4o API端点（覆盖配置文件）')
    parser.add_argument('--api-key', help='4o API密钥（覆盖配置文件）')
    parser.add_argument('--model', help='使用的模型名称（覆盖配置文件）')
    parser.add_argument('--max-items', type=int, help='最大处理文件数（覆盖配置文件）')
    parser.add_argument('--save-responses', action='store_true', help='保存API请求和响应')
    parser.add_argument('--response-dir', type=str, default='logs/api_responses', help='API响应保存目录')
    
    return parser.parse_args()

def process_file(file_path, cot_generator, output_dir):
    """
    处理单个文件，并返回token使用统计
    
    参数:
        file_path: 输入文件路径
        cot_generator: CoT生成器实例
        output_dir: 输出目录
        
    返回:
        (成功状态, 错误信息, token使用统计)
    """
    try:
        # 添加调试信息
        logger.info(f"开始处理文件: {file_path}")
        logger.info(f"文件完整路径: {file_path.absolute()}")
        
        # 检查case_main字段是否存在且有内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
            
            # 调试信息：打印文件解析后的结构
            logger.info(f"文件解析成功，包含keys: {list(input_data.keys())}")
            if "cases" in input_data:
                logger.info(f"cases键包含: {list(input_data['cases'].keys())}")
                
            cases = input_data.get("cases", {})
            if not cases:
                error_msg = f"输入文件缺少cases字段: {file_path.name}"
                logger.error(error_msg)
                return False, error_msg, {}
            
            # 检查cases中是否包含有效数据
            valid_data_found = False
            logger.info(f"检查cases字段，包含 {len(cases)} 个键")
            
            # 特殊处理：如果case_main直接作为cases的子项
            if "case_main" in cases:
                logger.info("发现cases.case_main直接模式")
                case_main = cases["case_main"]
                
                # 检查case_main是否为有效对象
                if isinstance(case_main, dict):
                    logger.info(f"case_main是字典，包含keys: {list(case_main.keys())}")
                    
                    # 检查每个关键字段
                    # 1. basic_info
                    basic_info = case_main.get("basic_info", "")
                    has_basic_info = basic_info and len(basic_info.strip()) > 0
                    logger.info(f"basic_info: '{basic_info[:50]}...'，有效: {has_basic_info}")
                    
                    # 2. examination
                    examination = case_main.get("examination", {})
                    logger.info(f"examination类型: {type(examination)}")
                    exam_items = examination.get("exam_items", "") if isinstance(examination, dict) else ""
                    exam_results = examination.get("exam_results", "") if isinstance(examination, dict) else ""
                    has_examination = (exam_items and len(exam_items.strip()) > 0) or (exam_results and len(exam_results.strip()) > 0)
                    logger.info(f"exam_items长度: {len(exam_items)}, exam_results长度: {len(exam_results)}, 有效: {has_examination}")
                    
                    # 3. diagnosis
                    diagnosis = case_main.get("diagnosis", "")
                    has_diagnosis = diagnosis and len(diagnosis.strip()) > 0
                    logger.info(f"diagnosis: '{diagnosis}'，有效: {has_diagnosis}")
                    
                    # 4. raw_data
                    raw_data = case_main.get("raw_data", {})
                    logger.info(f"raw_data类型: {type(raw_data)}")
                    if isinstance(raw_data, dict):
                        case_content = raw_data.get("case_content", "")
                        discussion = raw_data.get("discussion", "")
                        has_raw_data = (case_content and len(case_content.strip()) > 0) or (discussion and len(discussion.strip()) > 0)
                        logger.info(f"case_content长度: {len(case_content)}, discussion长度: {len(discussion)}, 有效: {has_raw_data}")
                    else:
                        has_raw_data = False
                        logger.warning(f"raw_data不是字典: {raw_data}")
                    
                    # 打印每个字段的检查结果
                    logger.info(f"字段检查结果 - basic_info: {has_basic_info}, examination: {has_examination}, diagnosis: {has_diagnosis}, raw_data: {has_raw_data}")
                    
                    # 只要有任意一个关键字段有内容，就认为是有效的
                    if has_basic_info or has_examination or has_diagnosis or has_raw_data:
                        valid_data_found = True
                        logger.info(f"找到有效数据 [case_main直接模式]")
                else:
                    logger.warning(f"case_main不是字典: {type(case_main)}")
            else:
                # 常规处理：遍历cases中的每个键，查找case_main子项
                for case_id, case_data in cases.items():
                    logger.info(f"检查case_id: {case_id}")
                    
                    # 检查是否存在case_main结构
                    if "case_main" not in case_data:
                        logger.warning(f"case_id {case_id} 缺少case_main结构")
                        
                        # 如果case_data本身就含有常见的case字段，可能是直接的case数据
                        if isinstance(case_data, dict) and ("basic_info" in case_data or "examination" in case_data or "diagnosis" in case_data):
                            logger.info(f"case_id {case_id} 可能是直接的case数据，检查其内容")
                            
                            # 将case_data直接作为case_main处理
                            case_main = case_data
                            
                            # 检查各字段是否有内容
                            # 1. basic_info
                            basic_info = case_main.get("basic_info", "")
                            has_basic_info = basic_info and len(basic_info.strip()) > 0
                            logger.info(f"basic_info: '{basic_info[:50]}...'，有效: {has_basic_info}")
                            
                            # 2. examination
                            examination = case_main.get("examination", {})
                            exam_items = examination.get("exam_items", "") if isinstance(examination, dict) else ""
                            exam_results = examination.get("exam_results", "") if isinstance(examination, dict) else ""
                            has_examination = (exam_items and len(exam_items.strip()) > 0) or (exam_results and len(exam_results.strip()) > 0)
                            logger.info(f"exam_items长度: {len(exam_items)}, exam_results长度: {len(exam_results)}, 有效: {has_examination}")
                            
                            # 3. diagnosis
                            diagnosis = case_main.get("diagnosis", "")
                            has_diagnosis = diagnosis and len(diagnosis.strip()) > 0
                            logger.info(f"diagnosis: '{diagnosis}'，有效: {has_diagnosis}")
                            
                            # 4. raw_data
                            raw_data = case_main.get("raw_data", {})
                            if isinstance(raw_data, dict):
                                case_content = raw_data.get("case_content", "")
                                discussion = raw_data.get("discussion", "")
                                has_raw_data = (case_content and len(case_content.strip()) > 0) or (discussion and len(discussion.strip()) > 0)
                                logger.info(f"case_content长度: {len(case_content)}, discussion长度: {len(discussion)}, 有效: {has_raw_data}")
                            else:
                                has_raw_data = False
                            
                            # 打印每个字段的检查结果
                            logger.info(f"字段检查结果 - basic_info: {has_basic_info}, examination: {has_examination}, diagnosis: {has_diagnosis}, raw_data: {has_raw_data}")
                            
                            # 只要有任意一个关键字段有内容，就认为是有效的
                            if has_basic_info or has_examination or has_diagnosis or has_raw_data:
                                valid_data_found = True
                                logger.info(f"找到有效数据，case_id: {case_id} [直接字段模式]")
                                break
                        
                        continue
                    
                    # 获取case_main
                    case_main = case_data["case_main"]
                    logger.info(f"case_main类型: {type(case_main)}")
                    
                    # 检查关键字段是否有内容（不为空字符串）
                    # 1. basic_info
                    basic_info = case_main.get("basic_info", "")
                    has_basic_info = basic_info and len(basic_info.strip()) > 0
                    logger.info(f"basic_info: '{basic_info[:50]}...'，有效: {has_basic_info}")
                    
                    # 2. examination
                    examination = case_main.get("examination", {})
                    logger.info(f"examination类型: {type(examination)}")
                    exam_items = examination.get("exam_items", "") if isinstance(examination, dict) else ""
                    exam_results = examination.get("exam_results", "") if isinstance(examination, dict) else ""
                    has_examination = (exam_items and len(exam_items.strip()) > 0) or (exam_results and len(exam_results.strip()) > 0)
                    logger.info(f"exam_items长度: {len(exam_items)}, exam_results长度: {len(exam_results)}, 有效: {has_examination}")
                    
                    # 3. diagnosis
                    diagnosis = case_main.get("diagnosis", "")
                    has_diagnosis = diagnosis and len(diagnosis.strip()) > 0
                    logger.info(f"diagnosis: '{diagnosis}'，有效: {has_diagnosis}")
                    
                    # 4. raw_data
                    raw_data = case_main.get("raw_data", {})
                    logger.info(f"raw_data类型: {type(raw_data)}")
                    if isinstance(raw_data, dict):
                        case_content = raw_data.get("case_content", "")
                        discussion = raw_data.get("discussion", "")
                        has_raw_data = (case_content and len(case_content.strip()) > 0) or (discussion and len(discussion.strip()) > 0)
                        logger.info(f"case_content长度: {len(case_content)}, discussion长度: {len(discussion)}, 有效: {has_raw_data}")
                    else:
                        has_raw_data = False
                        logger.warning(f"raw_data不是字典: {raw_data}")
                    
                    # 打印每个字段的检查结果
                    logger.info(f"字段检查结果 - basic_info: {has_basic_info}, examination: {has_examination}, diagnosis: {has_diagnosis}, raw_data: {has_raw_data}")
                    
                    # 只要有任意一个关键字段有内容，就认为是有效的case_main
                    if has_basic_info or has_examination or has_diagnosis or has_raw_data:
                        valid_data_found = True
                        logger.info(f"找到有效的case_main，case_id: {case_id} [嵌套模式]")
                        break
                    else:
                        logger.warning(f"case_id {case_id} 的所有字段均为空")
            
            if not valid_data_found:
                error_msg = f"输入文件中所有案例均为空数据: {file_path.name}"
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
        
        # 处理文件 - 注意：process_file返回的是布尔值，表示是否修改了数据
        success = cot_generator.process_file(file_path)
        
        # 获取token使用统计
        token_usage = cot_generator.four_o_client.get_token_usage()
        
        if not success:
            logger.warning(f"CoT生成器处理文件返回失败: {file_path.name}")
            return False, "CoT生成器处理失败", token_usage
        
        # 不需要额外保存结果，CoT生成器已经保存了结果
        logger.info(f"文件处理成功: {file_path.name}")
        
        return True, "", token_usage
        
    except Exception as e:
        logger.error(f"处理文件 {file_path.name} 时出错: {str(e)}")
        return False, str(e), {}

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 加载配置文件
    config = load_config(args.config)
    
    # 创建日志目录
    os.makedirs('logs/stage_three', exist_ok=True)
    
    # 合并配置和命令行参数
    input_dir = args.input_dir or config['paths']['output_dir'] + '/stage_two'
    output_dir = args.output_dir or config['paths']['output_dir'] + '/stage_three'
    max_items = args.max_items or config.get('general', {}).get('max_items')
    
    # API配置
    api_endpoint = args.api_endpoint or config['stage_three']['api']['endpoint']
    api_key = args.api_key or config['stage_three']['api']['key']
    api_key = os.environ.get(api_key[2:-1]) if api_key.startswith('${') and api_key.endswith('}') else api_key
    model = args.model or config['stage_three']['api'].get('model', 'gpt-4o')
    
    logger.info(f"运行第三阶段: 生成CoT")
    logger.info(f"输入目录: {input_dir}")
    logger.info(f"输出目录: {output_dir}")
    logger.info(f"4o API端点: {api_endpoint}")
    logger.info(f"模型: {model}")
    logger.info(f"最大处理文件数: {max_items if max_items else '不限'}")
    
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建四天客户端
        four_o_client = FourOClient(
            api_endpoint=api_endpoint,
            api_key=api_key,
            timeout=config['stage_three']['api'].get('timeout', 60),
            retry_attempts=config['stage_three']['api'].get('retry_attempts', 3),
            retry_delay=config['stage_three']['api'].get('retry_delay', 5),
            model=model,
            save_responses=args.save_responses,
            response_dir=args.response_dir
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
            return 0
            
        # 批量处理文件
        success_count = 0
        failure_count = 0
        case_main_failure_count = 0  # 新增：专门统计case_main相关的失败
        total_token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        total_requests = 0
        failure_details = {}  # 记录失败详情
        
        for file_path in json_files:
            success, error, token_usage = process_file(file_path, cot_generator, output_dir)
            
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
        
        return 0 if failure_count == 0 else 1
        
    except Exception as e:
        logger.error(f"运行第三阶段时出错: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 