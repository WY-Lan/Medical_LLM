#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4o API客户端：负责与4o API交互
"""

import os
import json
import time
import logging
import requests
from pathlib import Path
import re
import uuid
from datetime import datetime

class FourOClient:
    """
    4o API客户端，用于发送请求并获取响应
    支持重试和错误处理
    """
    
    def __init__(self, api_endpoint, api_key, timeout=60, retry_attempts=3, retry_delay=5, model="qwq-plus", 
                 save_responses=False, response_dir=None):
        """
        初始化4o API客户端
        
        参数:
            api_endpoint (str): API端点URL
            api_key (str): API密钥
            timeout (int): 请求超时时间(秒)
            retry_attempts (int): 重试次数
            retry_delay (int): 重试间隔(秒)
            model (str): 使用的模型名称，默认为"qwq-plus"
            save_responses (bool): 是否保存API请求和响应
            response_dir (str): 保存响应的目录
        """
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.model = model
        self.logger = logging.getLogger(__name__)
        
        # 保存响应相关
        self.save_responses = save_responses
        self.response_dir = Path(response_dir) if response_dir else None
        if self.save_responses and self.response_dir:
            os.makedirs(self.response_dir, exist_ok=True)
            self.logger.info(f"将保存API响应到目录: {self.response_dir}")
        
        # Token使用统计
        self.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        self.request_count = 0
        
        self.logger.info(f"初始化4o API客户端: {api_endpoint}, 模型: {model}")
    
    def _save_response(self, request_data, response_data, function_name="unknown"):
        """
        保存请求和响应数据
        
        参数:
            request_data (dict): 请求数据
            response_data (dict): 响应数据
            function_name (str): 调用函数的名称
        """
        if not self.save_responses or not self.response_dir:
            return
        
        try:
            # 创建唯一文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}_{function_name}_{unique_id}.json"
            filepath = self.response_dir / filename
            
            # 保存数据
            data_to_save = {
                "timestamp": timestamp,
                "function": function_name,
                "request": request_data,
                "response": response_data
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"已保存API响应到: {filepath}")
        
        except Exception as e:
            self.logger.error(f"保存API响应失败: {str(e)}")
    
    def _update_token_usage(self, response):
        """
        更新token使用统计
        
        参数:
            response (dict): API响应数据
        """
        if "usage" in response:
            usage = response["usage"]
            self.token_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            self.token_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            self.token_usage["total_tokens"] += usage.get("total_tokens", 0)
            self.request_count += 1
            self.logger.debug(f"更新token使用统计: +{usage.get('total_tokens', 0)} 总计:{self.token_usage['total_tokens']}")
    
    def get_token_usage(self):
        """
        获取token使用统计
        
        返回:
            dict: token使用统计
        """
        return {
            "token_usage": self.token_usage,
            "request_count": self.request_count,
            "average_tokens_per_request": self.token_usage["total_tokens"] / self.request_count if self.request_count > 0 else 0
        }
    
    def reset_token_usage(self):
        """重置token使用统计"""
        self.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        self.request_count = 0
        self.logger.debug("已重置token使用统计")
    
    def send_request(self, prompt, max_tokens=1000, temperature=0.7, system_prompt=None, function_name=None):
        """
        发送请求到4o API
        
        参数:
            prompt (str): 提示文本
            max_tokens (int): 最大生成token数
            temperature (float): 采样温度
            system_prompt (str): 系统提示，用于指导模型生成
            function_name (str): 调用函数的名称，用于保存响应
            
        返回:
            str: API响应文本，失败则返回None
        """
        # 获取调用者函数名称，如果未提供
        if not function_name:
            import inspect
            caller_frame = inspect.currentframe().f_back
            if caller_frame:
                function_name = caller_frame.f_code.co_name
        
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(f"发送请求到4o API，尝试 {attempt+1}/{self.retry_attempts}")
                
                # 构造请求数据 - 使用Chat API格式
                messages = []
                
                # 添加系统提示（如果提供）
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                
                # 添加用户提示
                messages.append({"role": "user", "content": prompt})
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature
                }
                
                # 设置请求头
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
                
                # 确保API端点正确指向chat/completions
                api_url = self.api_endpoint
                if not api_url.endswith('/v1/chat/completions'):
                    if api_url.endswith('/v1'):
                        api_url = f"{api_url}/chat/completions"
                    elif api_url.endswith('/'):
                        api_url = f"{api_url}v1/chat/completions"
                    else:
                        api_url = f"{api_url}/v1/chat/completions"
                
                self.logger.debug(f"请求API端点: {api_url}")
                
                # 发送请求
                response = requests.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # 检查响应
                response.raise_for_status()
                
                # 解析响应
                result = response.json()
                
                # 更新token使用统计
                self._update_token_usage(result)
                
                # 提取生成的文本 - 从Chat API响应格式
                generated_text = ""
                if "choices" in result and len(result["choices"]) > 0:
                    generated_text = result["choices"][0]["message"]["content"]
                
                if not generated_text:
                    self.logger.warning("API响应中没有生成文本")
                
                # 保存请求和响应
                if self.save_responses:
                    request_data = {
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "model": self.model
                    }
                    self._save_response(request_data, result, function_name)
                
                return generated_text
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"请求出错: {str(e)}")
                if attempt < self.retry_attempts - 1:
                    self.logger.info(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(f"达到最大重试次数，请求失败")
                    return None
            
            except Exception as e:
                self.logger.error(f"处理请求时出错: {str(e)}")
                return None
    
    def _extract_json_from_response(self, response_text):
        """
        从可能包含markdown格式的响应中提取JSON内容
        
        参数:
            response_text (str): API响应文本
            
        返回:
            dict: 解析后的JSON对象，或者None如果解析失败
        """
        if not response_text:
            self.logger.warning("响应文本为空")
            return None
            
        try:
            # 尝试直接解析（如果已经是纯JSON）
            self.logger.debug("尝试直接解析JSON")
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            self.logger.debug(f"直接解析JSON失败: {str(e)}")
            
            # 尝试提取并修复JSON
            cleaned_json = None
            
            # 检查是否包含markdown代码块
            if "```json" in response_text or "```" in response_text:
                self.logger.info("检测到markdown格式的JSON响应，尝试提取...")
                # 提取```json和```之间的内容或者```和```之间的内容
                json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
                matches = re.findall(json_pattern, response_text)
                
                if matches:
                    # 尝试解析提取的JSON内容
                    for json_str in matches:
                        try:
                            cleaned_json = json_str.strip()
                            return json.loads(cleaned_json)
                        except json.JSONDecodeError:
                            self.logger.debug(f"解析markdown代码块中的JSON失败: {cleaned_json[:100]}")
                            continue
            
            # 如果没有markdown代码块或解析失败，尝试更复杂的修复
            self.logger.info("尝试修复可能格式不正确的JSON...")
            
            # 尝试找到JSON对象的开始和结束
            json_obj_pattern = r"\{[\s\S]*\}"
            obj_match = re.search(json_obj_pattern, response_text)
            if obj_match:
                potential_json = obj_match.group(0)
                self.logger.debug(f"找到潜在JSON对象: {potential_json[:100]}...")
                
                try:
                    # 尝试解析找到的JSON对象
                    return json.loads(potential_json)
                except json.JSONDecodeError as e:
                    self.logger.debug(f"解析潜在JSON对象失败: {str(e)}")
                    
                    # 尝试修复常见JSON格式问题
                    try:
                        # 替换单引号为双引号
                        fixed_json = potential_json.replace("'", "\"")
                        # 处理没有引号的键
                        fixed_json = re.sub(r'(\{|\,)\s*([a-zA-Z0-9_]+)\s*:', r'\1"\2":', fixed_json)
                        # 处理使用Python None的情况
                        fixed_json = fixed_json.replace("None", "null")
                        # 处理使用Python True/False的情况
                        fixed_json = fixed_json.replace("True", "true").replace("False", "false")
                        
                        self.logger.debug(f"尝试解析修复后的JSON: {fixed_json[:100]}...")
                        return json.loads(fixed_json)
                    except json.JSONDecodeError as e:
                        self.logger.debug(f"修复JSON格式后解析仍然失败: {str(e)}")
            
            # 如果所有方法都失败，记录错误并返回None
            preview = response_text[:100] + "..." if len(response_text) > 100 else response_text
            self.logger.error(f"无法从响应中提取有效的JSON: {preview}")
            return None
    
    def confirm_case_section(self, title, content_sample):
        """
        确认章节是否为案例部分
        
        参数:
            title (str): 章节标题
            content_sample (str): 章节内容样本
            
        返回:
            tuple: (is_case, explanation)
        """
        prompt = CASE_SECTION_CONFIRMATION_TEMPLATE.format(
            title=title,
            content_sample=content_sample[:500]
        )
        
        response = self.send_request(prompt, max_tokens=300, temperature=0.3)
        
        if not response:
            return False, "API请求失败"
        
        # 解析响应
        is_case = response.strip().upper().startswith("YES")
        explanation = response.strip()
        
        return is_case, explanation
    
    def extract_case_info(self, case_content):
        """
        提取病例的基本信息和检查信息
        
        参数:
            case_content (str): 病例内容
            
        返回:
            dict: 包含basic_info和examination的字典
        """
        try:
            prompt = CASE_INFO_EXTRACTION_TEMPLATE.format(
                case_content=case_content
            )
            
            self.logger.info("开始发送extract_case_info请求...")
            response = self.send_request(prompt, max_tokens=1500, temperature=0.3)
            
            if not response:
                self.logger.error("extract_case_info API请求失败，返回空响应")
                return {
                    "basic_info": "提取失败 - API请求返回空响应",
                    "examination": {
                        "exam_items": "提取失败",
                        "exam_results": "提取失败"
                    }
                }
            
            # 记录原始响应
            response_preview = response[:200] + "..." if len(response) > 200 else response
            self.logger.info(f"extract_case_info API响应预览: {response_preview}")
            
            # 尝试解析JSON响应
            try:
                # 先尝试直接解析JSON
                result = self._extract_json_from_response(response)
                if result:
                    # 验证结果格式
                    if "basic_info" not in result:
                        self.logger.warning("API响应中缺少basic_info字段")
                        result["basic_info"] = "响应缺少basic_info字段"
                        
                    if "examination" not in result:
                        self.logger.warning("API响应中缺少examination字段")
                        result["examination"] = {
                            "exam_items": "响应缺少examination字段",
                            "exam_results": "响应缺少examination字段"
                        }
                    elif not isinstance(result["examination"], dict):
                        self.logger.warning(f"examination字段不是字典: {type(result['examination'])}")
                        result["examination"] = {
                            "exam_items": "examination格式错误",
                            "exam_results": "examination格式错误"
                        }
                    
                    self.logger.info("成功解析extract_case_info API响应")
                    return result
                else:
                    # 如果_extract_json_from_response失败，尝试手动解析
                    self.logger.warning("通过_extract_json_from_response解析失败，尝试手动处理响应")
                    
                    # 记录完整响应用于调试
                    if self.save_responses and self.response_dir:
                        debug_file = self.response_dir / f"debug_extract_case_info_{int(time.time())}.txt"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(response)
                        self.logger.info(f"已保存完整响应到: {debug_file}")
                    
                    # 手动尝试提取关键信息
                    basic_info = ""
                    exam_items = ""
                    exam_results = ""
                    
                    # 尝试从文本中提取基本信息和检查信息
                    if "basic_info" in response.lower():
                        basic_info_match = re.search(r"basic_info[\"']?\s*:\s*[\"']?(.*?)[\"']?(?:,|\})", response, re.DOTALL | re.IGNORECASE)
                        if basic_info_match:
                            basic_info = basic_info_match.group(1).strip()
                            if basic_info.startswith('"') and basic_info.endswith('"'):
                                basic_info = basic_info[1:-1]
                    
                    if "exam_items" in response.lower():
                        exam_items_match = re.search(r"exam_items[\"']?\s*:\s*[\"']?(.*?)[\"']?(?:,|\})", response, re.DOTALL | re.IGNORECASE)
                        if exam_items_match:
                            exam_items = exam_items_match.group(1).strip()
                            if exam_items.startswith('"') and exam_items.endswith('"'):
                                exam_items = exam_items[1:-1]
                    
                    if "exam_results" in response.lower():
                        exam_results_match = re.search(r"exam_results[\"']?\s*:\s*[\"']?(.*?)[\"']?(?:,|\})", response, re.DOTALL | re.IGNORECASE)
                        if exam_results_match:
                            exam_results = exam_results_match.group(1).strip()
                            if exam_results.startswith('"') and exam_results.endswith('"'):
                                exam_results = exam_results[1:-1]
                    
                    result = {
                        "basic_info": basic_info or "手动提取失败",
                        "examination": {
                            "exam_items": exam_items or "手动提取失败",
                            "exam_results": exam_results or "手动提取失败"
                        }
                    }
                    
                    self.logger.info("完成手动提取")
                    return result
            except Exception as e:
                self.logger.error(f"解析extract_case_info API响应时出错: {str(e)}", exc_info=True)
                
                # 记录完整响应用于调试
                if self.save_responses and self.response_dir:
                    debug_file = self.response_dir / f"error_extract_case_info_{int(time.time())}.txt"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(response)
                    self.logger.info(f"已保存出错响应到: {debug_file}")
                
                return {
                    "basic_info": f"解析失败: {str(e)}",
                    "examination": {
                        "exam_items": "解析失败",
                        "exam_results": "解析失败"
                    }
                }
        except KeyError as e:
            # 处理模板格式错误
            self.logger.error(f"模板格式错误: {str(e)}", exc_info=True)
            return {
                "basic_info": f"模板格式错误: {str(e)}",
                "examination": {
                    "exam_items": "模板格式错误",
                    "exam_results": "模板格式错误"
                }
            }
    
    def extract_diagnosis(self, case_content, discussion_content):
        """
        从病例内容和讨论中提取诊断信息
        
        参数:
            case_content (str): 病例内容
            discussion_content (str): 讨论内容
            
        返回:
            str: 诊断信息
        """
        try:
            prompt = DIAGNOSIS_EXTRACTION_TEMPLATE.format(
                case_content=case_content[:2000],
                discussion_content=discussion_content[:2000]
            )
            
            response = self.send_request(prompt, max_tokens=800, temperature=0.3)
            
            if not response:
                return "提取失败"
            
            # 尝试解析JSON响应
            result = self._extract_json_from_response(response)
            if result:
                return result.get("diagnosis", "解析失败")
            else:
                return "解析失败"
        except KeyError as e:
            # 处理模板格式错误
            self.logger.error(f"模板格式错误: {str(e)}", exc_info=True)
            return f"模板格式错误: {str(e)}"
    
    def extract_treatment(self, content, sections=None):
        """
        从内容中提取治疗信息，并按照病程时间线动态组织成结构化格式
        
        参数:
            content (str): 内容文本，可能是整个病例
            sections (dict, optional): 病例的章节字典，键为章节标题，值为章节内容
            
        返回:
            dict/str: 按照病程动态组织的治疗信息结构，如果提取失败则返回错误字符串
        """
        try:
            # 首先尝试从特定治疗章节提取
            treatment_content = None
            if sections:
                # 查找可能的治疗相关章节
                treatment_keywords = ["treatment", "therapy", "therapeutic", "management", "intervention", 
                                    "procedure", "surgery", "surgical", "medication", "drug", "treat", 
                                    "治疗", "处理", "用药", "给药", "手术", "干预"]
                
                treatment_sections = {}
                for title, content_text in sections.items():
                    if any(keyword.lower() in title.lower() for keyword in treatment_keywords):
                        treatment_sections[title] = content_text
                
                # 如果找到治疗相关章节，则合并内容
                if treatment_sections:
                    treatment_content = "\n\n".join([f"### {title} ###\n{content_text}" 
                                                for title, content_text in treatment_sections.items()])
                    self.logger.info(f"找到治疗相关章节: {list(treatment_sections.keys())}")

            # 构建提示词，根据是否找到专门的治疗章节调整策略
            if treatment_content:
                prompt = TREATMENT_FROM_SECTIONS_TEMPLATE.format(
                    treatment_content=treatment_content
                )
            else:
                # 如果没有找到治疗专门章节，则搜索整个内容
                prompt = TREATMENT_FROM_CONTENT_TEMPLATE.format(
                    content=content
                )
                
                self.logger.info("未找到专门的治疗章节，从整个内容中提取治疗信息")
            
            # 不限制token数量，使用较低温度以确保输出稳定性
            response = self.send_request(prompt, max_tokens=2000, temperature=0.2)
            
            if not response:
                return "提取失败"
            
            # 尝试解析JSON响应
            result = self._extract_json_from_response(response)
            if result:
                # 如果结果为空字典，则添加一个默认键
                if len(result) == 0:
                    result = {"no_treatment_found": "未发现治疗信息"}
                return result
            else:
                return "解析失败"
        except KeyError as e:
            # 处理模板格式错误
            self.logger.error(f"模板格式错误: {str(e)}", exc_info=True)
            return {"template_error": f"模板格式错误: {str(e)}"}
