package com.northstar.meridian;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;

import java.util.List;
import java.util.Map;

/** Day 10 Lab 2: the toy payments tool-set (same data as the Python Day 2 mock data). */
public class PaymentsTools {

    public record Batch(String batchId, String method, double amount, String currency) {}

    public record Merchant(String id, String riskTier, double limit, String limitCurrency, List<Batch> mtd) {}

    private static final Map<String, Merchant> MERCHANTS = Map.of(
        "ACME", new Merchant("ACME", "Medium", 9_500_000, "USD", List.of(
            new Batch("B-1001", "card_cnp", 4_200_000, "EUR"),
            new Batch("B-1002", "card_cnp", 3_100_000, "USD"),
            new Batch("B-1003", "wallet",   2_000_000, "EUR"))),
        "BOLT", new Merchant("BOLT", "Low", 5_000_000, "GBP", List.of(
            new Batch("B-2001", "card_cnp", 1_500_000, "USD"),
            new Batch("B-2002", "card_cnp", 2_000_000, "GBP"))),
        "CRUX", new Merchant("CRUX", "High", 800_000_000, "INR", List.of(
            new Batch("B-3001", "upi",      650_000_000, "INR"),
            new Batch("B-3002", "card_cnp", 2_000_000,   "USD"))));

    private static final Map<String, Double> FX = Map.of(
        "EUR/USD", 1.10, "GBP/USD", 1.30, "USD/INR", 85.0);

    @Tool("Look up a merchant: risk tier, monthly processing limit (amount + currency) and month-to-date settlement batches")
    public Merchant lookupMerchant(@P("merchant id, e.g. ACME") String merchantId) {
        var m = MERCHANTS.get(merchantId.trim().toUpperCase());
        if (m == null) throw new IllegalArgumentException("unknown merchant; valid: " + MERCHANTS.keySet());
        return m;
    }

    @Tool("Spot FX rate converting 1 unit of base into quote. Use for ANY currency conversion; never guess rates.")
    public double getFxRate(@P("ISO code you have") String base, @P("ISO code you want") String quote) {
        if (base.equals(quote)) return 1.0;
        Double r = FX.get(base + "/" + quote);
        if (r != null) return r;
        Double inv = FX.get(quote + "/" + base);
        if (inv != null) return 1.0 / inv;
        throw new IllegalArgumentException("no rate for " + base + "/" + quote + "; convert via USD");
    }

    @Tool("Add numbers exactly. Use for all addition.")
    public double sum(@P("the numbers to add") List<Double> values) {
        return values.stream().mapToDouble(Double::doubleValue).sum();
    }

    @Tool("Multiply two numbers exactly.")
    public double multiply(@P("first number") double a, @P("second number") double b) {
        return a * b;
    }

    @Tool("Divide a by b exactly (e.g. volume / limit for utilisation).")
    public double divide(@P("numerator") double a, @P("denominator, not zero") double b) {
        if (b == 0) throw new IllegalArgumentException("division by zero");
        return a / b;
    }
}
