# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An Egyptian real estate AI expert system combining a fine-tuned LLaMA 3 model with a vector search (RAG) pipeline. The system answers real estate queries in Arabic using retrieval-augmented generation.

## Architecture

The pipeline has three stages:

1. **Data Collection** (`scraper.js`, `scraper.py`) → `data_lake/market_data.json`
   - Collects Egyptian real estate listings (location, price `pr`, area `ar`)
   - `scraper.js` is the primary scraper (Arabic-language target sites); `scraper.py` is a Python stub

2. **Embedding & Vector DB** (`embed_engine.py`) → `vector_db/`
   - Uses `intfloat/multilingual-e5-large` (1024-dim) via `sentence_transformers`
   - Stores vectors in a **local Qdrant** instance; collection name: `egypt_estate`, distance: Cosine
   - Qdrant data lives in `vector_db/collection/`

3. **Fine-tuned LLM** (`models/expert_model_final/`)
   - Base model: `unsloth/llama-3-8b-bnb-4bit` (LLaMA 3 8B, 4-bit quantized)
   - LoRA adapter: r=16, alpha=16, targets all attention + MLP projection layers
   - Training data format: `final_expert_v3.jsonl` — chat messages with `system="Expert"`
   - `fix_data.py` generated training data by extracting `expert_model_final.zip` → `extracted_docs/` and converting file contents to JSONL

## Key Dependencies

Python: `sentence_transformers`, `qdrant_client`, `peft` (0.18.1), `transformers`, `unsloth`, `trl`
Node.js: `fs`, `path` (built-ins; add scraping libs like `puppeteer`/`axios` as needed)

## Running the Pipeline

```bash
# 1. Collect market data
node scraper.js

# 2. Embed documents and populate Qdrant
python embed_engine.py

# 3. Prepare / regenerate fine-tuning data
python fix_data.py
```

## Data Formats

- `data_lake/market_data.json`: array of `{ loc, pr, ar }` objects (location, price EGP, area m²)
- `final_expert_v3.jsonl`: one JSON object per line, shape `{ messages: [{role, content}, ...] }` with roles `system` / `user` / `assistant`
- Qdrant collection `egypt_estate`: vectors of size 1024, Cosine distance

## Known Issues

- `embed_engine.py` and `scraper.py` are missing indentation (likely encoding/copy-paste corruption) — the logic stubs need to be completed and properly indented before running.
- `fix_data.py` is encoded in UTF-16 LE; open it with that encoding if editing directly.
