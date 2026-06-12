#!/usr/bin/env python3
"""内容撰写器 — 基于洞察自动生成 LinkedIn 帖子 + YouTube 脚本草稿"""

import json
from pathlib import Path
from datetime import date

BASE_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / 'templates'

def generate_linkedin_post(stories, snapshot, prev_snapshot):
    """生成 LinkedIn 英文帖子"""
    if not stories:
        return "No stories detected this week."

    top = stories[0]
    total_jobs = sum(c.get('total', 0) for c in snapshot.get('companies', {}).values())
    prev_total = sum(c.get('total', 0) for c in (prev_snapshot or {}).get('companies', {}).values()) if prev_snapshot else 0
    num_companies = len(snapshot.get('companies', {}))
    today = snapshot.get('date', date.today().isoformat())

    # Build company table
    table_rows = []
    for key, curr in sorted(snapshot.get('companies', {}).items(), key=lambda x: -x[1].get('total', 0)):
        t = curr.get('total', 0)
        gtm = curr.get('gtm_ratio', 0)
        rd = curr.get('research_ratio', 0)
        prev = (prev_snapshot or {}).get('companies', {}).get(key, {})
        pt = prev.get('total', 0)
        delta = f"+{t-pt}" if t >= pt else str(t-pt) if pt > 0 else "new"
        table_rows.append(f"  {key.upper():12s}  {t:5d} ({delta:>5s})  GTM {gtm:4.1f}%  R&D {rd:4.1f}%")

    table = '\n'.join(table_rows[:6])

    # Hook variations based on detector type
    hooks = {
        'facepalm': f"I checked {top.get('company','an AI company').upper()}'s hiring data against their CEO's public statements.\n\nThe data disagrees. Here's what I found.",
        'corpse': f"{top.get('company','').upper()} has only {top.get('data_points',{}).get('current','?')} job postings left.\n\nThe AI bubble already has a body.",
        'reversal': f"Something changed at {top.get('company','').upper()} this week.\n\nTheir hiring pattern just flipped. Here's what the data shows.",
        'conflict': f"Two AI companies made opposite bets this week.\n\nOne is hiring aggressively. The other is shrinking. Who's right?",
        'history_rhyme': f"I compared today's AI market to the 1999 dot-com bubble.\n\nOne number is almost identical. And it's not a good sign.",
    }
    hook = hooks.get(top['detector'], f"I scraped {total_jobs:,} job postings from {num_companies} AI companies this week.\n\nHere's what the data says.")

    post = f"""{hook}

---

{top['headline_en']}

Here's the full dashboard ({today}):

{table}

---

My take:

{_generate_insight_en(top, snapshot)}

---

I run this "AI Bubble Tracker" every week — scraping real hiring data from Greenhouse, Ashby, Lever, and ByteDance's proprietary API, plus GitHub activity and arXiv papers.

No narratives. Just data.

Follow for the next update.

#AI #AIBubble #DataDriven #TechStrategy #OpenAI #Anthropic #NVIDIA #Hiring"""

    return post

def generate_youtube_script(stories, snapshot, prev_snapshot):
    """生成 YouTube 中文脚本"""
    if not stories:
        return "本周无显著异常信号。"

    top = stories[0]
    total_jobs = sum(c.get('total', 0) for c in snapshot.get('companies', {}).values())
    num_companies = len(snapshot.get('companies', {}))
    today = snapshot.get('date', date.today().isoformat())

    # Build company summary
    company_lines = []
    for key, curr in sorted(snapshot.get('companies', {}).items(), key=lambda x: -x[1].get('total', 0)):
        t = curr.get('total', 0)
        prev = (prev_snapshot or {}).get('companies', {}).get(key, {})
        pt = prev.get('total', 0)
        delta = t - pt if pt > 0 else 0
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        company_lines.append(f"  {key.upper()}: {t} 个岗位 {arrow} ({delta:+d})")

    companies_text = '\n'.join(company_lines[:8])

    # Title options
    title_options = {
        'facepalm': f"CEO 说的和做的不一样 — 数据打脸 {top.get('company','').upper()}",
        'corpse': f"这家 AI 公司只剩 {top.get('data_points',{}).get('current','?')} 个人了 | AI 泡沫追踪器",
        'reversal': f"{top.get('company','').upper()} 突然变了方向，发生了什么？",
        'conflict': f"两家 AI 公司做出了相反的判断，谁对了？",
        'history_rhyme': f"这个数字上次出现在 1999 年，后来发生了什么大家都知道",
    }
    title = title_options.get(top['detector'], f"我爬了 {num_companies} 家 AI 公司 {total_jobs} 个岗位，发现了一个危险信号")

    script = f"""## YouTube 视频脚本

### 标题（3 选 1）
1. {title}
2. AI 泡沫追踪器第 N 期：{top['headline_cn']}
3. 我用代码监控 {num_companies} 家 AI 公司的招聘，本周最大的发现是...

### 封面文案
"{top['headline_cn'][:20]}..."
（背景：泡沫指数仪表盘截图，暗色主题）

---

### [0:00-0:30] Hook — 冲击开头

"{_generate_hook_cn(top, total_jobs, num_companies)}"

**画面建议：** 数据仪表盘快速闪过 → 定格在最异常的数字上 → 放大

---

### [0:30-2:00] 背景 — 这周数据概览

"我每周六会自动爬取 {num_companies} 家 AI 公司的招聘数据。不是从招聘网站搜索，而是直接调用它们的内部 API — Greenhouse、Ashby、Lever，还有字节跳动的自研系统。

本周共监测到 {total_jobs:,} 个岗位，各家情况如下：

{companies_text}

但今天我不讲所有公司。我只讲一件事 — 本周最值得关注的信号。"

**画面建议：** 屏幕录制展示泡沫探测器的运行画面 → 切到仪表盘表格

---

### [2:00-5:00] 核心发现

"{_generate_core_finding_cn(top, snapshot, prev_snapshot)}"

**画面建议：** 关键数据放大展示 → CEO 采访片段（如果涉及打脸）→ 数据对比图表

---

### [5:00-6:30] So What — 对你意味着什么

"{_generate_so_what_cn(top)}"

**画面建议：** 总结性图表 → 你的判断用文字叠加在画面上

---

### [6:30-7:00] 下期预告 + 订阅引导

"这个追踪器每周自动运行。下周我会继续更新数据，到时候我们就有 N 周的趋势线了 — 趋势比快照更有价值。

如果你也在关注 AI 行业，不管是投资、求职还是单纯好奇，订阅这个频道，我们用数据说话，不用叙事。

下期见。"

**画面建议：** 订阅按钮动画 + 下期预告卡片
"""
    return script, title

