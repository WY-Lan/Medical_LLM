import requests
import json
import numpy as np
from typing import Dict, List, Tuple, Optional

class MedicalRewardModel:
    def __init__(self, api_key: str, api_url: str):
        """
        初始化医疗奖励模型评估器
        
        Args:
            api_key: 大模型API的密钥
            api_url: 大模型API的URL
        """
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 存储历史评分用于平滑处理
        self.score_history = {
            "检查": [],
            "诊断": [],
            "治疗": []
        }
        
        # 平滑系数
        self.smoothing_factor = 0.7
        
    def identify_task_type(self, model_output: str, ground_truth: str) -> str:
        """
        识别医疗任务类型：检查、诊断或治疗
        
        Args:
            model_output: 模型的输出文本
            ground_truth: 真实标准答案
            
        Returns:
            任务类型: "检查", "诊断", 或 "治疗"
        """
        prompt = f"""
        请识别以下医疗文本所属的任务类型。任务类型只能是"检查"、"诊断"或"治疗"三种之一。
        
        模型输出:
        {model_output}
        
        真实答案:
        {ground_truth}
        
        请只返回一个词作为任务类型: "检查", "诊断", 或 "治疗"。
        """
        
        response = self._call_api(prompt)
        task_type = response.strip().lower()
        
        # 将返回结果映射到三种任务类型之一
        if "检查" in task_type:
            return "检查"
        elif "诊断" in task_type:
            return "诊断"
        elif "治疗" in task_type:
            return "治疗"
        else:
            # 默认为诊断任务
            return "诊断"
    
    def evaluate_examination(self, model_output: str, ground_truth: str) -> float:
        """
        评估检查任务的得分
        
        Args:
            model_output: 模型的输出文本
            ground_truth: 真实标准答案
            
        Returns:
            评分 (0-10)
        """
        prompt = f"""
        请评估这个医疗检查任务的质量，满分10分。
        
        评估标准:
        1. 检查项目的完整性 (0-3分): 是否包含了所有必要的检查项目
        2. 检查步骤的正确性 (0-3分): 检查步骤是否正确、顺序是否合理
        3. 检查方法的专业性 (0-2分): 使用的检查方法是否专业、规范
        4. 检查结果的解读 (0-2分): 是否对检查结果进行了准确解读
        
        模型输出:
        {model_output}
        
        真实答案:
        {ground_truth}
        
        请给出一个0到10之间的分数，并简要说明评分理由。格式为: "分数: X"，然后是评分理由。
        """
        
        response = self._call_api(prompt)
        score = self._extract_score(response)
        return score
    
    def evaluate_diagnosis(self, model_output: str, ground_truth: str) -> float:
        """
        评估诊断任务的得分
        
        Args:
            model_output: 模型的输出文本
            ground_truth: 真实标准答案
            
        Returns:
            评分 (0-10)
        """
        prompt = f"""
        请评估这个医疗诊断任务的质量，满分10分。
        
        评估标准:
        1. 诊断准确性 (0-4分): 诊断结果是否与真实答案一致
        2. 诊断推理过程 (0-3分): 推理过程是否合理、逻辑严密
        3. 鉴别诊断考虑 (0-2分): 是否考虑了合理的鉴别诊断
        4. 表述专业性 (0-1分): 表述是否专业、规范
        
        模型输出:
        {model_output}
        
        真实答案:
        {ground_truth}
        
        请给出一个0到10之间的分数，并简要说明评分理由。格式为: "分数: X"，然后是评分理由。
        """
        
        response = self._call_api(prompt)
        score = self._extract_score(response)
        return score
    
    def evaluate_treatment(self, model_output: str, ground_truth: str) -> float:
        """
        评估治疗任务的得分
        
        Args:
            model_output: 模型的输出文本
            ground_truth: 真实标准答案
            
        Returns:
            评分 (0-10)
        """
        prompt = f"""
        请评估这个医疗治疗任务的质量，满分10分。
        
        评估标准:
        1. 治疗方案的适当性 (0-3分): 治疗方案是否适当、符合标准
        2. 治疗步骤的完整性 (0-2分): 治疗步骤是否完整
        3. 用药/手术的准确性 (0-3分): 用药剂量、手术方式等是否准确
        4. 潜在风险和预后评估 (0-2分): 是否评估了治疗的风险和预后
        
        模型输出:
        {model_output}
        
        真实答案:
        {ground_truth}
        
        请给出一个0到10之间的分数，并简要说明评分理由。格式为: "分数: X"，然后是评分理由。
        """
        
        response = self._call_api(prompt)
        score = self._extract_score(response)
        return score
    
    def _call_api(self, prompt: str) -> str:
        """调用大模型API获取回复"""
        payload = {
            "model": "gpt-4.1",  # 或其他适用的模型
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2  # 低温度以获得更确定性的评分
        }
        
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"API调用错误: {e}")
            return "分数: 5 (API调用失败，返回默认中间分数)"
    
    def _extract_score(self, response: str) -> float:
        """从API回复中提取分数"""
        try:
            if "分数:" in response:
                score_text = response.split("分数:")[1].split()[0].strip()
            elif "分数：" in response:
                score_text = response.split("分数：")[1].split()[0].strip()
            else:
                # 尝试查找数字
                import re
                numbers = re.findall(r'\d+\.?\d*', response)
                if numbers and 0 <= float(numbers[0]) <= 10:
                    score_text = numbers[0]
                else:
                    return 5.0  # 默认中间分数
                    
            return float(score_text)
        except Exception as e:
            print(f"分数提取错误: {e}, 原始回复: {response}")
            return 5.0  # 默认中间分数
    
    def smooth_score(self, task_type: str, raw_score: float) -> float:
        """
        使用指数平滑法对分数进行平滑处理
        
        Args:
            task_type: 任务类型
            raw_score: 原始评分
            
        Returns:
            平滑后的评分
        """
        history = self.score_history[task_type]
        
        if not history:
            smoothed_score = raw_score
        else:
            # 指数平滑
            last_smoothed = history[-1]
            smoothed_score = self.smoothing_factor * raw_score + (1 - self.smoothing_factor) * last_smoothed
        
        # 更新历史
        self.score_history[task_type].append(smoothed_score)
        
        # 保持历史记录在合理范围内
        if len(self.score_history[task_type]) > 100:
            self.score_history[task_type].pop(0)
            
        return smoothed_score
    
    def evaluate(self, model_output: str, ground_truth: str) -> Dict:
        """
        评估医疗任务，包括任务识别、打分和平滑处理
        
        Args:
            model_output: 模型的输出文本（包括推理过程和结果）
            ground_truth: 真实标准答案
            
        Returns:
            包含任务类型、原始评分和平滑评分的字典
        """
        # 识别任务类型
        task_type = self.identify_task_type(model_output, ground_truth)
        
        # 根据任务类型进行评分
        if task_type == "检查":
            raw_score = self.evaluate_examination(model_output, ground_truth)
        elif task_type == "诊断":
            raw_score = self.evaluate_diagnosis(model_output, ground_truth)
        elif task_type == "治疗":
            raw_score = self.evaluate_treatment(model_output, ground_truth)
        else:
            # 默认诊断评分
            raw_score = self.evaluate_diagnosis(model_output, ground_truth)
            task_type = "诊断"
        
        # 对评分进行平滑处理
        smoothed_score = self.smooth_score(task_type, raw_score)
        
        return {
            "task_type": task_type,
            "raw_score": raw_score,
            "smoothed_score": smoothed_score
        }

