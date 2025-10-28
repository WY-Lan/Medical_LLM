#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoT生成器：负责生成三个CoT步骤的思维链
"""

import os
import json
import logging
import re
from pathlib import Path

from .prompts import COT1_TEMPLATE, COT2_TEMPLATE, COT3_TEMPLATE, SYSTEM_PROMPT
from ..api.four_o_client import FourOClient

class CoTGenerator:
    """
    CoT生成器，用于生成医学案例的思维链
    """
    
    def __init__(self, four_o_client, output_dir):
        """
        初始化CoT生成器
        
        参数:
            four_o_client (FourOClient): 4o API客户端
            output_dir (str): 输出目录路径
        """
        self.four_o_client = four_o_client
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_case_cots(self, case_data):
        """
        为单个案例生成所有CoT
        
        参数:
            case_data (dict): 案例数据，包含basic_info, examination, diagnosis, treatment
            
        返回:
            dict: 生成的CoT数据
        """
        self.logger.info("开始生成CoT")
        
        # 提取必要数据
        basic_info = case_data.get("basic_info", "")
        examination = case_data.get("examination", {})
        diagnosis = case_data.get("diagnosis", "")
        treatment = case_data.get("treatment", "")
        discussion = case_data.get("raw_data", {}).get("discussion", "")
        
        # 格式化检查数据
        examination_text = f"检查项目：{examination.get('exam_items', '')}\n\n检查结果：{examination.get('exam_results', '')}"
        
        # 提取用作groundtruth的内容
        actual_examination = examination_text  # 真实的检查结果
        actual_diagnosis = diagnosis  # 真实的诊断
        
        # 处理treatment数据，可能是字符串或字典
        if isinstance(treatment, dict):
            # 如果是字典，可能是动态阶段处理过的结构
            # 将字典转换为易读的文本格式，用于提供groundtruth
            treatment_text = "\n\n".join([f"* {phase}: {details}" for phase, details in treatment.items() if details])
            if not treatment_text:
                treatment_text = "未提供详细治疗信息。"
        else:
            # 如果是字符串，直接使用
            treatment_text = treatment if treatment else "未提供详细治疗信息。"
        
        actual_treatment = treatment_text  # 真实的治疗
        
        # 生成CoT1：基本信息 -> 检查推理 (指向实际检查结果)
        cot1 = self._generate_cot1(basic_info, discussion, actual_examination)
        self.logger.info("CoT1生成完成")
        
        # 生成CoT2：基本信息 + 检查 -> 诊断推理 (指向实际诊断)
        cot2 = self._generate_cot2(basic_info, examination_text, discussion, actual_diagnosis)
        self.logger.info("CoT2生成完成")
        
        # 生成CoT3：基本信息 + 检查 + 诊断 -> 治疗推理 (指向实际治疗)
        cot3 = self._generate_cot3(basic_info, examination_text, diagnosis, discussion, actual_treatment)
        self.logger.info("CoT3生成完成")
        
        # 构建CoT数据
        cot_data = {
            "cot1": cot1,
            "cot2": cot2,
            "cot3": cot3,
            "original_data": {
                "basic_info": basic_info,
                "examination": examination,
                "diagnosis": diagnosis,
                "treatment": treatment,
                "discussion": discussion
            }
        }
        
        return cot_data
    
    def _generate_cot1(self, basic_info, discussion, actual_examination):
        """
        生成CoT1：基本信息 -> 检查推理，指向实际检查结果
        
        参数:
            basic_info (str): 基本信息
            discussion (str): 讨论内容
            actual_examination (str): 实际的检查结果
            
        返回:
            str: 生成的CoT1
        """
        prompt = COT1_TEMPLATE.format(
            basic_info=basic_info,
            discussion=discussion,
            actual_examination=actual_examination
        )
        
        cot = self.four_o_client.send_request(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
            system_prompt=SYSTEM_PROMPT
        )
        
        return cot or "生成失败"
    
    def _generate_cot2(self, basic_info, examination, discussion, actual_diagnosis):
        """
        生成CoT2：基本信息 + 检查 -> 诊断推理，指向实际诊断
        
        参数:
            basic_info (str): 基本信息
            examination (str): 检查信息
            discussion (str): 讨论内容
            actual_diagnosis (str): 实际的诊断
            
        返回:
            str: 生成的CoT2
        """
        prompt = COT2_TEMPLATE.format(
            basic_info=basic_info,
            examination=examination,
            discussion=discussion,
            actual_diagnosis=actual_diagnosis
        )
        
        cot = self.four_o_client.send_request(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
            system_prompt=SYSTEM_PROMPT
        )
        
        return cot or "生成失败"
    
    def _generate_cot3(self, basic_info, examination, diagnosis, discussion, actual_treatment):
        """
        生成CoT3：基本信息 + 检查 + 诊断 -> 治疗推理，指向实际治疗
        
        参数:
            basic_info (str): 基本信息
            examination (str): 检查信息
            diagnosis (str): 诊断信息
            discussion (str): 讨论内容
            actual_treatment (str): 实际的治疗
            
        返回:
            str: 生成的CoT3
        """
        prompt = COT3_TEMPLATE.format(
            basic_info=basic_info,
            examination=examination,
            diagnosis=diagnosis,
            discussion=discussion,
            actual_treatment=actual_treatment
        )
        
        cot = self.four_o_client.send_request(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
            system_prompt=SYSTEM_PROMPT
        )
        
        return cot or "生成失败"
    
    def process_file(self, input_file):
        """
        处理单个文件，生成所有案例的CoT
        
        参数:
            input_file (Path): 输入文件路径
            
        返回:
            bool: 处理成功返回True，否则返回False
        """
        try:
            self.logger.info(f"开始处理文件: {input_file}")
            
            # 加载输入数据
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取案例数据
            cases = data.get("cases", {})
            if not cases:
                self.logger.warning(f"文件不包含案例数据: {input_file}")
                return False
            
            # 处理每个案例，重新组织数据结构
            modified = False
            filtered_cases = {}
            
            for case_id, case_data in cases.items():
                # 检查是否应该跳过此案例
                if case_data.get("skip_in_stage_three", False):
                    skip_reasons = case_data.get("skip_reasons", ["未知原因"])
                    skip_reasons_text = "、".join(skip_reasons)
                    self.logger.warning(f"跳过案例 {case_id}: {skip_reasons_text}")
                    continue
                
                self.logger.info(f"处理案例: {case_id}")
                cot_data = self.generate_case_cots(case_data)
                
                if cot_data is None:
                    self.logger.warning(f"跳过案例 {case_id}: CoT生成失败")
                    continue
                
                # 获取原始数据
                basic_info = case_data.get("basic_info", "")
                examination = case_data.get("examination", {})
                diagnosis = case_data.get("diagnosis", "")
                treatment = case_data.get("treatment", "")
                raw_data = case_data.get("raw_data", {})
                
                # 重新组织数据结构，将CoT放在相关位置
                new_case_structure = {
                    "basic_info": basic_info,
                    "reasoning_for_examination": cot_data["cot1"],  # CoT1放在basic_info和examination之间
                    "examination": examination,
                    "reasoning_for_diagnosis": cot_data["cot2"],    # CoT2放在examination和diagnosis之间
                    "diagnosis": diagnosis,
                    "reasoning_for_treatment": cot_data["cot3"],    # CoT3放在diagnosis和treatment之间
                    "treatment": treatment,
                    "raw_data": raw_data
                }
                
                # 添加到过滤后的案例中
                filtered_cases[case_id] = new_case_structure
                modified = True
            
            # 如果所有案例都被过滤掉，则返回失败
            if not filtered_cases:
                self.logger.warning(f"文件处理完成，但所有案例都被过滤: {input_file}")
                return False
                
            # 用过滤后的案例替换原始案例
            data["cases"] = filtered_cases
            
            # 保存重组后的数据到原文件名_cot.json
            output_file = self.output_dir / f"{input_file.stem}_cot.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"文件处理完成，输出保存到: {output_file}")
            return modified
            
        except Exception as e:
            self.logger.error(f"处理文件时出错: {str(e)}")
            return False
    
    def process_batch(self, input_files):
        """
        批量处理多个文件
        
        参数:
            input_files (list): 输入文件路径列表
            
        返回:
            tuple: (成功数, 失败数)
        """
        success_count = 0
        failure_count = 0
        
        for input_file in input_files:
            success = self.process_file(input_file)
            if success:
                success_count += 1
            else:
                failure_count += 1
                
        self.logger.info(f"批处理完成. 成功: {success_count}, 失败: {failure_count}")
        return success_count, failure_count
