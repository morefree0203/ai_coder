from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import os

@dataclass
class Settings:
    # 通用开关
    debug: bool = True

    # 记忆 & 压缩
    memory_max_turns: int = 12
    memory_compress_after: int = 8
    memory_keep_last_n: int = 4

    # MCP / 搜索
    mcp_config_path: str = "src/mcp/config.yaml"
    enable_search_tool: bool = True
    search_tool_name: str = "web_search"

    # agents 配置文件（可用环境变量 AGENTS_CONFIG_PATH 覆盖）
    agents_config_path: Optional[str] = None

    # 运行时加载的 agents 内容缓存
    agents: Dict[str, Any] = field(default_factory=dict)

    # 其他默认
    max_subquestions: int = 5

    def __post_init__(self):
        # 尝试加载 .env（如果安装了 python-dotenv）
        try:
            from dotenv import load_dotenv
            load_dotenv(override=False)
        except Exception:
            pass

    def _default_agents_path(self) -> Path:
        # 默认在本文件夹（src/config）下查找 agents.yaml
        return Path(__file__).resolve().parent / "agents.yaml"

    def load_agents(self) -> None:
        """
        加载 agents.yaml。优先级：
         1. 环境变量 AGENTS_CONFIG_PATH
         2. self.agents_config_path（实例化时可覆盖）
         3. src/config/agents.yaml（相对于本文件）
        """
        env_path = os.getenv("AGENTS_CONFIG_PATH") or self.agents_config_path
        if env_path:
            p = Path(env_path)
            if not p.is_absolute():
                # 以 settings.py 所在目录为基准，避免 current working directory 导致的问题
                p = Path(__file__).resolve().parent.joinpath(env_path).resolve()
        else:
            p = self._default_agents_path()

        if not p.exists():
            raise FileNotFoundError(f"agents.yaml 未找到: {p}")

        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self.agents = data.get("agents", {})

    def get_agent_config(self, agent_key: str) -> Dict[str, Any]:
        if not self.agents:
            self.load_agents()
        cfg = self.agents.get(agent_key)
        if not cfg:
            raise KeyError(f"在 agents.yaml 中未找到 agent: {agent_key}")
        return cfg

# 全局单例
settings = Settings()