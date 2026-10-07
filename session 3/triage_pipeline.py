from dotenv import load_dotenv
load_dotenv()  # reads OPENROUTER_API_KEY from .env

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openrouter import ChatOpenRouter      # Claude via OpenRouter

from emails import EMAILS

class TriageTicket(BaseModel):
    """Triage ticket for a merchant support email."""
    merchant_id: str | None = Field(description="ACME, BOLT, CRUX… or null if not identifiable")
    batch_id: str | None = Field(description="Settlement batch id like B-1003, if mentioned")
    category: Literal["payout_delay", "chargeback_dispute", "fraud_suspected", "refund_issue", "api_integration", "other"]
    severity: Literal["P1", "P2", "P3"] = Field(description="P1 = money at risk or merchant cannot trade today")
    amount: float | None = Field(description="Amount in major units, if stated")
    currency: str | None
    next_action: str = Field(description="One imperative sentence for the support agent")

prompt = ChatPromptTemplate.from_messages([
    ("system", "You triage merchant support emails for Northstar Pay, a payment processor. "
               "Suspected fraud attacks and chargeback spikes are always P1. Payout delays over 2 days are P1. "
               "API questions are P3 unless payments are failing. Never include card numbers in any field."),
    ("human", "{email}"),
])

print(prompt)

model = ChatOpenRouter(model="anthropic/claude-haiku-4.5", max_tokens=4000)
print("------------")
print(model)

triage = prompt | model.with_structured_output(TriageTicket)
print("------------")
print(triage)

tickets = triage.batch([{"email": e} for e in EMAILS])   # parallel, free from LCEL
for t in tickets:
    print(t.model_dump_json(indent=2))