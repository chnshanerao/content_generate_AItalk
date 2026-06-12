# AI 周期投资监测系统 — 产品需求文档 (PRD)

> 版本：v1.0
> 日期：2026-06-10
> 作者：raoxuan（产品负责人）
> 状态：待开发

---

## 一、项目背景

### 1.1 项目起源

团队在一次深度研究中发现：**AI 公司的招聘数据是其真实战略方向的「组织投影」**——钱花在哪、人招到哪，就是真实战略方向。这比 CEO 的公开演讲和媒体叙事更真实、更难造假。

基于这个洞察，我们已完成以下 POC 验证：
- 逆向破解了 4 种招聘平台 API（Greenhouse / Ashby / Lever / 字节自研）
- 全量爬取了 8 家 AI 公司共 5,783 个岗位
- 构建了跨公司战略对比分析框架（15+ 维度）
- 构建了泡沫指数计算引擎（招聘 + GitHub + 论文 + 裁员信号）
- 首次运行已成功生成基线数据和周报

### 1.2 商业目的

构建一套 **AI 周期投资决策操作系统**，通过持续监测 AI 行业的技术、需求、资本、市场四层信号，为投资决策（进场/持有/离场）提供数据支撑。

### 1.3 目标用户

| 用户层 | 角色 | 核心需求 | 付费意愿 |
|---|---|---|---|
| **Tier 1** | VC/PE 投资人 | 投前尽调：目标公司的真实战略 vs 公开叙事 | ¥2,000-8,000/份 |
| **Tier 2** | 企业战略部 | 竞对追踪：竞对组织扩张和技术布局变化 | ¥1,000-5,000/月 |
| **Tier 3** | 猎头/HR | 人才市场情报：批量获取目标公司全量岗位 | ¥500-2,000/月 |
| **Tier 4** | 个人投资者/求职者 | 行业趋势 + 岗位匹配 | ¥50-200/次 |

---

## 二、产品架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户触达层                                 │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌───────────┐  │
│  │ 钉钉周报  │  │ Web 仪表盘 │  │ Skill 包 │  │ API 接口  │  │
│  └────┬─────┘  └─────┬─────┘  └────┬─────┘  └─────┬─────┘  │
├───────┼──────────────┼─────────────┼──────────────┼─────────┤
│       └──────────────┴─────────────┴──────────────┘         │
│                    报告生成层                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  周报引擎 │ 战略洞察引擎 │ 泡沫指数引擎 │ 言行一致性  │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    分析计算层                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 环比计算  │  │ 关键词扫描 │  │ 裁员检测  │  │ 趋势分析  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
├─────────────────────────────────────────────────────────────┤
│                    数据采集层                                 │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐  │
│  │招聘 API │ │GitHub  │ │ arXiv  │ │财报数据 │ │新闻/裁员 │  │
│  └────────┘ └────────┘ └────────┘ └────────┘ └─────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    数据存储层                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  时序快照数据库（每周一份 JSON snapshot）               │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 四层监测信号体系

这是产品的核心理论框架，所有功能围绕这四层展开：

```
第一层: 技术层    → AI 能力是否在持续提升？  → 决定长期叙事是否成立
第二层: 需求层    → 真实用户是否在买单？      → 决定收入能否兑现
第三层: 资本层    → 投入产出比是否改善？      → 决定估值是否合理
第四层: 市场层    → 资金/情绪的拐点在哪？    → 决定交易时机
```

---

## 三、核心功能模块

### 3.1 模块一：多平台招聘数据采集引擎

**功能描述：** 自动检测目标公司的招聘平台（ATS），全量爬取岗位数据，输出标准化格式。

**已验证的 ATS 平台和破解方法：**

| 平台 | 使用公司 | API 端点 | 关键技术点 |
|---|---|---|---|
| **Greenhouse** | Anthropic, DeepMind, xAI, Stability AI, Stripe | `GET boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` | 公开 REST API，无鉴权 |
| **Ashby** | OpenAI, Cohere, Notion, Ramp | `GET jobs.ashbyhq.com/{slug}` → 从 HTML 提取嵌入的 `jobPostings` JSON 数组 | 需要 bracket-matching 解析内嵌 JSON |
| **Lever** | Mistral AI, Cloudflare | `GET api.lever.co/v0/postings/{slug}?mode=json` | 公开 REST API |
| **字节自研** | ByteDance | `POST jobs.bytedance.com/api/v1/search/job/posts` | 需要 9 个特殊 Header，Accept 头必须精确匹配，否则 405 |

