package com.northstar.meridian;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.guardrail.InputGuardrails;
import dev.langchain4j.service.guardrail.OutputGuardrails;

/** The agent's contract. LangChain4j implements it: tool calls, the loop, and both guardrails. */
@InputGuardrails(PanInputGuardrail.class)
@OutputGuardrails(value = VerdictGuardrail.class, maxRetries = 2)   // at most 2 model calls in total: answer + 1 reprompt
public interface Meridian {
    @SystemMessage("""
        You are Meridian, a merchant-risk analyst at Northstar Pay. Use the tools for every fact and number.
        Convert every batch into the limit currency with fxRate before adding. Use the tools for arithmetic.
        Finish with exactly one line: VERDICT: <OVER_LIMIT|NEAR_LIMIT|OK> (<utilisation percentage>%)""")
    String ask(String question);
}
