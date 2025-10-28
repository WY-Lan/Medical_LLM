#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内容提取器：从医学文献中提取病例信息
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

from ..api.four_o_client import FourOClient
from .prompts import (
    CASE_SECTION_CONFIRMATION_TEMPLATE,
    CONTENT_ONLY_CASE_CONFIRMATION_TEMPLATE,
    STRICT_CASE_CONTENT_TEMPLATE,
    STRICT_DISCUSSION_CONTENT_TEMPLATE,
    CASE_INFO_EXTRACTION_TEMPLATE,
    DIAGNOSIS_EXTRACTION_TEMPLATE,
    TREATMENT_ITEMS_EXTRACTION_TEMPLATE
)

class ContentExtractor:
    """
    内容提取器：从医学文献中提取病例信息
    使用更严格的提示模板和映射字典
    """
    
    def __init__(self, api_client: FourOClient, mapping_dir: str):
        """
        初始化内容提取器
        
        参数:
            api_client: API客户端实例
            mapping_dir: 映射字典目录
        """
        self.api_client = api_client
        self.mapping_dir = Path(mapping_dir)
        self.logger = logging.getLogger(__name__)
        
        # 确保映射目录存在
        os.makedirs(self.mapping_dir, exist_ok=True)
        
        # 加载映射字典
        self.case_content_mapping = self._load_mapping('case_content_mapping.json')
        self.discussion_mapping = self._load_mapping('discussion_mapping.json')
        
        self.logger.info("内容提取器初始化完成")
    
    def _load_mapping(self, filename: str) -> Dict[str, bool]:
        """
        加载映射字典
        
        参数:
            filename: 映射文件名
            
        返回:
            映射字典
        """
        mapping_file = self.mapping_dir / filename
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"加载映射文件 {filename} 失败: {str(e)}")
                return {}
        return {}
    
    def _save_mapping(self, filename: str, mapping: Dict[str, bool]):
        """
        保存映射字典
        
        参数:
            filename: 映射文件名
            mapping: 映射字典
        """
        mapping_file = self.mapping_dir / filename
        try:
            with open(mapping_file, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存映射文件 {filename} 失败: {str(e)}")
    
    def _get_section_content(self, section: Dict[str, Any]) -> str:
        """
        获取章节内容，处理content字段为数组的情况
        
        参数:
            section: 章节字典
            
        返回:
            章节内容字符串
        """
        try:
            content = section.get('content', '')
            if isinstance(content, list):
                return '\n'.join(str(item) for item in content if item)
            elif isinstance(content, str):
                return content
            elif isinstance(content, dict):
                return json.dumps(content, ensure_ascii=False)
            else:
                return str(content) if content else ''
        except Exception as e:
            self.logger.error(f"获取章节内容失败: {str(e)}")
            return ''
    
    def is_case_section(self, title: str, content: str) -> Tuple[bool, str]:
        """
        判断是否为病例章节
        
        参数:
            title: 章节标题
            content: 章节内容
            
        返回:
            (是否为病例章节, 解释)
        """
        # 检查映射字典
        if title in self.case_content_mapping:
            return self.case_content_mapping[title], "从映射字典中获取"
        
        # 使用API判断
        prompt = CASE_SECTION_CONFIRMATION_TEMPLATE.format(
            title=title,
            content_sample=content[:1500]
        )
        
        response = self.api_client.send_request(prompt, max_tokens=300, temperature=0.3)
        if not response:
            return False, "API请求失败"
        
        # 解析响应
        is_case = response.strip().upper().startswith("YES")
        explanation = response.strip()
        
        # 更新映射字典
        self.case_content_mapping[title] = is_case
        self._save_mapping('case_content_mapping.json', self.case_content_mapping)
        
        return is_case, explanation
    
    def is_discussion_section(self, title: str, content: str) -> Tuple[bool, str]:
        """
        判断是否为讨论章节
        
        参数:
            title: 章节标题
            content: 章节内容
            
        返回:
            (是否为讨论章节, 解释)
        """
        # 检查映射字典
        if title in self.discussion_mapping:
            return self.discussion_mapping[title], "从映射字典中获取"
        
        # 使用API判断，确保传递章节标题
        try:
            prompt = STRICT_DISCUSSION_CONTENT_TEMPLATE.format(
                title=title,
                content_sample=content
            )
            
            response = self.api_client.send_request(prompt, max_tokens=300, temperature=0.3)
            if not response:
                self.logger.warning(f"讨论章节API请求失败: {title}")
                return False, "API请求失败"
            
            # 解析响应
            is_discussion = response.strip().upper().startswith("YES")
            explanation = response.strip()
            
            # 更新映射字典
            self.discussion_mapping[title] = is_discussion
            self._save_mapping('discussion_mapping.json', self.discussion_mapping)
            
            if is_discussion:
                self.logger.info(f"识别到讨论章节: {title}")
            
            return is_discussion, explanation
        
        except Exception as e:
            self.logger.error(f"判断讨论章节时出错: {str(e)}")
            return False, f"处理错误: {str(e)}"
    
    def extract_case_content(self, sections: List[Dict[str, Any]]) -> Optional[str]:
        """
        提取病例内容
        
        参数:
            sections: 文章章节列表
            
        返回:
            病例内容，如果没有找到则返回None
        """
        for section in sections:
            title = section.get('title', '')
            content = self._get_section_content(section)
            
            # 检查是否为病例章节
            is_case, explanation = self.is_case_section(title, content)
            if is_case:
                self.logger.info(f"找到病例章节: {title}")
                return content
        
        return None
    
    def extract_discussion_content(self, sections: List[Dict[str, Any]]) -> Optional[str]:
        """
        提取讨论内容
        
        参数:
            sections: 文章章节列表
            
        返回:
            讨论内容，如果没有找到则返回None
        """
        for section in sections:
            title = section.get('title', '')
            content = self._get_section_content(section)
            
            # 检查是否为讨论章节
            is_discussion, explanation = self.is_discussion_section(title, content)
            if is_discussion:
                self.logger.info(f"找到讨论章节: {title}")
                return content
        
        return None
    
    def extract_case_info(self, case_content: str) -> Dict[str, Any]:
        """
        提取病例基本信息
        
        参数:
            case_content: 病例内容
            
        返回:
            病例基本信息字典
        """
        if not case_content:
            return {}
        
        # 创建默认结构
        default_result = {
            "basic_info": "",
            "examination": {
                "exam_items": "",
                "exam_results": ""
            }
        }
            
        try:    
            prompt = CASE_INFO_EXTRACTION_TEMPLATE.format(
                case_content=case_content
            )
            
            response = self.api_client.send_request(prompt, temperature=0.3)
            if not response:
                self.logger.warning("病例信息API请求返回空响应")
                return default_result
                
            self.logger.debug(f"收到病例信息API响应: {response[:100]}...")
            
            # 清理响应，去除可能导致解析错误的前缀和空格
            cleaned_response = response.strip()
            
            # 如果响应以JSON标记开头和结尾，移除这些标记
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
                
            cleaned_response = cleaned_response.strip()
            self.logger.debug(f"清理后的响应: {cleaned_response[:100]}...")
            
            # 保存原始响应供调试
            try:
                raw_file_path = "test_output/raw_api_response.json"
                os.makedirs(os.path.dirname(raw_file_path), exist_ok=True)
                with open(raw_file_path, 'w', encoding='utf-8') as file:
                    file.write(cleaned_response)
                self.logger.info(f"已保存原始API响应: {raw_file_path}")
            except Exception as save_err:
                self.logger.warning(f"保存原始API响应时出错: {str(save_err)}")
                
            # 尝试修复JSON格式问题，特别是内部引号问题
            import re
            
            # 首先处理花括号格式问题
            # 查找连续的结束花括号 (`}}`)，并将它们分开
            def fix_closing_braces(text):
                # 使用查找方式定位连续花括号，确保它们不是在字符串内部
                in_string = False
                escape_next = False
                result = []
                i = 0
                while i < len(text):
                    char = text[i]
                    # 处理字符串边界
                    if char == '"' and not escape_next:
                        in_string = not in_string
                    
                    # 处理转义字符
                    if char == '\\':
                        escape_next = not escape_next
                    else:
                        escape_next = False
                    
                    # 检查连续花括号，但仅在不在字符串内时处理
                    if not in_string and char == '}' and i+1 < len(text) and text[i+1] == '}':
                        # 找到连续花括号，添加第一个并加入换行和缩进
                        result.append('}')
                        result.append('\n')
                        # 确定适当的缩进级别
                        indent_level = 0
                        j = i - 1
                        while j >= 0 and text[j] in ' \t\n':
                            j -= 1
                        # 添加适当的缩进
                        result.append('  ')
                        # 不要增加i，让下一个循环处理第二个花括号
                    else:
                        result.append(char)
                    i += 1
                return ''.join(result)
            
            # 应用花括号修复
            cleaned_response = fix_closing_braces(cleaned_response)
            
            # 修复内部引号的问题 (在字段内容中的引号)
            def fix_internal_quotes(match):
                content = match.group(1)
                # 替换内容中的双引号为单引号
                fixed_content = content.replace('"', "'")
                return f'"{fixed_content}"'
                
            # 正则表达式模式，避免匹配到已经转义的引号
            pattern = r'"((?:[^"\\]|\\.)*)(?<!\\)"'
            # 匹配字符串内容并处理其中的引号
            cleaned_response = re.sub(pattern, fix_internal_quotes, cleaned_response)
            
            # 特殊处理exam_results字段，因为它经常包含内部引号
            exam_results_pattern = r'"exam_results"\s*:\s*"(.*?)(?:"(?=[,}])|$)'
            exam_results_match = re.search(exam_results_pattern, cleaned_response, re.DOTALL)
            if exam_results_match:
                full_match = exam_results_match.group(0)
                content = exam_results_match.group(1)
                # 替换内容中的所有双引号为单引号
                fixed_content = content.replace('"', "'")
                # 用修复后的内容替换
                cleaned_response = cleaned_response.replace(full_match, f'"exam_results":"{fixed_content}"')
                self.logger.info("已修复exam_results中的内部引号")
            
            # 修复键值对问题 (缺少引号或逗号)
            cleaned_response = re.sub(r'(\w+)(\s*:)', r'"\1"\2', cleaned_response)
            # 修复换行问题
            cleaned_response = re.sub(r',\s*\n\s*}', '}', cleaned_response)
            
            # 修复可能的未终止字符串问题
            # 检查是否有未配对的引号
            quote_count = cleaned_response.count('"')
            if quote_count % 2 != 0:
                self.logger.warning(f"检测到未配对的引号，尝试修复JSON格式")
                # 寻找最后一个未配对的引号位置并添加关闭引号
                last_open_pos = -1
                for i, char in enumerate(cleaned_response):
                    if char == '"':
                        if last_open_pos == -1:
                            last_open_pos = i
                        else:
                            last_open_pos = -1
                
                if last_open_pos != -1:
                    # 在最后一个未配对引号后添加引号
                    cleaned_response = cleaned_response[:last_open_pos+1] + '"' + cleaned_response[last_open_pos+1:]
            
            # 确保JSON对象和数组正确闭合
            brace_count = cleaned_response.count('{') - cleaned_response.count('}')
            if brace_count > 0:
                self.logger.warning(f"检测到未闭合的花括号，尝试修复")
                cleaned_response += "}" * brace_count
            elif brace_count < 0:
                self.logger.warning(f"检测到多余的花括号，尝试修复")
                # 查找并删除多余的花括号
                extra_braces = abs(brace_count)
                last_idx = len(cleaned_response) - 1
                count = 0
                while last_idx >= 0 and count < extra_braces:
                    if cleaned_response[last_idx] == '}':
                        # 标记要删除的花括号
                        cleaned_response = cleaned_response[:last_idx] + cleaned_response[last_idx+1:]
                        count += 1
                    last_idx -= 1
            
            bracket_count = cleaned_response.count('[') - cleaned_response.count(']')
            if bracket_count > 0:
                self.logger.warning(f"检测到未闭合的方括号，尝试修复")
                cleaned_response += "]" * bracket_count
            
            # 尝试解析JSON前先保存预处理后的JSON供调试
            try:
                debug_file_path = "test_output/preprocessed_json.json"
                os.makedirs(os.path.dirname(debug_file_path), exist_ok=True)
                with open(debug_file_path, 'w', encoding='utf-8') as file:
                    file.write(cleaned_response)
                self.logger.info(f"已保存预处理后的JSON: {debug_file_path}")
            except Exception as save_err:
                self.logger.warning(f"保存预处理JSON时出错: {str(save_err)}")
            
            # 尝试使用带格式化的方式解析和输出JSON，这有助于发现问题
            try:
                # 先尝试解析
                parsed_json = json.loads(cleaned_response)
                # 再格式化输出
                formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                formatted_path = "test_output/formatted_json.json"
                with open(formatted_path, 'w', encoding='utf-8') as file:
                    file.write(formatted_json)
                self.logger.info(f"JSON格式有效，已保存格式化版本: {formatted_path}")
                
                # 验证结果格式并确保所有必需字段存在
                if not isinstance(parsed_json, dict):
                    self.logger.error(f"病例信息格式错误: 不是字典 - {type(parsed_json)}")
                    return default_result
               
                # 确保基本字段存在
                if "basic_info" not in parsed_json:
                    parsed_json["basic_info"] = ""
                    
                # 确保examination字段格式正确
                if "examination" not in parsed_json:
                    parsed_json["examination"] = {"exam_items": "", "exam_results": ""}
                elif not isinstance(parsed_json["examination"], dict):
                    self.logger.warning(f"examination字段不是字典 - {type(parsed_json['examination'])}")
                    parsed_json["examination"] = {"exam_items": "", "exam_results": ""}
                else:
                    if "exam_items" not in parsed_json["examination"]:
                        parsed_json["examination"]["exam_items"] = ""
                    if "exam_results" not in parsed_json["examination"]:
                        parsed_json["examination"]["exam_results"] = ""
                
                self.logger.info("成功解析病例信息")
                return parsed_json
                
            except json.JSONDecodeError as e:
                self.logger.error(f"病例信息JSON解析失败: {str(e)}")
                self.logger.error(f"Problematic JSON string that caused the error: \n{cleaned_response}")
                
                # 记录错误信息以便调试
                try:
                    file_path = "test_output/failed_json_extraction.json"
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(cleaned_response)
                    self.logger.info(f"已将失败的JSON字符串保存到文件: {file_path}")
                except Exception as save_err:
                    self.logger.error(f"保存失败的JSON字符串时出错: {str(save_err)}")

                # 尝试直接手动构建结构化数据
                try:
                    # 更可靠的方式提取字段：直接查找键并获取其值
                    # 使用正则表达式更精确地识别字段的开始和结束位置
                    
                    # 提取basic_info
                    basic_info_pattern = r'"basic_info"\s*:\s*"(.*?)(?:"(?=[,}])|$)'
                    basic_info_match = re.search(basic_info_pattern, cleaned_response, re.DOTALL)
                    if basic_info_match:
                        default_result["basic_info"] = basic_info_match.group(1).strip()
                        self.logger.info("成功提取basic_info")
                        
                    # 提取exam_items
                    exam_items_pattern = r'"exam_items"\s*:\s*"(.*?)(?:"(?=[,}])|$)'
                    exam_items_match = re.search(exam_items_pattern, cleaned_response, re.DOTALL)
                    if exam_items_match:
                        default_result["examination"]["exam_items"] = exam_items_match.group(1).strip()
                        self.logger.info("成功提取exam_items")
                    
                    # 提取exam_results - 使用更复杂的模式来处理内部引号问题
                    # 找到exam_results字段的开始位置
                    start_idx = cleaned_response.find('"exam_results"')
                    if start_idx != -1:
                        # 找到值引号的开始位置
                        value_start = cleaned_response.find('"', start_idx + 15) + 1
                        if value_start > 0:
                            # 搜索内容直到找到下一个未转义的引号，或者直到找到结束括号
                            content = []
                            i = value_start
                            while i < len(cleaned_response):
                                if cleaned_response[i] == '"' and (i == 0 or cleaned_response[i-1] != '\\'):
                                    # 看看这个引号后面是否跟着逗号或花括号，如果是，这是结束的引号
                                    if i+1 < len(cleaned_response) and cleaned_response[i+1] in ',}':
                                        break
                                content.append(cleaned_response[i])
                                i += 1
                            
                            exam_results = ''.join(content)
                            default_result["examination"]["exam_results"] = exam_results.strip()
                            self.logger.info("成功手动提取exam_results")
                    
                    self.logger.info("通过自定义解析成功提取信息")
                    return default_result
                    
                except Exception as parse_err:
                    self.logger.error(f"尝试手动解析JSON失败: {str(parse_err)}")
                
                # 如果自定义解析也失败，使用更原始的正则提取
                basic_info_match = re.search(r'"basic_info"\s*:\s*"(.*?)"', cleaned_response, re.DOTALL)
                if basic_info_match:
                    default_result["basic_info"] = basic_info_match.group(1).strip()
                    self.logger.info("通过正则表达式提取到基本信息")
                
                exam_items_match = re.search(r'"exam_items"\s*:\s*"(.*?)"', cleaned_response, re.DOTALL)
                if exam_items_match:
                    default_result["examination"]["exam_items"] = exam_items_match.group(1).strip()
                    self.logger.info("通过正则表达式提取到检查项目")
                    
                # 修改正则表达式以提取不完整的exam_results字段内容
                # 使用非贪婪匹配来获取尽可能多的内容，而不必依赖于结束引号
                exam_results_match = re.search(r'"exam_results"\s*:\s*"([^"]*)', cleaned_response, re.DOTALL)
                if exam_results_match:
                    default_result["examination"]["exam_results"] = exam_results_match.group(1).strip()
                    self.logger.info("通过正则表达式提取到部分检查结果")
                    
                    # 尝试补全结果，查找exam_results之后的内容直到JSON结构可能结束的地方
                    full_text = cleaned_response
                    start_idx = full_text.find('"exam_results"')
                    if start_idx != -1:
                        content_start_idx = full_text.find('"', start_idx + 14) + 1  # 14 = len('"exam_results"')
                        if content_start_idx != 0:  # 找到了开始引号
                            # 查找可能的结束标记 (引号+逗号 或 引号+花括号)
                            possible_end_idx = -1
                            for end_pattern in ['"', '",', '"}']:
                                end_idx = full_text.find(end_pattern, content_start_idx)
                                if end_idx != -1 and (possible_end_idx == -1 or end_idx < possible_end_idx):
                                    possible_end_idx = end_idx
                            
                            if possible_end_idx != -1:
                                default_result["examination"]["exam_results"] = full_text[content_start_idx:possible_end_idx].strip()
                                self.logger.info("通过查找可能的结束位置提取到完整检查结果")
                
                return default_result
                
        except Exception as e:
            self.logger.error(f"提取病例信息时发生异常: {str(e)}")
            return default_result
    
    def extract_diagnosis(self, case_content: str, discussion_content: Optional[str] = None) -> Dict[str, str]:
        """
        提取诊断信息
        
        参数:
            case_content: 病例内容
            discussion_content: 讨论内容（可选）
            
        返回:
            诊断信息字典，格式为 {"diagnosis": "最终诊断"}
        """
        # 创建默认结果
        default_result = {"diagnosis": ""}
        
        try:
            prompt = DIAGNOSIS_EXTRACTION_TEMPLATE.format(
                case_content=case_content[:1500],
                discussion_content=(discussion_content or "")[:1500]
            )
            
            response = self.api_client.send_request(
                prompt=prompt, 
                max_tokens=500, 
                temperature=0.3,
                function_name="extract_diagnosis"
            )
            
            if not response:
                self.logger.warning("诊断信息API请求返回空响应")
                return default_result
                
            self.logger.debug(f"收到诊断信息API响应: {response[:100]}...")
            
            # 清理响应
            cleaned_response = response.strip()
            
            # 如果响应以JSON标记开头和结尾，移除这些标记
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]
                
            cleaned_response = cleaned_response.strip()
            self.logger.debug(f"清理后的响应: {cleaned_response[:100]}...")
            
            # 尝试解析JSON
            try:
                result = json.loads(cleaned_response)
                
                # 验证结果格式
                if isinstance(result, dict) and "diagnosis" in result:
                    diagnosis = result["diagnosis"]
                    if diagnosis:
                        self.logger.info(f"成功提取诊断信息: {diagnosis[:50]}...")
                        return result
                    else:
                        self.logger.warning("提取的诊断信息为空")
                        return default_result
                else:
                    self.logger.warning(f"诊断信息格式不符合预期: {cleaned_response[:50]}...")
                    return default_result
                    
            except json.JSONDecodeError as e:
                self.logger.error(f"诊断信息JSON解析失败: {str(e)}")
                
                # 尝试通过正则表达式提取诊断
                import re
                diagnosis_match = re.search(r'"diagnosis"\s*:\s*"([^"]+)"', cleaned_response)
                if diagnosis_match:
                    diagnosis = diagnosis_match.group(1).strip()
                    self.logger.info(f"通过正则表达式提取到诊断: {diagnosis[:50]}...")
                    return {"diagnosis": diagnosis}
                    
                # 如果正则表达式也失败，尝试直接提取带引号的文本
                quoted_text_match = re.search(r'"([^"]+)"', cleaned_response)
                if quoted_text_match:
                    diagnosis = quoted_text_match.group(1).strip()
                    if diagnosis and len(diagnosis) > 5:  # 长度检查以避免提取非诊断内容
                        self.logger.info(f"提取到可能的诊断文本: {diagnosis[:50]}...")
                        return {"diagnosis": diagnosis}
                
                return default_result
                
        except Exception as e:
            self.logger.error(f"提取诊断信息时发生异常: {str(e)}")
            return default_result
    
    def extract_treatment_items(self, case_content: str) -> Dict[str, List[str]]:
        """
        提取治疗项目列表
        
        参数:
            case_content: 病例内容
            
        返回:
            包含治疗项目列表的字典
        """
        if not case_content:
            self.logger.warning("提取治疗项目时收到空内容")
            return {"treatment_items": []}
            
        try:
            # 确保内容是字符串类型
            case_content_text = str(case_content)
            
            # 构建请求提示，限制大小
            text_content = case_content_text[:1500]
            
            # 构建完整提示 - 使用英文
            complete_prompt = f"""
You are a medical treatment extraction specialist. Your task is to extract a list of ALL treatment interventions from the medical case report.
Focus ONLY on treatments that were ACTUALLY ADMINISTERED to the patient, not planned or proposed treatments.

Below is the clinical case content:
---------------
{text_content}
---------------

EXTRACTION GUIDELINES:
1. Extract ONLY concrete treatment interventions that were definitively administered
2. Include medication names with dosages, routes, and durations when mentioned
3. Include surgical procedures, therapies, and other interventions
4. Include supportive care measures
5. DO NOT include diagnostic procedures unless they served a therapeutic purpose
6. DO NOT include planned treatments or general treatment discussions
7. BE PRECISE - include only clearly stated treatments with their details

Format your response as a valid JSON with the following structure:
{{
  "treatment_items": [
    "Treatment 1: details if available",
    "Treatment 2: details if available",
    ...
  ]
}}

If no confirmed treatments were administered, return: {{"treatment_items": []}}
"""
            # 发送请求
            self.logger.debug("发送治疗项目提取请求")
            response = self.api_client.send_request(
                prompt=complete_prompt,
                max_tokens=500,
                temperature=0.3,
                function_name="extract_treatment_items"
            )
            
            if not response:
                self.logger.warning("治疗项目API请求返回空响应")
                return {"treatment_items": []}
                
            self.logger.debug(f"收到治疗项目API响应: {response[:100]}...")
            
            # 清理和解析响应
            cleaned_response = response.strip()
            # 移除可能的代码块标记
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith('```'):
                    cleaned_response = cleaned_response[:-3]
            
            cleaned_response = cleaned_response.strip()
            self.logger.debug(f"清理后的响应: {cleaned_response[:100]}...")
            
            # 尝试解析JSON
            try:
                result = json.loads(cleaned_response)
                
                # 验证结果格式
                if isinstance(result, dict) and "treatment_items" in result:
                    items = result["treatment_items"]
                    # 确保items是列表
                    if not isinstance(items, list):
                        self.logger.warning(f"treatment_items不是列表，类型为: {type(items)}")
                        items = []
                        result["treatment_items"] = items
                    
                    self.logger.info(f"成功提取到 {len(items)} 项治疗项目")
                    return result
                else:
                    # 尝试构造一个有效的结果
                    self.logger.warning("API响应格式不符合预期，尝试修复")
                    if isinstance(result, dict):
                        # 如果有其他键，尝试找到可能的治疗项目
                        for key, value in result.items():
                            if isinstance(value, list) and len(value) > 0:
                                self.logger.info(f"从键 '{key}' 找到可能的治疗项目列表")
                                return {"treatment_items": value}
                    
                    self.logger.warning("无法修复API响应格式，使用空列表")
                    return {"treatment_items": []}
                    
            except json.JSONDecodeError as e:
                # JSON解析失败，尝试提取列表
                self.logger.warning(f"治疗信息JSON解析失败: {str(e)}")
                
                # 尝试从文本中提取列表项
                import re
                # 查找可能的列表项 (带引号的字符串数组)
                list_match = re.search(r'\[\s*"(.*?)"\s*(?:,\s*"(.*?)"\s*)*\]', cleaned_response)
                if list_match:
                    # 提取所有引号括起来的项
                    items = re.findall(r'"(.*?)"', list_match.group(0))
                    if items:
                        self.logger.info(f"通过正则表达式提取到 {len(items)} 项治疗项目")
                        return {"treatment_items": items}
                
                # 如果还是失败，尝试搜索"treatment_items"部分
                items_match = re.search(r'"treatment_items"\s*:\s*\[(.*?)\]', cleaned_response, re.DOTALL)
                if items_match:
                    content = items_match.group(1).strip()
                    if content:
                        # 提取引号括起来的项
                        items = re.findall(r'"(.*?)"', content)
                        if items:
                            self.logger.info(f"从treatment_items部分提取到 {len(items)} 项治疗项目")
                            return {"treatment_items": items}
                
                self.logger.warning("所有解析尝试失败，返回空列表")
                return {"treatment_items": []}
                
        except Exception as e:
            self.logger.error(f"提取治疗项目时发生异常: {str(e)}")
            return {"treatment_items": []}
    
    def process_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理文章数据
        
        参数:
            article_data: 文章数据
            
        返回:
            处理结果
        """
        try:
            # 提取文章基本信息
            result = {
                "cases": {
                    "case_main": {
                        "basic_info": "",
                        "examination": {
                            "exam_items": "",
                            "exam_results": ""
                        },
                        "diagnosis": "",
                        "treatment": "",
                        "raw_data": {
                            "case_content": "",
                            "treatment": "",
                            "discussion": ""
                        }
                    }
                },
                "metadata": {
                    "source_file": article_data.get("source_file", ""),
                    "title": article_data.get("title", ""),
                    "article_id": article_data.get("article_id", "")
                }
            }
            
            # 获取文章章节
            sections = article_data.get("sections", [])
            if not sections:
                self.logger.warning("文章没有章节")
                return result
            
            # 提取病例内容
            case_content = self.extract_case_content(sections)
            # 提取讨论内容
            discussion_content = self.extract_discussion_content(sections)
            
            if case_content:
                self.logger.info(f"成功提取病例内容，长度: {len(case_content)}")
                result["cases"]["case_main"]["raw_data"]["case_content"] = case_content
                
                # file_path = "test_output/case_content_extraction_result.json"
                # with open(file_path, 'w', encoding='utf-8') as f:
                #     json.dump(result, f, ensure_ascii=False, indent=2)
                # print(f"保存到文件: {file_path}")

                try:
                    # 提取病例基本信息
                    case_info = self.extract_case_info(case_content)
                    if case_info:
                        file_path = "test_output/case_info_extraction_result.json"
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(case_info, f, ensure_ascii=False, indent=2)
                        print(f"保存到文件: {file_path}")
                        self.logger.info("成功提取病例基本信息")
                        result["cases"]["case_main"]["basic_info"] = case_info.get("basic_info", "")
                        result["cases"]["case_main"]["examination"]["exam_items"] = case_info.get("examination", {}).get("exam_items", "")
                        result["cases"]["case_main"]["examination"]["exam_results"] = case_info.get("examination", {}).get("exam_results", "")
                    else:
                        self.logger.warning("提取病例基本信息失败")
                except Exception as e:
                    self.logger.error(f"提取病例基本信息时发生异常: {str(e)}")
                
                try:
                    # 提取诊断信息
                    diagnosis = self.extract_diagnosis(case_content, discussion_content)
                    if diagnosis:
                        self.logger.info("成功提取诊断信息")
                        result["cases"]["case_main"]["diagnosis"] = diagnosis.get("diagnosis", "")
                    else:
                        self.logger.warning("提取诊断信息失败")
                except Exception as e:
                    self.logger.error(f"提取诊断信息时发生异常: {str(e)}")
                
                try:
                    # 提取治疗项目
                    treatment_items = self.extract_treatment_items(case_content)
                    if treatment_items and isinstance(treatment_items, dict) and "treatment_items" in treatment_items:
                        self.logger.info("成功提取治疗项目")
                        # 确保treatment_items中有treatment_items键并且是列表
                        items_list = treatment_items.get("treatment_items", [])
                        if not isinstance(items_list, list):
                            self.logger.warning(f"treatment_items不是列表，类型为: {type(items_list)}")
                            items_list = []
                        # 尝试序列化为JSON字符串，并处理可能的错误
                        try:
                            treatment_json = json.dumps(items_list, ensure_ascii=False)
                            result["cases"]["case_main"]["treatment"] = treatment_json
                            result["cases"]["case_main"]["raw_data"]["treatment"] = treatment_json
                        except Exception as json_err:
                            self.logger.error(f"序列化治疗项目时出错: {str(json_err)}")
                            result["cases"]["case_main"]["treatment"] = "[]"
                            result["cases"]["case_main"]["raw_data"]["treatment"] = "[]"
                    else:
                        self.logger.warning("提取治疗项目失败或无治疗项目")
                        result["cases"]["case_main"]["treatment"] = "[]"
                        result["cases"]["case_main"]["raw_data"]["treatment"] = "[]"
                except Exception as e:
                    self.logger.error(f"提取治疗项目时发生异常: {str(e)}")
                    result["cases"]["case_main"]["treatment"] = "[]"
                    result["cases"]["case_main"]["raw_data"]["treatment"] = "[]"
            else:
                self.logger.warning("未找到病例内容")
            
            # 保存讨论内容
            if discussion_content:
                self.logger.info(f"成功提取讨论内容，长度: {len(discussion_content)}")
                result["cases"]["case_main"]["raw_data"]["discussion"] = discussion_content
            else:
                self.logger.warning("未找到讨论内容")
            
            return result
        except Exception as e:
            self.logger.error(f"处理文章时发生异常: {str(e)}")
            # 返回默认结果
            return {
                "cases": {
                    "case_main": {
                        "basic_info": "",
                        "examination": {
                            "exam_items": "",
                            "exam_results": ""
                        },
                        "diagnosis": "",
                        "treatment": "[]",
                        "raw_data": {
                            "case_content": "",
                            "treatment": "[]",
                            "discussion": ""
                        }
                    }
                },
                "metadata": {
                    "source_file": article_data.get("source_file", ""),
                    "title": article_data.get("title", ""),
                    "article_id": article_data.get("article_id", "")
                }
            }
