# paper-fetch — Academic Search & Legal OA Download Pipeline

> Forked from [Agents365-ai/paper-fetch](https://github.com/Agents365-ai/paper-fetch), extended with **triple-source unified search** (OpenAlex + Semantic Scholar + Unpaywall) and **one-command batch download**.

---

## ✨ What's New in This Fork

| Feature | Original | This Fork |
|---------|----------|-----------|
| **Search** | ❌ Not supported | ✅ Triple-source fusion (OpenAlex + S2 + Unpaywall OA tagging) |
| **One-click download** | DOI-only input | `grab "keyword"` — search & download in one command |
| **Citation network** | ❌ | `grab-refs` / `grab-citations` — download an entire reference tree |
| **Rate limiting** | None | Built-in 1.2s S2 throttle + 100ms Unpaywall interval |
| **Output formats** | JSON only | `table` / `compact` / `citation (NSFC/APA)` / `json` |

Everything from the original project (5-source fallback download, agent-native JSON contract, idempotent retries, self-update) is **fully preserved**.

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.8+** (standard library only — zero `pip install`)
- Environment variables (recommended):

```bash
# Add to ~/.zshrc or ~/.bashrc
export UNPAYWALL_EMAIL="your-email@example.com"       # Enables Unpaywall (highest OA coverage)
export SEMANTIC_SCHOLAR_API_KEY="your-s2-key"          # Optional: raises S2 rate limit
```

### Installation

```bash
# Default setup for OpenAI Codex / Antigravity Agent
git clone https://github.com/zyzhou-saffron/paper-fetch.git ~/.agents/skills/paper-fetch
```

#### Cross-Platform Agent Installation Paths

If you are using a different AI agent engine, install to its designated skills directory:

| Platform | Global path | Project path |
|----------|-------------|--------------|
| **Claude Code** | `~/.claude/skills/paper-fetch/` | `.claude/skills/paper-fetch/` |
| **OpenClaw** | `~/.openclaw/skills/paper-fetch/` | `skills/paper-fetch/` |
| **Hermes Agent** | `~/.hermes/skills/research/paper-fetch/` | Via `external_dirs` |
| **pi-mono** | `~/.pimo/skills/paper-fetch/` | — |
| **OpenAI / Antigravity**| `~/.agents/skills/paper-fetch/` | `.agents/skills/paper-fetch/` |

---

## 📖 Usage

### Search Only — Explore the Literature

```bash
# Triple-source fusion search with deduplication and OA status tagging
python scripts/search_and_fetch.py search "CRISPR perturbation prediction" --limit 10 --format table

# Filter by year range
python scripts/search_and_fetch.py search "single cell RNA-seq" --year-from 2022 --year-to 2025 --format table

# Use a single source
python scripts/search_and_fetch.py search "graph neural network" --source s2 --format json

# Export DOIs only (pipe-friendly)
python scripts/search_and_fetch.py search "AlphaFold" --doi-only

# Citation format output (NSFC or APA style)
python scripts/search_and_fetch.py search "protein language model" --format citation --citation-style apa
```

### Search + Download — The Power Move

```bash
# Search and auto-download all available OA PDFs
python scripts/search_and_fetch.py grab "foundation models biology" --out ~/papers

# Limit to 5 results
python scripts/search_and_fetch.py grab "gene regulation deep learning" --limit 5

# Preview without downloading
python scripts/search_and_fetch.py grab "AlphaFold protein structure" --dry-run
```

### Citation Network Download

```bash
# Download all OA references of a paper
python scripts/search_and_fetch.py grab-refs "DOI:10.1038/s41586-021-03819-2" --out ~/refs

# Download all OA papers that cite a paper
python scripts/search_and_fetch.py grab-citations "DOI:10.1038/s41586-021-03819-2" --out ~/citations

# Just browse references (no download)
python scripts/search_and_fetch.py refs "DOI:10.1038/s41586-021-03819-2" --format table
```

### Original DOI Download (Unchanged)

```bash
# Single DOI
python scripts/fetch.py 10.1038/s41586-021-03819-2

# Batch from file
python scripts/fetch.py --batch dois.txt --out ~/papers

# Dry-run preview
python scripts/fetch.py 10.1038/s41586-021-03819-2 --dry-run

# Agent schema discovery
python scripts/fetch.py schema --pretty
```

---

## 🏗️ Architecture

```
paper-fetch/
├── scripts/
│   ├── fetch.py               # Original: 5-source DOI → PDF engine (upstream, untouched)
│   ├── search_and_fetch.py     # NEW: Unified CLI orchestrator
│   ├── search_openalex.py      # NEW: OpenAlex search module
│   └── search_s2.py            # NEW: Semantic Scholar search module
├── SKILL.md                    # Agent skill definition (updated)
├── SEARCH_README.md            # Search extension documentation (中文)
└── README.md                   # This file
```

### Design Principles

1. **Zero coupling to upstream internals** — Only imports the public `fetch()` function from `fetch.py`. No private `_underscore` functions are used, so upstream `git pull --ff-only` auto-updates never break the extension.
2. **Zero new dependencies** — Pure Python stdlib, same as the original.
3. **Graceful degradation** — If one data source fails (e.g., S2 rate-limited), results from remaining sources are still returned.
4. **Built-in rate limiting** — 1.2s delay between `fetch()` calls (respects S2's 1 req/s limit); 100ms delay between Unpaywall OA checks.

---

## 🔧 Command Reference

### `search_and_fetch.py` Subcommands

| Subcommand | Description |
|------------|-------------|
| `search "query"` | Search only — returns a merged, deduplicated paper list |
| `grab "query"` | Search + auto-download all OA PDFs |
| `refs "DOI:xxx"` | List references of a paper |
| `citations "DOI:xxx"` | List papers that cite a paper |
| `grab-refs "DOI:xxx"` | Download reference PDFs |
| `grab-citations "DOI:xxx"` | Download citing-paper PDFs |

### Common Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--source` | `auto` | Data source: `auto` (fusion), `openalex`, `s2` |
| `--limit N` | `10` (search) / unlimited (grab) | Max results. `0` = unlimited |
| `--year-from` / `--year-to` | — | Publication year filter |
| `--format` | `json` | Output: `json`, `table`, `compact`, `citation` |
| `--citation-style` | `nsfc` | `nsfc` or `apa` |
| `--doi-only` | off | Print DOIs only (one per line) |
| `--no-oa-check` | off | Skip Unpaywall OA enrichment (faster) |
| `--out DIR` | `pdfs` | Download output directory |
| `--dry-run` | off | Preview without downloading |

---

## 🌐 Data Sources

### Search Sources

| Source | Coverage | Unique Value |
|--------|----------|--------------|
| **OpenAlex** | 250M+ works, all disciplines | Free, no key needed, inverted-index abstracts |
| **Semantic Scholar** | 200M+ works, all disciplines | AI-generated TLDR summaries, citation graph |
| **Unpaywall** | OA enrichment for any Crossref DOI | Most comprehensive OA availability detection |

### Download Sources (via `fetch.py`)

| Priority | Source | Scope |
|----------|--------|-------|
| 1 | **Unpaywall** | All disciplines — highest OA hit rate |
| 2 | **Semantic Scholar** | All disciplines — `openAccessPdf` field |
| 3 | **arXiv** | Physics, Math, CS, Stats, EE |
| 4 | **PubMed Central** | Biomedical |
| 5 | **bioRxiv / medRxiv** | Biology / medicine preprints |

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `UNPAYWALL_EMAIL` | Recommended | Contact email for Unpaywall + OpenAlex polite pool |
| `SEMANTIC_SCHOLAR_API_KEY` | Optional | Raises S2 rate limit from 100/5min to 1/sec |
| `PAPER_FETCH_ALLOWED_HOSTS` | Optional | Comma-separated extra download hostnames |
| `PAPER_FETCH_NO_AUTO_UPDATE` | Optional | Disable background `git pull` self-update |

---

## ⚠️ Known Limitations

- **Coverage depends on OA availability** — if a paper has no legal OA copy, this tool cannot get it. This is by design.
- **S2 rate limit** — Even with an API key, S2 allows ~1 request/second. Batch downloads of 50+ papers will take a few minutes.
- **Host allowlist** — Downloads are restricted to known academic domains. Extend with `PAPER_FETCH_ALLOWED_HOSTS`.
- **50 MB per-PDF cap** — Prevents runaway downloads of supplementary data bundles.
- **Never bypasses paywalls** — This tool will not use Sci-Hub or any paywall-circumvention service.

---

## License

MIT
