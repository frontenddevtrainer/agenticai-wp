package com.northstar.meridian;

import java.util.regex.Pattern;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.ai.chat.client.ChatClientRequest;
import org.springframework.ai.chat.client.ChatClientResponse;
import org.springframework.ai.chat.client.advisor.api.CallAdvisor;
import org.springframework.ai.chat.client.advisor.api.CallAdvisorChain;
import org.springframework.core.Ordered;

/**
 * An advisor wraps every call, like a servlet filter: code BEFORE the model (block bad requests) and AFTER it
 * (audit: who asked, how long it took, how many tokens). Every ChatClient call goes through it.
 */
class PolicyAdvisor implements CallAdvisor {
    private static final Logger log = LoggerFactory.getLogger(PolicyAdvisor.class);
    private static final Pattern CARD = Pattern.compile("\\b(?:\\d[ -]?){12,18}\\d\\b");

    static class PolicyViolation extends RuntimeException {
        PolicyViolation(String message) { super(message); }
    }

    @Override
    public ChatClientResponse adviseCall(ChatClientRequest request, CallAdvisorChain chain) {
        String text = request.prompt().getUserMessage().getText();
        if (CARD.matcher(text).find()) {
            throw new PolicyViolation("blocked: the request contains what looks like a card number");   // never reaches the model
        }
        long start = System.nanoTime();
        ChatClientResponse response = chain.nextCall(request);                                         // the model (and tools)
        var usage = response.chatResponse().getMetadata().getUsage();
        log.info("AUDIT conversation={} ms={} tokens={}", request.context().get("chat_memory_conversation_id"),
                 (System.nanoTime() - start) / 1_000_000, usage.getTotalTokens());
        return response;
    }

    @Override public String getName() { return "PolicyAdvisor"; }
    @Override public int getOrder() { return Ordered.HIGHEST_PRECEDENCE; }    // outermost: runs before memory is added
}
