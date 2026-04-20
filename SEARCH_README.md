# paper-fetch 扩展篇：三源融合搜索与下载

本项目除了提供原版的单 DOI 下载 (`fetch.py`) 外，还内置了**聚合学术搜索引擎** (`search_and_fetch.py`)。它能在一行命令内实现 **OpenAlex + Semantic Scholar + Unpaywall** 的多源检索并批量下载。

## 工作原理

1. 搜索 `query` 时，脚本分别向 OpenAlex 和 Semantic Scholar 请求 API。
2. 将结果以 DOI 为主键进行去重和融合，优先使用 S2 提供的高级 AI 全文摘要（TLDR）。
3. 解析出 DOI 后，通过 Unpaywall API 自动检测这篇论文是否开源（以 `🟢 OA Available` / `🔴 Closed Access` 醒目标注）。
4. 通过 `grab` 模式，直接对接原项目的 `fetch.py` 极速下载引擎，无缝拉取免费优质 PDF。

一切发生得很优雅。同时我们内置了 **1.2秒 API 限速器** 和 **100ms 探测间隔**，让你哪怕批量下载 100 篇论文，也绝不会收到任何一家出版社和 API 服务商的拉黑邮件！

## 环境配置建议（强烈推荐）

在你的 `~/.zshrc` 或 `~/.bashrc` 中写入：

```bash
export UNPAYWALL_EMAIL="你的真实邮箱@example.com"
# 可选，获取方式：前往 semanticscholar.org 申请
export SEMANTIC_SCHOLAR_API_KEY="你的S2 API Key" 
```

## 命令与示例

### 1. 探索模式 (search)
*用于：查看前沿领域的文献综述，把命令行当成带摘要和引用的学术搜索引擎。*
```bash
python scripts/search_and_fetch.py search "crispr gene editing" --limit 10 --format table
```
> 会输出排版精美的命令行文献卡片包含作者、发表年份、引用量、源头和 TLDR（一行核心快评）。

### 2. 扫荡模式 (grab)
*用于：我不关心这百来篇文献的各自状态，统统给我把开源的 PDF 下下来存进当前 `/papers` 目录！*
```bash
python scripts/search_and_fetch.py grab "foundation models biology" --limit 50 --out ./papers
```

### 3. 引用溯源追踪 (grab-refs / grab-citations)
*用于：我读了一篇神作 (如 AlphaFold)，我想把它所有引用的前置论文、以及未来引用了它拓展工作的所有论文全都下下来。*
```bash
# 把一篇文章背后的前沿地基全扒下来
python scripts/search_and_fetch.py grab-refs "DOI:10.1038/s41586-021-03819-2" --out ./alphafold_foundation

# 把站在它肩膀上的工作全扒下来
python scripts/search_and_fetch.py grab-citations "DOI:10.1038/s41586-021-03819-2" --out ./alphafold_next
```
