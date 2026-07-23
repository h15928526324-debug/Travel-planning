"""
智行规划师 — Streamlit 前端交互界面

运行方式: streamlit run frontend/app.py

提供:
  - 自然语言输入 + 结构化表单双入口
  - 实时进度展示
  - 行程日历视图
  - 预算表可视化
  - 避坑/拍照/清单折叠面板
  - 多轮对话修改
  - Markdown/PDF 导出
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

# 将项目根目录加入 Python Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from models.schemas import TravelRequest, TravelStyle
from workflows.graph import TravelPlannerGraph

# ═══════════════════════════════════════════════════════
# 页面配置
# ═══════════════════════════════════════════════════════

st.set_page_config(
    page_title="智行规划师 | AI 旅行全案定制",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════
# CSS 样式
# ═══════════════════════════════════════════════════════

st.markdown("""
<style>
/* 主色调 */
:root {
    --primary: #FF6B35;
    --primary-light: #FFF0EB;
    --bg: #FAFAFA;
}

/* 标题 */
.main-title {
    font-size: 2.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #FF6B35, #FF8C42);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}

.subtitle {
    color: #888;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
}

/* 卡片 */
.card {
    background: white;
    border-radius: 12px;
    padding: 1.2rem;
    margin: 0.5rem 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border: 1px solid #eee;
}

/* 进度步骤 */
.step-active { color: #FF6B35; font-weight: 600; }
.step-done { color: #4CAF50; font-weight: 600; }
.step-pending { color: #ccc; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════
# Session State 初始化 (放在最前面，sidebar 和 main 共用)
# ═══════════════════════════════════════════════════════

if "plan_result" not in st.session_state:
    st.session_state.plan_result = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "main"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "generating" not in st.session_state:
    st.session_state.generating = False
if "planner" not in st.session_state:
    st.session_state.planner = TravelPlannerGraph()

# --- 用户 session 标识 (积分系统用) ---
import uuid
if "user_session_id" not in st.session_state:
    st.session_state.user_session_id = str(uuid.uuid4())


def get_cm():
    """获取当前用户的 CreditManager 实例"""
    from services.credit_manager import get_credit_manager
    return get_credit_manager(st.session_state.user_session_id)


# ═══════════════════════════════════════════════════════
# 侧边栏 — 积分面板 + 出行偏好
# ═══════════════════════════════════════════════════════

with st.sidebar:
    st.image("https://img.icons8.com/color/96/road-perspective.png", width=60)
    st.markdown("## 🗺️ 智行规划师")

    # ── 💰 积分面板 ──
    cm = get_cm()
    credits = cm.balance
    remaining = cm.remaining_plans

    credit_col1, credit_col2 = st.columns([2, 1])
    with credit_col1:
        st.metric("💰 我的积分", f"{credits}", help=f"可生成 {remaining} 次方案")
    with credit_col2:
        st.metric("✈️ 可生成", f"{remaining}次")

    # 积分进度条
    from services.credit_manager import PLAN_COST
    st.progress(min(1.0, credits / (PLAN_COST * 5)), text=f"每次规划消耗 **{PLAN_COST}** 积分")

    # ── 💳 充值面板 ──
    with st.expander("💳 充值积分", expanded=False):
        from services.credit_manager import RECHARGE_PLANS

        for plan in RECHARGE_PLANS:
            cols = st.columns([1, 3, 2])
            with cols[0]:
                st.markdown(f"### {plan['badge']}")
            with cols[1]:
                st.markdown(f"**{plan['name']}**\n\n{plan['credits']} 积分 · ¥{plan['price']}")
            with cols[2]:
                if st.button(f"¥{plan['price']} 充值", key=f"recharge_{plan['id']}",
                             use_container_width=True):
                    new_balance = cm.recharge(
                        plan["credits"],
                        f"💳 {plan['name']} · ¥{plan['price']} → {plan['credits']} 积分"
                    )
                    st.success(f"✅ 充值成功！当前余额: {new_balance} 积分")
                    st.rerun()

        st.markdown("---")
        st.caption("💡 以上为模拟充值，实际接入微信/支付宝支付")

    # ── 📋 交易记录 ──
    with st.expander("📋 积分明细", expanded=False):
        history = cm.history(limit=10)
        if history:
            for tx in history:
                amount_str = f"+{tx['amount']}" if tx['amount'] > 0 else str(tx['amount'])
                st.markdown(
                    f"{tx['icon']} {tx['description']}  "
                    f"**{amount_str}** → 余额 {tx['balance_after']}\n\n"
                    f"*{tx['time']}*"
                )
        else:
            st.caption("暂无记录")

    st.markdown("---")

    # ── ⚙️ 出行偏好 ──
    st.markdown("## ⚙️ 出行偏好")

    destination = st.text_input("🎯 目的地", placeholder="例如: 杭州、成都、日本大阪")
    days = st.slider("📅 旅行天数", 1, 15, 3)
    travelers = st.number_input("👥 出行人数", 1, 50, 1)
    budget_total = st.number_input("💰 预算上限 (元)", 0, 100000, 0, step=1000,
                                    help="0 表示不限预算")
    departure_city = st.text_input("🏠 出发城市", placeholder="例如: 上海")
    start_date = st.date_input("📆 出发日期")

    style_map = {
        "穷游🎒": TravelStyle.BUDGET,
        "轻奢✨": TravelStyle.LIGHT_LUXURY,
        "亲子👨‍👩‍👧": TravelStyle.FAMILY,
        "美食🍜": TravelStyle.FOODIE,
        "拍照打卡📸": TravelStyle.PHOTOGRAPHY,
        "探险🏔️": TravelStyle.ADVENTURE,
        "休闲度假🏖️": TravelStyle.RELAXATION,
        "人文历史📚": TravelStyle.CULTURE,
    }
    style_label = st.selectbox("🎨 出行风格", list(style_map.keys()))
    travel_style = style_map[style_label]

    special_req = st.text_area("✨ 特殊需求", placeholder="例如: 不去博物馆、多安排拍照点、需要无障碍设施",
                               height=80)

    # 生成按钮
    st.markdown("---")
    generate_btn = st.button("🚀 开始规划", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("### 💡 试试这样说")
    st.markdown("""
    > "我和闺蜜想去成都玩4天，
    > 预算每人3000，想要美食+拍照，
    > 不去熊猫基地"
    """)
    st.markdown("""
    > "带爸妈去北京3天，
    > 经典景点为主，不要太累，
    > 住宿要舒适"
    """)

# ═══════════════════════════════════════════════════════
# 主内容区
# ═══════════════════════════════════════════════════════

st.markdown('<p class="main-title">🗺️ 智行规划师</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">基于多智能体协同的一站式旅行全案定制系统 · 输入需求，自动生成完整攻略</p>',
            unsafe_allow_html=True)

# 自然语言输入区
st.markdown("### 📝 用自然语言描述你的旅行需求")
natural_input = st.text_area(
    "natural_input",
    placeholder="试试说: 我下个月想去杭州玩3天，一个人，预算2000，喜欢拍照和美食，帮我规划一下~",
    height=80,
    label_visibility="collapsed",
)


def run_planning():
    """触发规划流程 — 检查积分后再启动"""
    from services.credit_manager import PLAN_COST
    cm = get_cm()
    if not cm.can_plan():
        st.error(f"❌ 积分不足！当前余额 {cm.balance} 积分，需要 {PLAN_COST} 积分。请充值后再试。")
        return
    st.session_state.generating = True
    st.session_state.plan_result = None


# 触发生成
if generate_btn or (natural_input and st.button("🎯 解析自然语言输入", type="secondary")):
    run_planning()

if st.session_state.generating:
    # 构建 TravelRequest
    if natural_input and not (destination or departure_city):
        travel_req = None
        raw = natural_input
    else:
        travel_req = TravelRequest(
            destination=destination or "杭州",
            days=days,
            travelers=travelers,
            budget_total=budget_total,
            style=travel_style,
            departure_city=departure_city,
            start_date=str(start_date) if start_date else "",
            special_requirements=[s.strip() for s in special_req.split("\n") if s.strip()],
            raw_input=natural_input or "",
        )
        raw = ""

    # ── 使用 st.status 容器实现增量进度展示 ──
    status_container = st.status("🤖 多智能体协同工作启动...", expanded=True)

    accumulated_state: dict = {}
    final_travel_req = travel_req

    try:
        # 选择流式方法
        if travel_req:
            stream_iter = st.session_state.planner.stream_run_with_request(
                travel_req, thread_id=st.session_state.thread_id
            )
        else:
            stream_iter = st.session_state.planner.stream_run(
                raw, thread_id=st.session_state.thread_id
            )

        for chunk in stream_iter:
            node = chunk["node"]
            update = chunk["update"]

            # 合并状态
            for k, v in update.items():
                if k == "messages":
                    accumulated_state.setdefault("messages", []).extend(v)
                elif k == "errors":
                    accumulated_state.setdefault("errors", []).extend(v)
                else:
                    accumulated_state[k] = v

            # 根据节点追加进度行
            if node == "parse":
                msgs = update.get("messages", [])
                for m in msgs:
                    status_container.write(m)

            elif node == "research":
                status_container.write("✅ 🔍 **调研 Agent 完成** — 目的地情报已搜集")
                research = update.get("research_result")
                if research:
                    n_attr = len(research.attractions) if research.attractions else 0
                    n_food = len(research.foods) if research.foods else 0
                    n_hotel = len(research.hotels) if research.hotels else 0
                    weather = research.weather
                    if weather and isinstance(weather, dict):
                        cur = weather.get("current", {})
                        status_container.write(
                            f"   🌤️ {cur.get('weather','?')} {cur.get('temperature','?')}°C | "
                            f"🏛️ {n_attr}个景点 | 🍜 {n_food}个美食 | 🏨 {n_hotel}个住宿"
                        )
                    else:
                        status_container.write(f"   🏛️ {n_attr}个景点 | 🍜 {n_food}个美食 | 🏨 {n_hotel}个住宿")

            elif node == "planning":
                status_container.write("✅ 📅 **行程规划 Agent 完成** — 每日行程已编排")
                daily = update.get("daily_plans", [])
                for day in daily:
                    spots = []
                    for p in ["morning", "afternoon", "evening"]:
                        for act in getattr(day, p, []):
                            spots.append(act.name)
                    status_container.write(f"   Day {day.day} — {day.theme or '探索日'}: {' → '.join(spots[:4])}")

            elif node == "budget":
                status_container.write("✅ 💰 **预算 Agent 完成** — 明细表已生成")
                budget = update.get("budget_table")
                if budget:
                    status_container.write(f"   总预算: ¥{budget.total:,.0f} | 人均: ¥{budget.per_person:,.0f} | 应急: ¥{budget.contingency:,.0f}")

            elif node == "tips":
                status_container.write("✅ ⚠️ **避坑攻略 Agent 完成** — 防坑指南+清单+应急已就绪")
                pitfalls = update.get("pitfalls")
                if pitfalls:
                    n_scams = len(pitfalls.common_scams) if pitfalls.common_scams else 0
                    n_traps = len(pitfalls.tourist_traps) if pitfalls.tourist_traps else 0
                    status_container.write(f"   避坑 {n_scams + n_traps} 条 | 拍照机位、物品清单、应急预案已生成")

            elif node == "copywriting":
                status_container.write("✅ ✍️ **文案 Agent 完成** — 行程总览已生成")
                overview = update.get("overview", "")
                if overview:
                    status_container.write(f"   {overview[:120]}...")

            elif node == "finalize":
                pass  # 汇总节点不需要额外展示

        # ── 流式完成，构建 TravelPlan ──
        status_container.update(label="✅ 全案生成完毕！", state="complete")

        request = accumulated_state.get("user_request") or final_travel_req
        if request is None:
            from models.schemas import TravelRequest as TR, TravelStyle as TS
            request = TR(destination="成都", days=2, travelers=2, budget_total=1500, style=TS.BUDGET)

        from models.schemas import TravelPlan, BudgetTable, PitfallTips, PackingList, EmergencyPlan, PhotoGuide

        plan = TravelPlan(
            request=request,
            daily_plans=accumulated_state.get("daily_plans", []),
            budget=accumulated_state.get("budget_table") or BudgetTable(),
            research=accumulated_state.get("research_result"),
            pitfalls=accumulated_state.get("pitfalls") or PitfallTips(),
            packing=accumulated_state.get("packing_list") or PackingList(),
            emergency=accumulated_state.get("emergency_plan") or EmergencyPlan(),
            photo_guide=accumulated_state.get("photo_guide") or PhotoGuide(),
            overview=accumulated_state.get("overview", ""),
        )
        st.session_state.plan_result = plan
        st.session_state.messages = accumulated_state.get("messages", [])

        # 扣减积分
        from services.credit_manager import PLAN_COST
        cm2 = get_cm()
        dest = request.destination if request else "未知目的地"
        if cm2.deduct(PLAN_COST, f"✈️ {dest}{request.days if request else ''}日游方案"):
            status_container.write(f"💰 已消耗 {PLAN_COST} 积分，剩余 {cm2.balance} 积分")

    except Exception as e:
        st.error(f"❌ 规划失败: {str(e)}")
        import traceback
        with st.expander("🔧 错误详情"):
            st.code(traceback.format_exc())
        status_container.update(label="规划出错", state="error")
    finally:
        st.session_state.generating = False


# ═══════════════════════════════════════════════════════
# 结果展示
# ═══════════════════════════════════════════════════════

plan = st.session_state.plan_result

if plan:
    st.markdown("---")

    # Tab 切换不同视图
    tabs = st.tabs([
        "📅 每日行程",
        "💰 预算明细",
        "⚠️ 避坑指南",
        "📸 拍照攻略",
        "🎒 物品清单",
        "🆘 应急预案",
        "📄 完整方案",
    ])

    # ── Tab 1: 每日行程 ──
    with tabs[0]:
        if plan.overview:
            st.markdown(f"### 📋 行程总览\n\n{plan.overview}")

        st.markdown("### 📅 每日详细行程")

        for day in plan.daily_plans:
            with st.expander(
                f"**Day {day.day}** — {day.theme or '探索日'}",
                expanded=(day.day == 1)
            ):
                col1, col2 = st.columns([3, 1])

                with col1:
                    # 上午
                    if day.morning:
                        st.markdown("☀️ **上午**")
                        for act in day.morning:
                            st.markdown(
                                f"- 🏛️ **{act.name}** "
                                f"({act.duration_minutes}分钟) "
                                f"{'⭐' * int(act.rating) if act.rating else ''}"
                            )
                            if act.description:
                                st.markdown(f"  *{act.description}*")
                            if act.tips:
                                for t in act.tips:
                                    st.markdown(f"  💡 {t}")

                    # 下午
                    if day.afternoon:
                        st.markdown("🌤️ **下午**")
                        for act in day.afternoon:
                            st.markdown(
                                f"- 🏛️ **{act.name}** "
                                f"({act.duration_minutes}分钟)"
                            )
                            if act.description:
                                st.markdown(f"  *{act.description}*")

                    # 晚上
                    if day.evening:
                        st.markdown("🌙 **晚上**")
                        for act in day.evening:
                            st.markdown(
                                f"- 🍽️ **{act.name}** "
                                f"({act.duration_minutes}分钟)"
                            )
                            if act.description:
                                st.markdown(f"  *{act.description}*")

                with col2:
                    # 餐食推荐
                    if day.meals:
                        st.markdown("**🍴 推荐餐厅**")
                        for m in day.meals:
                            st.markdown(
                                f"- **{m.get('meal_type', '')}**: "
                                f"{m.get('name', '')} (¥{m.get('avg_cost', 0)})\n"
                                f"  *{m.get('recommended', '')}*"
                            )

                    # 交通
                    if day.transport_notes:
                        st.markdown("**🚗 交通**")
                        st.info(day.transport_notes)

                    # 体力
                    energy = getattr(day, "energy_level", "") or getattr(day, "highlights", "")
                    if energy:
                        st.markdown(f"**⚡ 体力**: {energy}")

    # ── Tab 2: 预算明细 ──
    with tabs[1]:
        if plan.budget and plan.budget.items:
            col_a, col_b = st.columns(2)

            with col_a:
                st.metric("💰 总预算", f"¥{plan.budget.total:,.0f}")
            with col_b:
                st.metric("👤 人均", f"¥{plan.budget.per_person:,.0f}")

            if plan.budget.contingency:
                st.metric("🆘 应急备用", f"¥{plan.budget.contingency:,.0f}")

            # 表格
            df_data = []
            for item in plan.budget.items:
                df_data.append({
                    "类别": item.category,
                    "项目": item.item,
                    "金额(元)": f"¥{item.amount:,.0f}",
                    "备注": item.notes,
                })
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 省钱建议
            if plan.budget.savings_tips:
                st.markdown("#### 💡 省钱建议")
                for tip in plan.budget.savings_tips:
                    st.markdown(f"- {tip}")
        else:
            st.info("暂无预算明细")

    # ── Tab 3: 避坑指南 ──
    with tabs[2]:
        if plan.pitfalls:
            pit = plan.pitfalls
            sections = [
                ("🚫 常见骗局", pit.common_scams),
                ("🎯 游客陷阱", pit.tourist_traps),
                ("🚗 交通避坑", pit.transport_pitfalls),
                ("🍔 饮食安全", pit.food_safety),
                ("🙏 文化禁忌", pit.cultural_taboos),
            ]
            for title, items in sections:
                if items:
                    st.markdown(f"### {title}")
                    for item in items:
                        st.markdown(f"- ⚠️ {item}")
                    st.markdown("")
        else:
            st.info("暂无避坑指南")

    # ── Tab 4: 拍照攻略 ──
    with tabs[3]:
        if plan.photo_guide:
            pg = plan.photo_guide

            if pg.best_spots:
                st.markdown("### 📍 最佳拍照机位")
                spot_data = []
                for s in pg.best_spots:
                    spot_data.append({
                        "地点": s.get("name", ""),
                        "最佳时间": s.get("best_time", ""),
                        "拍照技巧": s.get("pose_tips", ""),
                    })
                st.dataframe(pd.DataFrame(spot_data), use_container_width=True, hide_index=True)

            if pg.outfit_suggestions:
                st.markdown("### 👗 穿搭建议")
                for s in pg.outfit_suggestions:
                    st.markdown(f"- {s}")

            if pg.camera_settings:
                st.markdown(f"### 📷 拍摄参数\n{pg.camera_settings}")
        else:
            st.info("暂无拍照指南")

    # ── Tab 5: 物品清单 ──
    with tabs[4]:
        if plan.packing:
            cats = [
                ("📋 证件资金", plan.packing.essentials),
                ("👔 衣物", plan.packing.clothing),
                ("🧴 洗漱用品", plan.packing.toiletries),
                ("📱 电子设备", plan.packing.electronics),
                ("💊 药品", plan.packing.medicine),
                ("🎯 目的地专属", plan.packing.travel_specific),
            ]
            cols = st.columns(3)
            for i, (title, items) in enumerate(cats):
                if items:
                    with cols[i % 3]:
                        st.markdown(f"**{title}**")
                        for item in items:
                            st.checkbox(item, key=f"pack_{i}_{item}")
        else:
            st.info("暂无物品清单")

    # ── Tab 6: 应急预案 ──
    with tabs[5]:
        if plan.emergency:
            em = plan.emergency

            if em.emergency_contacts:
                st.markdown("### 📞 紧急联系")
                for k, v in em.emergency_contacts.items():
                    st.markdown(f"- **{k}**: {v}")

            if em.nearest_hospital:
                st.markdown(f"### 🏥 最近医院\n{em.nearest_hospital}")

            if em.rainy_day_plan:
                st.markdown(f"### 🌧️ 雨天备选方案\n{em.rainy_day_plan}")

            if em.backup_routes:
                st.markdown("### 🔄 备用路线")
                for r in em.backup_routes:
                    st.markdown(f"- {r}")

            if em.lost_items_procedure:
                st.markdown(f"### 📦 物品遗失处理\n{em.lost_items_procedure}")
        else:
            st.info("暂无应急预案")

    # ── Tab 7: 完整方案 ──
    with tabs[6]:
        st.markdown("### 📄 完整方案 Markdown 预览")

        # 构建 Markdown
        from tools.export import _build_markdown
        md_content = _build_markdown(plan)

        st.markdown(md_content)

        # 导出按钮
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 下载 Markdown",
                data=md_content,
                file_name=f"旅行攻略_{plan.request.destination}.md",
                mime="text/markdown",
            )
        with col2:
            st.download_button(
                label="📋 复制到剪贴板",
                data=md_content,
                file_name=f"旅行攻略_{plan.request.destination}.txt",
                mime="text/plain",
            )

    # ── 底部: 反馈迭代 ──
    st.markdown("---")
    st.markdown("### 💬 不满意？告诉我想怎么改")

    feedback = st.text_input(
        "修改意见",
        placeholder="例如: 去掉第三天的博物馆，在第二天多加两个拍照点，把预算压到1500以内",
        key="feedback_input",
    )

    if st.button("🔄 提交修改", type="secondary") and feedback:
        with st.spinner("正在根据反馈修改行程..."):
            try:
                state = st.session_state.planner.give_feedback(
                    feedback, thread_id=st.session_state.thread_id
                )

                from models.schemas import TravelPlan, BudgetTable, PitfallTips, PackingList, EmergencyPlan, PhotoGuide

                updated_plan = TravelPlan(
                    request=state.get("user_request") or plan.request,
                    daily_plans=state.get("daily_plans", []),
                    budget=state.get("budget_table") or BudgetTable(),
                    research=state.get("research_result"),
                    pitfalls=state.get("pitfalls") or PitfallTips(),
                    packing=state.get("packing_list") or PackingList(),
                    emergency=state.get("emergency_plan") or EmergencyPlan(),
                    photo_guide=state.get("photo_guide") or PhotoGuide(),
                    overview=state.get("overview", ""),
                )
                st.session_state.plan_result = updated_plan
                st.success("✅ 行程已更新！")
                st.rerun()
            except Exception as e:
                st.error(f"修改失败: {str(e)}")

elif not st.session_state.generating:
    # 欢迎页
    st.markdown("---")
    st.markdown("""
    ### 🚀 如何使用？

    1. **左侧边栏** 填写你的出行偏好，或在 **上方输入框** 用自然语言描述需求
    2. 点击 **开始规划**，AI 多智能体系统自动为你生成完整旅行方案
    3. 查看 **每日行程、预算明细、避坑指南、拍照攻略、物品清单**
    4. 不满意？在底部 **输入修改意见**，AI 自动迭代优化

    ---

    ### 🤖 多智能体分工

    | Agent | 角色 | 产出 |
    |-------|------|------|
    | 🔍 调研 Agent | 旅行情报专家 | 景点/美食/住宿/天气/交通全面调研 |
    | 📅 规划 Agent | 金牌行程规划师 | 每日精细化行程，兼顾体力与时间 |
    | 💰 预算 Agent | 财务顾问 | 明细预算表 + 省钱建议 |
    | ⚠️ 避坑 Agent | 资深背包客 | 防骗指南 + 物品清单 + 应急预案 |
    | ✍️ 文案 Agent | 内容主编 | 行程总览 + 社交分享文案 |

    ---

    > 💡 **提示**: 首次使用请先在项目根目录创建 `.env` 文件并配置 API Key
    """)
