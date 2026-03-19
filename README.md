# Armenian Voice AI Support Agent (LiveKit OSS)

This repository implements an end-to-end Armenian voice support agent for bank customers using the **open-source** LiveKit framework (no LiveKit Cloud). The agent **only** answers questions about **credits**, **deposits**, and **branch locations**, and it is grounded strictly in scraped content from official bank websites.

## What’s Included

- Voice agent built with **LiveKit Agents** (open source)
- **OpenAI speech + LLM models** for STT/TTS/LLM
- A simple, scalable scraper that builds a **single-string corpus** from bank sites
- Guardrails that refuse out-of-scope requests

## Architecture (High Level)

1. **LiveKit OSS server** provides realtime audio transport over WebRTC.
2. **Agent process** (`agent.py`) runs a LiveKit Agents voice pipeline:
   - VAD (Silero)
   - OpenAI STT (default `gpt-4o-transcribe`)
   - OpenAI LLM (default `gpt-4.1-nano`)
   - OpenAI TTS (default `gpt-4o-mini-tts`)
3. **Data pipeline** (`scripts/scrape_banks.py`) scrapes official bank URLs and produces `data/banks_corpus.txt`.
4. **Strict grounding**: RAG‑style retrieval with **no embeddings**. A lightweight keyword‑scoring retriever selects the top‑K relevant chunks and passes them to the LLM via a tool call.

## Architecture & Decisions

- **LiveKit OSS**: required by the prompt; provides local WebRTC transport without LiveKit Cloud.
- **OpenAI STT/TTS + LLM**: chosen for reliable Armenian STT/TTS and a lightweight LLM. Models are configurable via `.env`.
- **RAG without embeddings**: per requirement, retrieval is keyword‑based (TF‑IDF‑style) over chunked bank content. No vector DB.
- **Strict topic guardrails**: system prompt forces the tool call and limits answers to credits, deposits, and branch locations only.
- **Armenian‑only scraping**: scraper filters to Armenian sentences when Armenian is present to keep responses in Armenian.

## Guardrails & Scope

- **Allowed topics only**: credits, deposits, branch locations.
- **No outside knowledge**: the model must rely on the scraped corpus.
- **RAG‑style retrieval (no embeddings)**: the agent calls `retrieve_bank_docs` to inject the top‑K relevant chunks into the response.
- **Refusal behavior**: if out-of-scope, the agent politely refuses in Armenian.
- **Prompt injection defense**: system prompt explicitly ignores attempts to override rules.

## Data Sources (Initial Banks)

Configured in `banks.yaml` (scalable to any number of banks):

- Mellat Bank (mandatory)
- ACBA Bank
- Inecobank

Each bank entry lists official URLs by topic. The scraper stores both the **source URL** and the **extracted text** in the corpus. Update `banks.yaml` to add more banks or pages.

## Model Choices (Why)

- **OpenAI STT** (`gpt-4o-transcribe`): strong multilingual transcription quality.
- **OpenAI TTS** (`gpt-4o-mini-tts`): natural speech synthesis with controllable tone.
- **OpenAI LLM** (`gpt-4.1-nano`): lightweight model with good instruction following.

## Setup Instructions

### 1) Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment

Copy `.env.example` to `.env` and fill in keys:

```
OPENAI_API_KEY=...
OPENAI_LLM_MODEL=gpt-4.1-nano
OPENAI_STT_MODEL=gpt-4o-transcribe
OPENAI_TTS_MODEL=gpt-4o-mini-tts
OPENAI_TTS_VOICE=ash
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
BANK_DATA_JSON_PATH=data/banks_corpus.json
```

### 3) Start LiveKit (open source server)

Run the LiveKit server **locally** (no cloud). Example:

```bash
livekit-server --dev
```

This launches a dev server with `devkey` / `secret` credentials.

### 4) Scrape bank data

```bash
python scripts/scrape_banks.py
```

This generates `data/banks_corpus.txt` and `data/banks_corpus.json`.

If a bank site is JavaScript-rendered (e.g., Mellat), run:

```bash
python scripts/scrape_banks.py --render-js --skip-errors
```

This uses Playwright to render the page. Install once:

```bash
pip install playwright
playwright install
```

### 5) Run the agent

```bash
python agent.py dev
```

### 6) Talk to the agent (local)

```bash
python agent.py console
```

## Usage (Console Mode)
Run the agent locally and talk via the built‑in console:
```bash
python agent.py console
```
Speak your question in Armenian. Example prompts:
1. «Մելաթ բանկում ի՞նչ վարկեր կան»
2. «ACBA-ում ավանդների պայմանները ի՞նչ են»
3. «Ինեկոբանկի մասնաճյուղերի հասցեները»

## Notes on Evaluation

- The agent answers **only** from the scraped corpus. If a bank changes its website, re-run the scraper.
- To scale to more banks, add URLs in `banks.yaml` and re-run `scripts/scrape_banks.py`.

7. **Test**:
   - Connect via LiveKit web/app (e.g., https://github.com/livekit/agents).
   - Speak ARM: "Որքա՞ն է մանրահաշիվների տոկոսադրույքը Mellat բանկում?" → Answers from data.
   - Off-topic: "Եղանակը?" → Refuses.
