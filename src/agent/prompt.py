from langchain_core.prompts import PromptTemplate

# Research Agent 使用的提示模板常量

SYSTEM_RESEARCH_BASE = """
你是一位专业的研究助手，擅长进行系统性的信息检索和分析。
你的任务是：
1. 分析用户的问题，制定合理的搜索策略
2. 使用网络搜索工具获取相关信息
3. 综合分析搜索结果，提供准确、有见地的回答
4. 在对话过程中保持上下文连贯性

请始终以客观、专业的方式回答问题，确保信息准确可靠。
"""

PLAN_PROMPT = """
基于用户的问题："{query}"

请制定一个信息检索计划，分解为最多 {max_subquestions} 个子问题。
每个子问题应该：
1. 具体且可搜索
2. 相互补充，避免重复
3. 能够帮助全面回答用户的问题

请以 JSON 数组格式返回，格式如下：
[
  {{"subq": "具体的子问题1", "reason": "为什么要搜索这个问题"}},
  {{"subq": "具体的子问题2", "reason": "为什么要搜索这个问题"}}
]

只返回 JSON 数组，不要包含其他文本。
"""

SYNTHESIS_PROMPT = """
基于用户的问题："{query}"

以下是搜索到的信息片段：
{snippets}

请综合这些信息，撰写一个完整、准确的回答。
要求：
1. 直接回答用户的问题
2. 引用相关信息来源
3. 保持逻辑清晰，结构合理
4. 如果信息不足，明确说明
"""

CRITIQUE_PROMPT = """
用户对之前的回答提出了反馈："{feedback}"

请分析用户的反馈，判断是否需要：
1. 进行新的搜索来补充信息
2. 修改或完善现有回答
3. 澄清某些概念

请以 JSON 格式返回：
{{
  "need_new_search": true/false,
  "new_subquestions": ["新搜索问题1", "新搜索问题2"] （如果需要新搜索）,
  "improved_answer": "改进后的完整回答"
}}

如果不需要新搜索，new_subquestions 设为空数组。
"""

MEMORY_SUMMARIZE_PROMPT = """
以下是对话历史记录，请将其压缩为一段简洁的摘要，保留关键信息和上下文。

对话历史：
{history}

请生成一个简洁的摘要，要求：
1. 保留用户的主要问题和研究目标
2. 保留重要的发现和结论
3. 保留关键的技术细节和概念
4. 使用简洁的语言，控制在1000字以内

摘要：
"""

RESEARCH_PROMPT = PromptTemplate(
    input_variables=["requirement", "research_data", "previous_plan", "instruction"],
    template="""
你是一位高级系统架构师。基于以下调研数据，请生成一份详细的技术方案。

---用户需求---
{requirement}

--- 之前的记录---
{previous_plan}

---调研数据---
{research_data}

---重要说明---
{instruction}

---输出要求---
请输出严格的 JSON 格式，包含以下字段（不要输出任何多余文本或代码块）：
1. project_name: 项目名称
2. description: 简述
3. tech_stack: {{ "language": "...", "backend": "...", "frontend": "...", "database": "..." }}
4. implementation_steps: [ "第一步...", "第二步..." ]
5. key_features: [ ... ]

确保技术选型具体（例如指明具体的 Python 库或版本），不要输出 ```json 代码块标记，直接输出 JSON 字符串。
""",
    template_format="f-string"
)