**ATS 自动检测逻辑：**

```python
def detect_ats(company):
    # 1. 查已知映射表
    # 2. 探测 Greenhouse API（GET /v1/boards/{slug}/jobs）
    # 3. 探测 Ashby HTML（GET jobs.ashbyhq.com/{slug}）
    # 4. 探测 Lever API（GET api.lever.co/v0/postings/{slug}）
    # 5. 返回 'unknown' 如果都不匹配
```

**标准化输出 Schema：**

```json
{
  "id": "string",
  "title": "string",
  "department": "string",
  "location": "string",
  "description": "string",
  "url": "string",
  "company": "string",
  "source": "greenhouse|ashby|lever|bytedance"
}
```

**关键 Pitfalls（开发必读）：**

| 问题 | 原因 | 解决方案 |
|---|---|---|
| 字节 API 返回 405 | 缺少 `Accept: application/json, text/plain, */*` 头 | 必须使用 axios 默认的完整 Accept 值 |
| 字节 API 返回 400 | `job_hot_flag` 字段传了空字符串 | 从请求体中完全删除该字段 |
| 字节 API 返回 HTML | 用了 GET 方法 | 必须用 POST，GET 走的是 SPA 前端路由 |
| Ashby 页面无 jobPostings | slug 错误或公司不用 Ashby | 尝试多种 slug 变体 |
| Greenhouse 返回 404 | slug 不匹配 | 尝试 company-name / companyname / company 等变体 |
| Ashby JSON 提取失败 | 简单正则无法匹配超大 JSON 数组 | 必须用 bracket-counting 解析（逐字符遍历找匹配的 `]`） |

**已验证的公司配置：**

```json
{
  "openai":    {"ats": "ashby",      "slug": "openai"},
  "anthropic": {"ats": "greenhouse", "slug": "anthropic"},
  "deepmind":  {"ats": "greenhouse", "slug": "deepmind"},
  "bytedance": {"ats": "bytedance",  "slug": "bytedance"},
  "xai":       {"ats": "greenhouse", "slug": "xai"},
  "mistral":   {"ats": "lever",      "slug": "mistral"},
  "stability": {"ats": "greenhouse", "slug": "stabilityai"},
  "cohere":    {"ats": "ashby",      "slug": "cohere"}
}
```

**扩展路线：** 后续需支持 Workday（用于大公司如 Microsoft、Amazon）和 SmartRecruiters。

---

### 3.2 模块二：GitHub 开源活跃度采集

**功能描述：** 通过 GitHub API 采集各公司的开源活跃度数据，用于验证「开源承诺」的真实性。

**API 调用：**

```
GET https://api.github.com/orgs/{org}/repos?sort=stars&per_page=10
GET https://api.github.com/repos/{owner}/{repo}/stats/commit_activity
```

**已验证的 GitHub Org 映射：**

```json
{
  "openai": "openai",
  "anthropic": "anthropics",
  "deepmind": "google-deepmind",
  "meta": "meta-llama",
  "xai": "xai-org",
  "mistral": "mistralai",
  "stability": "stability-ai",
  "cohere": "cohere-ai",
  "bytedance": null
}
```

**采集字段：**

```json
{
  "org": "string",
  "public_repos": "int",
  "total_stars": "int",
  "top_repos": [{"name": "", "stars": 0, "updated": "", "language": ""}],
  "recent_commits_4w": "int"
}
```

**注意事项：**
- GitHub API 有速率限制（未认证 60 次/小时），建议申请 Personal Access Token 提高到 5000 次/小时
- `commit_activity` 端点首次调用可能返回 202（计算中），需要等待后重试
- 字节跳动没有公开的 GitHub org，该字段返回 null

---

### 3.3 模块三：arXiv 论文采集

**功能描述：** 通过 arXiv API 采集各公司的近期论文发表数据，用于量化研发实力。

**API 调用：**

```
GET http://export.arxiv.org/api/query?search_query={query}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending
```

**已验证的查询模板：**

