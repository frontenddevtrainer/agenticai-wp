# Day 10 Lab 5: Advisors, memory and records you can trust (Spring AI 2.0)

A command-line Spring Boot app (no web server) with a Spring AI `ChatClient` that has:

- **`PolicyAdvisor`**: wraps every model call like a servlet filter. Before the model: blocks anything that looks like
  a card number. After the model: logs an `AUDIT` line (conversation, ms, tokens).
- **Chat memory** (`MessageChatMemoryAdvisor`): the follow-up "And BOLT?" only makes sense if the conversation is remembered.
- **Typed records checked in code**: `.entity(LimitVerdict.class)` gives a typed record, not a correct one. `check(...)`
  compares it with figures computed deterministically (`MerchantTools.expected`), retries once with the specific
  problem, and escalates if it's still wrong. A wrong record is never shown as right.

## Run

Needs JDK 21+ and Maven 3.9+.

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
mvn spring-boot:run
```

Optional: `MODEL=anthropic/claude-sonnet-5.5` (faster), `BASE_URL=...` (any OpenAI-compatible endpoint).

Expected (your wording will differ):

```
AUDIT conversation=analyst-42 ms=... tokens=...
Q: Is ACME over its processing limit? One line.   -> OVER_LIMIT, 104.4% (9.92M USD vs 9.5M USD)
Q: And BOLT? One line.                            -> OK, 63.1% (3.15M GBP vs 5M GBP)     <- needs memory
CRUX as a record: LimitVerdict[..., mtdVolume=8.2E8, limit=8.0E8, currency=INR, utilisationPct=102.5, verdict=OVER_LIMIT]  ✓ checked
BLOCKED: blocked: the request contains what looks like a card number
```

## Exercises

1. **Remove the lookup rule.** Delete the "For EVERY merchant you mention, call lookupMerchant..." sentence from the
   system prompt in `AdvisorsApp.java` and run a few times. Watch for a confident, invented BOLT answer taken from
   memory instead of the tools.
2. **Stretch: a token budget advisor.** Write a `BudgetAdvisor` that reads `usage.getTotalTokens()` after each call,
   adds it to a per-conversation counter, and throws when a conversation passes 20,000 tokens.

## Files

| File | What it is |
|---|---|
| `AdvisorsApp.java` | the app: ChatClient with system prompt, tools and both advisors; memory demo, checked CRUX record, blocked card number |
| `PolicyAdvisor.java` | `CallAdvisor` at `HIGHEST_PRECEDENCE`: card-number block before the model, audit log after |
| `MerchantTools.java` | `@Tool` methods (`lookupMerchant`, `fxRate`) + `expected(...)`: the figures computed in code |
| `application.yml` | OpenRouter base URL (must end in `/v1`), model, no web server, quiet logging |

## If something goes wrong

| Symptom | Fix |
|---|---|
| `conversationId cannot be null` | with a memory advisor, Spring AI 2.x needs `ChatMemory.CONVERSATION_ID` on every call (`memoryOf(...)` does this) |
| 404 from OpenRouter | the base URL must end in `/v1` |
| 400 about `temperature` | Claude 5.x rejects sampling parameters: don't set them |
| Answers mention `[ADDRESS]` / ask which merchant | OpenRouter's Sensitive Info guardrail (Address / Person name) is redacting merchant ids: turn it off for your key |
| `Record rejected (...) ... escalate to a person` | the check worked: the model's record was wrong twice and was not shown as correct |

Built from the course snippets (`site/src/content/snippets/day10/lab5_*`). Only change: `java.version` is 21 instead of 25.
