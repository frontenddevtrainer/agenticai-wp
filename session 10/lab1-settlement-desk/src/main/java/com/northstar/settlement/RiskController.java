package com.northstar.settlement;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** Day 10 Lab 1: the RiskController from 02-spring-ai-and-langchain4j.md, made runnable. */
@RestController
class RiskController {

    private final ChatClient chat;

    RiskController(ChatClient.Builder builder) {
        this.chat = builder
                .defaultSystem("You are a payments risk analyst at Northstar Pay (fictional PSP).")
                .build();
    }

    // Step 3 (stretch): replace the constructor above with this one to give the model the MCP server's tools
    // (needs the spring-ai-starter-mcp-client dependency and the spring.ai.mcp config).
    //
    // RiskController(ChatClient.Builder builder, org.springframework.ai.tool.ToolCallbackProvider mcpTools) {
    //     this.chat = builder
    //             .defaultSystem("You are a payments risk analyst at Northstar Pay (fictional PSP).")
    //             .defaultToolCallbacks(mcpTools)
    //             .build();
    // }

    record Explain(String term, String audience) {}

    record LimitVerdict(String merchantId, double mtdVolume, double limit, String currency,
                        double utilisationPct, String verdict) {}

    @PostMapping("/explain")
    String explain(@RequestBody Explain req) {
        return chat.prompt()
                .user(u -> u.text("Explain {term} to a {audience} in 3 bullets.")   // PromptTemplate under the hood
                        .param("term", req.term())
                        .param("audience", req.audience()))
                .call()
                .content();
    }

    @PostMapping("/verdict")
    LimitVerdict verdict(@RequestBody String facts) {
        return chat.prompt()
                .user("Give the processing-limit verdict for: " + facts)
                .call()
                .entity(LimitVerdict.class);                                         // structured output -> record
    }
}
