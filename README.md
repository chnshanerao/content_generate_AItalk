# AI Industry Insight System — AI 行业洞察系统

> 用 AI 解构 AI 行业：从招聘数据反推公司战略，追踪泡沫信号，一键生成内容

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 这是什么

一套从「数据采集」到「内容发布」的端到端 AI 行业洞察系统，覆盖：

1. **AI 泡沫追踪器** — 每周自动爬取 8 家 AI 公司招聘数据 + GitHub + arXiv 论文，计算泡沫指数
2. **爆点发现器** — 5 类检测器自动找出最有传播力的故事线索
3. **内容生产线** — 一键生成 LinkedIn 英文帖子 + YouTube 中文脚本 + 数据图表
4. **CEO 打脸检测** — 对比 CEO 公开叙事与实际招聘数据的一致性
5. **知识图谱** — 9 位硅谷 AI 领袖的观点交叉对比

## 核心数据

| 指标 | 数据 |
|---|---|
| 监测公司 | OpenAI, Anthropic, Google DeepMind, ByteDance, xAI, Mistral, Stability AI, Cohere |
| 招聘平台 | Greenhouse API / Ashby HTML / Lever API / 字节自研 API（已逆向） |
| 总岗位 | 5,783+（持续增长） |
| 数据维度 | 招聘 + GitHub 活跃度 + arXiv 论文 + 裁员信号 + 言行一致性 |
| 更新频率 | 每周自动运行 |

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/chnshanerao/content_generate_AItalk.git
cd content_generate_AItalk
```

### 2. 安装依赖

```bash
pip install requests openpyxl matplotlib
```

### 3. 运行泡沫追踪器

```bash
cd ai-bubble-monitor
python3 scripts/monitor.py
```

输出：
```
=== AI 泡沫探测器 v2.0 — 2026-06-12 ===

── Phase 1: 招聘数据 ──
  OpenAI (ashby)... ✓ 724 岗 (GTM:202, R&D:198)
  Anthropic (greenhouse)... ✓ 374 岗 (GTM:110, R&D:96)
  ...

── Phase 4: 泡沫指数计算 ──
  OpenAI: 🟢 1/10
  Stability AI: 🟢 0/10
  Cohere: 🔴 10/10 ⚠ 岗位暴跌 -100.0%

── Phase 5: 言行一致性检测 ──
  ✅ DeepMind: GTM ≈0% → 确实是纯研究院
  ❌ OpenAI: 研发占比 <30% → 嘴上说 AGI，实际优先商业化
```

### 4. 一键生成内容

```bash
python3 scripts/content_pipeline.py
```

输出：
```
[2/4] 爆点发现...
  [1] 传播力 10/10 | 尸体检测 | STABILITY 只剩 5 个岗位了
  [2] 传播力 9/10 | 打脸检测 | Sam Altman 说 AGI，但研发占比只有 27%

[3/4] 内容撰写...
  LinkedIn post: 1,052 chars ✓
  YouTube script: 3,114 chars ✓

[4/4] 图表生成...
  Dashboard chart: ✓
  Comparison chart: ✓
  Trend chart: ✓
```

生成文件：
```
content_output/{date}/
├── linkedin_post.md       ← 英文帖子，可直接复制到 LinkedIn 发布
├── youtube_script.md      ← 中文脚本，含时间戳和画面建议
├── charts/
│   ├── bubble_dashboard.png    ← 泡沫仪表盘
│   ├── company_comparison.png  ← 公司对比图
│   └── highlight_trend.png     ← 趋势图
└── raw_insights.json      ← 原始洞察数据
```

## 项目结构

```
content_generate_AItalk/
│
├── ai-bubble-monitor/              # 核心监测系统
│   ├── config.json                 # 监测公司配置（ATS 平台映射）
│   ├── scripts/
│   │   ├── monitor.py              # 数据采集引擎（607行）
│   │   │                            # - 4 平台招聘爬取
│   │   │                            # - GitHub 活跃度
│   │   │                            # - arXiv 论文
│   │   │                            # - 泡沫指数计算
│   │   │                            # - 言行一致性检测
│   │   ├── story_detector.py       # 爆点发现器
│   │   │                            # - 打脸检测（CEO 叙事 vs 数据）
│   │   │                            # - 尸体检测（公司濒死信号）
│   │   │                            # - 反转检测（扩张↔收缩突变）
│   │   │                            # - 冲突检测（竞对反向变化）
│   │   │                            # - 历史重演（对比互联网泡沫）
│   │   ├── content_writer.py       # 内容撰写器
│   │   │                            # - LinkedIn 英文帖子
│   │   │                            # - YouTube 中文脚本
│   │   ├── chart_generator.py      # 图表生成器（暗色主题 PNG）
│   │   └── content_pipeline.py     # 主控 Pipeline（一键串联）
│   ├── templates/
│   │   ├── linkedin_template.md    # LinkedIn 帖子结构
│   │   └── youtube_template.md     # YouTube 脚本结构
│   ├── data/snapshots/             # 时序快照（核心数据资产）
│   ├── reports/weekly/             # 周报存档
│   └── content_output/             # 生成的内容
│
├── skills/                         # AI Agent Skill 包
│   ├── job-radar/SKILL.md          # 岗位雷达（单公司爬取+匹配）
│   ├── talent-intel/SKILL.md       # 人才情报（跨公司战略对比）
│   ├── job-radar.skill             # 打包好的 Skill（可安装）
│   ├── talent-intel.skill          # 打包好的 Skill（可安装）
│   └── 商业化方案.md                 # 商业化方案文档
│
├── silicon-valley-interviews/      # 硅谷 AI 领袖知识库
│   ├── INDEX.md                    # 9 篇逐字稿索引
│   ├── 知识图谱.html                # 交互式知识图谱（HTML）
│   └── 独立观察者观点汇编.md          # 6 位独立分析师的反面观点
│
└── docs/                           # 文档
    ├── PRD.md                      # 产品需求文档
    └── 架构与评审.md                 # 系统架构 + 五视角评审
