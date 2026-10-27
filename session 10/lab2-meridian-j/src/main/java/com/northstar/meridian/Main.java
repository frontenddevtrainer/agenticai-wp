package com.northstar.meridian;

import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;

/**
 * Day 10 Lab 2: LangChain4j tool-using agent (the Java twin of the Day 2/3 Meridian agent).
 *
 * Run:  export OPENROUTER_API_KEY=sk-or-v1-...
 *       mvn -q compile exec:java
 * Logs: LOG_HTTP=true mvn -q compile exec:java     (shows the tool-call loop in the HTTP traffic: exercise 1)
 */
public class Main {

    public static void main(String[] args) {
        String key = System.getenv("OPENROUTER_API_KEY");
        if (key == null || key.isBlank()) {
            System.err.println("OPENROUTER_API_KEY is not set. Run: export OPENROUTER_API_KEY=sk-or-v1-...");
            System.exit(1);
        }
        boolean logHttp = Boolean.parseBoolean(System.getenv().getOrDefault("LOG_HTTP", "false"));
        String modelName = System.getenv().getOrDefault("MERIDIAN_MODEL", "anthropic/claude-sonnet-5.5");

        ChatModel model = OpenAiChatModel.builder()          // Claude via OpenRouter's OpenAI-compatible API
            .baseUrl("https://openrouter.ai/api/v1")
            .apiKey(key)
            .modelName(modelName)
            .maxTokens(8000)
            // no temperature/topP/topK: rejected on current Claude models
            .logRequests(logHttp)
            .logResponses(logHttp)
            .build();

        MeridianJ agent = AiServices.builder(MeridianJ.class)
            .chatModel(model)                                // 1.x name (was chatLanguageModel in 0.x)
            .tools(new PaymentsTools())
            .chatMemoryProvider(id -> MessageWindowChatMemory.withMaxMessages(30))
            .maxSequentialToolsInvocations(10)               // ≈ Day 2 MAX_TURNS (check the name if your version differs)
            .build();

        System.out.println("model: " + modelName + "\n");

        System.out.println("Q: Is ACME over its processing limit?");
        System.out.println("A: " + agent.ask("analyst-42", "Is ACME over its processing limit?") + "\n");

        System.out.println("Q: And BOLT?   (follow-up: same analyst id -> memory)");
        System.out.println("A: " + agent.ask("analyst-42", "And BOLT?") + "\n");

        System.out.println("Q: Is CRUX over its processing limit?   (structured output -> record)");
        System.out.println("A: " + agent.verdict("analyst-7", "Is CRUX over its processing limit?"));

        // Expected (Day 2 answer key): ACME OVER_LIMIT 104.4%, BOLT OK 63.1%, CRUX OVER_LIMIT 102.5%
    }
}