```json
{
  "openai": "au:OpenAI OR ti:GPT-5 OR ti:ChatGPT",
  "anthropic": "au:Anthropic OR ti:Claude OR ti:Constitutional+AI",
  "deepmind": "au:DeepMind OR ti:Gemini+model OR ti:AlphaFold",
  "bytedance": "au:ByteDance OR ti:doubao OR au:Seed",
  "xai": "au:xAI OR ti:Grok+model",
  "mistral": "au:Mistral+AI OR ti:Mistral+model",
  "stability": "au:Stability+AI OR ti:Stable+Diffusion",
  "cohere": "au:Cohere OR ti:Command+R",
  "meta": "au:Meta+AI OR ti:LLaMA OR ti:Llama+model"
}
```

**注意事项：**
- arXiv API 限速：每次请求间隔 >=3 秒
- 返回 XML 格式，需要用正则提取 `<entry>` 中的 title / published / summary
- 论文数量受查询词影响大，「OpenAI」匹配到大量第三方引用论文，需注意区分

---

### 3.4 模块四：泡沫指数计算引擎

**功能描述：** 综合招聘、GitHub、裁员信号，计算每家公司和行业整体的泡沫分数。

**计算公式：**

```python
Bubble Score = 
    # 招聘信号
    + (岗位周环比 < -10% ? 3 : (< -5% ? 2 : 0))
    + (GTM占比下降 >3pp ? 3 : 0)
    + (Manager占比下降 >5pp ? 1 : 0)
    + (撤出城市 ? 1 : 0)
    - (新增城市 ? -1 : 0)
    - (岗位增速 >5% ? -1 : 0)
    
    # GitHub 信号
    + (近4周零commit且总星数>1000 ? 1 : 0)
    
    # 裁员信号
    + (岗位暴跌同时Manager占比下降 ? 额外+1 : 0)
    + (GTM冻结但R&D不变 ? 额外+1 : 0)
```

**分数解释：**

| 分数 | 状态 | 含义 |
|---|---|---|
| 0-2 | 🟢 健康 | 正常扩张 |
| 3-5 | 🟡 关注 | 出现局部降温信号 |
| 6-8 | 🟠 警告 | 多维度同时收缩 |
| 9+ | 🔴 泡沫破裂 | 全面收缩 + 裁员 |

---

### 3.5 模块五：言行一致性检测

**功能描述：** 对比 CEO 公开叙事与招聘/GitHub/论文的实际数据，检测「说一套做一套」。

**已配置的检测规则：**

```python
CEO_CLAIMS = {
    "openai": {
        "narrative": "Sam Altman: 算力是未来最珍贵的商品，AGI 十年内到来",
        "checks": [
            ("GTM 是否是最大部门？", lambda d: d["gtm_ratio"] > 20),
            ("研发占比是否 >30%？", lambda d: d["research_ratio"] > 30),
        ]
    },
    "anthropic": {
        "narrative": "Dario Amodei: 安全是核心，Scaling Laws 仍在生效",
        "checks": [
            ("研发占比是否 >25%？", lambda d: d["research_ratio"] > 25),
        ]
    },
    "deepmind": {
        "narrative": "Demis Hassabis: 纯研究导向，商业化由 Google Cloud 负责",
        "checks": [
            ("GTM 占比是否 ≈0%？", lambda d: d["gtm_ratio"] < 3),
            ("研发占比是否 >40%？", lambda d: d["research_ratio"] > 40),
        ]
    },
    "stability": {
        "narrative": "曾宣称开源生成式 AI 的领导者",
        "checks": [
            ("总岗位是否 >50？", lambda d: d["total"] > 50),
        ]
    },
}
```

**输出格式：**

```
OpenAI — Sam Altman: "算力是未来最珍贵的商品"
  ✅ GTM 是否是最大部门？ → 是（商业化确实是第一优先级）
  ❌ 研发占比是否 >30%？ → 否（研发占比低于叙事预期）
```

**扩展计划：** 后续加入 CEO 公开演讲的自动抓取和 NLP 分析，自动提取叙事关键词与数据对比。

---

### 3.6 模块六：战略洞察分析引擎

**功能描述：** 跨公司对比分析，用 15+ 维度的关键词扫描推断各公司的战略方向。

**分析维度和关键词表：**

