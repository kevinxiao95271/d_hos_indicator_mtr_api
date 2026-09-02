package com.hospital.indicator.util;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

class ExpressionParserTest {

    @Test
    void shouldCalculatePercentageAsDisplayValue() {
        Map<String, BigDecimal> values = values("numerator", "5", "denominator", "200");

        BigDecimal result = ExpressionParser.calculate(
                "(numerator * 1.0 / denominator) * 100", values);

        assertEquals(new BigDecimal("2.5000"), result);
    }

    @Test
    void shouldCalculatePermilleAsDisplayValue() {
        Map<String, BigDecimal> values = values("numerator", "5", "denominator", "200");

        BigDecimal result = ExpressionParser.calculate(
                "(numerator * 1.0 / denominator) * 1000", values);

        assertEquals(new BigDecimal("25.0000"), result);
    }

    @Test
    void shouldReturnZeroWhenRatioDenominatorIsZero() {
        Map<String, BigDecimal> values = values("numerator", "5", "denominator", "0");

        BigDecimal result = ExpressionParser.calculate(
                "(numerator * 1.0 / denominator) * 100", values);

        assertEquals(new BigDecimal("0.0000"), result);
    }

    private Map<String, BigDecimal> values(
            String firstCode, String firstValue, String secondCode, String secondValue) {
        Map<String, BigDecimal> values = new HashMap<>();
        values.put(firstCode, new BigDecimal(firstValue));
        values.put(secondCode, new BigDecimal(secondValue));
        return values;
    }
}
