from langchain_core.prompts import PromptTemplate

# 系统消息基础提示
SYSTEM_RESEARCH_BASE = """
你是一位专业的研究助手，擅长进行深度研究和信息综合。
你的任务是：
1. 基于用户问题进行深入研究
2. 使用搜索工具获取相关信息
3. 综合分析搜索结果，提供准确、全面的回答
4. 保持回答的客观性和逻辑性
"""

# 问题规划提示
PLAN_PROMPT = """
请分析用户的问题，将其分解为多个子问题，以便进行更有效的网络搜索。

用户问题：{query}

请输出 JSON 格式的子问题列表，每个子问题包含：
- subq: 具体的搜索问题
- reason: 为什么需要这个子问题

最多输出 {max_subquestions} 个子问题。

输出格式示例：
[
    {{"subq": "什么是递归摘要法在对话压缩中的应用", "reason": "了解基本概念和技术原理"}},
    {{"subq": "递归摘要法与聚类法的性能对比", "reason": "比较两种方法的优缺点"}}
]
"""

# 搜索结果综合提示
SYNTHESIS_PROMPT = """
基于以下搜索结果，回答用户的问题：{query}

搜索结果：
{snippets}

请提供一个全面、准确的回答，引用相关来源。
"""

# 用户质疑处理提示
CRITIQUE_PROMPT = """
用户对之前的回答提出了质疑/反馈：{feedback}

请分析反馈内容，判断是否需要进行新的搜索来改进回答。

输出 JSON 格式：
{{
    "need_new_search": true/false,
    "new_subquestions": ["新的搜索问题1", "新的搜索问题2"],
    "improved_answer": "基于反馈改进的回答内容"
}}
"""

# 记忆压缩提示
MEMORY_SUMMARIZE_PROMPT = """
请对以下对话历史进行压缩摘要，保留关键信息和研究主题。

对话历史：
{history}

请生成一个简洁的摘要，突出：
1. 主要研究主题
2. 用户的关注点和质疑
3. 已有的研究成果

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