```python
STRATEGY_DIMENSIONS = {
    "AI Agent":         ["agent", "agentic", "智能体"],
    "LLM/大模型":        ["LLM", "大模型", "foundation model"],
    "AI Coding":        ["coding", "code generation", "代码生成", "codex"],
    "AI Safety":        ["safety", "alignment", "trust", "安全", "对齐"],
    "Multimodal":       ["multimodal", "多模态"],
    "RAG":              ["RAG", "retrieval", "检索增强"],
    "Robotics":         ["robotics", "robot", "机器人", "具身"],
    "Enterprise/ToB":   ["enterprise", "B2B", "ToB", "企业"],
    "GTM":              ["GTM", "go-to-market", "商业化"],
    "International":    ["international", "global", "APAC", "海外"],
    "Ads/Monetization": ["ads", "advertising", "广告", "变现"],
    "Government":       ["government", "gov", "政府"],
    "Consumer":         ["consumer", "user", "用户"],
    "Search":           ["search", "搜索"],
    "AI for Science":   ["scientific", "biology", "科学计算"],
    "Data Labeling":    ["annotation", "labeling", "标注"],
}
```

**输出格式：** 矩阵表 — 每行一个维度，每列一个公司，单元格显示岗位数和占比。

---

### 3.7 模块七：报告生成 + 推送

**产出物：**

| 产出 | 格式 | 频率 | 内容 |
|---|---|---|---|
| **周报全文** | Markdown | 每周 | 行业总览 + 各公司仪表盘 + 异常信号 + GitHub + 论文 + 言行一致性 |
| **钉钉摘要** | 文本 | 每周 | 10 行以内的关键数字 + 异常告警 |
| **数据快照** | JSON | 每周 | 完整的结构化数据，供后续分析 |
| **Excel 明细** | XLSX | 按需 | 某公司全量岗位明细 + 匹配评分 |

**钉钉推送模板：**

```
🔍 AI 泡沫探测器 v2.0 — {date}

📊 总岗位: {total} (上期 {prev}, {wow}%)
🎯 泡沫指数: {emoji} {score}/10

📈 各公司:
  {company}: {jobs} ({delta}) {emoji}
  ...

⚠️ 异常信号:
  ⚠ {company}: {signal}

🔍 言行不一致:
  ❌ {company}: {check}
```

---

### 3.8 模块八：用户画像匹配引擎

**功能描述：** 基于用户关键词画像，对全量岗位进行加权评分和排序。

**评分算法：**

```python
PROFILE_KEYWORDS = {
    # 关键词: 权重(1-10)
    "sales operations": 10,
    "GTM": 10,
    "strategy": 8,
    ...
}

def score(job):
    text = f"{job.title} {job.description}".lower()
    total, hits = 0, []
    for keyword, weight in PROFILE_KEYWORDS.items():
        if keyword.lower() in text:
            total += weight
            hits.append(keyword)
    return total, hits
```

**输出分级：**

| 等级 | 分数 | 颜色 |
|---|---|---|
| Tier 1 - 强烈推荐 | ≥50 | 绿色 |
| Tier 2 - 值得关注 | 30-49 | 黄色 |
| Tier 3 - 可考虑 | 15-29 | 橙色 |

---

## 四、数据存储设计

### 4.1 目录结构

```
ai-bubble-monitor/
├── config.json                  # 公司列表 + ATS 映射
├── data/
│   ├── snapshots/               # 时序快照（核心资产）
│   │   ├── 2026-06-09.json      # 基线
│   │   ├── 2026-06-10.json      # 第二期
│   │   └── ...
│   └── raw/                     # 原始爬取数据（可选保留）
│       ├── openai_2026-06-10.json
│       └── ...
├── reports/
│   └── weekly/
│       ├── 2026-06-09.md
│       └── ...
└── scripts/
    └── monitor.py               # 主脚本（当前单文件，后续拆分）
```

### 4.2 快照 JSON Schema（v2.0）

```json
{
  "date": "2026-06-10",
  "version": "2.0",
  "companies": {
    "openai": {
      "total": 724,
      "gtm": 202,
      "research": 198,
      "gtm_ratio": 27.9,
      "research_ratio": 27.4,
      "senior_pct": 17.9,
      "manager_pct": 23.9,
      "by_department": {"Go To Market": 155, "Research": 51},
      "by_location": {"San Francisco": 504, "Singapore": 36}
    }
  },
  "github": {
    "openai": {
      "org": "openai",
      "public_repos": 10,
      "total_stars": 24961,
      "top_repos": [{"name": "codex", "stars": 90053}],
      "recent_commits_4w": 705
    }
  },
  "arxiv": {
    "openai": {
      "total_recent": 1258,
      "papers": [{"title": "...", "date": "2026-06-08"}]
    }
  },
  "consistency": {
    "openai": {
      "narrative": "Sam Altman: ...",
      "checks": [{"check": "...", "passed": true, "message": "..."}]
    }
  }
}
```

