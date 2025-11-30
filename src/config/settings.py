from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any
import yaml
import os

class Settings(BaseSettings):
    # 通用设置（非 agent 级别）
    debug: bool = Field(default=True)

    # 记忆 & 压缩
    memory_max_turns: int = Field(default=12, description="超过即尝试压缩历史")
    memory_compress_after: int = Field(default=8, description="开始压缩阈值")
    memory_keep_last_n: int = Field(default=4, description="压缩时保留最近原始轮数")

    # MCP / 搜索
    mcp_config_path: str = Field(default="src/mcp/config.yaml")
    enable_search_tool: bool = Field(default=True)
    search_tool_name: str = Field(default="web_search")

    # 配置文件路径
    agents_config_path: str = Field(default="src/config/agents.yaml")

    # agents 动态配置缓存
    agents: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def load_agents(self):
        path = self.agents_config_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"agents.yaml 未找到: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        self.agents = data.get("agents", {})

    def get_agent_config(self, agent_key: str) -> Dict[str, Any]:
        if not self.agents:
            self.load_agents()
        cfg = self.agents.get(agent_key)
        if not cfg:
            raise KeyError(f"在 agents.yaml 中未找到 agent: {agent_key}")
        return cfg

settings = Settings()