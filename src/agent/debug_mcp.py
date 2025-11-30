# 调试脚本：检测 MCP 配置加载情况
from pathlib import Path
import json, yaml, sys
from src.config.settings import settings
from src.agent.tools import MCPToolClient

def print_settings():
    print("settings.mcp_config_path:", settings.mcp_config_path)
    try:
        settings_path = settings.mcp_config_path
        p = Path(settings_path)
        if not p.is_absolute():
            p = Path(__file__).resolve().parents[1].joinpath(settings_path).resolve()
        print("Resolved mcp config path:", p)
        print("Exists?:", p.exists())
    except Exception as e:
        print("Error resolving path:", e)

def load_and_print_json(path):
    p = Path(path)
    if not p.exists():
        print("文件不存在:", p)
        return
    try:
        if p.suffix.lower() in (".yaml", ".yml"):
            with p.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        else:
            with p.open('r', encoding='utf-8') as f:
                data = json.load(f)
        print("Raw config keys:", list(data.keys()))
        # pretty print some content
        print(json.dumps(data, indent=2, ensure_ascii=False)[:2000])
    except Exception as e:
        print("解析配置文件失败:", e)

def debug_mcp_client():
    try:
        client = MCPToolClient(settings.mcp_config_path)
    except Exception as e:
        print("MCPToolClient 初始化异常:", repr(e))
        return
    print("MCPToolClient.raw_path:", getattr(client, "raw_path", None))
    tools = getattr(client, "tools", {})
    print("client.tools keys:", list(tools.keys()))
    # print a sample tool config
    for k, v in list(tools.items())[:10]:
        print(" -", k, "->", v)

if __name__ == "__main__":
    print_settings()
    cfgpath = settings.mcp_config_path
    load_and_print_json(cfgpath)
    debug_mcp_client()