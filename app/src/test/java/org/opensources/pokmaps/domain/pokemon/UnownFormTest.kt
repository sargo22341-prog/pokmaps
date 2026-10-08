package org.opensources.pokmaps.domain.pokemon

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class UnownFormTest {
    @Test
    fun formsFollowTheirGeneration() {
        assertTrue(UnownForm.available(1).isEmpty())
        assertEquals(26, UnownForm.available(2).size)
        assertFalse(UnownForm.EXCLAMATION in UnownForm.available(2))
        assertEquals(28, UnownForm.available(3).size)
        assertEquals(UnownForm.entries, UnownForm.available(9))
    }

    @Test
    fun spritesDistinguishAllFourVariants() {
        assertEquals("sprites/unown/static/a.webp", UnownForm.A.sprite(false, false))
        assertEquals("sprites/unown/animated/a.webp", UnownForm.A.sprite(true, false))
        assertEquals("sprites/unown/shiny/static/question.webp", UnownForm.QUESTION.sprite(false, true))
        assertEquals("sprites/unown/shiny/animated/question.webp", UnownForm.QUESTION.sprite(true, true))
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsUnknownStoredForms() {
        UnownForm.from("unknown")
    }
}
