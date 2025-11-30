from typing import List, Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from .prompt import (
    SYSTEM_RESEARCH_BASE,
    PLAN_PROMPT,
    SYNTHESIS_PROMPT,
    CRITIQUE_PROMPT
)
from .memory import ConversationMemory
from .tools import MCPToolClient, WebSearchTool
from ..config.settings import settings

class ResearchAgent:
    """
    单用户多轮 Research Agent。
    使用 agents.yaml 的 research 配置来初始化模型，并从 MCP 的 agent_tools 映射中选取优先工具。
    """
    def __init__(self, agent_key: str = "research"):
        # 主 LLM（仍然使用配置文件里指定的 agent 配置）
        try:
            cfg = settings.get_agent_config(agent_key)
            self.llm = ChatOpenAI(
                model=cfg.get("model"),
                api_key=cfg.get("api_key"),
                base_url=cfg.get("base_url"),
                temperature=cfg.get("temperature", 0.3),
                max_tokens=cfg.get("max_tokens", 2048),
            )
        except Exception:
            # 回退到默认（若没有 agents.yaml 或配置不完整）
            self.llm = ChatOpenAI(model=settings.__dict__.get("default_model", "gpt-4o-mini"))

        # 记忆管理
        self.memory = ConversationMemory()

        # 压缩记忆 LLM（可以与主模型相同）
        try:
            summary_model = cfg.get("memory_summary_model", cfg.get("model"))
            self.memory.summarizer_llm = ChatOpenAI(
                model=summary_model,
                api_key=cfg.get("api_key"),
                base_url=cfg.get("base_url"),
                temperature=0.2,
                max_tokens=1024
            )
        except Exception:
            self.memory.summarizer_llm = None

        # 工具初始化：从 MCP 配置中读取 agent_tools 映射作为 preferred list
        self.tools: Dict[str, Any] = {}
        if settings.enable_search_tool:
            mcp_client = MCPToolClient(settings.mcp_config_path)

            # 获取 mcp.json 中 agent_tools 映射（如果有）
            preferred: List[str] = []
            try:
                if hasattr(mcp_client, "agent_tools"):
                    mapping = getattr(mcp_client, "agent_tools") or {}
                    if agent_key in mapping and isinstance(mapping[agent_key], dict):
                        raw_preferred = mapping[agent_key].get("tools", []) or []
                        # 将 server_key 映射为对应的 name（工具键）
                        for tool_ref in raw_preferred:
                            # 如果 tool_ref 在 tools 中，直接使用
                            if tool_ref in mcp_client.tools:
                                preferred.append(tool_ref)
                            else:
                                # 尝试通过 server_key 找到对应的 name
                                for tool_name, tool_entry in mcp_client.tools.items():
                                    if isinstance(tool_entry, dict) and tool_entry.get("server_key") == tool_ref:
                                        preferred.append(tool_name)
                                        break
            except Exception:
                preferred = []

            # 如果 settings.search_tool_name 是有效工具名，确保它在 preferred 前列
            stn = getattr(settings, "search_tool_name", None)
            if stn and stn in mcp_client.tools and stn not in preferred:
                preferred.insert(0, stn)

            # Debug 输出：列出 MCP client 解析到的工具，以及给 WebSearchTool 的 preferred 列表
            try:
                print("MCPTools available:", list(mcp_client.tools.keys()))
                print("Preferred tools for agent", agent_key, ":", preferred)
            except Exception:
                pass

            self.tools["web_search"] = WebSearchTool(mcp_client, preferred_tool_names=preferred)

        self.system_message = SystemMessage(content=SYSTEM_RESEARCH_BASE)

    def _plan(self, query: str) -> List[Dict[str, str]]:
        plan_prompt = PLAN_PROMPT.format(
            query=query,
            max_subquestions=getattr(settings, "max_subquestions", 5)
        )
        response = self.llm.invoke([self.system_message, HumanMessage(content=plan_prompt)])
        text = response.content.strip()
        try:
            import json
            data = json.loads(text)
            if isinstance(data, list):
                return data[: getattr(settings, "max_subquestions", 5)]
        except Exception:
            return [{"subq": query, "reason": "原始问题（JSON解析失败回退）"}]
        return [{"subq": query, "reason": "原始问题（未识别结构）"}]

    def _search(self, subquestions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        search_tool = self.tools.get("web_search")
        if not search_tool:
            return [{"subq": sq["subq"], "results": [], "error": "搜索工具未启用"} for sq in subquestions]

        aggregated = []
        for sq in subquestions:
            query = sq["subq"]
            chosen_tool = None
            try:
                # 在此处可以打印实际选用的 MCP 工具名，便于调试
                if hasattr(search_tool, "_choose_tool_name"):
                    chosen_tool = search_tool._choose_tool_name()
                    print(f"Using MCP tool '{chosen_tool}' for query: {query}")
                results = search_tool.run(query)
                # 检查返回结果格式
                if results is None:
                    results = []
                    err = "MCP 返回 None"
                elif not isinstance(results, list):
                    results = []
                    err = f"MCP 返回格式错误: 期望 list，实际 {type(results).__name__}"
                elif len(results) == 0:
                    err = "MCP 返回空结果列表"
                else:
                    err = ""
                    print(f"  ✅ 获取到 {len(results)} 条结果")
            except Exception as e:
                results = []
                err = f"MCP 调用异常: {str(e)}"
                print(f"  ❌ MCP 调用失败: {err}")
            
            aggregated.append({
                "subq": query,
                "reason": sq.get("reason", ""),
                "results": results or [],
                "error": err,
                "mcp_tool_used": chosen_tool  # 记录使用的 MCP 工具
            })
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
            import json
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