import json
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random

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

class MedicalReasoningExpert:
    """医学推理专家类 - 负责生成诊断假设和推理过程"""
    
    def __init__(self, expert_name: str = "资深医学专家"):
        self.expert_name = expert_name
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
        content = self.reasoning_template[ReasoningStage.INFORMATION_COLLECTION].format(
            patient_info=case.patient_info,
            chief_complaint=case.chief_complaint,
            medical_history=case.medical_history,
            symptoms=", ".join(case.symptoms)
        )
        
        return ReasoningStep(
            step_id=1,
            content=content,
            stage=ReasoningStage.INFORMATION_COLLECTION,
            validity_score=0.8,  # 信息收集阶段通常较为可靠
            feedback="信息收集完整，关键要素已识别",
            timestamp=time.time()
        )
    
    def _generate_hypothesis_step(self, case: MedicalCase, context: str) -> ReasoningStep:
        """生成假设生成步骤"""
        hypotheses = self._generate_possible_hypotheses(case)
        
        content = self.reasoning_template[ReasoningStage.HYPOTHESIS_GENERATION].format(
            hypotheses="\n- ".join([""] + hypotheses)
        )
        
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
        analysis = self._perform_differential_analysis(case)
        
        content = self.reasoning_template[ReasoningStage.DIFFERENTIAL_DIAGNOSIS].format(
            differential_analysis=analysis
        )
        
        return ReasoningStep(
            step_id=3,
            content=content,
            stage=ReasoningStage.DIFFERENTIAL_DIAGNOSIS,
            validity_score=0.6,  # 鉴别诊断需要更多验证
            feedback="鉴别诊断过程需要进一步细化",
            timestamp=time.time()
        )
        
    def _generate_conclusion_step(self, case: MedicalCase, context: str) -> ReasoningStep:
        """生成结论步骤"""
        # 简单模拟结论生成，实际应用中需更复杂的推理
        conclusion = self._derive_conclusion(case, context)
        reasoning = self._extract_reasoning_for_conclusion(context, conclusion)
        
        content = self.reasoning_template[ReasoningStage.CONCLUSION].format(
            conclusion=conclusion,
            reasoning=reasoning
        )
        
        return ReasoningStep(
            step_id=4,
            content=content,
            stage=ReasoningStage.CONCLUSION,
            validity_score=0.75,
            feedback="诊断结论明确，推理链条完整",
            timestamp=time.time()
        )
    
    def _generate_possible_hypotheses(self, case: MedicalCase) -> List[str]:
        """根据病例生成可能的诊断假设"""
        # 根据症状匹配可能的疾病
        symptom_disease_map = {
            "胸痛": ["急性心肌梗死", "主动脉夹层", "肺栓塞", "胸膜炎", "胃食管反流病"],
            "呼吸困难": ["心力衰竭", "慢性阻塞性肺病", "哮喘", "肺炎", "肺栓塞"],
            "出汗": ["感染", "甲状腺功能亢进", "焦虑症", "低血糖"],
            "头痛": ["偏头痛", "紧张性头痛", "蛛网膜下腔出血", "脑膜炎", "颅内高压"],
            "腹痛": ["阑尾炎", "胆囊炎", "肠梗阻", "胃炎", "胰腺炎"],
            "发热": ["感染", "自身免疫性疾病", "药物热", "恶性肿瘤"]
        }
        
        # 结合病史中的关键词
        history_disease_map = {
            "高血压": ["心肌梗死", "脑卒中", "肾衰竭", "动脉硬化"],
            "糖尿病": ["糖尿病酮症酸中毒", "糖尿病足", "糖尿病视网膜病变"],
            "吸烟": ["冠心病", "肺癌", "慢性阻塞性肺病", "外周血管疾病"],
            "酗酒": ["酒精性肝病", "胰腺炎", "韦尼克脑病", "酒精戒断综合征"]
        }
        
        # 收集可能的疾病
        potential_diseases = set()
        
        # 基于症状
        for symptom in case.symptoms:
            for disease in symptom_disease_map.get(symptom, []):
                potential_diseases.add(disease)
        
        # 基于病史
        for history_keyword, diseases in history_disease_map.items():
            if history_keyword.lower() in case.medical_history.lower():
                for disease in diseases:
                    potential_diseases.add(disease)
        
        # 如果是胸痛且有高血压、吸烟史，提高心肌梗死的权重
        if "胸痛" in case.symptoms and ("高血压" in case.medical_history.lower() or 
                                     "吸烟" in case.medical_history.lower()):
            if "急性心肌梗死" in potential_diseases:
                # 确保心肌梗死在假设列表的前面
                potential_diseases.remove("急性心肌梗死")
                return ["急性心肌梗死"] + list(potential_diseases)[:4]
        
        # 最多返回5个可能的疾病假设
        return list(potential_diseases)[:5]
    
    def _perform_differential_analysis(self, case: MedicalCase) -> str:
        """执行鉴别诊断分析"""
        hypotheses = self._generate_possible_hypotheses(case)
        
        analyses = []
        
        for hypothesis in hypotheses:
            supporting_evidence = []
            contradicting_evidence = []
            
            # 简化版的证据收集逻辑
            if hypothesis == "急性心肌梗死":
                if "胸痛" in case.symptoms:
                    supporting_evidence.append("患者表现为持续性胸痛")
                if "出汗" in case.symptoms:
                    supporting_evidence.append("患者有冷汗")
                if "呼吸困难" in case.symptoms:
                    supporting_evidence.append("伴有呼吸困难")
                if "高血压" in case.medical_history.lower():
                    supporting_evidence.append("有高血压病史（危险因素）")
                if "吸烟" in case.medical_history.lower():
                    supporting_evidence.append("有长期吸烟史（危险因素）")
            
            elif hypothesis == "肺栓塞":
                if "呼吸困难" in case.symptoms:
                    supporting_evidence.append("患者表现为呼吸困难")
                if "胸痛" in case.symptoms:
                    supporting_evidence.append("伴有胸痛")
                if not any(risk in case.medical_history.lower() for risk in ["卧床", "手术", "外伤"]):
                    contradicting_evidence.append("缺乏肺栓塞的典型危险因素")
            
            # 生成分析文本
            analysis = f"**{hypothesis}**:\n"
            
            if supporting_evidence:
                analysis += "支持证据：\n- " + "\n- ".join(supporting_evidence) + "\n"
            
            if contradicting_evidence:
                analysis += "反对证据：\n- " + "\n- ".join(contradicting_evidence) + "\n"
            
            # 评估可能性
            if len(supporting_evidence) > len(contradicting_evidence) + 1:
                analysis += "评估：可能性较高\n"
            elif len(supporting_evidence) > len(contradicting_evidence):
                analysis += "评估：中等可能性\n"
            else:
                analysis += "评估：可能性较低\n"
            
            analyses.append(analysis)
        
        return "\n".join(analyses)
    
    def _derive_conclusion(self, case: MedicalCase, context: str) -> str:
        """根据上下文推导出最终诊断结论"""
        # 简单模拟，实际应用需更复杂的逻辑
        hypotheses = self._generate_possible_hypotheses(case)
        
        # 如果有ground truth且在假设中，以一定概率返回正确答案
        if case.ground_truth and case.ground_truth in hypotheses:
            if random.random() < 0.8:  # 80%概率返回正确答案
                return case.ground_truth
        
        # 否则返回第一个假设
        return hypotheses[0] if hypotheses else "无法确定诊断"
    
    def _extract_reasoning_for_conclusion(self, context: str, conclusion: str) -> str:
        """提取支持结论的关键推理过程"""
        # 实际应用中应该基于上下文提取相关证据
        return f"1. 患者临床表现符合{conclusion}的典型特征\n2. 已排除其他可能的鉴别诊断\n3. 患者具有{conclusion}的高危因素"

