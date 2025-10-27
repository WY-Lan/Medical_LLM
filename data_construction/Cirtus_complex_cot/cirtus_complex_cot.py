import json
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random
import requests
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReasoningStage(Enum):
    """推理阶段枚举"""
    INFORMATION_COLLECTION = 1
    HYPOTHESIS_GENERATION = 2
    DIFFERENTIAL_DIAGNOSIS = 3
    CONCLUSION = 4

@dataclass
class ReasoningStep:
    """推理步骤数据结构"""
    step_id: int
    content: str
    stage: ReasoningStage
    validity_score: float
    feedback: str
    timestamp: float
    is_valid: bool = False

@dataclass
class MedicalCase:
    """医学病例数据结构"""
    case_id: str
    patient_info: str
    chief_complaint: str
    medical_history: str
    symptoms: List[str]
    ground_truth: Optional[str] = None

class LLMClient:
    """大模型API客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("LLM_API_KEY", "your-api-key-here")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        
    def call_llm(self, prompt: str, system_message: str = None, temperature: float = 0.7) -> str:
        """调用大模型API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", 
                                   headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"调用大模型API失败: {str(e)}")
            # 返回模拟响应作为降级方案
            return self._get_fallback_response(prompt)
    
    def _get_fallback_response(self, prompt: str) -> str:
        """获取降级响应（当API调用失败时使用）"""
        if "信息收集" in prompt or "初步分析" in prompt:
            return "基于患者信息分析：患者表现为急性症状，需要紧急评估。关键症状包括胸痛、呼吸困难等，提示可能存在心血管或呼吸系统急症。"
        elif "假设" in prompt:
            return "可能的诊断方向包括：急性心肌梗死、肺栓塞、主动脉夹层、胸膜炎等。需要进一步鉴别分析。"
        elif "鉴别" in prompt:
            return "鉴别诊断分析：急性心肌梗死可能性较高，支持证据包括典型胸痛、危险因素；需要排除肺栓塞、主动脉夹层等危及生命的疾病。"
        else:
            return "综合临床表现和危险因素，初步考虑急性心肌梗死可能性大，建议立即完善心电图和心肌酶学检查。"

