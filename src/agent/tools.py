from typing import Any, Dict, List, Optional
import yaml
import json
import requests
from pathlib import Path
from langchain.tools import BaseTool
from ..config.settings import settings

class MCPToolClient:
    """
    兼容两种配置格式：
      - src/mcp/config.yaml（自定义简易工具列表）
      - src/mcp/mcp.json（ModelScope MCP 风格）
    """
    def __init__(self, config_path: str | None = None):
        path = Path(config_path or settings.mcp_config_path)
        if not path.is_absolute():
            # 以项目 src 目录为相对基准（更稳健）
            path = (Path(__file__).resolve().parents[2] / path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"MCP 配置文件未找到: {path}")

        self.raw_path = path
        if path.suffix.lower() in (".yml", ".yaml"):
            with path.open("r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            self.tools = {t["name"]: t for t in cfg.get("tools", [])}
        elif path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
            self.tools = {}
            if "tools" in cfg and isinstance(cfg["tools"], list):
                for t in cfg["tools"]:
                    self.tools[t["name"]] = t
            if "mcp_servers" in cfg:
                for server_key, server in cfg["mcp_servers"].items():
                    # 优先使用配置的 name，如果没有则使用 server_key
                    # 只注册一个键，避免重复
                    name = server.get("name") or server_key
                    entry = {
                        "name": name,
                        "endpoint": server.get("url"),
                        "method": "POST",
                        "api_key": server.get("api_key"),
                        "server_key": server_key,
                        "raw": server
                    }
                    # 只注册一个键（使用 name），保持与配置一致
                    self.tools[name] = entry
            if "agent_tools" in cfg:
                self.agent_tools = cfg.get("agent_tools", {})
            else:
                self.agent_tools = {}
        else:
            raise ValueError(f"不支持的 MCP 配置文件类型: {path.suffix}")

    def list_tools(self) -> List[str]:
        return list(self.tools.keys())

    def call(self, name: str, query: str) -> List[Dict[str, Any]]:
        """
        调用某个工具/服务器，返回解析后的 JSON（约定返回 list[ {title,snippet,url} ]）
        若工具不存在，会抛出并列出可用工具以便调试。
        注意：不同 MCP 的请求/返回格式不同，必要时在此处适配 headers / payload / response parsing。
        """
        tool = self.tools.get(name)
        if not tool:
            raise ValueError(f"未在 MCP 配置中找到工具: {name}. 可用工具: {', '.join(sorted(self.list_tools()))}")

        endpoint = tool.get("endpoint") or tool.get("url") or tool.get("raw", {}).get("url")
        if not endpoint:
            raise ValueError(f"工具 {name} 未配置 endpoint/url")

        method = (tool.get("method") or "POST").upper()
        headers: Dict[str, str] = {}
        # 将 api_key 放到 x-api-key，若 MCP 要求 Authorization: Bearer ... 请修改这里
        if tool.get("api_key"):
            headers["x-api-key"] = tool.get("api_key")
        if tool.get("raw") and isinstance(tool["raw"], dict) and tool["raw"].get("api_key"):
            headers.setdefault("x-api-key", tool["raw"].get("api_key"))

        params_template = tool.get("params")
        try:
            if params_template and isinstance(params_template, dict):
                params = {k: (v.replace("{{query}}", query) if isinstance(v, str) else v) for k, v in params_template.items()}
                if method == "GET":
                    resp = requests.get(endpoint, params=params, headers=headers, timeout=30)
                else:
                    resp = requests.post(endpoint, json=params, headers=headers, timeout=30)
            else:
                payload = {"query": query}
                if tool.get("server_key"):
                    payload["server"] = tool.get("server_key")
                resp = requests.request(method, endpoint, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"MCP 调用失败: {e}")

        try:
            data = resp.json()
            # 检查返回数据格式
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # 如果返回的是字典，尝试提取结果
                # 常见的 MCP 返回格式：{"results": [...]} 或 {"data": [...]}
                if "results" in data and isinstance(data["results"], list):
                    return data["results"]
                elif "data" in data and isinstance(data["data"], list):
                    return data["data"]
                elif "items" in data and isinstance(data["items"], list):
                    return data["items"]
                else:
                    # 如果字典中没有列表，返回包装后的结果
                    return [{"title": str(data.get("title", "MCP 响应")), 
                            "snippet": str(data.get("content", data.get("message", str(data)))), 
                            "url": endpoint}]
            else:
                # 其他类型，包装成列表
                return [{"title": "MCP 响应", "snippet": str(data), "url": endpoint}]
        except ValueError as e:
            # JSON 解析失败
            return [{"title": "(非 JSON 响应)", "snippet": resp.text[:500], "url": endpoint}]

# 为兼容 pydantic v2（LangChain BaseTool 使用 pydantic），把字段声明为注解字段
class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "使用外部搜索引擎(MCP)进行信息检索，输入自然语言查询。"
    client: Optional[Any] = None
    preferred: List[str] = []

    def __init__(self, client: MCPToolClient, preferred_tool_names: Optional[List[str]] = None):
        # 把需要作为字段的值通过 BaseModel 的 __init__ 路径注入，避免 pydantic 拦截普通赋值
        preferred = preferred_tool_names or []
        # 调用基类 __init__，它会把注解字段设置为模型字段
        super().__init__(client=client, preferred=preferred)

    def _choose_tool_name(self) -> str:
        if getattr(settings, "search_tool_name", None):
            if settings.search_tool_name in self.client.tools:
                return settings.search_tool_name
        for n in self.preferred:
            if n in self.client.tools:
                return n
        available = list(self.client.tools.keys())
        if not available:
            raise RuntimeError("MCP 客户端没有注册任何工具/服务器")
        return available[0]

    def _run(self, query: str) -> Any:
        tool_name = self._choose_tool_name()
        return self.client.call(tool_name, query)

    async def _arun(self, query: str) -> Any:
        return self._run(query)