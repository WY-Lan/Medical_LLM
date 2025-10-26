# 医疗奖励模型评估器（MedicalRewardModel）

> 使用大语言模型（LLM）对**检查 / 诊断 / 治疗**三类医疗任务进行自动化评分，并通过指数平滑得到稳定的奖励信号

> **重要声明**：本项目仅用于教学/研究示例，**不构成医疗建议**，不得用于真实临床决策或替代专业医生判断。

---

## ✨ 功能特性

* **任务自识别**：从模型输出与标准答案中，自动识别为「检查 / 诊断 / 治疗」。
* **分任务细则评分**：针对三类任务内置独立评分维度与打分 prompt，输出 0–10 分区间的原始分数。
* **稳态奖励**：采用**指数平滑**（默认 α = 0.7）对序列评分进行平滑，减少单次波动。
* **轻依赖**：仅依赖 `requests`、`numpy`，可快速集成到现有评估/训练流水线。

---

## 🧱 代码结构

* `MedicalRewardModel`：核心评估器

  * `identify_task_type`：识别任务类型
  * `evaluate_examination / evaluate_diagnosis / evaluate_treatment`：三类任务评分
  * `_call_api`：调用大模型 API（示例为 Chat Completions 形式）
  * `_extract_score`：从回复文本中抽取数值分数
  * `smooth_score`：对分数做指数平滑
  * `evaluate`：端到端评估（识别 → 评分 → 平滑）
* `main()`：可直接运行的示例脚本

---

## 🛠️ 环境要求

* Python ≥ 3.8
* 依赖安装：

```bash
pip install requests numpy
```

---

## 🚀 快速开始

### 1) 配置 API Key 与 URL

在 `main()` 或你的业务代码中设置：

```python
api_key = "YOUR_API_KEY"
api_url = "https://your-llm-provider/chat/completions"
reward_model = MedicalRewardModel(api_key, api_url)
```

> **提示**：建议通过环境变量或配置文件注入密钥，避免硬编码。

### 2) 构造输入并评估

```python
model_output = """
推理过程：...
诊断结果：...
"""

ground_truth = """
诊断：...
建议检查：...
"""

result = reward_model.evaluate(model_output, ground_truth)
print(result)
# {
#   'task_type': '诊断',
#   'raw_score': 8.5,
#   'smoothed_score': 8.2
# }
```

### 3) 运行示例脚本

```bash
python your_file.py
```

脚本包含一个右上腹痛病例的演示输入，便于快速验证流程。

---

## 📐 评分设计

### 任务类型识别（`identify_task_type`）

* 通过 prompt 让 LLM 在 **检查 / 诊断 / 治疗** 中三选一；无法识别时默认「诊断」。

### 三类任务评分维度

* **检查**（0–10）

  1. 完整性（0–3）
  2. 步骤正确性（0–3）
  3. 方法专业性（0–2）
  4. 结果解读（0–2）
* **诊断**（0–10）

  1. 诊断准确性（0–4）
  2. 推理过程（0–3）
  3. 鉴别诊断（0–2）
  4. 表述专业性（0–1）
* **治疗**（0–10）

  1. 方案适当性（0–3）
  2. 步骤完整性（0–2）
  3. 用药/手术准确性（0–3）
  4. 风险与预后（0–2）

> 三个 `evaluate_*` 方法都会向 LLM 发送打分提示，并要求以“**分数: X** + 简要理由”的格式返回。


## 🔌 与大模型 API 的对接

* `_call_api` 默认以如下负载调用：

```json
{
  "model": "gpt-4.1",
  "messages": [{"role": "user", "content": "<prompt>"}],
  "temperature": 0.2
}
```

---

## 🧪 示例：端到端输出

输入为含“急性胆囊炎”线索的推理文本与标准答案。运行后将输出：

```text
任务类型: 诊断
原始评分: <LLM返回的分数>
平滑评分: <指数平滑后的分数>
```
