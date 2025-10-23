# Huatuo_complex_cot 使用指南

该目录提供基于大型语言模型的医疗开放题 Complex CoT（复杂链式推理）生成流水线：初始推理 → 自动验证 → 多策略重思考 →（可选）带标签修正 → 自然化重写 → 最终回答。适用于从医疗问答或病例描述中自动构建结构化推理过程与答案。

## 快速开始
- 安装依赖：
  - `pip install requests retrying tqdm`
- 准备数据：输入 JSON 至少包含两个字段：
  - `Open-ended Verifiable Question`（开放式可验证问题）
  - `Ground-True Answer`（标准答案）
- 准备 API：
  - 兼容 Chat Completions 风格的接口（请求体包含 `model` 与 `messages`）
  - 获取 `--api_url` 与 `--api_key`

示例数据（`train_data_sample.json`）：
```json
[
  {
    "Open-ended Verifiable Question": "患者信息...请基于病历为我提供一个详细、全面的诊断分析，并给出诊断结果。",
    "Ground-True Answer": "糖尿病"
  }
]
```

## 如何运行
- 中文版脚本（自然化重写为中文，默认并发更高）：
  ```bash
  python search_for_complex_reasoning_path_chinese_version.py \
    --data_path train_data_sample.json \
    --api_url https://api.your-provider.com/v1/chat/completions \
    --api_key YOUR_API_KEY \
    --model_name your-model
  ```
- 英文版脚本（自然化重写为英文，默认并发更低）：
  ```bash
  python search_for_complex_reasoning_path.py \
    --data_path train_data_sample.json \
    --api_url https://api.your-provider.com/v1/chat/completions \
    --api_key YOUR_API_KEY \
    --model_name your-model
  ```

## 常用参数说明
- `--data_path`：输入数据路径，默认 `train_data_sample.json`
- `--model_name`：模型名称（会放入请求体；中文脚本也用于输出路径分层）
- `--api_key`：API 密钥（用作 `Authorization: Bearer`）
- `--api_url`：API 地址（需兼容 Chat Completions）
- `--max_search_attempts`：重思考外层尝试次数，默认 3
- `--max_search_depth`：每次尝试的最大深度，默认 3
- `--efficient_search`：失败时是否使用带标签修正，默认 True
- `--num_process`：并发线程数（中文脚本默认 128；英文脚本默认 5）
- `--limit_num`：限制处理样本数量（调试时建议设置）

调优示例（限制样本与并发）：
```bash
python search_for_complex_reasoning_path_chinese_version.py \
  --data_path train_data_sample.json \
  --api_url https://api.your-provider.com/v1/chat/completions \
  --api_key YOUR_API_KEY \
  --model_name your-model \
  --limit_num 10 \
  --num_process 8
```



## 输出与目录结构
- 单样本输出：
  - 中文版：`output_data/<model_name>/<task_name>/<process_id>.json`
  - 英文版：`output_data/<task_name>/<process_id>.json`
- 合并输出：运行结束生成 `task_name_<N>.json`（当前工作目录），包含所有成功的样本，其中 `<N>` 为样本数。
- `task_name` 由数据文件名派生，例如 `train_data_sample_CoT_search`。

单样本 JSON 含主要字段：
- `Long_CoT`：结构化 CoT（含多步 `Inner Thinking`、`Final Conclusion`、`Verification`）
- `verify`：每次校验结果（布尔）
- `Complex_CoT`：自然化复杂推理文本（字段名为 `NaturalReasoning`）
- `Response`：最终面向用户的回答
- 以及调试信息：`gpt4_query_cot`、`gpt4_response_cot`、`response_struct`、`response_type`、`prior_fail_try` 等

## 流水线细节
- 初始推理：使用 `query_prompt_init` 生成 CoT，`parse_gpt_response` 检查格式（最后三步必须为 `Inner Thinking`、`Final Conclusion`、`Verification`）。
- 自动验证：`verify_prompt` 对比结论与 `Ground-True Answer`（返回 `true/false`）。
- 多策略重思考：在未通过验证时，按策略（回溯、探索新路径、强化校验、纠错）生成新的 CoT 并再次验证；每次保持最后的 `Verification`，在其前拼接新的思考与结论。
- 带标签修正：`efficient_search=True` 且仍失败时，使用带标签提示生成正确的 CoT，并直接视为通过（类型标记为 `Label_CoT`）。
- 自然化重写与最终回答：将 `Long_CoT` 转为按步文本，调用 `reformat_to_complex_cot_prompt` 得到 `Complex_CoT`，再用 `get_final_response_prompt` 产出最终 `Response`。

## 断点续跑
- 脚本启动时会合并已有输出，计算剩余样本。当前实现的并发映射仍遍历 `data`，可能导致重复处理；如需严格跳过已完成样本，可将并发映射目标改为剩余集合 `input_data`。

## 最佳实践与注意事项
- 速率限制：高并发（中文脚本默认 128）可能触发限流，建议根据服务端限流能力调整 `--num_process`。
- 数据质量：`Ground-True Answer` 若不准确，会影响自动终止条件与最终结果。
- 接口兼容：确保 `--api_url` 支持 `model` 与 `messages` 的 Chat Completions 风格。
- 调试建议：先用 `--limit_num` 跑少量样本，确认输出格式与接口稳定后再扩大规模。

## 结果检查
- 单样本：检查对应 `process_id.json` 是否包含 `Complex_CoT` 与 `Response`。
- 合并输出：确认生成 `task_name_<N>.json`，并检查样本数与内容完整性。


> 
Chen J, Cai Z, Ji K, et al. Huatuogpt-o1, towards medical complex reasoning with llms. arXiv preprint arXiv:2412.18925, 2024.

> 
Lan W, Wang W, Ji C, et al. Clinicalgpt-r1: Pushing reasoning capability of generalist disease diagnosis with large language model. arXiv preprint arXiv:2504.09421, 2025.
