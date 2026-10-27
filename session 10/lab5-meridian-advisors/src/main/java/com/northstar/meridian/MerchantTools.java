package com.northstar.meridian;

import java.util.Map;
import org.springframework.ai.tool.annotation.Tool;

/** Northstar's data as Spring AI tools. */
class MerchantTools {
    private static final Map<String, String> MERCHANTS = Map.of(
        "ACME", "limit 9,500,000 USD; batches 4,200,000 EUR, 3,100,000 USD, 2,000,000 EUR; Medium tier",
        "BOLT", "limit 5,000,000 GBP; batches 1,500,000 USD, 2,000,000 GBP; Low tier",
        "CRUX", "limit 800,000,000 INR; batches 650,000,000 INR, 2,000,000 USD; High tier; chargeback watchlist");
    private static final Map<String, Double> FX = Map.of("EUR/USD", 1.10, "GBP/USD", 1.30, "USD/INR", 85.0);

    /** The figures that matter, computed in code from the same data the tools return. Used to CHECK the model. */
    record Expected(double volume, double limit, String currency, String verdict) {}

    private static final Map<String, Object[]> FILES = Map.of(       // limit, currency, batches (amount, currency)...
        "ACME", new Object[] {9_500_000.0, "USD", 4_200_000.0, "EUR", 3_100_000.0, "USD", 2_000_000.0, "EUR"},
        "BOLT", new Object[] {5_000_000.0, "GBP", 1_500_000.0, "USD", 2_000_000.0, "GBP"},
        "CRUX", new Object[] {800_000_000.0, "INR", 650_000_000.0, "INR", 2_000_000.0, "USD"});

    static Expected expected(String merchantId) {
        Object[] f = FILES.get(merchantId);
        double limit = (double) f[0];
        String ccy = (String) f[1];
        double volume = 0;
        var tools = new MerchantTools();
        for (int i = 2; i < f.length; i += 2) volume += (double) f[i] * tools.fxRate((String) f[i + 1], ccy);
        double pct = volume / limit * 100;
        return new Expected(volume, limit, ccy, pct > 100 ? "OVER_LIMIT" : pct > 90 ? "NEAR_LIMIT" : "OK");
    }

    @Tool(description = "Look up a merchant file: monthly processing limit, month-to-date settlement batches, risk tier")
    String lookupMerchant(String merchantId) {
        String m = MERCHANTS.get(merchantId.trim().toUpperCase());
        return m != null ? m : "unknown merchant; valid: " + MERCHANTS.keySet();
    }

    @Tool(description = "Spot FX rate: how many units of quote one unit of base buys. Use for ANY currency conversion.")
    double fxRate(String base, String quote) {
        String b = base.toUpperCase(), q = quote.toUpperCase();
        if (b.equals(q)) return 1.0;
        if (FX.containsKey(b + "/" + q)) return FX.get(b + "/" + q);
        if (FX.containsKey(q + "/" + b)) return 1 / FX.get(q + "/" + b);
        throw new IllegalArgumentException("no rate for " + b + "/" + q);
    }
}
