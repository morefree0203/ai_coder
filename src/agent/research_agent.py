import json
from typing import List, Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
# 方法1：使用 langchain-openai 包（推荐，兼容 1.x 最新规范）
from langchain_openai import ChatOpenAI
# 方法2：如果只装了 openai 包，用旧路径兼容（1.0.8 仍支持）
# from langchain.chat_models.openai import ChatOpenAI

# 消息类的导入路径修正（1.x 版本统一在 langchain.schema 下）
from .prompt import (
    SYSTEM_RESEARCH_BASE,
    PLAN_PROMPT,
    SYNTHESIS_PROMPT,
    CRITIQUE_PROMPT
)
from .memory import ConversationMemory
from .tools import MCPToolClient, WebSearchTool
from ..config.settings import settings

def build_chat_llm_from_agent(agent_key: str) -> ChatOpenAI:
    """
    通过 agents.yaml 的指定 agent 配置构建 ChatOpenAI。
    ModelScope 提供 OpenAI 兼容的 API（base_url + api_key）。
    """
    cfg = settings.get_agent_config(agent_key)
    model = cfg.get("model")
    api_key = cfg.get("api_key")
    base_url = cfg.get("base_url", None)
    temperature = cfg.get("temperature", 0.3)
    max_tokens = cfg.get("max_tokens", 2048)

    # ChatOpenAI 支持自定义 base_url 与 api_key（OpenAI兼容接口）
    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return llm

class ResearchAgent:
    """
    单用户多轮 Research Agent。
    使用 agents.yaml 的 research 配置来初始化模型。
    """
    def __init__(self, agent_key: str = "research"):
        # 主 LLM
        self.llm = build_chat_llm_from_agent(agent_key)

        # 记忆管理器
        self.memory = ConversationMemory()

        # 压缩记忆 LLM（可复用主模型，或用配置里 memory_summary_model）
        cfg = settings.get_agent_config(agent_key)
        summary_model = cfg.get("memory_summary_model", cfg.get("model"))
        self.memory.summarizer_llm = ChatOpenAI(
            model=summary_model,
            api_key=cfg.get("api_key"),
            base_url=cfg.get("base_url"),
            temperature=0.2,
            max_tokens=1024
        )

        # 工具初始化
        self.tools = {}
        if settings.enable_search_tool:
            mcp_client = MCPToolClient(settings.mcp_config_path)
            self.tools["web_search"] = WebSearchTool(mcp_client)

        self.system_message = SystemMessage(content=SYSTEM_RESEARCH_BASE)

    def _plan(self, query: str) -> List[Dict[str, str]]:
        plan_prompt = PLAN_PROMPT.format(
            query=query,
            max_subquestions=settings.max_subquestions if hasattr(settings, "max_subquestions") else 5
        )
        response = self.llm.invoke([self.system_message, HumanMessage(content=plan_prompt)])
        text = response.content.strip()
        try:
            data = json.loads(text)
            if isinstance(data, list):
                max_n = getattr(settings, "max_subquestions", 5)
                return data[: max_n]
        except Exception:
            return [{"subq": query, "reason": "原始问题（JSON解析失败回退）"}]
        return [{"subq": query, "reason": "原始问题（未识别结构）"}]

    def _search(self, subquestions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        search_tool = self.tools.get("web_search")
        if not search_tool:
            print("🔍 未进行 Web Research：搜索工具未启用")
            return [{"subq": sq["subq"], "results": [], "error": "搜索工具未启用"} for sq in subquestions]

        print(f"🔍 正在进行 Web Research，共 {len(subquestions)} 个子问题...")
        aggregated = []
        for i, sq in enumerate(subquestions, 1):
            query = sq["subq"]
            print(f"  搜索问题 {i}: {query}")
            try:
                results = search_tool.run(query)
                print(f"    找到 {len(results)} 个结果")
                # 打印搜索结果摘要
                for j, result in enumerate(results[:3], 1):  # 只显示前3个结果
                    title = result.get('title', '(无标题)')
                    snippet = result.get('snippet', '')[:100] + '...' if len(result.get('snippet', '')) > 100 else result.get('snippet', '')
                    url = result.get('url', '')
                    print(f"      [{j}] {title}")
                    print(f"          {snippet}")
                    print(f"          URL: {url}")
                err = ""
            except Exception as e:
                results = []
                err = str(e)
                print(f"    搜索失败: {err}")
            aggregated.append({
                "subq": query,
                "reason": sq.get("reason", ""),
                "results": results,
                "error": err
            })
        print("🔍 Web Research 完成")
        return aggregated

    def _synthesize(self, query: str, search_data: List[Dict[str, Any]]) -> str:
        snippets_lines = []
        idx = 1
        for block in search_data:
            results = block.get("results", [])
            if not results:
                snippets_lines.append(f"[{idx}] (无结果) {block['subq']}")
                idx += 1
                continue
            for r in results:
                line = f"[{idx}] {r.get('title','(无标题)')} | {r.get('snippet','')} | {r.get('url','')}"
                snippets_lines.append(line)
                idx += 1

        synth_prompt = SYNTHESIS_PROMPT.format(
            query=query,
            snippets="\n".join(snippets_lines) if snippets_lines else "(无搜索数据)"
        )

        response = self.llm.invoke([self.system_message, HumanMessage(content=synth_prompt)])
        return response.content

    def ask(self, query: str) -> Dict[str, Any]:
        self.memory.add("user", query)
        plan = self._plan(query)
        search_data = self._search(plan)
        answer_markdown = self._synthesize(query, search_data)
        self.memory.add("assistant", answer_markdown)
        self.memory.maybe_compress()

        return {
            "plan": plan,
            "search_raw": search_data,
            "answer_markdown": answer_markdown
        }

    def critique(self, feedback: str) -> Dict[str, Any]:
        self.memory.add("user", feedback)
        critique_prompt = CRITIQUE_PROMPT.format(feedback=feedback)
        response = self.llm.invoke([self.system_message, HumanMessage(content=critique_prompt)])
        txt = response.content.strip()
        try:
            data = json.loads(txt)
        except Exception:
            data = {
                "need_new_search": False,
                "new_subquestions": [],
                "improved_answer": f"解析反馈 JSON 失败，原始内容：\n{txt}"
            }

        if data.get("need_new_search") and data.get("new_subquestions"):
            subqs = [{"subq": q, "reason": "用户质疑后新增"} for q in data["new_subquestions"]]
            search_data = self._search(subqs)
            improved_full = self._synthesize(data["new_subquestions"][0], search_data)
            data["improved_answer"] += "\n\n## 新增补充搜索综合\n" + improved_full
        else:
            search_data = []

        self.memory.add("assistant", data["improved_answer"])
        self.memory.maybe_compress()

        return {
            "critique_result": data,
            "new_search_raw": search_data
        }

    def export_state(self) -> Dict[str, Any]:
        return {
            "compressed_context": self.memory.compressed_context,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in self.memory.messages
            ]
        }

    def continue_dialog(self, user_message: str) -> str:
        self.memory.add("user", user_message)
        context_msgs = [self.system_message] + [
            HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
            for m in self.memory.messages
        ]
        response = self.llm.invoke(context_msgs)
        self.memory.add("assistant", response.content)
        self.memory.maybe_compress()
        return response.content