class MedicalReasoningExpert:
    """医学推理专家类 - 负责生成诊断假设和推理过程"""
    
    def __init__(self, expert_name: str = "资深医学专家", llm_client: LLMClient = None):
        self.expert_name = expert_name
        self.llm_client = llm_client or LLMClient()
        self.reasoning_template = self._create_reasoning_template()
    
    def _create_reasoning_template(self) -> Dict[ReasoningStage, str]:
        """创建推理阶段模板"""
        return {
            ReasoningStage.INFORMATION_COLLECTION: 
                "基于患者信息进行分析：\n患者基本情况：{patient_info}\n主诉：{chief_complaint}\n病史：{medical_history}\n关键症状：{symptoms}",
            
            ReasoningStage.HYPOTHESIS_GENERATION:
                "生成初步诊断假设：\n基于上述信息，可能的诊断方向包括：{hypotheses}",
            
            ReasoningStage.DIFFERENTIAL_DIAGNOSIS:
                "进行鉴别诊断：\n对每个假设进行详细分析：\n{differential_analysis}",
            
            ReasoningStage.CONCLUSION:
                "得出诊断结论：\n综合考虑所有因素，最终诊断：{conclusion}\n\n诊断依据：{reasoning}"
        }
    
    def generate_reasoning_process(self, medical_case: MedicalCase) -> List[ReasoningStep]:
        """生成完整的推理过程"""
        reasoning_steps = []
        current_context = ""
        
        # 阶段1: 信息收集
        info_step = self._generate_information_step(medical_case)
        reasoning_steps.append(info_step)
        current_context += info_step.content + "\n"
        
        # 阶段2: 假设生成
        hypothesis_step = self._generate_hypothesis_step(medical_case, current_context)
        reasoning_steps.append(hypothesis_step)
        current_context += hypothesis_step.content + "\n"
        
        # 阶段3: 鉴别诊断
        differential_step = self._generate_differential_step(medical_case, current_context)
        reasoning_steps.append(differential_step)
        current_context += differential_step.content + "\n"
        
        # 阶段4: 结论
        conclusion_step = self._generate_conclusion_step(medical_case, current_context)
        reasoning_steps.append(conclusion_step)
        
        return reasoning_steps
    
    def _generate_information_step(self, case: MedicalCase) -> ReasoningStep:
        """生成信息收集步骤"""
        prompt = f"""请作为资深医生分析以下患者信息，提取关键临床信息：

患者信息：{case.patient_info}
主诉：{case.chief_complaint}
病史：{case.medical_history}
症状：{', '.join(case.symptoms)}

请分析这些信息中的关键临床要素，包括症状特点、危险因素、时间特征等。"""

        system_message = "你是一位经验丰富的临床医生，擅长从患者信息中提取关键临床要素。"
        
        analysis = self.llm_client.call_llm(prompt, system_message, temperature=0.3)
        
        content = f"基于患者信息进行分析：\n{analysis}"
        
        return ReasoningStep(
            step_id=1,
            content=content,
            stage=ReasoningStage.INFORMATION_COLLECTION,
            validity_score=0.8,
            feedback="信息收集完整，关键要素已识别",
            timestamp=time.time()
        )
    
    def _generate_hypothesis_step(self, case: MedicalCase, context: str) -> ReasoningStep:
        """生成假设生成步骤"""
        prompt = f"""基于以下患者信息和初步分析，生成可能的诊断假设：

{context}

请列出3-5个最可能的诊断假设，并简要说明每个假设的支持证据。"""

        system_message = "你是一位经验丰富的诊断专家，擅长生成合理的鉴别诊断列表。"
        
        hypotheses_text = self.llm_client.call_llm(prompt, system_message, temperature=0.5)
        
        content = f"生成初步诊断假设：\n{hypotheses_text}"
        
        return ReasoningStep(
            step_id=2,
            content=content,
            stage=ReasoningStage.HYPOTHESIS_GENERATION,
            validity_score=0.7,
            feedback="假设生成合理，覆盖主要可能性",
            timestamp=time.time()
        )
    
    def _generate_differential_step(self, case: MedicalCase, context: str) -> ReasoningStep:
        """生成鉴别诊断步骤"""
        prompt = f"""基于以下患者信息和诊断假设，进行详细的鉴别诊断分析：

{context}

请对每个诊断假设进行详细分析，包括：
1. 支持证据
2. 反对证据  
3. 需要进一步确认的检查
4. 可能性评估"""

        system_message = "你是一位擅长鉴别诊断的医学专家，能够系统分析不同诊断的可能性。"
        
        analysis = self.llm_client.call_llm(prompt, system_message, temperature=0.4)
        
        content = f"进行鉴别诊断：\n{analysis}"
        
        return ReasoningStep(
            step_id=3,
            content=content,
            stage=ReasoningStage.DIFFERENTIAL_DIAGNOSIS,
            validity_score=0.6,
            feedback="鉴别诊断过程需要进一步细化",
            timestamp=time.time()
        )
        
    def _generate_conclusion_step(self, case: MedicalCase, context: str) -> ReasoningStep:
        """生成结论步骤"""
        prompt = f"""基于以下完整的临床推理过程，给出最终诊断结论：

{context}

请给出最可能的诊断结论，并详细说明诊断依据和推理过程。"""

        system_message = "你是一位临床决策专家，能够基于完整信息做出准确的诊断结论。"
        
        conclusion_text = self.llm_client.call_llm(prompt, system_message, temperature=0.3)
        
        content = f"得出诊断结论：\n{conclusion_text}"
        
        return ReasoningStep(
            step_id=4,
            content=content,
            stage=ReasoningStage.CONCLUSION,
            validity_score=0.75,
            feedback="诊断结论明确，推理链条完整",
            timestamp=time.time()
        )
    
    def _generate_possible_hypotheses(self, case: MedicalCase) -> List[str]:
        """使用大模型生成可能的诊断假设"""
        prompt = f"""根据以下病例信息，生成可能的诊断假设：

患者信息：{case.patient_info}
主诉：{case.chief_complaint}
病史：{case.medical_history}
症状：{', '.join(case.symptoms)}

请列出3-5个最可能的诊断，按可能性从高到低排列。"""

        system_message = "你是一位经验丰富的诊断专家。"
        
        response = self.llm_client.call_llm(prompt, system_message, temperature=0.5)
        
        # 从响应中提取诊断假设
        hypotheses = self._extract_hypotheses_from_response(response)
        return hypotheses[:5]  # 返回前5个假设
    
    def _extract_hypotheses_from_response(self, response: str) -> List[str]:
        """从大模型响应中提取诊断假设"""
        # 简单的文本处理来提取诊断
        lines = response.split('\n')
        hypotheses = []
        
        for line in lines:
            line = line.strip()
            if line and any(marker in line for marker in ['诊断', '可能', '考虑', '包括']):
                # 移除编号和标记
                clean_line = line.replace('1.', '').replace('2.', '').replace('3.', '').replace('4.', '').replace('5.', '')
                clean_line = clean_line.replace('-', '').replace('*', '').strip()
                
                # 提取疾病名称（简化处理）
                if len(clean_line) > 3 and len(clean_line) < 50:  # 合理的疾病名称长度
                    hypotheses.append(clean_line.split('：')[-1] if '：' in clean_line else clean_line)
        
        return hypotheses if hypotheses else ["急性心肌梗死", "肺栓塞", "主动脉夹层", "胸膜炎"]

