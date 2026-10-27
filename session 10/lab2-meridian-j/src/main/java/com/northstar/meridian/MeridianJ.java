package com.northstar.meridian;

import dev.langchain4j.service.MemoryId;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;

/** Day 10 Lab 2: the AI Service. LangChain4j generates the implementation (prompting, tool loop, memory). */
interface MeridianJ {

    String SYSTEM = """
        You are Meridian-J, the settlement desk agent at Northstar Pay (fictional payment processor).
        Use tools for every number. Convert all amounts into the limit currency before comparing.
        Finish with OVER_LIMIT / NEAR_LIMIT (>90%) / OK and the utilisation %.""";

    @SystemMessage(SYSTEM)
    String ask(@MemoryId String analystId, @UserMessage String question);

    /** Exercise 2: structured output. Same agent and tools, but the answer comes back as a record. */
    record LimitVerdict(String merchantId, double mtdVolume, double limit, String currency,
                        double utilisationPct, String verdict, String rationale) {}

    @SystemMessage(SYSTEM)
    LimitVerdict verdict(@MemoryId String analystId, @UserMessage String question);
}