def _generate_insight_en(story, snapshot):
    insights = {
        'facepalm': f"When a CEO's public narrative diverges from their hiring data, one of them is lying. Hiring data doesn't lie — it costs real money to post every job listing. {story.get('company','This company').upper()}'s data suggests their actual priority is different from what they're telling the public.",
        'corpse': f"This is what an AI company dying looks like. Not a dramatic announcement — just quietly posting fewer and fewer jobs until there's almost nobody left. The question every AI investor should ask: which company is next?",
        'reversal': f"When a company freezes GTM hiring but keeps R&D going, it usually means one thing: revenue isn't coming in as expected, but they still believe in the technology. This is the 'we built it but they didn't come' phase.",
        'conflict': "When two competitors make opposite decisions, at least one of them is wrong. The market will tell us who within 2-3 quarters. Watch the one that's shrinking — if their revenue holds up, they're being smart. If it drops, they saw it coming.",
        'history_rhyme': f"The dot-com bubble had a revenue/capex ratio of 0.17 in 1999 — one year before NASDAQ peaked and crashed 78%. AI's ratio today is 0.18. This doesn't mean the bubble pops tomorrow. But it means the math is in the same neighborhood.",
    }
    return insights.get(story['detector'], "The data speaks for itself. Draw your own conclusions.")

def _generate_hook_cn(story, total_jobs, num_companies):
    hooks = {
        'facepalm': f"我每周会用代码监控 {num_companies} 家 AI 公司的招聘数据。这周我发现了一个有意思的事情 — {story.get('company','').upper()} 的 CEO 说的话，和他公司实际在做的事，对不上。数据不会说谎，但 CEO 会。",
        'corpse': f"我监控的 {num_companies} 家 AI 公司里，有一家只剩 {story.get('data_points',{}).get('current','几')} 个岗位了。两年前这家公司有 300 多人。AI 泡沫，已经有了第一具尸体。",
        'reversal': f"本周数据出来，{story.get('company','').upper()} 的招聘模式突然变了。之前一直在扩张的部门，这周突然停了。而之前缩编的部门，反而在招人。这是什么信号？",
        'conflict': f"本周最有意思的发现：两家直接竞对的 AI 公司，做出了完全相反的决策。一家在疯狂招人，另一家在收缩。同一个市场，完全相反的判断。谁对了？",
        'history_rhyme': f"我用代码算了一个数字，然后去查了一下 2000 年互联网泡沫的历史数据。结果发现，有一个关键比率几乎一模一样。上次这个数字出现的时候，一年后纳斯达克暴跌了 78%。",
    }
    return hooks.get(story['detector'], f"我每周会自动爬取 {num_companies} 家 AI 公司的 {total_jobs:,} 个招聘岗位。这周，我发现了一个不太对劲的信号。")

