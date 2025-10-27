# 医学推理数据生成系统

医学推理数据生成系统是一个基于双专家协作框架的智能数据生成工具，专门用于生成高质量的医学诊断推理训练数据。该系统通过模拟资深医学专家和反思专家的协作过程，生成结构化的临床推理数据，适用于医学AI模型的训练和评估。

## 核心特性

🧠 **双专家协作框架**：推理专家生成诊断假设，反思专家评估推理质量
🏥 **专业医学推理**：模拟真实临床诊断思维过程
🤖 **大模型集成**：支持多种大语言模型API调用
📊 **质量评估**：自动评估生成数据的逻辑性和医学准确性
🔄 **迭代优化**：多轮推理迭代，持续优化诊断结论
💾 **标准化输出**：生成符合SFT训练格式的数据

## 系统架构

```
MedicalCase (输入)
    ↓
DualExpertReasoningSystem (双专家推理系统)
    ├── MedicalReasoningExpert (推理专家)
    │   ├── 信息收集
    │   ├── 假设生成
    │   ├── 鉴别诊断
    │   └── 结论推导
    └── ReflectionExpert (反思专家)
        ├── 逻辑一致性评估
        ├── 医学准确性评估
        ├── 证据充分性评估
        └── 推理连贯性评估
    ↓
Training Data (输出)
```

## 输入数据格式

```python
MedicalCase(
    case_id: str,                    # 病例ID
    patient_info: str,                # 患者基本信息
    chief_complaint: str,             # 主诉
    medical_history: str,             # 病史
    symptoms: List[str],              # 症状列表
    ground_truth: Optional[str]       # 正确答案（可选）
)
```

## 输出数据格式

```json
{
    "sft-input": "完整的诊断提示词",
    "sft-target": "<thinking>推理过程</thinking>\n\n<answer>诊断结论</answer>",
    "metadata": {
        "case_id": "病例ID",
        "iterations": 推理迭代次数,
        "success": 是否成功,
        "quality_score": 质量评分,
        "timestamp": 生成时间戳
    }
}
```
