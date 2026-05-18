import json
import re
import requests
from src.LLM.llms import get_llm
import os

JUDGE_SYSTEM_PROMPT = """
You are a strict but fair evaluation judge for a business analytics chatbot.
You will be given:
  1. QUESTION    – the original user question
  2. REFERENCE   – the ground-truth answer, expressed in plain English
  3. ACTUAL      – the chatbot's response to the question

Your job is to decide whether the ACTUAL response is correct.

Scoring rules:
  - PASS   : the ACTUAL conveys all key facts from REFERENCE (numbers within ~1 %, 
              names present, no contradictions). Minor wording differences are fine.
  - PARTIAL: the ACTUAL contains some but not all key facts, or is ambiguous.
  - FAIL   : the ACTUAL is missing critical facts, contains wrong numbers, or 
              contradicts the REFERENCE.

Reply with ONLY a JSON object — nothing else:
{
  "verdict": "PASS" | "PARTIAL" | "FAIL",
  "reason": "<one concise sentence explaining the verdict>"
}
""".strip()
def judge(question: str, reference_answer: str, actual_response: str) -> tuple[str, str]:
    judge_prompt = (f"""
        INSTRUCTIONS:{JUDGE_SYSTEM_PROMPT},
        QUESTION:{question},
        REFERENCE:{reference_answer},
        ACTUAL:{actual_response}""")
    # ── ADD: call the LLM judge and parse its verdict ──────────────────
    api_key = os.environ.get("GROQ_API_KEY")
    judge = get_llm("groq", api_key=api_key, model="llama-3.1-8b-instant")
    judge_response = judge.query(
        prompt=judge_prompt,
        context="",
        system=JUDGE_SYSTEM_PROMPT,
        history=[]
    )
    try:
        verdict_data = json.loads(judge_response)
        verdict = verdict_data.get("verdict", "FAIL")
        reason = verdict_data.get("reason", "No reason provided")
    except json.JSONDecodeError:
        verdict = "FAIL"
        reason = f"Judge response is not valid JSON: {judge_response[:200]}"
    print(f"Judge verdict: {verdict}\nReason: {reason}")
    return verdict, reason