```

## 技术细节

### 招聘平台 API 逆向

| 平台 | 使用公司 | 方法 | 关键技术点 |
|---|---|---|---|
| **Greenhouse** | Anthropic, DeepMind, xAI, Stability | REST API | `GET boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true` |
| **Ashby** | OpenAI, Cohere | HTML 内嵌 JSON 提取 | 从 HTML 中用 bracket-matching 解析 `jobPostings` 数组 |
| **Lever** | Mistral | REST API | `GET api.lever.co/v0/postings/{slug}?mode=json` |
| **字节自研** | ByteDance | POST API + 9 个特殊 Header | `Accept` 头必须精确匹配 `application/json, text/plain, */*`，否则 405 |

### 泡沫指数计算公式

```
Bubble Score (0-10) =
  + (岗位周环比 < -10% ? 3 : < -5% ? 2 : 0)
  + (GTM占比下降 >3pp ? 3 : 0)
  + (Manager占比下降 >5pp ? 1 : 0)
  + (城市撤出 ? 1 : 0)
  - (新增城市 ? -1 : 0)
  - (岗位增速 >5% ? -1 : 0)
  + (GitHub 近4周零commit ? 1 : 0)
  + (裁员信号 ? N : 0)

🟢 0-2 健康 | 🟡 3-5 关注 | 🟠 6-8 警告 | 🔴 9+ 泡沫破裂
```

### 爆点发现器的 5 类检测器

| 检测器 | 触发条件 | 传播力 | 情绪 |
|---|---|---|---|
| 打脸检测 | CEO 叙事 vs 数据出现矛盾 | 9/10 | 确认偏差 |
| 尸体检测 | 某公司岗位 ≤10 或暴跌 >15% | 10/10 | 震惊 |
| 反转检测 | 某公司从扩张突然转为收缩 | 8/10 | 焦虑 |
| 冲突检测 | 两家竞对在同一维度反向变化 | 8/10 | 好奇 |
| 历史重演 | 某指标与 1999 互联网泡沫相似 | 9/10 | 焦虑 |

## 部署指南

### 方式一：本地运行（最简单）

```bash
# 每周手动运行
python3 ai-bubble-monitor/scripts/monitor.py
python3 ai-bubble-monitor/scripts/content_pipeline.py
```

### 方式二：云服务器自动化

```bash
# 1. 部署到云服务器
scp -r . user@server:~/ai-insight/

# 2. 安装依赖
ssh user@server
pip install requests openpyxl matplotlib

# 3. 配置 crontab（每周六 9:00 SGT 自动运行）
crontab -e
# 添加：
0 1 * * 6 cd ~/ai-insight/ai-bubble-monitor && python3 scripts/monitor.py && python3 scripts/content_pipeline.py >> /var/log/ai-monitor.log 2>&1

# 4. 配置钉钉推送（编辑 config.json，填入 webhook URL）
```

### 方式三：Claude Code CLI 交互式

```bash
# 安装 Claude Code CLI
# 在项目目录下启动
cd ~/ai-insight
claude

# 然后你可以对话式操作：
> "跑一下本周的泡沫追踪器"
> "以 NVIDIA vs Cisco 为主题生成一期视频内容"
> "分析 Anthropic 最近的招聘变化"
```

## 内容创作工作流

```
每周六 09:00  系统自动运行
              ↓
09:30         你收到钉钉推送：泡沫指数 + 爆点标题 + LinkedIn 帖子草稿
              ↓
10:00         微调 LinkedIn 帖子（加入你的观点），发布
              ↓
10:30         微调 YouTube 脚本，录制（屏幕录制+画外音，5-8分钟）
              ↓
周日          上传 YouTube

总额外时间：~90 分钟/周
```

## 四层监测信号体系（投资决策框架）

```
第一层: 技术层    AI 能力是否在持续提升？       → Benchmark + 论文追踪
第二层: 需求层    真实用户是否在买单？           → 招聘数据 + 企业续约率
第三层: 资本层    投入产出比是否改善？           → Revenue/Capex 比率
第四层: 市场层    资金/情绪的拐点在哪？         → NVIDIA 财报 + IPO 表现
```

## 关键发现（首期数据）

- **OpenAI 言行不一致：** CEO 说 AGI，但 GTM 团队（155 岗）比 Research（51 岗）多 3 倍
- **Stability AI 泡沫已破：** 从 300+ 人萎缩至 5 人，是行业唯一已确认的「破裂」案例
- **收入/投入比 0.18：** 与 1999 年互联网泡沫的 0.17 几乎一致
- **所有公司 GitHub 近 4 周 commit 为 0：** 「拥抱开源」的叙事需要打折扣

## 许可证

MIT License

## 致谢

- 招聘数据来自各公司公开招聘页面（Greenhouse / Ashby / Lever API）
- CEO 访谈逐字稿来自 [Lex Fridman Podcast](https://lexfridman.com)
- 独立观察者观点引用了 Gary Marcus、François Chollet、Jim Covello (Goldman Sachs) 等人的公开发表内容
