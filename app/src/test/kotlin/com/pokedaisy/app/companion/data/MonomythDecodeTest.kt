package com.pokedaisy.app.companion.data

import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/**
 * Pokémon Monomyth v1.0: vanilla's party struct under a key of its own, its eight-pocket bag, its gMain without intrCheck,
 * and its own names. The save is the developer's (the monomyth fixture's README has what the game's own screens showed).
 */
class MonomythDecodeTest {
    private val cfg = NATIVE_MONOMYTH

    @Before fun setUp() {
        activeGame = GameKind.MONOMYTH
    }

    @After fun tearDown() {
        activeGame = GameKind.FIRERED
    }

    @Test
    fun `the substruct key - as 0x08056C60 computes it`() {
        // The save's MISHIMIZU: personality 0xA4E4DA59, OT ID 0x8635AA5B; vanilla's key would be 0x22D17002.
        assertEquals(0x30D32A52L, monomythBoxKey(0xA4E4DA59L, 0x8635AA5BL))
    }

    @Test
    fun `the save - party, bag, money and place`() {
        val t = decodeNative("monomyth", cfg)
        assertEquals(listOf(194), t.party.map { it.species })
        assertEquals(listOf("Mishimizu"), t.party.map { speciesName(it.species) })
        val mon = t.party[0]
        assertEquals(5, mon.level)
        assertEquals(20 to 20, mon.hp to mon.maxHp)
        assertEquals("Mishimizu", mon.nickname)
        assertEquals(GENDER_SYMBOL_MALE, mon.genderSymbol)
        assertEquals(11 to 11, activeSpeciesTypeData[194]!!.let { it.type1 to it.type2 })   // WATER
        assertEquals(listOf("Scratch", "Growl", "Assist"), mon.moves.filter { it != 0 }.map { lookupMove(it).name })
        assertEquals(listOf(35, 40, 20, 0), mon.pp.toList())
        assertEquals(0, mon.heldItem)
        assertEquals(153L, mon.exp)
        val stats = mon.stats!!
        assertEquals(4, stats.nature)   // personality % 25; the game calls it "Meek"
        assertEquals(listOf(20, 11, 11, 11, 11, 11), stats.stats)
        // The bag: the Potion in the second (Medicine) pocket, folded into the app's ITEMS.
        val bag = t.items.associate { itemName(it.itemId) to (it.quantity to it.pocket) }
        assertEquals(mapOf("Potion" to (1 to POCKET_ITEMS)), bag)
        assertPocketsInRange(t)
        assertEquals(3000L, t.money)
        assertFalse(t.inBattle)
        assertEquals(0, t.regionMapSectionId)
        assertEquals("Chamomile Town", activeMapSecData[0]!!.name)
    }

    @Test
    fun `the town outside - the same place, the same party`() {
        val t = decodeNative("monomyth_town", cfg)
        assertEquals(listOf(194), t.party.map { it.species })
        assertEquals(0, t.regionMapSectionId)
        assertFalse(t.inBattle)
    }

    @Test
    fun `a scripted wild battle - the battle flag, set in it and clear once run from`() {
        assertTrue(decodeNative("monomyth_battle", cfg).inBattle)
        val after = decodeNative("monomyth_ran", cfg)
        assertFalse(after.inBattle)
        assertEquals(listOf(194), after.party.map { it.species })
    }
}
