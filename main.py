"""
智行规划师 — 主入口

用法:
    # 启动 Web UI (Streamlit)
    python main.py

    # 或直接运行
    streamlit run frontend/app.py

    # CLI 模式 (命令行生成方案)
    python main.py --cli "我想去杭州玩3天，预算2000"
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

# 确保项目根目录在 Python Path 中
sys.path.insert(0, str(Path(__file__).parent))


def run_cli(user_input: str):
    """命令行模式 — 直接生成方案并保存为 Markdown"""
    import json
    from workflows.graph import create_travel_plan
    from tools.export import export_to_markdown

    print(f"\n{'='*60}")
    print(f"  🗺️  智行规划师 — CLI 模式")
    print(f"{'='*60}\n")
    print(f"📝 需求: {user_input}")
    print(f"⏳ 正在生成旅行方案... (预计 30-60 秒)\n")

    try:
        plan_dict = create_travel_plan(user_input)
        plan_json = json.dumps(plan_dict, ensure_ascii=False, default=str)

        print(f"✅ 方案生成成功！\n")
        print(f"📊 基本信息:")
        req = plan_dict.get("request", {})
        print(f"   目的地: {req.get('destination', 'N/A')}")
        print(f"   天数: {req.get('days', 'N/A')}")
        print(f"   风格: {req.get('style', 'N/A')}")
        print(f"   天数: {len(plan_dict.get('daily_plans', []))} 天行程")

        budget = plan_dict.get("budget", {})
        if budget:
            print(f"   预算: ¥{budget.get('total', 0):,.0f} (人均 ¥{budget.get('per_person', 0):,.0f})")

        # 导出 Markdown
        filepath = export_to_markdown(plan_json)
        print(f"\n📄 方案已导出: {filepath}")

        # 简单预览
        print(f"\n{'='*60}")
        print(f"  📅 行程速览")
        print(f"{'='*60}")
        for day in plan_dict.get("daily_plans", []):
            spots = []
            for period in ["morning", "afternoon", "evening"]:
                for act in day.get(period, []):
                    spots.append(act.get("name", ""))
            print(f"  Day {day['day']} ({day.get('theme', '')}): {' → '.join(spots[:6])}")

        print(f"\n{'='*60}")
        print(f"  ✅ 完成！")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n❌ 生成失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_web():
    """启动 Streamlit Web UI"""
    import subprocess

    frontend_path = Path(__file__).parent / "frontend" / "app.py"
    print(f"🚀 启动 Web 界面...")
    print(f"   访问地址: http://localhost:8501\n")

    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(frontend_path),
        "--server.port", "8501",
        "--browser.serverAddress", "localhost",
    ])


def main():
    parser = argparse.ArgumentParser(
        description="🗺️ 智行规划师 — 基于多智能体协同的一站式旅行全案定制系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                           # 启动 Web UI
  python main.py --cli "杭州3天穷游"        # CLI 模式
  streamlit run frontend/app.py            # 直接启动 Web UI
        """,
    )
    parser.add_argument(
        "--cli", type=str, default=None,
        help="CLI 模式，传入自然语言旅行需求"
    )

    args = parser.parse_args()

    if args.cli:
        run_cli(args.cli)
    else:
        run_web()


if __name__ == "__main__":
    main()