class ReflectionExpert:
    """反思专家类 - 负责评估推理步骤的合理性"""
    
    def __init__(self, ground_truth: Optional[str] = None):
        self.ground_truth = ground_truth
        self.evaluation_criteria = {
            "logic_consistency": "逻辑一致性",
            "medical_accuracy": "医学准确性",
            "evidence_sufficiency": "证据充分性",
            "reasoning_coherence": "推理连贯性"
        }
    
    def evaluate_step(self, step: ReasoningStep, previous_steps: List[ReasoningStep]) -> ReasoningStep:
        """评估推理步骤"""
        # 计算各项评分
        logic_score = self._evaluate_logic(step.content, previous_steps)
        medical_score = self._evaluate_medical_accuracy(step.content)
        evidence_score = self._evaluate_evidence(step.content)
        coherence_score = self._evaluate_coherence(step.content, previous_steps)
        
        # 综合评分
        overall_score = (logic_score + medical_score + evidence_score + coherence_score) / 4
        
        # 生成反馈
        feedback = self._generate_feedback(step.content, overall_score)
        
        # 更新步骤信息
        step.validity_score = overall_score
        step.feedback = feedback
        step.is_valid = overall_score > 0.6  # 有效性阈值
        
        return step
    
    def _evaluate_logic(self, reasoning: str, previous_steps: List[ReasoningStep]) -> float:
        """评估逻辑一致性"""
        logical_indicators = {
            "因此": 0.8, "因为": 0.7, "基于": 0.6, "由此可见": 0.9,
            "所以": 0.8, "因而": 0.7, "导致": 0.6
        }
        
        score = 0.5  # 基础分
        for indicator, weight in logical_indicators.items():
            if indicator in reasoning:
                score += weight * 0.1  # 累加得分
        
        # 检查与之前步骤的连贯性
        if previous_steps:
            for prev_step in previous_steps:
                for keyword in prev_step.content.split():
                    if len(keyword) > 3 and keyword in reasoning:  # 只考虑长度>3的关键词
                        score += 0.02  # 小幅加分
        
        return min(score, 1.0)
    
    def _evaluate_medical_accuracy(self, reasoning: str) -> float:
        """评估医学准确性"""
        accurate_terms = ["应考虑", "需鉴别", "符合", "支持诊断", "可能性大"]
        inaccurate_terms = ["肯定是", "绝对是", "必然", "一定"]
        
        accurate_count = sum(1 for term in accurate_terms if term in reasoning)
        inaccurate_count = sum(1 for term in inaccurate_terms if term in reasoning)
        
        total_terms = accurate_count + inaccurate_count
        if total_terms == 0:
            return 0.5
        
        return min(0.3 + (accurate_count / (total_terms + 0.1)) * 0.7, 1.0)
    
    def _evaluate_evidence(self, reasoning: str) -> float:
        """评估证据充分性"""
        evidence_markers = ["表现为", "症状", "体征", "检查", "病史", "结果显示"]
        
        evidence_count = sum(1 for marker in evidence_markers if marker in reasoning)
        
        # 评分函数：基础分0.4，每有一个证据标记加0.1分，最高1.0分
        return min(0.4 + evidence_count * 0.1, 1.0)
    
    def _evaluate_coherence(self, reasoning: str, previous_steps: List[ReasoningStep]) -> float:
        """评估推理连贯性"""
        if not previous_steps:
            return 0.7  # 第一步默认较高连贯性
        
        coherence_score = 0.5
        
        # 检查当前推理是否引用了之前步骤的关键内容
        prev_content = " ".join([step.content for step in previous_steps])
        
        # 提取关键词（简化版）
        keywords = [word for word in prev_content.split() if len(word) > 3]
        
        # 计算当前步骤中包含之前关键词的比例
        if keywords:
            matches = sum(1 for word in keywords if word in reasoning)
            coherence_score = min(0.5 + (matches / len(keywords)) * 0.5, 1.0)
        
        return coherence_score
    
    def _generate_feedback(self, reasoning: str, score: float) -> str:
        """生成评估反馈"""
        if score >= 0.8:
            return "推理过程严谨，逻辑清晰，证据充分。"
        elif score >= 0.6:
            return "推理基本合理，但某些论证可以进一步完善。"
        else:
            # 找出具体的问题
            issues = []
            
            # 检查逻辑指示词
            logical_indicators = ["因此", "因为", "基于", "所以"]
            if not any(indicator in reasoning for indicator in logical_indicators):
                issues.append("缺乏明确的逻辑推导")
            
            # 检查医学准确性
            inaccurate_terms = ["肯定是", "绝对是", "必然", "一定"]
            if any(term in reasoning for term in inaccurate_terms):
                issues.append("存在过度确定性的表述")
            
            # 检查证据
            evidence_markers = ["表现为", "症状", "体征", "检查", "结果显示"]
            if not any(marker in reasoning for marker in evidence_markers):
                issues.append("缺少具体的临床证据支持")
            
            if issues:
                return "推理存在问题：" + "；".join(issues) + "。需要重新评估。"
            else:
                return "推理质量不足，需要重新组织思路。"

