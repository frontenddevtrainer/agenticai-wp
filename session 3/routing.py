from dotenv import load_dotenv
load_dotenv()  # reads OPENROUTER_API_KEY from .env

from langchain_openrouter import ChatOpenRouter      # Claude via OpenRouter
from langchain_core.runnables import RunnableLambda

cheap = ChatOpenRouter(model="anthropic/claude-haiku-4.5", max_tokens=1000)
smart = ChatOpenRouter(model="anthropic/claude-sonnet-6.5", max_tokens=8000).with_fallbacks([cheap])



def route(inp: dict):
    # Simple, explicit rule. Teach that routing rules are business logic: keep them readable and logged.
    return cheap if inp["task"] in {"classify", "summarise_short"} else smart

router = RunnableLambda(lambda inp: route(inp).invoke(inp["prompt"]))

print(router.invoke({"task": "classify", "prompt": "Classify tone (neutral/negative): 'BOLT says their payout is late again.'"}).text)
print(router.invoke({"task": "investigate", "prompt": "Explain how a 2M EUR position could push ACME over a 9.5M USD limit."}).text)


# q = "In one sentence, what is a chargeback, and why does it cost the acquirer money?"
# for name, m in [("Sonnet", smart), ("Haiku", cheap)]:
#     r = m.invoke(q)
#     print(name, "→", r.text, "\n   usage:", r.usage_metadata)
#     print("---------------")