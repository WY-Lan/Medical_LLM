# 双专家医学推理与数据生成

> 一个基于“推理专家 + 反思专家”的轻量级医学推理与数据生成示例，用于模拟临床诊断思维并产出 SFT（Supervised Fine-Tuning）训练样本。

> **重要声明**：本项目仅用于教学/研究示例，**不构成医疗建议**，不得用于真实临床决策。

---

## ✨ 特色

* **双专家协同**：`MedicalReasoningExpert` 负责结构化推理与诊断，`ReflectionExpert` 负责基于多维指标打分与反馈。
* **阶段化推理模板**：信息收集 → 假设生成 → 鉴别诊断 → 诊断结论，自动拼接完整推理链条。
* **可迭代优化**：通过多轮迭代与有效性阈值筛选，逐步完善推理质量。
* **SFT 数据就绪**：内置 `CitrusS3DataGenerator`，一键生成包含 `<thinking>` 与 `<answer>` 的训练样本。
* **零第三方依赖**：全部基于 Python 标准库（`dataclasses`、`Enum`、`logging` 等）。

---

## 🧱 项目结构（建议）

```
.
├─ medical_reasoning.py     # 主实现（可按需命名）
├─ README.md
└─ citrus_s3_training_data.json  # 运行后生成
```

---

## 🚀 快速开始

### 环境要求

* Python ≥ 3.8
* 仅使用标准库，无需安装第三方依赖

### 运行示例

```bash
python cirtus_complex_cot.py.py
```

成功运行后终端会输出生成摘要，并在当前目录生成：

* `citrus_s3_training_data.json`：包含全部生成记录（病例、推理结果、时间戳等）

---

## 🔎 核心概念

### 数据结构

* **`MedicalCase`**：单个病例（`case_id`、`patient_info`、`chief_complaint`、`medical_history`、`symptoms`、`ground_truth`）
* **`ReasoningStep`**：一步推理产物（阶段、内容、评分、反馈、时间戳、有效性）
* **`ReasoningStage`**：推理阶段枚举（信息收集 / 假设生成 / 鉴别诊断 / 结论）

### 双专家职责

* **推理专家 `MedicalReasoningExpert`**

  * 依据模板生成四阶段推理文本
  * 基于症状/病史的启发式映射产出候选诊断
  * 形成鉴别诊断分析并给出初步结论
* **反思专家 `ReflectionExpert`**

  * 从 **逻辑一致性 / 医学准确性 / 证据充分性 / 连贯性** 四维打分
  * 生成改进反馈，判断步骤是否“有效”（默认阈值：0.6）

### 工作流（`DualExpertReasoningSystem`）

1. 迭代生成推理步骤并即时评估
2. 仅吸收“有效”步骤进入最终推理
3. 出现“诊断结论”关键字即提前收敛
4. 按迭代权重计算整体**质量分**（后期权重更高）

---

## 🧪 最小可用示例（代码片段）

```python
# 1) 构造病例
cases = [
    MedicalCase(
        case_id="case_001",
        patient_info="45岁男性",
        chief_complaint="持续性胸痛2小时",
        medical_history="高血压病史5年，吸烟史20年",
        symptoms=["胸痛", "呼吸困难", "出汗"],
        ground_truth="急性心肌梗死"
    )
]

# 2) 初始化系统
system = DualExpertReasoningSystem(max_iterations=3)

# 3) 生成训练数据
writer = CitrusS3DataGenerator(system)
training_data = writer.generate_dataset(cases)
writer.save_dataset("citrus_s3_training_data.json")
```
