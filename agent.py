import asyncio
import os
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import AgentSession, WorkerOptions, cli, JobContext, Worker
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai
from banks_data import FULL_BANK_DATA

load_dotenv()

# Strict system prompt with all data
SYSTEM_PROMPT = f"""Մի՛ ել չօգտագործիր քո նախնական գիտելիքները: Դու հայկական բանկերի աջակցության օգնական ես: ՄԱՏՈՒՐ ՄԸԼԱՆՔ ՄԸԼՈՒ Credits, Deposits կամ Branch Locations-ի մասին հարցերին, օգտագործելով ՄԸԼԱՆՔ ԱՊՈՒ ԲՈՒՅՍ bank data-ն:

Bank Data:
{FULL_BANK_DATA}

Եթե հարցը այս թեմաներից դուրս է կամ տվյալները չեն բավարարում, ասա 'ՑԱՓԸՍ, չեմ կարող պատասխանել այդ հարցին բանկային տվյալների հիման վրա':

Պատասխանի հայերենով:"""


async def entrypoint(ctx: JobContext):
    # OpenAI STT: multilingual Whisper for Armenian
    stt = openai.STT(model="whisper-large-v3")  # Supports Armenian

    # GPT-4o-mini LLM: fast, powerful, multilingual Armenian
    llm = openai.LLM(model="gpt-4o-mini")

    # OpenAI TTS: natural Armenian speech
    tts = openai.TTS(model="tts-1-hd", voice="alloy")  # Clear multilingual voice

    assistant = VoiceAssistant(
        vad={},
        stt=stt,
        llm=llm,
        tts=tts,
        chat_ctx=openai.ChatContext().append(role="system", text=SYSTEM_PROMPT),
    )

    # Reject non-topic via fnc (guardrail)
    @assistant.function()
    async def is_valid_topic(session: AgentSession, topic: str):
        valid_topics = [
            "credits",
            "deposits",
            "branches",
            "լոն",
            "գումար",
            "մասնաճյուղ",
        ]
        return any(t in topic.lower() for t in valid_topics)

    await ctx.connect_assistant(assistant)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            redis_url=None,  # Local
        )
    )
