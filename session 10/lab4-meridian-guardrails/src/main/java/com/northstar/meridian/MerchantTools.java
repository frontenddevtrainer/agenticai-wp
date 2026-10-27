package com.northstar.meridian;

import dev.langchain4j.agent.tool.Tool;
import java.util.Map;

/** Northstar's data as tools the model can call. Same numbers as the Python course. */
public class MerchantTools {
    private static final Map<String, String> MERCHANTS = Map.of(
        "ACME", "limit 9,500,000 USD; batches 4,200,000 EUR, 3,100,000 USD, 2,000,000 EUR; Medium tier",
        "BOLT", "limit 5,000,000 GBP; batches 1,500,000 USD, 2,000,000 GBP; Low tier",
        "CRUX", "limit 800,000,000 INR; batches 650,000,000 INR, 2,000,000 USD; High tier; chargeback watchlist");
    private static final Map<String, Double> FX = Map.of("EUR/USD", 1.10, "GBP/USD", 1.30, "USD/INR", 85.0);

    @Tool("Look up a merchant file: monthly processing limit, month-to-date settlement batches, risk tier")
    public String lookupMerchant(String merchantId) {
        String m = MERCHANTS.get(merchantId.trim().toUpperCase());
        return m != null ? m : "unknown merchant; valid: " + MERCHANTS.keySet();
    }

    @Tool("Spot FX rate: how many units of `quote` one unit of `base` buys. Use for ANY currency conversion.")
    public double fxRate(String base, String quote) {
        String b = base.toUpperCase(), q = quote.toUpperCase();
        if (b.equals(q)) return 1.0;
        Double direct = FX.get(b + "/" + q);
        if (direct != null) return direct;
        Double inverse = FX.get(q + "/" + b);
        if (inverse != null) return 1 / inverse;
        throw new IllegalArgumentException("no rate for " + b + "/" + q);
    }

    @Tool("Multiply two numbers")
    public double multiply(double a, double b) { return a * b; }

    @Tool("Add a list of numbers")
    public double sum(double[] values) {
        double total = 0;
        for (double v : values) total += v;
        return total;
    }
}
