from typing import Any, Dict, List
import yaml
import requests
from langchain.tools import BaseTool
from ..config.settings import settings

class MCPToolClient:
    """
    读取 MCP 配置并执行工具调用。
    假设 config.yaml 中:
    tools:
      - name: web_search
        endpoint: "http://localhost:8000/search"
        method: GET
        params:
          q: "{{query}}"
    """
    def __init__(self, config_path: str | None = None):
        path = config_path or settings.mcp_config_path
        with open(path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.tools = {t["name"]: t for t in self.config.get("tools", [])}

    def call(self, name: str, query: str) -> List[Dict[str, Any]]:
        tool = self.tools.get(name)
        if not tool:
            raise ValueError(f"MCP tool '{name}' not found.")
        method = tool.get("method", "GET").upper()
        endpoint = tool["endpoint"]
        params_template = tool.get("params", {})
        # 简单模板替换
        params = {k: v.replace("{{query}}", query) for k, v in params_template.items()}
        if method == "GET":
            resp = requests.get(endpoint, params=params, timeout=30)
        else:
            resp = requests.post(endpoint, json=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # 约定：返回 list[ { "title": ..., "snippet": ..., "url": ... } ]
        return data

class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "使用外部搜索引擎(MCP)进行信息检索，输入自然语言查询。"
    client: MCPToolClient

    def __init__(self, client: MCPToolClient):
        super().__init__()
        self.client = client

    def _run(self, query: str) -> Any:
        results = self.client.call(settings.search_tool_name, query)
        return results

    async def _arun(self, query: str) -> Any:
        # 简单串行
        return self._run(query)