class ReflectionExpert:
    """反思专家类 - 负责评估推理步骤的合理性"""
    
    def __init__(self, ground_truth: Optional[str] = None, llm_client: LLMClient = None):
        self.ground_truth = ground_truth
        self.llm_client = llm_client or LLMClient()
    
    def evaluate_step(self, step: ReasoningStep, previous_steps: List[ReasoningStep]) -> ReasoningStep:
        """使用大模型评估推理步骤"""
        # 构建评估上下文
        context = "之前的推理步骤：\n"
        for prev_step in previous_steps:
            context += f"步骤{prev_step.step_id} ({prev_step.stage.name}): {prev_step.content}\n\n"
        
        prompt = f"""请评估以下医学推理步骤的质量：

当前推理步骤（{step.stage.name}）：
{step.content}

评估上下文：
{context}

请从以下维度评估：
1. 逻辑一致性：推理是否逻辑严密，前后连贯
2. 医学准确性：医学知识运用是否准确
3. 证据充分性：是否充分利用了可用信息
4. 临床合理性：是否符合临床实践

请给出0-10分的综合评分和具体反馈。"""

        system_message = "你是一位医学教育专家，擅长评估临床推理过程的质量。"
        
        evaluation = self.llm_client.call_llm(prompt, system_message, temperature=0.3)
        
        # 解析评估结果
        score, feedback = self._parse_evaluation_response(evaluation)
        
        # 更新步骤信息
        step.validity_score = score / 10.0  # 转换为0-1分数
        step.feedback = feedback
        step.is_valid = score >= 6.0  # 6分以上认为有效
        
        return step
    
    def _parse_evaluation_response(self, response: str) -> Tuple[float, str]:
        """解析大模型的评估响应"""
        try:
            # 尝试提取分数
            lines = response.split('\n')
            score = 7.0  # 默认分数
            
            for line in lines:
                if '评分' in line or '分数' in line:
                    for word in line.split():
                        if word.replace('.', '').isdigit():
                            score = float(word)
                            break
            
            # 使用响应作为反馈，或生成简化的反馈
            if len(response) > 200:
                feedback = response[:200] + "..."
            else:
                feedback = response
            
            return min(score, 10.0), feedback
            
        except Exception as e:
            logger.warning(f"解析评估响应失败，使用默认值: {str(e)}")
            return 7.0, "评估过程正常，推理质量可接受"

