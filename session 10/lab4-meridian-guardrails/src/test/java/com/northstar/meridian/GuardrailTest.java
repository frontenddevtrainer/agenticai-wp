package com.northstar.meridian;

import static org.junit.jupiter.api.Assertions.*;

import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.message.ChatMessage;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.guardrail.InputGuardrailException;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.model.chat.response.ChatResponse;
import dev.langchain4j.service.AiServices;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import org.junit.jupiter.api.Test;

/** No LLM: a scripted fake model plays back answers, so we can test the agent's rules exactly and in milliseconds. */
class GuardrailTest {

    static class ScriptedModel implements ChatModel {
        final Deque<String> replies;
        final List<List<ChatMessage>> seen = new ArrayList<>();
        ScriptedModel(String... replies) { this.replies = new ArrayDeque<>(List.of(replies)); }
        @Override public ChatResponse doChat(ChatRequest request) {
            seen.add(request.messages());
            return ChatResponse.builder().aiMessage(AiMessage.from(replies.removeFirst())).build();
        }
    }

    Meridian meridian(ChatModel model) {
        return AiServices.builder(Meridian.class).chatModel(model).tools(new MerchantTools()).build();
    }

    @Test
    void wrongVerdictIsRepromptedAndFixed() {
        var model = new ScriptedModel(
            "ACME processed 9.92M USD against 9.5M.\nVERDICT: OK (104.4%)",          // contradicts itself
            "ACME processed 9.92M USD against 9.5M.\nVERDICT: OVER_LIMIT (104.4%)"); // fixed after the reprompt
        String answer = meridian(model).ask("Is ACME over its limit?");
        assertTrue(answer.endsWith("VERDICT: OVER_LIMIT (104.4%)"));
        assertEquals(2, model.seen.size(), "the guardrail asked the model once more");
        String reprompt = ((UserMessage) model.seen.get(1).getLast()).singleText();
        assertTrue(reprompt.contains("contradicts"), reprompt);
    }

    @Test
    void cardNumberNeverReachesTheModel() {
        var model = new ScriptedModel("should never be used");
        var e = assertThrows(InputGuardrailException.class, () -> meridian(model).ask("Card 4111 1111 1111 1111, is ACME over?"));
        assertTrue(e.getMessage().contains("card number"));
        assertEquals(0, model.seen.size());
    }

    @Test
    void ordinaryNumbersAreNotCardNumbers() {
        var model = new ScriptedModel("BOLT is fine.\nVERDICT: OK (63.1%)");
        assertEquals("BOLT is fine.\nVERDICT: OK (63.1%)", meridian(model).ask("Batch B-2001 was 1500000 USD; is BOLT near its limit?"));
    }

    @Test
    void givesUpAfterMaxRetries() {
        var model = new ScriptedModel("VERDICT: OK (150%)", "VERDICT: OK (150%)", "VERDICT: OK (150%)");
        assertThrows(Exception.class, () -> meridian(model).ask("Is ACME over its limit?"));
        // maxRetries = 2 means at most 2 model calls IN TOTAL: the first answer and one reprompt.
        assertEquals(2, model.seen.size());
    }
}
