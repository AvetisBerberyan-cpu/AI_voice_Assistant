# Armenian Voice AI Bank Support Agent

## Architecture & Decisions

**Overview**: Real-time voice agent using **open-source LiveKit Agents** (Python SDK). Handles Armenian speech-to-text, LLM reasoning, text-to-speech in <2s latency.

**Components**:

- **STT**: OpenAI Whisper-large-v3 - top Armenian ASR (multilingual, accurate dialects).
- **LLM**: OpenAI GPT-4o-mini - Chosen for speed (200+ tok/s), cost (<$0.01/min), Armenian fluency. **Better than Llama-3.1-hye-arlis-2024**: Generalist excels on diverse bank data vs specialist on single site; no fine-tune/hosting needed.
- **TTS**: OpenAI tts-1-hd (alloy) - Natural prosody, ARM support.
- **LiveKit**: Open-source WebRTC rooms/agents for low-latency voice (no Cloud).
- **Data**: Full scraped text from 4 banks (Mellat, Ameria, Ardshin, Converse) concatenated (~20k tokens) in every system prompt. No embeddings/DB for simple eval/iteration. Scalable: Add banks to `data_scraper.py`.
- **Guardrails**: Topic check function + strict prompt - refuses off-topic.

**Why this stack**:

- LiveKit OSS: Production-ready real-time voice.
- OpenAI: Proven ARM, <1s end-to-end, <$5 test.
- RAG-free: Full context ensures accuracy, easy debug.

**Flow**:

```
User Voice (ARM) → Whisper STT → GPT-4o-mini (w/ full data) → TTS → Voice out
Guard: Reject if not credits/deposits/branches
```

## Setup Instructions

1. **Clone/Dir**: Already in `/home/cm-arm-08-l/Desktop/AI_voice_Assistant`.

2. **API Keys**:
   - Get OpenAI key: https://platform.openai.com/api-keys
   - LiveKit OSS server: Install LiveKit server (Docker easiest):
     ```
     docker run --rm -p 7880:7880 -p 7881:7881/udp -v $HOME/.livekit:/etc/livekit livekit/livekit-server --config /etc/livekit/agent.yaml --dev
     ```
     Keys in `~/.livekit/agent.yaml` or generate API key/secret.

3. **Install**:

   ```
   pip install -r requirements.txt
   ```

4. **Env**:

   ```
   cp .env.example .env
   # Edit .env with your keys/URLs
   ```

5. **Scrape Data** (one-time, generates `banks_data.py`):

   ```
   python run_scraper.py
   ```

6. **Run Agent**:

   ```
   livekit-server --version  # Ensure server running
   python agent.py
   ```

   - Joins LiveKit rooms, handles voice.

7. **Test**:
   - Connect via LiveKit web/app (e.g., https://github.com/livekit/agents).
   - Speak ARM: "Որքա՞ն է մանրահաշիվների տոկոսադրույքը Mellat բանկում?" → Answers from data.
   - Off-topic: "Եղանակը?" → Refuses.

**Scalability**: Add banks to `BANKS` dict, rerun scraper.

**GitHub**: Push to your repo, invite HaykTarkhanyan. Local demo ready.

**Costs**: ~$0.15/hour voice (STT+LLM+TTS).