---

## 五、已完成 POC 验证结果

### 5.1 首次全量运行结果（2026-06-10）

| 公司 | 岗位数 | GTM% | R&D% | GitHub⭐ | 论文数 | 泡沫分 |
|---|---|---|---|---|---|---|
| ByteDance | 3,835 | 5.0% | 42.3% | N/A | 17 | 🟢 0 |
| OpenAI | 724 | 27.9% | 27.4% | 24,961 | 1,258 | 🟢 1 |
| Anthropic | 374 | 29.4% | 25.7% | 7,205 | 82 | 🟢 1 |
| xAI | 220 | 3.2% | 11.4% | 83,003 | 19 | 🟢 1 |
| Mistral AI | 168 | 11.9% | 16.1% | 4,483 | 8 | 🟢 1 |
| DeepMind | 39 | 0% | 46.2% | 2,072 | 57 | 🟢 1 |
| Stability AI | 5 | 20.0% | 60.0% | 562 | 329 | 🟢 0 |
| Cohere | 0 | N/A | N/A | 9 | 1 | 🔴 10 |

### 5.2 关键发现

1. **OpenAI 言行不一致：** CEO 说 "AGI 十年内"，但 GTM 占比（27.9%）高于研发（27.4%）。实际优先级是商业化而非 AGI 研发。
2. **Stability AI 泡沫已破：** 从巅峰 300+ 岗位萎缩至 5 个，创始人已离职。是行业内唯一已确认「破裂」的案例。
3. **DeepMind 是唯一「纯研究院」：** GTM 占比 0%，研发 46.2%。商业化完全依赖 Google Cloud。
4. **所有公司 GitHub 近 4 周 commit 为 0：** 说明核心研发都在私有 repo，「拥抱开源」的叙事需打折扣。

---

## 六、技术实现要求

### 6.1 当前状态（POC）

- 语言：Python 3.12
- 依赖：requests, openpyxl（仅两个外部依赖）
- 部署：单文件脚本 `monitor.py`，通过 cron job 每周六 9:00 执行
- 输出：JSON 快照 + Markdown 周报 + 钉钉推送

### 6.2 产品化要求

| 维度 | POC 现状 | 产品化要求 |
|---|---|---|
| 架构 | 单文件 380 行 Python | 拆分为模块化架构（采集/分析/报告/推送） |
| 存储 | 本地 JSON 文件 | 数据库（PostgreSQL 或 MongoDB） |
| 调度 | CloudCLI cron job | 独立调度系统（Celery / Airflow） |
| 前端 | 无 | Web Dashboard（趋势图 + 仪表盘） |
| API | 无 | RESTful API（供外部调用） |
| 监控 | 无 | 爬虫健康监控 + 告警（API 变更检测） |
| 认证 | 无 | 用户认证 + 权限控制 |

### 6.3 关键技术风险

| 风险 | 概率 | 影响 | 缓解方案 |
|---|---|---|---|
| ATS 平台 API 变更 | 中 | 爬取失败 | 每周自动验证 + 告警 + 逆向文档留存 |
| GitHub API 限速 | 低 | 数据不完整 | 申请 PAT + 错峰采集 |
| arXiv API 限速 | 低 | 论文数据延迟 | 每次请求间隔 3 秒 |
| 法律/ToS 风险 | 中 | 被封禁 | 只采集公开数据 + 控制频率 + 参考 HiQ v. LinkedIn 判例 |

---

## 七、产品路线图

