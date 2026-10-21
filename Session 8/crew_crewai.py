"""Day 7 Lab 2: the same scenario in CrewAI (role-based crew) for architectural contrast.

Separate env (CrewAI pins pydantic<2.13):  python3.13 -m venv .venv-crew && .venv-crew/bin/pip install crewai python-dotenv langchain-core
Run:  python crew_crewai.py            (uses OPENROUTER_API_KEY; CREWAI_MODEL overrides the model string)
"""
import json
import os
import sys

from crewai import LLM, Agent, Crew, Process, Task
from crewai.tools import tool
from dotenv import load_dotenv

from data import MERCHANTS, fx_rate

load_dotenv()
llm = LLM(model=os.getenv("CREWAI_MODEL", "openrouter/anthropic/claude-haiku-5.5"))   # LiteLLM-style string


@tool("lookup_merchant")
def lookup_merchant(merchant_id: str) -> str:
    """Merchant file: monthly processing limit (amount+currency), risk tier, MTD settlement batches (amount + currency)."""
    return json.dumps(MERCHANTS[merchant_id.strip().upper()])


@tool("get_fx_rate")
def get_fx_rate(base: str, quote: str) -> float:
    """Spot FX rate converting 1 unit of base into quote."""
    return fx_rate(base, quote)


@tool("calculator")
def calculator(expression: str) -> float:
    """Evaluate an arithmetic expression exactly."""
    from tools_lc import calculator as calc   # reuse Day 3's safe calculator
    return calc.invoke({"expression": expression})


researcher = Agent(role="Merchant Risk Research Analyst",
                   goal="Compute MTD volume in limit currency, utilisation and verdict for each merchant",
                   backstory="Meticulous analyst at Northstar Pay who never skips FX conversion.",
                   tools=[lookup_merchant, get_fx_rate, calculator], llm=llm)

writer = Agent(role="Risk Committee Report Writer",
               goal="Write a concise, accurate committee report from research findings",
               backstory="Former merchant risk officer; writes for busy executives; never invents numbers.", llm=llm)

critic = Agent(role="Independent Merchant Risk Reviewer",
               goal="Verify figures, currencies and recommended actions; reject reports with any error",
               backstory="Second line of defence. Applies the four-check rubric strictly.", llm=llm)

t_research = Task(description="Research ACME, BOLT, CRUX for October 2026.", expected_output="A factual table",
                  agent=researcher)

t_write = Task(description="Draft the committee report.", expected_output="Markdown report", agent=writer,
               context=[t_research])

t_review = Task(description="Review the draft against the research. List issues or say APPROVED.",
                expected_output="APPROVED or a list of issues", agent=critic, context=[t_research, t_write])

if __name__ == "__main__":
    process = Process.hierarchical if "--hierarchical" in sys.argv else Process.sequential
    kwargs = {"manager_llm": llm} if process == Process.hierarchical else {}
    crew = Crew(agents=[researcher, writer, critic], tasks=[t_research, t_write, t_review],
                process=process, verbose=True, **kwargs)
    print(crew.kickoff())