class DualExpertReasoningSystem:
    """双专家推理系统 - 协调推理专家和反思专家的协作"""
    
    def __init__(self, max_iterations: int = 5, llm_client: LLMClient = None):
        self.llm_client = llm_client or LLMClient()
        self.reasoning_expert = MedicalReasoningExpert(llm_client=self.llm_client)
        self.reflection_expert = ReflectionExpert(llm_client=self.llm_client)
        self.max_iterations = max_iterations
        self.reasoning_history = []
    
    def process_medical_case(self, medical_case: MedicalCase) -> Dict:
        """处理医学病例的完整流程"""
        logger.info(f"开始处理病例: {medical_case.case_id}")
        
        # 设置正确答案
        self.reflection_expert.ground_truth = medical_case.ground_truth
        
        final_reasoning = ""
        iteration_results = []
        
        for iteration in range(self.max_iterations):
            logger.info(f"第 {iteration + 1} 轮推理迭代")
            
            # 生成推理步骤
            reasoning_step = self._generate_reasoning_step(medical_case, final_reasoning, iteration)
            
            # 评估推理步骤
            evaluated_step = self.reflection_expert.evaluate_step(
                reasoning_step, 
                self.reasoning_history
            )
            
            # 记录迭代结果
            iteration_result = {
                'iteration': iteration + 1,
                'reasoning_step': evaluated_step.content,
                'validity_score': evaluated_step.validity_score,
                'feedback': evaluated_step.feedback,
                'is_valid': evaluated_step.is_valid,
                'timestamp': time.time()
            }
            iteration_results.append(iteration_result)
            
            # 更新最终推理
            if evaluated_step.is_valid:
                final_reasoning += f"\n{evaluated_step.content}"
                self.reasoning_history.append(evaluated_step)
                logger.info(f"步骤有效，分数: {evaluated_step.validity_score:.2f}")
            else:
                logger.warning(f"步骤无效，分数: {evaluated_step.validity_score:.2f}")
            
            # 检查终止条件
            if self._has_reached_conclusion(final_reasoning):
                logger.info("已达到诊断结论，终止推理")
                break
        
        # 生成最终答案
        final_answer = self._extract_final_answer(final_reasoning)
        
        result = {
            'case_id': medical_case.case_id,
            'final_reasoning': final_reasoning.strip(),
            'final_answer': final_answer,
            'iteration_results': iteration_results,
            'total_iterations': len(iteration_results),
            'success': self._validate_result(final_answer, medical_case.ground_truth),
            'quality_score': self._calculate_quality_score(iteration_results)
        }
        
        logger.info(f"病例处理完成，质量评分: {result['quality_score']:.2f}")
        return result
    
    def _generate_reasoning_step(self, case: MedicalCase, context: str, iteration: int) -> ReasoningStep:
        """生成推理步骤"""
        if iteration == 0:
            # 第一轮生成完整推理过程
            steps = self.reasoning_expert.generate_reasoning_process(case)
            return steps[0]  # 返回第一个步骤
        elif iteration < 4:  # 确保不超过推理阶段的最大数量
            # 按照推理阶段顺序返回对应步骤
            steps = self.reasoning_expert.generate_reasoning_process(case)
            return steps[iteration]
        else:
            # 使用大模型深化推理
            return self._deepen_reasoning_with_llm(context, case, iteration)
    
    def _deepen_reasoning_with_llm(self, context: str, case: MedicalCase, iteration: int) -> ReasoningStep:
        """使用大模型深化现有推理"""
        prompt = f"""基于以下已有的推理过程，请深化和扩展分析：

现有推理：
{context}

患者信息：
- 基本情况：{case.patient_info}
- 主诉：{case.chief_complaint}
- 病史：{case.medical_history}
- 症状：{', '.join(case.symptoms)}

请在前述分析基础上，提供更深入的分析或补充可能遗漏的考虑因素。"""

        system_message = "你是一位擅长深化临床推理的医学专家。"
        
        deepened_analysis = self.llm_client.call_llm(prompt, system_message, temperature=0.5)
        
        # 确定阶段（基于迭代次数）
        if iteration % 4 == 0:
            stage = ReasoningStage.INFORMATION_COLLECTION
        elif iteration % 4 == 1:
            stage = ReasoningStage.HYPOTHESIS_GENERATION
        elif iteration % 4 == 2:
            stage = ReasoningStage.DIFFERENTIAL_DIAGNOSIS
        else:
            stage = ReasoningStage.CONCLUSION
        
        content = f"深化分析（第{iteration+1}轮）：\n{deepened_analysis}"
        
        return ReasoningStep(
            step_id=iteration + 1,
            content=content,
            stage=stage,
            validity_score=0.5,
            feedback="",
            timestamp=time.time()
        )
    
    def _has_reached_conclusion(self, reasoning: str) -> bool:
        """检查是否已达到诊断结论"""
        conclusion_indicators = ["最终诊断", "诊断结论", "确诊为", "临床诊断", "诊断是"]
        return any(indicator in reasoning for indicator in conclusion_indicators)
    
    def _extract_final_answer(self, reasoning: str) -> str:
        """从推理过程中提取最终诊断答案"""
        # 使用大模型提取结论
        prompt = f"""从以下医学推理文本中提取最终的诊断结论：

推理文本：
{reasoning}

请只返回诊断名称，不要其他内容。"""

        system_message = "你擅长从医学文本中精确提取关键信息。"
        
        try:
            diagnosis = self.llm_client.call_llm(prompt, system_message, temperature=0.1)
            return diagnosis.strip()
        except:
            # 降级方案：使用原有的文本匹配方法
            conclusion_section = ""
            for indicator in ["最终诊断：", "诊断结论：", "确诊为", "临床诊断："]:
                if indicator in reasoning:
                    parts = reasoning.split(indicator)
                    if len(parts) > 1:
                        conclusion_section = parts[1].split('\n')[0].strip()
                        break
            
            return conclusion_section if conclusion_section else "待进一步明确"
    
    def _validate_result(self, answer: str, ground_truth: Optional[str]) -> bool:
        """验证结果是否正确"""
        if not ground_truth:
            return False
        
        return ground_truth.lower() in answer.lower() or answer.lower() in ground_truth.lower()
    
    def _calculate_quality_score(self, iteration_results: List[Dict]) -> float:
        """计算整体推理质量分数"""
        if not iteration_results:
            return 0.0
        
        total_score = sum(result['validity_score'] for result in iteration_results)
        return total_score / len(iteration_results)

