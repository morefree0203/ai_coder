from src.agent import ResearchAgent
from src.config.settings import settings

def print_mcp_usage(search_data):
    """打印 MCP 使用情况"""
    print("\n🔧 MCP 使用情况:")
    print("-" * 30)

    # 检查是否使用了 MCP（通过检查是否有搜索结果或错误信息）
    web_search_used = False
    fetch_used = False
    total_results = 0
    used_tools = set()  # 记录实际使用的工具名

    for block in search_data:
        results = block.get("results", [])
        error = block.get("error", "")
        mcp_tool = block.get("mcp_tool_used", "")
        
        # 记录实际使用的工具
        if mcp_tool:
            used_tools.add(mcp_tool)
            if 'web_search' in mcp_tool.lower() or 'bing' in mcp_tool.lower():
                web_search_used = True
            elif 'fetch' in mcp_tool.lower():
                fetch_used = True
        
        # 如果有结果或尝试调用（即使失败也算使用了）
        if results or error:
            # 检查错误信息或结果来判断使用了哪个 MCP
            if error and not mcp_tool:
                # 如果有错误但没有记录工具名，通过错误信息判断
                if 'web_search' in error.lower() or 'bing' in error.lower():
                    web_search_used = True
                elif 'fetch' in error.lower():
                    fetch_used = True
                else:
                    # 默认认为使用了 web_search（因为主要工具是 web_search）
                    web_search_used = True
            elif results:
                # 有结果说明成功调用了 MCP
                total_results += len(results)
                # 通过结果内容判断使用了哪个 MCP
                for result in results:
                    url = result.get('url', '')
                    if url:
                        if 'bing' in url.lower() or 'search' in url.lower():
                            web_search_used = True
                        else:
                            fetch_used = True
                    else:
                        # 如果没有 URL 但有内容，可能是 fetch 的结果
                        if result.get('content') or result.get('text'):
                            fetch_used = True
                        else:
                            web_search_used = True

    # 打印使用的工具
    if used_tools:
        print(f"🔧 实际使用的 MCP 工具: {', '.join(sorted(used_tools))}")
    
    print(f"📊 Web Search MCP: {'✅ 已使用' if web_search_used else '❌ 未使用'}")
    print(f"📊 Fetch MCP: {'✅ 已使用' if fetch_used else '❌ 未使用'}")
    
    if total_results > 0:
        print(f"📈 共获取到 {total_results} 条搜索结果")
    elif error:
        print(f"⚠️  调用过程中出现错误: {error[:100]}")

    if web_search_used or fetch_used:
        print(f"🎯 共使用了 {int(web_search_used) + int(fetch_used)} 个 MCP 服务")
    else:
        print("🎯 未使用任何 MCP 服务（可能调用失败或返回空结果）")

def print_search_results(search_data):
    """打印搜索结果"""
    print("\n🔍 搜索结果详情:")
    print("-" * 30)

    total_sites = 0
    for i, block in enumerate(search_data, 1):
        results = block.get("results", [])
        if results:
            print(f"\n📋 子问题 {i}: {block.get('subq', 'N/A')}")
            for j, result in enumerate(results, 1):
                title = result.get('title', '(无标题)')
                snippet = result.get('snippet', '(无摘要)')
                url = result.get('url', '(无URL)')

                print(f"  🌐 网站 {j}: {title}")
                print(f"     URL: {url}")
                print(f"     摘要: {snippet[:200]}{'...' if len(snippet) > 200 else ''}")
                total_sites += 1

    if total_sites == 0:
        print("📭 未找到相关搜索结果")
    else:
        print(f"\n📊 共找到 {total_sites} 个相关网站")

def interactive_dialog():
    """多轮对话交互界面"""
    print("🤖 AI 研究助手 (输入 'quit' 或 'q' 退出)")
    print("=" * 50)
    print("💡 支持功能：")
    print("   • 提出研究问题")
    print("   • 对回答进行质疑和反馈")
    print("   • 查看 MCP 使用情况和搜索结果")
    print("   • 自动维护对话上下文")
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

                # 打印 MCP 使用情况
                if "new_search_raw" in critique_result and critique_result["new_search_raw"]:
                    print_mcp_usage(critique_result["new_search_raw"])
                    print_search_results(critique_result["new_search_raw"])

                print("\n✅ 改进回答：")
                print(critique_result["critique_result"]["improved_answer"])
            else:
                print("🔍 正在处理新问题...")
                r = agent.ask(user_input)

                # 打印 MCP 使用情况
                if "search_raw" in r:
                    print_mcp_usage(r["search_raw"])
                    print_search_results(r["search_raw"])

                print("\n✅ 回答：")
                print(r["answer_markdown"])

            # 显示对话状态
            state = agent.export_state()
            compressed_ctx = state.get('compressed_context') or ""
            print("\n📊 对话状态:")
            print(f"   上下文长度: {len(compressed_ctx)} 字符")
            print(f"   消息历史: {len(state['messages'])} 条消息")

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