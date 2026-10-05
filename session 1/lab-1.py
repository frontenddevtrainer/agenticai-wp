import os, time
from dotenv import load_dotenv
import anthropic, ollama

load_dotenv()
LOCAL = os.getenv("OLLAMA_MODEL", "gemma3:1b")
CLAUDE = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")


SYSTEM = "You are a payments operations assistant at Northstar Pay. Answer in at most 4 sentences."
PROMPTS = [
    "What is a rolling reserve and why would a payment processor hold one for a high-risk merchant?",
    "A merchant's MTD volume is 4.2M EUR + 3.1M USD + 2.0M EUR. Their limit is 9.5M USD and EUR/USD is 1.10. Are they over the limit?",
    "Classify this email as payout_delay, chargeback_dispute, refund_issue or api_integration: "
    "'Batch B-1003 still hasn't hit our bank account after 3 days.'",
]

#Anthrophic API Chat
claude = anthropic.Anthropic()
def ask_claude(prompt):
    response = claude.messages.create(
        model = CLAUDE,
        max_tokens=800,
        system=SYSTEM,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.content[-1].text

#Ollama API Chat
def ask_local(prompt):
    response = ollama.chat(
        model=LOCAL,
        
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    return response.message.content

for prompt in PROMPTS:
    print(f"Prompt: {prompt}")
    print(f"Local Response: {ask_local(prompt)}")
    print(f"Claude Response: {ask_claude(prompt)}")
    time.sleep(1)