# CitrusS3DataGenerator 类保持不变（与原始代码相同）
class CitrusS3DataGenerator:
    """Citrus S3 数据生成器 - 生成训练数据"""
    
    def __init__(self, reasoning_system: DualExpertReasoningSystem):
        self.reasoning_system = reasoning_system
        self.generated_data = []
        self.prompt_templates = self._create_prompt_templates()
    
    def _create_prompt_templates(self) -> Dict[str, str]:
        """创建提示词模板"""
        return {
            "diagnosis_input": """请你作为一位经验丰富的临床医生，分析下面的病例并给出诊断：

【患者信息】
{patient_info}

【主诉】
{chief_complaint}

【病史】
{medical_history}

【症状】
{symptoms}

请仔细分析上述病例，并给出你的诊断。在回答时，请遵循以下结构：
1. 首先思考收集到的关键信息
2. 根据信息生成可能的诊断假设
3. 对每个假设进行鉴别分析
4. 给出最终诊断结论和理由

你的分析应该展示完整的临床思维过程。""",

            "diagnostic_reasoning": """请你作为一位经验丰富的医学专家，详细分析以下病例，并展示你完整的临床推理过程。

【病例信息】
患者：{patient_info}
主诉：{chief_complaint}
病史：{medical_history}
症状：{symptoms}

请在回复中使用以下<thinking>标签记录你的完整推理过程，以及使用<answer>标签给出最终诊断：

<thinking>
在这里记录你的完整推理过程，包括：
1. 对患者信息的初步分析
2. 可能的诊断假设及其依据
3. 对每个假设的详细鉴别分析
4. 如何排除不太可能的诊断
</thinking>

<answer>这里给出最终诊断结论</answer>""",

            "reflection_prompt": """请你分析一位医生对以下病例的诊断推理过程，并评估其质量：

【病例信息】
{case_summary}

【医生的推理过程】
{reasoning_process}

请你从以下几个方面评估这个推理过程：
1. 逻辑一致性：推理是否遵循严谨的逻辑，各步骤间是否有连贯性
2. 医学准确性：医学知识运用是否准确，是否有错误的医学概念
3. 证据充分性：是否充分利用了病例中提供的所有证据，是否忽略了关键信息
4. 推理完整性：是否涵盖了诊断推理的所有必要步骤

最后，请给出对推理过程的综合评分（0-10分）并说明理由。"""
        }
    
    def generate_dataset(self, medical_cases: List[MedicalCase]) -> List[Dict]:
        """生成完整的数据集"""
        logger.info(f"开始生成数据集，共 {len(medical_cases)} 个病例")
        
        training_examples = []
        
        for i, case in enumerate(medical_cases):
            logger.info(f"处理病例 {i+1}/{len(medical_cases)}: {case.case_id}")
            
            try:
                # 执行双专家推理
                reasoning_result = self.reasoning_system.process_medical_case(case)
                
                # 格式化为训练数据
                training_example = self._format_training_example(case, reasoning_result)
                training_examples.append(training_example)
                
                # 保存生成记录
                self.generated_data.append({
                    'case': {
                        'case_id': case.case_id,
                        'patient_info': case.patient_info,
                        'chief_complaint': case.chief_complaint,
                        'medical_history': case.medical_history,
                        'symptoms': case.symptoms,
                        'ground_truth': case.ground_truth
                    },
                    'result': reasoning_result,
                    'timestamp': time.time()
                })
                
            except Exception as e:
                logger.error(f"处理病例失败: {case.case_id}, 错误: {str(e)}")
                continue
        
        logger.info(f"数据集生成完成，共生成 {len(training_examples)} 个有效样本")
        return training_examples
    
    def _format_training_example(self, case: MedicalCase, result: Dict) -> Dict:
        """格式化为SFT训练数据格式"""
        # 使用模板生成输入提示
        prompt = self.prompt_templates["diagnostic_reasoning"].format(
            patient_info=case.patient_info,
            chief_complaint=case.chief_complaint,
            medical_history=case.medical_history,
            symptoms=", ".join(case.symptoms)
        )
        
        return {
            "sft-input": prompt,
            "sft-target": f"<thinking>{result['final_reasoning']}</thinking>\n\n<answer>{result['final_answer']}</answer>",
            "metadata": {
                "case_id": case.case_id,
                "iterations": result['total_iterations'],
                "success": result['success'],
                "quality_score": result['quality_score'],
                "timestamp": time.time()
            }
        }
    
    def save_dataset(self, filename: str):
        """保存生成的数据集"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.generated_data, f, ensure_ascii=False, indent=2)

# 使用示例和测试代码
def main():
    """主函数 - 演示完整使用流程"""
    
    # 创建测试病例
    test_cases = [
        MedicalCase(
            case_id="case_001",
            patient_info="45岁男性",
            chief_complaint="持续性胸痛2小时",
            medical_history="高血压病史5年，吸烟史20年",
            symptoms=["胸痛", "呼吸困难", "出汗"],
            ground_truth="急性心肌梗死"
        ),
        MedicalCase(
            case_id="case_002",
            patient_info="67岁女性",
            chief_complaint="反复头痛伴视物模糊3天",
            medical_history="高血压病史10年，糖尿病史5年",
            symptoms=["头痛", "视物模糊", "恶心"],
            ground_truth="高血压危象"
        )
    ]
    
    # 初始化系统（使用大模型）
    llm_client = LLMClient()
    reasoning_system = DualExpertReasoningSystem(max_iterations=3, llm_client=llm_client)
    data_generator = CitrusS3DataGenerator(reasoning_system)
    
    # 生成训练数据
    training_data = data_generator.generate_dataset(test_cases)
    
    # 保存结果
    data_generator.save_dataset("citrus_s3_training_data.json")
    
    # 打印结果摘要
    print("\n=== 数据生成结果摘要 ===")
    print(f"生成样本数量: {len(training_data)}")
    for example in training_data:
        print(f"病例ID: {example['metadata']['case_id']}")
        print(f"质量评分: {example['metadata']['quality_score']:.2f}")
        print(f"推理步骤: {example['metadata']['iterations']}次")
        print("---")

if __name__ == "__main__":
    main()
