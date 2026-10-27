package com.northstar.meridian;

import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.guardrail.InputGuardrail;
import dev.langchain4j.guardrail.InputGuardrailResult;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Blocks a request BEFORE it reaches the model if it contains a card number (13–19 digits passing the Luhn check). */
public class PanInputGuardrail implements InputGuardrail {
    private static final Pattern DIGITS = Pattern.compile("(?:\\d[ -]?){12,18}\\d");

    @Override
    public InputGuardrailResult validate(UserMessage message) {
        Matcher m = DIGITS.matcher(message.singleText());
        while (m.find()) {
            String digits = m.group().replaceAll("[ -]", "");
            if (luhn(digits)) {
                // fatal: stop here, never send this text to the model (or to the model provider's logs)
                return fatal("This message contains a card number. Remove it: Meridian must never see card data.");
            }
        }
        return success();
    }

    static boolean luhn(String digits) {
        int sum = 0;
        boolean dbl = false;
        for (int i = digits.length() - 1; i >= 0; i--) {
            int d = digits.charAt(i) - '0';
            if (dbl && (d *= 2) > 9) d -= 9;
            sum += d;
            dbl = !dbl;
        }
        return sum % 10 == 0;
    }
}
