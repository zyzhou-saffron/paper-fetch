# paper-fetch — 学术搜索与合法 OA 下载聚合流水线

> 基于 [Agents365-ai/paper-fetch](https://github.com/Agents365-ai/paper-fetch) 的深度 Fork 版本。扩展了 **三源融合全文搜索** (OpenAlex + Semantic Scholar + Unpaywall) 以及 **一键批量检索下载** 功能。

[English](README.md)

---

## ✨ Fork 版本新特性

| 功能 | 原版 | 本 Fork 版本 |
|---------|----------|-----------|
| **搜索** | ❌ 不支持 | ✅ 三源融合 (OpenAlex + S2 + Unpaywall OA状态标记) |
| **一键下载** | 仅支持已知 DOI 下载 | `grab "关键词"` — 检索、解析、去重、合法防封下载一条龙 |
| **引文网络跟踪**| ❌ | `grab-refs` / `grab-citations` — 批量下载所有参考文献/被引文献 |
| **速率限制保护** | 无限速 | S2 API 1.2秒延迟注入 + Unpaywall 100ms 拉黑保护 |
| **输出格式** | 仅 JSON / Text | JSON / `table` (表格) / `compact` / `citation` (标准引文NSFC/APA) |

同时，原版的所有核心功能（5源回退下载链、Agent 原生 JSON 契约、幂等重试、自动后台更新）在此被 **全部完美保留**。

---

## 🚀 快速上手

### 环境要求

- **Python 3.8+**（仅要求标准库——无需 `pip install`）
- 建议配置的环境变量：

```bash
# 写入 ~/.zshrc 或 ~/.bashrc
export UNPAYWALL_EMAIL="你的真实邮箱@example.com"       # 启用最高覆盖率的 Unpaywall 源
export SEMANTIC_SCHOLAR_API_KEY="你的S2-API-KEY"       # 可选：突破 Semantic Scholar 调用限制
```

### 跨平台 AI Agent 安装

如果你正在使用 AI Agent，将其克隆至其默认的技能扫描目录下即可：

```bash
# OpenAI Codex / Antigravity Agent:
git clone https://github.com/zyzhou-saffron/paper-fetch.git ~/.agents/skills/paper-fetch

# Claude Code:
git clone https://github.com/zyzhou-saffron/paper-fetch.git ~/.claude/skills/paper-fetch

# OpenClaw:
git clone https://github.com/zyzhou-saffron/paper-fetch.git ~/.openclaw/skills/paper-fetch
```

---

## 📖 核心使用场景

### 场景一：纯检索 — 探索文献边界
*聚合、去重、展示带有 TLDR 高级摘要的文献卡片。*

```bash
# 三源融合搜索
python scripts/search_and_fetch.py search "CRISPR perturbation prediction" --limit 10 --format table

# 按年份过滤
python scripts/search_and_fetch.py search "single cell RNA-seq" --year-from 2022 --year-to 2025 --format table

# 指定单独数据源并导出 JSON 供别的管道使用
python scripts/search_and_fetch.py search "graph neural network" --source s2 --format json

# 提取 DOI 列表
python scripts/search_and_fetch.py search "AlphaFold" --doi-only

# 导出参考文献格式 (支持 nsfc 和 apa)
python scripts/search_and_fetch.py search "protein language model" --format citation --citation-style nsfc
```

### 场景二：检索并下载 — 一步到位
*我不关心这些论文的状态，请直接把合法 OA 的 PDF 全拉到这个文件夹！*

```bash
# 搜索并自动批量提取 OA 全文
python scripts/search_and_fetch.py grab "foundation models biology" --out ~/papers

# 限量前5篇
python scripts/search_and_fetch.py grab "gene regulation deep learning" --limit 5

# 打印演习名单（预览不下载）
python scripts/search_and_fetch.py grab "AlphaFold protein structure" --dry-run
```

### 场景三：顺藤摸瓜 — 引文网络扫荡
*我读了一篇神作，我想把它所有的引用源头、以及后续致敬工作全都拉下来。*

```bash
# 获取某篇论文引用的所有合法文献
python scripts/search_and_fetch.py grab-refs "DOI:10.1038/s41586-021-03819-2" --out ~/refs

# 获取未来引用了这篇论文的所有合法文献
python scripts/search_and_fetch.py grab-citations "DOI:10.1038/s41586-021-03819-2" --out ~/citations
```

### 场景四：基于单篇文献的极速下载（原项目用法）
*基于原版的单篇极速引擎，依然完美生效。*

```bash
# 自动通过5大源链寻找下载
python scripts/fetch.py 10.1038/s41586-021-03819-2

# 批量拉取文本
python scripts/fetch.py --batch dois.txt --out ~/papers
```

---

## ⚙️ 架构与组件

```
paper-fetch/
├── scripts/
│   ├── fetch.py               # 原版：5大源链的内核底层 (零修改，随上游动态更新)
│   ├── search_and_fetch.py     # 新增：集成检索总编排器 (Orchestrator)
│   ├── search_openalex.py      # 新增：OpenAlex 数据源适配
│   └── search_s2.py            # 新增：Semantic Scholar 数据源适配
├── SKILL.md                    # Agent 技能标识描述文件 (已更新触发词)
├── SEARCH_README.md            # 新特性的补充文档
├── README.md                   # 英文说明
└── README_CN.md                # 本文件
```

### 设计哲学

1. **绝对解耦**：所有的新增逻辑均调用于公开暴露的 `fetch()` 接口，坚决不依赖私有底层的 `_get_json` 等逻辑，确保此魔改版在遭受底层的后台 `git pull --ff-only` 更新冲击时**永不崩溃**。
2. **零新增依赖**：为了符合原本小而美的理念，整个项目仍然仅依赖 Python 原生系统库，拒绝对各种第三方包的裹挟。

---

## ⚠️ 已知限制

- **必须存在 OA 版本**：本脚本尊重版权法案。如果目标文献全网都未托管合法的 OA 副件，脚本将坦诚宣告 0 产出，这在机制上就是不破壁的设计，而非 Bug。
- **速率封锁保护**：Semantic Scholar即使用了 API Key，也只能维持 `1 次/秒` 左右的并发请求。因此如果你下指令下载 50 篇文章，系统强制注入了每次间隔 `1.2` 秒的安全等待墙，所以用不着心急，慢慢刷完即可。
- **域名白板白名单防御**：PDF 下载局限于可信的论文出版端点（Nature, Springer 等），可通过自行挂载环境变量 `PAPER_FETCH_ALLOWED_HOSTS` 拓展解限。

---

## 📜 致谢与支持

**原开源底座通过 [Agents365-ai](https://github.com/Agents365-ai/paper-fetch) 分发构建。**
- Bilibili: https://space.bilibili.com/441831884
- 本扩展与多源合并架构系统由 [zyzhou-Saffrex](https://github.com/zyzhou-Saffrex) 开发及维护。

如果原始的 `paper-fetch` 引擎功能曾在你的研究生涯里极大挽救了你的时间，欢迎赞助原版作者一杯咖啡：

<table>
  <tr>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/wechat-pay.png" width="180" alt="WeChat Pay">
      <br>
      <b>微信支付</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/alipay.png" width="180" alt="Alipay">
      <br>
      <b>支付宝</b>
    </td>
    <td align="center">
      <img src="https://raw.githubusercontent.com/Agents365-ai/images_payment/main/qrcode/buymeacoffee.png" width="180" alt="Buy Me a Coffee">
      <br>
      <b>Buy Me a Coffee</b>
    </td>
  </tr>
</table>

## 许可
MIT
