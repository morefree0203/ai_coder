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

    # MCP / 搜索：默认改为读取 mcp.json（你已有此文件）
    # 可以通过环境变量 MCP_CONFIG_PATH 覆盖（推荐在 CI/部署中使用）
    mcp_config_path: str = "src/mcp/mcp.json"
    enable_search_tool: bool = True
    search_tool_name: str = "web_search"

    # agents 配置文件（可用环境变量 AGENTS_CONFIG_PATH 覆盖）
    agents_config_path: Optional[str] = None

    # 运行时加载的 agents 内容缓存
    agents: Dict[str, Any] = field(default_factory=dict)

    # 其他默认
    max_subquestions: int = 5

    def __post_init__(self):
        try:
            from dotenv import load_dotenv
            load_dotenv(override=False)
        except Exception:
            pass

    def _default_agents_path(self) -> Path:
        return Path(__file__).resolve().parent / "agents.yaml"

    def _resolve_path(self, rel_or_abs: str) -> Path:
        """
        将可能的相对路径解析为基于 src/config 的绝对路径或项目 src 根的绝对路径，避免工作目录差异。
        优先使用环境变量 MCP_CONFIG_PATH（若设置）。
        """
        p = Path(rel_or_abs)
        if p.is_absolute():
            return p
        # 1) 以当前 settings 文件夹为基准（src/config）
        candidate = Path(__file__).resolve().parent.joinpath(rel_or_abs).resolve()
        if candidate.exists():
            return candidate
        # 2) 以项目 src 根为基准（.. up two levels from this file）
        project_src = Path(__file__).resolve().parents[1]
        candidate2 = project_src.joinpath(rel_or_abs).resolve()
        return candidate2

    def load_agents(self) -> None:
        env_path = os.getenv("AGENTS_CONFIG_PATH") or self.agents_config_path
        if env_path:
            p = Path(env_path)
            if not p.is_absolute():
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

    def resolve_mcp_config_path(self) -> Path:
        """
        返回解析后的 MCP 配置路径（支持环境变量 MCP_CONFIG_PATH）
        """
        env = os.getenv("MCP_CONFIG_PATH")
        if env:
            return self._resolve_path(env)
        return self._resolve_path(self.mcp_config_path)

# 全局单例
settings = Settings()