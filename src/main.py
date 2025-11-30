from src.agent import ResearchAgent
from src.config.settings import settings

def demo():
    # 可在此处指定 agent_key，如 "research"（来自 agents.yaml）
    agent = ResearchAgent(agent_key="research")

    print("== 新研究轮 ==")
    r = agent.ask("请研究多轮对话中的上下文压缩策略，并比较递归摘要法与聚类法的优缺点。")
    print("初次回答：\n", r["answer_markdown"])

    print("\n== 用户质疑 ==")
    critique_result = agent.critique("请增加对窗口化策略的细节，并说明和记忆总结的组合方式。")
    print("改进回答：\n", critique_result["critique_result"]["improved_answer"])

    print("\n== 查看状态 ==")
    print(agent.export_state())

if __name__ == "__main__":
    # 确保配置加载
    settings.load_agents()
    demo()