import asyncio
import os
import traceback

from dotenv import load_dotenv
from livekit.agents import AutoSubscribe, Agent, AgentSession, JobContext, WorkerOptions, cli, llm
from livekit.plugins import openai, silero

from bank_corpus import build_rag_index, format_top_docs, load_corpus_json
from prompts import build_system_prompt

load_dotenv()

DEFAULT_GREETING = "Ողջույն, ես բանկային աջակցման ձայնային օգնական եմ։ Ինչպե՞ս կարող եմ օգնել։"


class BankAgent(Agent):
    def __init__(self, *, rag_index, **kwargs):
        self._rag_index = rag_index
        super().__init__(**kwargs)

    @llm.function_tool
    def retrieve_bank_docs(self, query: str, top_k: int = 10) -> str:
        """Return top-K relevant bank documents for the user's query (no embeddings)."""
        try:
            return format_top_docs(self._rag_index, query, top_k=top_k, max_chars=6000)
        except Exception:
            traceback.print_exc()
            return ""


async def entrypoint(ctx: JobContext) -> None:
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    corpus_json_path = os.getenv("BANK_DATA_JSON_PATH", "data/banks_corpus.json")
    llm_model = os.getenv("OPENAI_LLM_MODEL", "gpt-4.1-nano")
    stt_model = os.getenv("OPENAI_STT_MODEL", "gpt-4o-transcribe")
    tts_model = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
    tts_voice = os.getenv("OPENAI_TTS_VOICE", "ash").strip()
    corpus_json = load_corpus_json(corpus_json_path)
    rag_index = build_rag_index(corpus_json)
    system_prompt = build_system_prompt()

    agent = BankAgent(
        rag_index=rag_index,
        instructions=system_prompt,
        vad=silero.VAD.load(),
        stt=openai.STT(model=stt_model, language="hy"),
        llm=openai.LLM(model=llm_model),
        tts=openai.TTS(
            model=tts_model,
            voice=tts_voice,
            instructions="Խոսի՛ր բնական, բարեհամբույր և պրոֆեսիոնալ հայկականով։",
        ),
    )

    session = AgentSession()
    await session.start(agent, room=ctx.room)
    await asyncio.sleep(0.5)
    session.say(DEFAULT_GREETING, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
