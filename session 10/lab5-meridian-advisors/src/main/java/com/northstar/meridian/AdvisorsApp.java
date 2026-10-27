package com.northstar.meridian;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.MessageChatMemoryAdvisor;
import org.springframework.ai.chat.memory.ChatMemory;
import org.springframework.ai.chat.memory.MessageWindowChatMemory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class AdvisorsApp {
    record LimitVerdict(String merchantId, double mtdVolume, double limit, String currency, double utilisationPct, String verdict) {}

    public static void main(String[] args) { SpringApplication.run(AdvisorsApp.class, args); }

    /** Which conversation's memory to use. With a memory advisor configured, Spring AI 2.x requires one on EVERY call. */
    static java.util.function.Consumer<ChatClient.AdvisorSpec> memoryOf(String conversationId) {
        return a -> a.param(ChatMemory.CONVERSATION_ID, conversationId);
    }

    /** Deterministic checks the model can't argue with. null = the record is right. */
    static String check(LimitVerdict v, MerchantTools.Expected e) {
        if (!e.currency().equals(v.currency())) return "the limit currency is " + e.currency() + ", not " + v.currency();
        if (Math.abs(v.mtdVolume() - e.volume()) > e.volume() * 0.005) return "MTD volume should be " + Math.round(e.volume()) + " " + e.currency();
        if (Math.abs(v.limit() - e.limit()) > 0.5) return "the limit is " + Math.round(e.limit());
        return e.verdict().equals(v.verdict()) ? null : "the verdict should be " + e.verdict();
    }

    @Bean
    CommandLineRunner demo(ChatClient.Builder builder) {
        ChatMemory memory = MessageWindowChatMemory.builder().maxMessages(20).build();
        ChatClient meridian = builder
            .defaultSystem("You are Meridian, a merchant-risk analyst at Northstar Pay. Use the tools for every fact and number; "
                           + "convert batches into the limit currency before adding. Verdict: >100% OVER_LIMIT, >90% NEAR_LIMIT, else OK. "
                           // Memory makes follow-ups ("And BOLT?") feel answerable from the conversation. They aren't:
                           + "For EVERY merchant you mention, call lookupMerchant in this turn, even in follow-up questions. "
                           + "Never reuse or guess another merchant's figures.")
            .defaultTools(new MerchantTools())
            .defaultAdvisors(new PolicyAdvisor(), MessageChatMemoryAdvisor.builder(memory).build())
            .build();

        return args -> {
            // 1. Memory: the follow-up only makes sense if the conversation is remembered.
            for (String q : new String[] {"Is ACME over its processing limit? One line.", "And BOLT? One line."}) {
                String answer = meridian.prompt().user(q)
                    .advisors(memoryOf("analyst-42"))
                    .call().content();
                System.out.println("Q: " + q + "\nA: " + answer + "\n");
            }
            // 2. Structured output: a typed record instead of text. A record can still be WRONG (we saw 830M and "CNY"),
            //    so check it in code against figures computed deterministically, and retry once with the specific problem.
            String ask = "Give the processing-limit verdict for CRUX. Call lookupMerchant and fxRate first.";
            LimitVerdict crux = meridian.prompt().user(ask).advisors(memoryOf("analyst-42")).call().entity(LimitVerdict.class);
            String problem = check(crux, MerchantTools.expected("CRUX"));
            if (problem != null) {
                System.out.println("Record rejected (" + problem + "), asking again");
                crux = meridian.prompt().user(ask + " Your previous answer was wrong: " + problem).advisors(memoryOf("analyst-42")).call().entity(LimitVerdict.class);
                problem = check(crux, MerchantTools.expected("CRUX"));
            }
            System.out.println("CRUX as a record: " + crux + (problem == null ? "  ✓ checked" : "  ✗ still wrong (" + problem + "): escalate to a person"));
            System.out.println();
            // 3. The policy advisor stops a request before it reaches the model.
            try {
                meridian.prompt().user("Refund the customer on card 4111 1111 1111 1111").advisors(memoryOf("analyst-42")).call().content();
            } catch (PolicyAdvisor.PolicyViolation e) {
                System.out.println("BLOCKED: " + e.getMessage());
            }
        };
    }
}
