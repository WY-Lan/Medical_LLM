## 一、命令

```bash
CUDA_VISIBLE_DEVICES=0 \
llamafactory-cli train \
  --stage sft \
  --do_predict \
  --model_name_or_path /ai/home/wwz/model/llama2_7b_code \
  --adapter_name_or_path /ai/home/wwz/LLaMA-Factory/saves/llama2_7b_code/lora/sft \
  --eval_dataset identity,alpaca_en_demo \
  --dataset_dir ./data \
  --template llama2 \
  --finetuning_type lora \
  --output_dir ./saves/llama2_7b_code/lora/predict \
  --overwrite_cache \
  --overwrite_output_dir \
  --cutoff_len 1024 \
  --preprocessing_num_workers 16 \
  --per_device_eval_batch_size 1 \
  --max_samples 20 \
  --predict_with_generate
```

## 二、参数解释（核心项）

* `--stage sft`：监督微调阶段（与模板/数据格式配套）。
* `--do_predict`：在评估集上进行**生成式预测**（会跳到预测流程；如含训练流程，通常在训练/评估后执行预测）。
* `--model_name_or_path`：基座模型路径（需与 `--template llama2` 匹配）。
* `--adapter_name_or_path`：LoRA 适配器路径（用于加载已有 LoRA 权重进行预测，或继续 SFT）。
* `--finetuning_type lora`：启用 LoRA。
* `--eval_dataset identity,alpaca_en_demo`：评估集名称（可逗号分隔多个），需在 `--dataset_dir` 下配置。
* `--dataset_dir ./data`：数据目录根路径（需包含数据文件与 `dataset_info.json` 声明）。
* `--template llama2`：对话模板/分隔符等，需与模型/词表兼容。
* `--output_dir`：输出目录（预测结果与日志写入此处）。
* `--cutoff_len 1024`：样本最大序列长度（超长将被截断）。
* `--per_device_eval_batch_size 1`：评估/预测 batch 大小（显存紧张时设小一点更安全）。
* `--max_samples 20`：仅取前 20 条进行快速试跑（去掉即可跑全量）。
* `--predict_with_generate`：采用生成式推理而非仅打分。
* `--overwrite_cache` / `--overwrite_output_dir`：覆盖缓存/输出目录。
* `--preprocessing_num_workers 16`：预处理并行度（按 CPU 核心数调整）。
