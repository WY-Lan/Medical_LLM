# 医学病例报告处理系统

本项目是一个多阶段的医学病例报告处理系统，用于从医学文献中提取结构化的病例信息。

## 项目结构

- `stage_one`: HTML转JSON阶段，将原始HTML文件转换为JSON格式
- `stage_two`: 内容提取阶段，使用AI API从JSON中提取结构化病例信息
- `stage_three`: CoT生成阶段，使用Chain of Thought方法生成更深入的分析

## 问题分析与解决方案

### 1. API响应保存问题

**问题描述**：
- 大模型的response无法成功保存到文件系统
- 日志中没有API请求和响应的记录

**解决方案**：
- 在配置文件`config/default.yaml`中添加`save_responses: true`参数
- 确保`logs/api_responses`目录存在
- 修改`run_stage_two.py`中的API客户端初始化代码，正确传递参数

### 2. JSON解析错误问题

**问题描述**：
- 在`extract_treatment_items`函数中存在格式化字符串错误
- JSON响应解析失败，导致使用默认空结构

**解决方案**：
- 重写`extract_treatment_items`函数，使用更健壮的方式构建提示
- 增强JSON解析和错误处理逻辑，包括多种备选解析方法
- 添加详细日志记录，便于调试

### 3. 治疗项目提取问题

**问题描述**：
- 治疗项目提取API调用失败，出现格式化错误
- 无法正确解析治疗项目JSON响应

**解决方案**：
- 使用f-string直接构建提示，避免模板格式化问题
- 增加多层JSON解析容错机制
- 添加正则表达式备选提取方法，确保即使JSON解析失败也能提取内容

## 使用方法

运行第二阶段处理：

```bash
python scripts/run_stage_two.py --input-dir output/stage_one --output-dir output/stage_two --save-responses --log-level DEBUG
```

参数说明：
- `--input-dir`: 输入目录，包含第一阶段生成的JSON文件
- `--output-dir`: 输出目录，存储生成的结构化数据
- `--save-responses`: 保存API请求和响应
- `--log-level`: 日志级别，可选DEBUG, INFO, WARNING, ERROR

## 后续优化方向

1. 增强JSON解析的稳定性，处理更多边缘情况
2. 优化提示模板，提高信息提取准确率
3. 添加批量处理进度显示和断点续传功能
4. 实现更全面的错误处理和自动重试机制
2. stage_two：**大幅度优化**
	1. 同时要维护两个词典/ai/home/jcw/Project/case_report_v3.1/config/mapping，"case_content_mapping.json"、"discussion_mapping"这个词典包含 `case_contet` 、`discussion` 信息的映射。**不再维护 `treatment` 的词典**
	2. 提取所有的映射词典中可以对应上的二级标题下的所有内容（模糊匹配）。如果找不到映射，使用 `4o` 进行信息提取，（**先匹配标题，标题不匹配的话再匹配内容**）新增对应的章节标题到映射的词典下。
		- 注意：不再判断多 `case` 的情况，而是只提取第一个 case
		- 设计更加严格的 `prompt` 进行内容提取
		- 提取前进行文本内容过滤，最后截取前 `1500` 个字符作为判断内容，节省token
	3. 然后直接请求 `api` 通过 `4o` 进行数据集的生成。注意：不需要截取内容！！！！注意：一定要忠于原文，不要自己生成，改写。
		1. `basic_info` & `examination` ：根据 `case_contet` 进行生成，尽可能保存原文信息。
			- `basic_info`：患者的基础信息，不能包含诊断结果、治疗方案等等。
			- `exam`：下边还要有两个字段，分别保存检查项目（exam_items）、检查结果 (exam_results)
			- 如果有多个案例的话分别保存到各自字段

		2. `diagnosis`、`treatment_items`：通过 `case_contet` 和 `discussion` 来提取，一定要精准，给出最终的诊断和治疗项目
		3. 最后保存到 `output/stage_two`
	4. 注意：/ai/home/jcw/Project/case_report_v3.1/config/default.yaml，需要读取默认配置文件中的配置！

测试stage2
```py
python scripts/run_stage_two.py --input-dir output/stage_one --output-dir test_output --max-items 5
```



```
{
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
      },
    }
  },
  "metadata": {
    "source_file": "",
    "title": "",
    "article_id": ""
  }
}

```
