#!/usr/bin/env python3
"""Generates Pokémon Monomyth's display tables from the ROM the user owns (Team Monomyth's closed Emerald-engine game,
game code MONE, 32 MB; nothing is downloaded).

    scripts/gen_monomyth_tables.py "<monomyth_v1_0.gba>"

Writes app/src/main/kotlin/.../companion/data/MonomythGen.kt. Monomyth v1.0 keeps vanilla pokeemerald's table *shapes*
(names in arrays of their own, gBaseStats / gBattleMoves / gItems as separate tables) with its own sizes and fields.
Every table was found from the ROM (literal-pool references, names the game shows) and is checked here against the one
save the companion was mapped from (NATIVE_MONOMYTH says how): MISHIMIZU Lv5 (Scratch / Growl / Assist), met in
Webbed Woods, a Potion, standing in Chamomile Town.
  - gSpeciesNames 0x084E8BBC: 11-byte names, mixed case, 405 entries (0 is "??????????"; the move names follow at once).
    Species ids are the game's own, not Dex numbers (MISHIMIZU is 194, No. 007 in its Dex).
  - gBaseStats 0x084F6DBC: 24-byte entries (143 references): stats +0..+5, types +6 / +7 (vanilla ids, FAIRY 18),
    catchRate +8, genderRatio +9 (MISHIMIZU's 0x21: its personality's low byte 0x59 is male, as the summary shows),
    growthRate +0xC. Its experience curves are its own (gExperienceTables 0x084F65D8: medium fast ends at 1,189,244), so
    no growth rates are written: the app's curves are vanilla's.
  - gMoveNames 0x084E9D23: 13-byte names, 596 moves. gBattleMoves 0x084F17E0: 16-byte entries {u16 effect, u8 power,
    u8 type, u8 accuracy, u8 pp, ...}, a physical / special / status category at +9 (Gen 4's split).
  - gItems 0x089F15C0: 32-byte entries {fieldUseFunc, battleUseFunc, description, u16, u8 secondaryId, u8 pocket << 3 |
    type, u16 price, name[14]} - the name at +0x12, last. 447 items in the game's own order (Potion 32); pockets 1 Items,
    2 Medicine, 3 Poké Balls, 4 held items, 5 TMs / HMs, 6 Berries, 7 Key Items (MONOMYTH_BAG_POCKET_ORDER).
  - gTypeNames 0x084EC5F8 (7 bytes) and the chart 0x084EF720: [19][19] u16 uq4.12, [attacker][defender].
  - gRegionMapEntries 0x08A166AC: vanilla's {x, y, w, h, name pointer}, 206 sections (Chamomile Town 0). No region map
    picture is read yet, so every section is "not on the map" and the MAP tab names the place.
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_expansion_tables import CHARS, OUT_DIR, Rom, kstr  # noqa: E402

SHA1 = "ae1c4be9be8d706bb989602bc05731203d42860d"
LABEL = "Pokemon Monomyth v1.0"
SPECIES_NAMES, BASE_STATS = 0x084E8BBC, 0x084F6DBC
MOVE_NAMES, BATTLE_MOVES = 0x084E9D23, 0x084F17E0
ITEMS, TYPE_NAMES, CHART, MAPSECS = 0x089F15C0, 0x084EC5F8, 0x084EF720, 0x08A166AC
SPECIES, MOVES, ITEMS_COUNT, TYPES, MAPSEC_COUNT = 405, 596, 447, 19, 206
APP_TYPE_NAMES = {0: "Normal", 1: "Fighting", 2: "Flying", 3: "Poison", 4: "Ground", 5: "Rock", 6: "Bug", 7: "Ghost",
                  8: "Steel", 10: "Fire", 11: "Water", 12: "Grass", 13: "Electric", 14: "Psychic", 15: "Ice",
                  16: "Dragon", 17: "Dark", 18: "Fairy"}

# A few names use the Western charmap's accented letters.
CHARS.update({0x01: "À", 0x02: "Á", 0x03: "Â", 0x04: "Ç", 0x05: "È", 0x06: "É", 0x07: "Ê", 0x08: "Ë", 0x09: "Ì",
              0x0B: "Î", 0x0C: "Ï", 0x0D: "Ò", 0x0E: "Ó", 0x0F: "Ô", 0x11: "Ù", 0x12: "Ú", 0x13: "Û", 0x14: "Ñ",
              0x16: "à", 0x17: "á", 0x19: "ç", 0x1A: "è", 0x1C: "ê", 0x1D: "ë", 0x1E: "ì", 0x20: "î", 0x21: "ï",
              0x22: "ò", 0x23: "ó", 0x24: "ô", 0x26: "ù", 0x27: "ú", 0x28: "û", 0x29: "ñ", 0x2E: "+", 0x6F: "í"})


def read(rom):
    sp, ty, gr = {}, {}, {}
    skipped = []
    for i in range(1, SPECIES):
        n = rom.text(SPECIES_NAMES + 11 * i, 11)
        if not n or n.startswith("?") or n == "-":
            skipped.append(i)
            continue
        sp[i] = n
        a = BASE_STATS + 24 * i
        ty[i] = (rom.u8(a + 6), rom.u8(a + 7))
        gr[i] = rom.u8(a + 9)
    mv = {}
    for i in range(1, MOVES):
        n = rom.text(MOVE_NAMES + 13 * i, 13)
        if not n or n == "-":
            continue
        a = BATTLE_MOVES + 16 * i
        mv[i] = (n, rom.u8(a + 3), rom.u8(a + 2))
    it = {}
    for i in range(1, ITEMS_COUNT):
        n = rom.text(ITEMS + 32 * i + 0x12, 14)
        if not n or n.startswith("?") or n == "UNOBTAINABLE":
            continue
        it[i] = n
    tn = {i: rom.text(TYPE_NAMES + 7 * i, 7) for i in range(TYPES)}
    chart = {}
    for atk in APP_TYPE_NAMES:
        for dfn in APP_TYPE_NAMES:
            v = rom.u16(CHART + 2 * (atk * TYPES + dfn))
            if v != 0x1000:
                chart[atk * 100 + dfn] = v * 100 // 0x1000
    ms = {}
    for i in range(MAPSEC_COUNT):
        p = rom.u32(MAPSECS + 8 * i + 4)
        n = rom.text(p, 40) if rom.is_ptr(p) else None
        if n:
            ms[i] = n
    pockets = {i: rom.u8(ITEMS + 32 * i + 0xF) >> 3 for i in it}
    return dict(species=sp, types=ty, gender=gr, moves=mv, items=it, pockets=pockets, type_names=tn, chart=chart,
                mapsecs=ms, skipped=skipped)


def check(t):
    sp, mv, it = t["species"], t["moves"], t["items"]
    # The save's lead: MISHIMIZU (species 194), WATER, male at personality 0xA4E4DA59, Scratch / Growl / Assist.
    assert sp[194] == "Mishimizu" and t["types"][194] == (11, 11) and t["gender"][194] == 0x21
    assert sp[1] == "Kotora" and sp[305] == "Woobat" and t["types"][305] == (14, 2)
    assert [mv[i][0] for i in (10, 45, 271)] == ["Scratch", "Growl", "Assist"]
    assert mv[1] == ("Pound", 0, 40) and mv[33] == ("Tackle", 0, 40) and mv[89] == ("Earthquake", 4, 100)
    assert mv[52] == ("Ember", 10, 40) and mv[57] == ("Surf", 11, 70)
    # The bag's Potion (item 32, pocket 2) and the pockets the bag screen's capacities match.
    assert it[32] == "Potion" and t["pockets"][32] == 2 and it[1] == "Master Ball" and t["pockets"][1] == 3
    assert it[332] == "TM01" and t["pockets"][332] == 5 and it[329] == "Bicycle" and t["pockets"][329] == 7
    assert t["type_names"][18] == "Fairy" and t["type_names"][9] == "???" and t["type_names"][11] == "Water"
    assert t["chart"][1816] == 200 and t["chart"][1618] == 0 and t["chart"][7] == 0  # FAIRY->DRAGON, DRAGON->FAIRY, NORMAL->GHOST
    assert t["chart"][1012] == 200 and t["chart"][1110] == 200                         # FIRE->GRASS, WATER->FIRE
    # gMapHeader reads section 0 in Chamomile Town; MISHIMIZU's met location is 0x3C, the summary's Webbed Woods.
    assert t["mapsecs"][0] == "Chamomile Town" and t["mapsecs"][0x3C] == "Webbed Woods"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    data = open(sys.argv[1], "rb").read()
    h = hashlib.sha1(data).hexdigest()
    if h != SHA1:
        sys.exit(f"{sys.argv[1]}: sha1 {h} isn't {LABEL}'s ({SHA1})")
    t = read(Rom(data))
    check(t)
    top = max(t["gender"])
    gender = "".join("%02x" % t["gender"].get(i, 255) for i in range(top + 1))
    out = ["package com.pokedaisy.app.companion.data\n\n"
           f"// GENERATED by scripts/gen_monomyth_tables.py from the {LABEL} ROM\n"
           f"// (sha1 {SHA1[:8]}...) - do not hand-edit. Names in the game's own (mixed) case.\n\n"]
    out.append("internal val speciesNamesMonomyth: Map<Int, String> by lazy { mapOf(\n" +
               "".join(f"    {i} to {kstr(n)},\n" for i, n in sorted(t["species"].items())) + ") }\n")
    out.append("\ninternal val speciesTypeDataMonomyth: Map<Int, SpeciesTypes> by lazy { mapOf(\n" +
               "".join(f"    {i} to SpeciesTypes({a}, {b}),\n" for i, (a, b) in sorted(t["types"].items())) + ") }\n")
    out.append("\n// gBaseStats genderRatio by species id (0 always male, 254 always female, 255 genderless).\n"
               f"internal val genderRatiosMonomyth: IntArray by lazy {{ unhexRatios(\"{gender}\") }}\n")
    out.append("\n// gMoveNames + gBattleMoves type / power.\n"
               "internal val moveDataMonomyth: Map<Int, MoveInfo> by lazy { mapOf(\n" +
               "".join(f"    {i} to MoveInfo({kstr(n)}, {ty}, {p}),\n" for i, (n, ty, p) in sorted(t["moves"].items())) +
               ") }\n")
    out.append("\ninternal val itemNamesMonomyth: Map<Int, String> by lazy { mapOf(\n" +
               "".join(f"    {i} to {kstr(n)},\n" for i, n in sorted(t["items"].items())) + ") }\n")
    out.append("\n// Vanilla type ids, FAIRY 18; the chart: key = atkType*100+defType -> percent, pairs not listed are 100.\n"
               "internal val typeNamesMonomyth: Map<Int, String> = mapOf(\n" +
               "".join(f"    {i} to {kstr(n)},\n" for i, n in sorted(APP_TYPE_NAMES.items())) + ")\n\n"
               "internal val typeEffectivenessMonomyth: Map<Int, Int> by lazy { mapOf(\n" +
               "".join(f"    {k} to {v},\n" for k, v in sorted(t["chart"].items())) + ") }\n")
    out.append("\n// gRegionMapEntries' names by mapsec id; region -1 = not on a map the app draws (none read yet).\n"
               "internal val mapSecDataMonomyth: Map<Int, MapSecInfo> by lazy { mapOf(\n" +
               "".join(f"    {i} to MapSecInfo({kstr(n)}, -1, 0, 0, 0, 0),\n" for i, n in sorted(t["mapsecs"].items())) +
               ") }\n")
    path = os.path.join(OUT_DIR, "MonomythGen.kt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(out))
    print("wrote", os.path.relpath(path))
    print(f"{len(t['species'])} species (skipped {t['skipped']}), {len(t['moves'])} moves, {len(t['items'])} items, "
          f"{len(t['mapsecs'])} map sections")


if __name__ == "__main__":
    main()
