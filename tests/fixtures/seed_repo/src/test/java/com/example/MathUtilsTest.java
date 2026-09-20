package com.example;

import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class MathUtilsTest {

    @Test
    public void testFactorialBaseCases() {
        assertEquals(1L, MathUtils.factorial(0));
        assertEquals(1L, MathUtils.factorial(1));
    }

    @Test
    public void testFactorialOfFive() {
        assertEquals(120L, MathUtils.factorial(5));
    }

    @Test
    public void testMax() {
        assertEquals(5, MathUtils.max(3, 5));
        assertEquals(5, MathUtils.max(5, 3));
    }
}
