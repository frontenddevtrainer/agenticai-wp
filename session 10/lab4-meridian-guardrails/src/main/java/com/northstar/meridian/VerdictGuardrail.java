package com.northstar.meridian;

import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.guardrail.OutputGuardrail;
import dev.langchain4j.guardrail.OutputGuardrailResult;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Checks the answer against the business rule, in code: the verdict must match the percentage.
 * If it doesn't, the model is asked to fix it (reprompt), up to maxRetries times.
 */
public class VerdictGuardrail implements OutputGuardrail {
    private static final Pattern LINE = Pattern.compile("VERDICT:\\s*(OVER_LIMIT|NEAR_LIMIT|OK)\\s*\\((\\d+(?:\\.\\d+)?)%\\)");

    @Override
    public OutputGuardrailResult validate(AiMessage answer) {
        Matcher m = LINE.matcher(answer.text() == null ? "" : answer.text());
        if (!m.find()) {
            return reprompt("No verdict line", "End your answer with exactly one line: VERDICT: <OVER_LIMIT|NEAR_LIMIT|OK> (<percentage>%)");
        }
        double pct = Double.parseDouble(m.group(2));
        String expected = pct > 100 ? "OVER_LIMIT" : pct > 90 ? "NEAR_LIMIT" : "OK";
        if (!m.group(1).equals(expected)) {
            return reprompt("Verdict " + m.group(1) + " doesn't match " + pct + "%",
                "Your verdict contradicts your percentage. The rule: above 100% is OVER_LIMIT, above 90% NEAR_LIMIT, otherwise OK. "
                + "Recheck the numbers and answer again.");
        }
        return success();
    }
}
