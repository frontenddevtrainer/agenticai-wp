# Day 10 Lab 4: Meridian with guardrails and unit tests (LangChain4j 1.21)

A LangChain4j agent that:

- **blocks card numbers before the model** (`PanInputGuardrail`: 13–19 digits passing the Luhn check -> `fatal`,
  so the text never leaves your JVM or reaches the provider's logs)
- **re-prompts when its verdict contradicts its numbers** (`VerdictGuardrail`: above 100% must be OVER_LIMIT,
  above 90% NEAR_LIMIT, else OK; checked in code, not by the model)
- has **unit tests that need no LLM** (`GuardrailTest` uses a scripted fake model: no network, no tokens)

## 1. Run the tests first (no API key needed)

```bash
mvn test
```

Expected: `Tests run: 4, Failures: 0`, in well under a second.

| Test | Proves |
|---|---|
| `wrongVerdictIsRepromptedAndFixed` | a contradictory verdict triggers one reprompt, and the fixed answer is returned |
| `cardNumberNeverReachesTheModel` | a card number throws `InputGuardrailException` and the model is called 0 times |
| `ordinaryNumbersAreNotCardNumbers` | batch amounts and ids are not mistaken for card numbers |
| `givesUpAfterMaxRetries` | `maxRetries = 2` means 2 model calls in total, then it throws |

## 2. Run against a real model

```bash
export OPENROUTER_API_KEY=sk-or-v1-...
mvn -q compile exec:java
```

Expected:

```
Q: Is ACME over its processing limit?
... 9,920,000 USD against a 9,500,000 USD monthly limit ...
VERDICT: OVER_LIMIT (104.42%)

Q: Is BOLT near its limit?
... 3,153,846.15 GBP, which is 63.08% of the limit ...
VERDICT: OK (63.08%)

BLOCKED before the model: ... This message contains a card number ...
```

Options: `MODEL=anthropic/claude-sonnet-5.5` (faster), `BASE_URL=...` (any OpenAI-compatible endpoint, e.g. a local server).

> If OpenRouter's Sensitive Info guardrail (Address / Person name) is still on for your key, merchant ids get replaced
> with `[ADDRESS]` and step 2 misbehaves. Step 1 is unaffected because it never calls OpenRouter.

## 3. Break the rule (exercise)

In `GuardrailTest.wrongVerdictIsRepromptedAndFixed`, make the second scripted answer still contradict itself.
The service now throws after `maxRetries`. Decide what your API should return to a user then: a clear error,
never a wrong verdict.

## Files

| File | What it is |
|---|---|
| `MerchantTools.java` | `@Tool` methods: `lookupMerchant`, `fxRate`, `multiply`, `sum` |
| `PanInputGuardrail.java` | input guardrail: card numbers -> `fatal` |
| `VerdictGuardrail.java` | output guardrail: verdict vs percentage -> `reprompt` |
| `Meridian.java` | the AI Service interface with `@InputGuardrails` / `@OutputGuardrails(maxRetries = 2)` |
| `Main.java` | real-model run (OpenRouter by default, HTTP/1.1 client for local model servers) |
| `GuardrailTest.java` | 4 JUnit tests with a scripted fake model |

Built from the course snippets (`site/src/content/snippets/day10/lab4_*`). Only change: `maven.compiler.release`
is 21 instead of 25, so it builds on JDK 21.