# 使用示例
def main():
    # 配置信息
    api_key = ""
    api_url = ""  # 或其他大模型API的URL
    
    # 初始化评估器
    reward_model = MedicalRewardModel(api_key, api_url)
    
    # 示例输入
    example_model_output = """
    推理过程：患者主诉右上腹痛3天，伴有恶心、呕吐，体温38.2℃。体检发现右上腹压痛和反跳痛，墨菲征阳性。
    结合患者的临床表现，首先考虑急性胆囊炎的可能性较大。为了确诊，建议进行以下检查：
    1. 血常规检查，了解白细胞计数是否升高
    2. 肝功能检查，了解胆红素、转氨酶等指标
    3. 腹部超声检查，观察胆囊大小、壁厚、胆石情况
    4. 必要时进行腹部CT检查，进一步明确病变范围

    诊断结果：急性胆囊炎，疑似胆石症
    """
    
    example_ground_truth = """
    诊断：急性胆囊炎伴胆石症
    建议检查：血常规、肝功能、腹部超声、腹部CT
    """
    
    # 进行评估
    result = reward_model.evaluate(example_model_output, example_ground_truth)
    
    print(f"任务类型: {result['task_type']}")
    print(f"原始评分: {result['raw_score']}")
    print(f"平滑评分: {result['smoothed_score']}")

if __name__ == "__main__":
    main()
