from src.agent import ResearchAgent
from src.config.settings import settings

def interactive_dialog():
    """多轮对话交互界面"""
    print("🤖 AI 研究助手 (输入 'quit' 退出)")
    print("=" * 50)

    # 初始化智能体
    agent = ResearchAgent(agent_key="research")
    print("✅ 研究助手已初始化")

    conversation_count = 0

    while True:
        try:
            # 获取用户输入
            user_input = input("\n👤 您的问题: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 再见！")
                break

            if not user_input:
                continue

            conversation_count += 1
            print(f"\n🔄 第 {conversation_count} 轮对话")
            print("-" * 30)

            # 判断是否是质疑/反馈（基于关键词）
            is_critique = any(keyword in user_input.lower() for keyword in [
                '不对', '错误', '增加', '补充', '详细', '质疑', '不完整', '不够'
            ])

            if is_critique and conversation_count > 1:
                print("💭 检测到质疑/反馈，正在改进回答...")
                critique_result = agent.critique(user_input)
                print("✅ 改进回答：")
                print(critique_result["critique_result"]["improved_answer"])
            else:
                print("🔍 正在处理新问题...")
                r = agent.ask(user_input)
                print("✅ 回答：")
                print(r["answer_markdown"])

        except KeyboardInterrupt:
            print("\n👋 用户中断，再见！")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            continue

def demo():
    """演示模式（保留原有功能）"""
    print("🎯 演示模式：多轮对话上下文压缩策略研究")
    print("=" * 50)

    agent = ResearchAgent(agent_key="research")

    print("\n📝 第一轮：初始研究")
    r = agent.ask("请研究多轮对话中的上下文压缩策略，并比较递归摘要法与聚类法的优缺点。")
    print("回答：\n", r["answer_markdown"])

    print("\n💭 第二轮：用户质疑与改进")
    critique_result = agent.critique("请增加对窗口化策略的细节，并说明和记忆总结的组合方式。")
    print("改进回答：\n", critique_result["critique_result"]["improved_answer"])

    print("\n📊 对话状态：")
    state = agent.export_state()
    print(f"压缩上下文: {len(state['compressed_context'])} 字符")
    print(f"消息历史: {len(state['messages'])} 条消息")

if __name__ == "__main__":
    # 确保配置加载
    settings.load_agents()

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        interactive_dialog()