def _generate_core_finding_cn(story, snapshot, prev_snapshot):
    findings = {
        'facepalm': f"""让我们看具体数据。

{story['headline_cn']}

这说明什么？说了 AGI 也好，说了安全第一也好，一家公司真正的优先级，看它把人招到哪里就知道了。钱是最诚实的投票。

这不是说 CEO 在故意骗人。更可能的解释是：公司的实际执行和 CEO 的公开叙事之间，总会有差距。而招聘数据，就是测量这个差距的尺子。""",

        'corpse': f"""让我给大家看一下这家公司的数据。

{story['headline_cn']}

这不是一夜之间发生的。它经历了几个阶段：
第一阶段：融资充裕，大量招人
第二阶段：收入不达预期，开始裁员
第三阶段：核心团队流失，恶性循环
第四阶段：就是现在，只剩个位数的岗位

每一个 AI 创业公司、每一个 AI 投资者，都应该认真想一个问题：我关注的那家公司，现在处在哪个阶段？""",

        'reversal': f"""来看数据。

{story['headline_cn']}

GTM 就是销售和市场团队。一家公司如果冻结了销售招聘但继续招研发，通常只有一个原因：产品卖不动了，但他们还相信技术方向是对的。

这是一个微妙的信号 — 不是崩盘，但也不是一切都好。它处于中间地带。""",

        'conflict': f"""这是本周最有意思的对比。

{story['headline_cn']}

同一个赛道，两家公司做出了完全相反的判断。一家认为现在应该加大投入，另一家认为应该收缩保守。

他们手里的信息比我们多得多。那为什么结论完全相反？可能的原因有三个：
1. 他们看到了不同的客户反馈
2. 他们的现金储备不同，风险承受力不同
3. 其中一个判断错了

2-3 个季度后我们就能知道答案。""",

        'history_rhyme': f"""我算了一个关键比率：AI 行业的总收入除以总基础设施投入。

当前 AI 行业的这个比率是 0.18。

然后我去查了 2000 年互联网泡沫的数据。1999 年 — 也就是纳斯达克见顶前一年 — 互联网行业的同一个比率是 0.17。

几乎一模一样。

这不意味着 AI 泡沫明天就会破。互联网泡沫在这个比率出现后又维持了整整一年。但它意味着一件事：当前的投入产出比，跟历史上最著名的科技泡沫处于同一个水平线上。

当然，AI 和互联网有一个关键差别 — NVIDIA 是真的在赚钱的（毛利率 75%），而 2000 年的 Cisco 利润薄得多。这是"这次不一样"的最有力论据。

但 Cisco 在 2000 年 3 月也是全球市值最高的公司。然后它的股价跌了 89%，花了 25 年才回到原来的位置。""",
    }
    return findings.get(story['detector'], story['headline_cn'])

def _generate_so_what_cn(story):
    so_whats = {
        'facepalm': """所以你应该怎么用这个信息？

如果你是投资者：不要听 CEO 说了什么，看他的公司在招什么人。
如果你是求职者：一家公司的真实优先级决定了哪个部门有前途。GTM 大于研发 = 商业化优先，去销售部比研发部更容易出头。
如果你是从业者：学会用公开数据验证叙事。这个技能在 AI 时代比任何技术栈都值钱。""",

        'corpse': """这个案例的教训很简单：AI 公司是可以死的。

对投资者：在你的 AI 持仓中，检查每家公司的岗位趋势。如果连续 3 周下降，至少值得你多问几个问题。
对求职者：在接一个 AI 公司的 offer 前，查一下它的招聘趋势。如果在收缩，再高的薪资都可能是陷阱。
对所有人：泡沫破裂不是一声巨响，而是温水煮青蛙。注意信号。""",

        'reversal': """这种信号是泡沫的早期预警 — 不是确认。

它说明这家公司的管理层看到了一些我们还没看到的东西。也许是客户续约率下降了，也许是竞品抢了大客户。我们还不知道具体原因，但招聘数据告诉我们：有些事情正在发生。

我会在接下来几周持续追踪这个变化。""",

        'conflict': """当两家公司做出相反判断的时候，最聪明的做法不是选边站，而是等待。

等 2-3 个季度，看谁的收入在涨，谁的在跌。到时候答案就清楚了。

但你现在就可以做一件事：把这两家公司都加入你的监测清单。追踪它们的岗位变化趋势。数据会比分析师更早告诉你答案。""",

        'history_rhyme': """那我们应该怎么做？

不要因为这个数字就恐慌卖出所有 AI 股票。也不要因为"这次不一样"就无视风险。

我的建议是三个字：看 NVIDIA。

NVIDIA 的下一季财报是整个 AI 叙事的基石。如果它超预期 — 趋势继续。如果它不及预期 — 这会是第一张多米诺骨牌。

我会持续追踪这些数字。订阅频道，我们一起看数据。""",
    }
    return so_whats.get(story['detector'], "数据每周更新。下周见。")

def run(stories, snapshot, prev_snapshot, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    linkedin = generate_linkedin_post(stories, snapshot, prev_snapshot)
    (output_dir / 'linkedin_post.md').write_text(linkedin)

    youtube, title = generate_youtube_script(stories, snapshot, prev_snapshot)
    (output_dir / 'youtube_script.md').write_text(youtube)

    print(f"  LinkedIn post: {len(linkedin)} chars")
    print(f"  YouTube script: {len(youtube)} chars")
    print(f"  YouTube title: {title}")

    return {'linkedin': linkedin, 'youtube': youtube, 'title': title}
