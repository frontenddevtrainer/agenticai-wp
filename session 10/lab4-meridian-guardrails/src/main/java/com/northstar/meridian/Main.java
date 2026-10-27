package com.northstar.meridian;

import dev.langchain4j.guardrail.InputGuardrailException;
import dev.langchain4j.http.client.jdk.JdkHttpClient;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;
import java.net.http.HttpClient;

public class Main {
    public static void main(String[] args) {
        // Claude via OpenRouter by default; any OpenAI-compatible endpoint works (set BASE_URL / MODEL).
        var model = OpenAiChatModel.builder()
            .baseUrl(System.getenv().getOrDefault("BASE_URL", "https://openrouter.ai/api/v1"))
            .apiKey(System.getenv().getOrDefault("OPENROUTER_API_KEY", "none"))
            .modelName(System.getenv().getOrDefault("MODEL", "anthropic/claude-opus-5.5"))
            .timeout(java.time.Duration.ofMinutes(3))
            // HTTP/1.1: on plain http:// URLs Java's client tries an HTTP/2 upgrade, and Python model servers (vLLM, uvicorn)
            // then drop the request body ("400 body: Field required"). Harmless for https endpoints like OpenRouter.
            .httpClientBuilder(JdkHttpClient.builder().httpClientBuilder(HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1)))
            .build();
        Meridian meridian = AiServices.builder(Meridian.class).chatModel(model).tools(new MerchantTools()).build();

        for (String q : new String[] {"Is ACME over its processing limit?", "Is BOLT near its limit?"}) {
            System.out.println("Q: " + q + "\n" + meridian.ask(q) + "\n");
        }
        try {
            meridian.ask("Customer paid with 4111 1111 1111 1111. Is ACME over its limit?");
        } catch (InputGuardrailException e) {
            System.out.println("BLOCKED before the model: " + e.getMessage());
        }
    }
}