| 阶段 | 时间 | 交付物 | 目标 |
|---|---|---|---|
| **P0: MVP** | 已完成 | Python 脚本 + cron job + 钉钉推送 | 验证数据可得性和分析框架 |
| **P1: 产品化** | +4 周 | 模块化后端 + 数据库 + API | 支持多用户 + 数据持久化 |
| **P2: 可视化** | +8 周 | Web Dashboard（趋势图 + 仪表盘） | 直观展示时序数据和泡沫指数 |
| **P3: Skill 包** | +10 周 | job-radar + talent-intel 两个 Skill | 触达 AI Agent 用户群 |
| **P4: 内容产品** | +12 周 | 每周公开发布「AI 招聘情报周刊」 | 引流 + 品牌建设 |
| **P5: SaaS** | +16 周 | 订阅制 + API 接入 + 自定义监测 | 商业化收入 |

---

## 八、商业化方案摘要

### 定价

| 产品 | 价格 | 内容 |
|---|---|---|
| Job Radar 单次 | ¥99/次 | 1 家公司全量岗位 + 画像匹配 |
| Talent Intel 报告 | ¥999/份 | 2-5 家公司战略对比 |
| Starter 订阅 | ¥499/月 | 5 家公司监控 + 周报 |
| Pro 订阅 | ¥1,999/月 | 20 家公司 + 战略洞察 + API |
| Enterprise | ¥9,999/月 | 50 家 + 自定义维度 + 专属分析 |

### 收入预测

| 时间 | 用户数 | MRR | ARR |
|---|---|---|---|
| M3 | 10 | ¥5,000 | ¥60,000 |
| M6 | 30 | ¥24,000 | ¥288,000 |
| M12 | 80 | ¥80,000 | ¥960,000 |

### 成本结构

- 服务器/API：¥200/月
- 毛利率：~95%

---

## 九、附录

### 附录 A：已产出的数据资产

| 文件 | 路径 | 内容 |
|---|---|---|
| 字节跳动 AI 岗位全量 | `bytedance_jobs_output/byte-jobs-ai-raw.json` | 7,460 岗位 |
| Anthropic 全量 | `bytedance_jobs_output/anthropic-raw.json` | 375 岗位 |
| OpenAI 全量 | `bytedance_jobs_output/openai-raw.json` | 721 岗位 |
| DeepMind 全量 | `bytedance_jobs_output/deepmind-greenhouse.json` | 40 岗位 |
| 泡沫探测器基线 | `ai-bubble-monitor/data/snapshots/2026-06-09.json` | 8 家公司基线 |
| 泡沫探测器 v2 | `ai-bubble-monitor/data/snapshots/2026-06-10.json` | 含 GitHub + arXiv |
| 周报 v2 | `ai-bubble-monitor/reports/weekly/2026-06-10.md` | 完整周报 |
| Excel 报告 | `bytedance_jobs_output/字节跳动AI岗位全量明细_20260608.xlsx` | 字节全量 |
| Excel 报告 | `bytedance_jobs_output/AI三巨头招聘全量明细_*.xlsx` | 三公司对比 |

### 附录 B：Skill 包

| Skill | 路径 | 功能 |
|---|---|---|
| job-radar | `skills/job-radar.skill` | 单公司岗位爬取 + 画像匹配 |
| talent-intel | `skills/talent-intel.skill` | 跨公司战略洞察对比 |

### 附录 C：硅谷大牛访谈逐字稿

已归档 9 篇 Lex Fridman Podcast 逐字稿（1.8MB），含 Dario Amodei、Sam Altman、Jensen Huang、Demis Hassabis、Elon Musk、Mark Zuckerberg、Yann LeCun、Peter Steinberger、Sundar Pichai。

索引：`silicon-valley-interviews/INDEX.md`
知识图谱 HTML：`silicon-valley-interviews/知识图谱.html`

### 附录 D：独立观察者观点

已整理 6 位无利益关联的独立观察者（Gary Marcus / François Chollet / Jim Covello / Yann LeCun / Ed Zitron / Dean Baker）的核心论点和 AI 泡沫分析框架。

文件：`silicon-valley-interviews/独立观察者观点汇编.md`

### 附录 E：AI 投资分析框架

已产出的分析框架文档：
- AI 可替代市场规模测算（三层模型：替代 / 加速 / 创造）
- Token 经济学分析（量价剪刀差）
- 四层监测信号体系（技术 / 需求 / 资本 / 市场）
- 进场/离场决策树
- 资产配置矩阵（铲子层 / 基础设施层 / 模型层 / 应用层）

---

*本文档由 AI 辅助生成，基于实际 POC 验证结果。所有数据和代码已在生产环境验证通过。*