class DualExpertReasoningSystem:
    """双专家推理系统 - 协调推理专家和反思专家的协作"""
    
    def __init__(self, max_iterations: int = 5):
        self.reasoning_expert = MedicalReasoningExpert()
        self.reflection_expert = ReflectionExpert()
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
            # 后续轮次基于上下文深化推理
            return self._deepen_reasoning(context, case, iteration)
    
    def _deepen_reasoning(self, context: str, case: MedicalCase, iteration: int) -> ReasoningStep:
        """深化现有推理"""
        # 找出需要改进的部分
        improvement_areas = self._identify_improvement_areas(context)
        
        # 根据需要改进的区域生成深化推理内容
        if "诊断假设" in improvement_areas:
            hypotheses = self.reasoning_expert._generate_possible_hypotheses(case)
            content = f"深化诊断假设：\n基于前述信息，还需考虑以下诊断可能：\n- {hypotheses[-1]}"
            stage = ReasoningStage.HYPOTHESIS_GENERATION
        elif "鉴别诊断" in improvement_areas:
            content = f"补充鉴别诊断：\n针对主要诊断假设，还需考虑以下鉴别要点：\n" + \
                     f"1. 进一步询问{case.symptoms[0]}的具体特征\n" + \
                     f"2. 考虑完善相关辅助检查"
            stage = ReasoningStage.DIFFERENTIAL_DIAGNOSIS
        else:
            # 默认深化结论
            content = "完善诊断结论：\n综合前述分析，需要考虑以下几点：\n" + \
                     "1. 临床表现与主要诊断高度符合\n" + \
                     "2. 建议立即开展进一步检查以确认诊断"
            stage = ReasoningStage.CONCLUSION
        
        return ReasoningStep(
            step_id=iteration + 1,
            content=content,
            stage=stage,
            validity_score=0.5,  # 初始评分，将由反思专家重新评估
            feedback="",  # 初始无反馈
            timestamp=time.time()
        )
    
    def _identify_improvement_areas(self, context: str) -> List[str]:
        """识别推理中需要改进的区域"""
        areas = []
        
        if "诊断假设" not in context or context.count("假设") < 2:
            areas.append("诊断假设")
        
        if "鉴别诊断" not in context or "鉴别" in context and context.count("鉴别") < 2:
            areas.append("鉴别诊断")
        
        if "结论" not in context or "诊断结论" not in context:
            areas.append("诊断结论")
        
        # 如果没有找到需要改进的区域，默认深化结论
        if not areas:
            areas.append("诊断结论")
        
        return areas
    
    def _has_reached_conclusion(self, reasoning: str) -> bool:
        """检查是否已达到诊断结论"""
        conclusion_indicators = ["最终诊断", "诊断结论", "确诊为", "临床诊断"]
        return any(indicator in reasoning for indicator in conclusion_indicators)
    
    def _extract_final_answer(self, reasoning: str) -> str:
        """从推理过程中提取最终诊断答案"""
        conclusion_section = ""
        
        # 查找结论部分
        if "最终诊断：" in reasoning:
            conclusion_section = reasoning.split("最终诊断：")[1].split("\n")[0]
        elif "诊断结论：" in reasoning:
            conclusion_section = reasoning.split("诊断结论：")[1].split("\n")[0]
        elif "确诊为" in reasoning:
            conclusion_section = reasoning.split("确诊为")[1].split("\n")[0]
        elif "临床诊断" in reasoning:
            conclusion_section = reasoning.split("临床诊断")[1].split("\n")[0]
        
        # 清理和格式化
        conclusion = conclusion_section.strip()
        if not conclusion and "综合考虑" in reasoning:
            # 尝试从综合考虑部分提取
            for line in reasoning.split("\n"):
                if "综合考虑" in line and "诊断" in line:
                    words = line.split()
                    for i, word in enumerate(words):
                        if "诊断" in word and i+1 < len(words):
                            conclusion = words[i+1]
                            break
        
        return conclusion.strip("：:,，.。、 ")
    
    def _validate_result(self, answer: str, ground_truth: Optional[str]) -> bool:
        """验证结果是否正确"""
        if not ground_truth:
            return False
        
        return ground_truth.lower() in answer.lower() or answer.lower() in ground_truth.lower()
    
    def _calculate_quality_score(self, iteration_results: List[Dict]) -> float:
        """计算整体推理质量分数"""
        if not iteration_results:
            return 0.0
        
        # 计算加权平均分数，后面的迭代步骤权重更高
        total_weight = 0
        weighted_sum = 0
        
        for i, result in enumerate(iteration_results):
            weight = i + 1  # 权重递增
            weighted_sum += result['validity_score'] * weight
            total_weight += weight
        
        return weighted_sum / total_weight

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
    
    # 初始化系统
    reasoning_system = DualExpertReasoningSystem(max_iterations=3)
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
