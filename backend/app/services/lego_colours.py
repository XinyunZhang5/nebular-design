"""LEGO colours, read from the Rebrickable catalogue. GENERATED — do not edit.

Regenerate with scripts/build_colour_table.py. Names and RGB values come from
Rebrickable's colors.csv; none of it was recalled.

102 opaque colours and 35 transparent ones, each appearing on at least
50 known parts. Ordered by how much of the catalogue they cover, so the
common colours are first and a caller that truncates the list keeps the useful
half.
"""

from typing import NamedTuple


class Colour(NamedTuple):
    colour_id: int  # Rebrickable colour ID
    name: str  # official LEGO / BrickLink colour name
    rgb: tuple[int, int, int]

    @property
    def hex(self) -> str:
        """The colour as `#RRGGBB`, for clients that draw a swatch.

        Names alone are not enough on the wire: a client that keeps its own
        name-to-hex table silently falls back to grey the moment this catalogue
        gains a colour, and the drift is invisible until someone looks at a
        rendered palette. Shipping the hex from here keeps one source of truth.
        """
        return "#{:02X}{:02X}{:02X}".format(*self.rgb)


SOLID: list[Colour] = [
    Colour(0, "Black", (0x05, 0x13, 0x1D)),  # 841,614 parts
    Colour(15, "White", (0xFF, 0xFF, 0xFF)),  # 521,025 parts
    Colour(71, "Light Bluish Gray", (0xA0, 0xA5, 0xA9)),  # 519,861 parts
    Colour(72, "Dark Bluish Gray", (0x6C, 0x6E, 0x68)),  # 375,403 parts
    Colour(4, "Red", (0xC9, 0x1A, 0x09)),  # 322,720 parts
    Colour(14, "Yellow", (0xF2, 0xCD, 0x37)),  # 217,043 parts
    Colour(1, "Blue", (0x00, 0x55, 0xBF)),  # 208,609 parts
    Colour(19, "Tan", (0xE4, 0xCD, 0x9E)),  # 197,531 parts
    Colour(70, "Reddish Brown", (0x58, 0x2A, 0x12)),  # 180,390 parts
    Colour(7, "Light Gray", (0x9B, 0xA1, 0x9D)),  # 92,820 parts
    Colour(2, "Green", (0x23, 0x78, 0x41)),  # 91,771 parts
    Colour(28, "Dark Tan", (0x95, 0x8A, 0x73)),  # 74,295 parts
    Colour(25, "Orange", (0xFE, 0x8A, 0x18)),  # 55,309 parts
    Colour(297, "Pearl Gold", (0xAA, 0x7F, 0x2E)),  # 54,793 parts
    Colour(272, "Dark Blue", (0x0A, 0x34, 0x63)),  # 53,996 parts
    Colour(320, "Dark Red", (0x72, 0x0E, 0x0F)),  # 50,549 parts
    Colour(27, "Lime", (0xBB, 0xE9, 0x0B)),  # 46,350 parts
    Colour(84, "Medium Nougat", (0xAA, 0x7D, 0x55)),  # 44,891 parts
    Colour(322, "Medium Azure", (0x36, 0xAE, 0xBF)),  # 31,020 parts
    Colour(191, "Bright Light Orange", (0xF8, 0xBB, 0x3D)),  # 30,488 parts
    Colour(484, "Dark Orange", (0xA9, 0x55, 0x00)),  # 28,477 parts
    Colour(10, "Bright Green", (0x4B, 0x9F, 0x4A)),  # 28,414 parts
    Colour(288, "Dark Green", (0x18, 0x46, 0x32)),  # 27,188 parts
    Colour(378, "Sand Green", (0xA0, 0xBC, 0xAC)),  # 26,308 parts
    Colour(308, "Dark Brown", (0x35, 0x21, 0x00)),  # 25,328 parts
    Colour(3, "Dark Turquoise", (0x00, 0x8F, 0x9B)),  # 23,941 parts
    Colour(179, "Flat Silver", (0x89, 0x87, 0x88)),  # 23,148 parts
    Colour(8, "Dark Gray", (0x6D, 0x6E, 0x5C)),  # 22,452 parts
    Colour(29, "Bright Pink", (0xE4, 0xAD, 0xC8)),  # 19,043 parts
    Colour(321, "Dark Azure", (0x07, 0x8B, 0xC9)),  # 17,667 parts
    Colour(85, "Dark Purple", (0x3F, 0x36, 0x91)),  # 17,380 parts
    Colour(5, "Dark Pink", (0xC8, 0x70, 0xA0)),  # 16,431 parts
    Colour(26, "Magenta", (0x92, 0x39, 0x78)),  # 13,931 parts
    Colour(73, "Medium Blue", (0x5A, 0x93, 0xDB)),  # 13,324 parts
    Colour(226, "Bright Light Yellow", (0xFF, 0xF0, 0x3A)),  # 12,416 parts
    Colour(326, "Olive Green", (0x9B, 0x9A, 0x5A)),  # 12,068 parts
    Colour(78, "Light Nougat", (0xF6, 0xD7, 0xB3)),  # 11,819 parts
    Colour(323, "Light Aqua", (0xAD, 0xC3, 0xC0)),  # 10,815 parts
    Colour(379, "Sand Blue", (0x60, 0x74, 0xA1)),  # 10,668 parts
    Colour(30, "Medium Lavender", (0xAC, 0x78, 0xBA)),  # 10,236 parts
    Colour(212, "Bright Light Blue", (0x9F, 0xC3, 0xE9)),  # 9,890 parts
    Colour(6, "Brown", (0x58, 0x39, 0x27)),  # 9,557 parts
    Colour(31, "Lavender", (0xE1, 0xD5, 0xED)),  # 8,874 parts
    Colour(1103, "Pearl Titanium", (0x3E, 0x3C, 0x39)),  # 7,874 parts
    Colour(1050, "Coral", (0xFF, 0x69, 0x8F)),  # 7,849 parts
    Colour(135, "Pearl Light Gray", (0x9C, 0xA3, 0xA8)),  # 5,501 parts
    Colour(80, "Metallic Silver", (0xA5, 0xA9, 0xB4)),  # 4,164 parts
    Colour(158, "Yellowish Green", (0xDF, 0xEE, 0xA5)),  # 3,944 parts
    Colour(1136, "Reddish Orange", (0xCA, 0x4C, 0x0B)),  # 3,674 parts
    Colour(82, "Metallic Gold", (0xDB, 0xAC, 0x34)),  # 3,673 parts
    Colour(92, "Nougat", (0xD0, 0x91, 0x68)),  # 3,076 parts
    Colour(1062, "Vibrant Yellow", (0xEB, 0xD8, 0x00)),  # 2,258 parts
    Colour(334, "Chrome Gold", (0xBB, 0xA5, 0x3D)),  # 2,202 parts
    Colour(383, "Chrome Silver", (0xE0, 0xE0, 0xE0)),  # 1,336 parts
    Colour(351, "Medium Dark Pink", (0xF7, 0x85, 0xB1)),  # 1,093 parts
    Colour(22, "Purple", (0x81, 0x00, 0x7B)),  # 1,005 parts
    Colour(1147, "Blue Violet", (0xA3, 0xA9, 0xFF)),  # 856 parts
    Colour(1051, "Pastel Blue", (0x5A, 0xC4, 0xDA)),  # 734 parts
    Colour(1000, "Glow in Dark White", (0xD9, 0xD9, 0xD9)),  # 664 parts
    Colour(1089, "Warm Tan", (0xCC, 0xA3, 0x73)),  # 628 parts
    Colour(335, "Sand Red", (0xD6, 0x75, 0x72)),  # 603 parts
    Colour(74, "Medium Green", (0x73, 0xDC, 0xA1)),  # 572 parts
    Colour(148, "Pearl Dark Gray", (0x57, 0x58, 0x57)),  # 533 parts
    Colour(462, "Medium Orange", (0xFF, 0xA7, 0x0B)),  # 491 parts
    Colour(13, "Pink", (0xFC, 0x97, 0xAC)),  # 482 parts
    Colour(313, "Maersk Blue", (0x35, 0x92, 0xC3)),  # 469 parts
    Colour(1146, "Warm Pink", (0xF6, 0xB7, 0xBF)),  # 419 parts
    Colour(18, "Light Yellow", (0xFB, 0xE6, 0x96)),  # 340 parts
    Colour(118, "Aqua", (0xB3, 0xD7, 0xD1)),  # 322 parts
    Colour(151, "Very Light Bluish Gray", (0xE6, 0xE3, 0xE0)),  # 284 parts
    Colour(503, "Very Light Gray", (0xE6, 0xE3, 0xDA)),  # 261 parts
    Colour(132, "Speckle Black-Silver", (0x05, 0x13, 0x1D)),  # 246 parts
    Colour(79, "Milky White", (0xFF, 0xFF, 0xFF)),  # 239 parts
    Colour(1088, "Medium Brown", (0x75, 0x59, 0x45)),  # 225 parts
    Colour(21, "Glow In Dark Opaque", (0xD4, 0xD5, 0xC9)),  # 215 parts
    Colour(115, "Medium Lime", (0xC7, 0xD2, 0x3C)),  # 192 parts
    Colour(134, "Copper", (0xAE, 0x7A, 0x59)),  # 192 parts
    Colour(89, "Royal Blue", (0x4C, 0x61, 0xDB)),  # 191 parts
    Colour(110, "Violet", (0x43, 0x54, 0xA3)),  # 191 parts
    Colour(20, "Light Violet", (0xC9, 0xCA, 0xE2)),  # 186 parts
    Colour(12, "Salmon", (0xF2, 0x70, 0x5E)),  # 185 parts
    Colour(77, "Light Pink", (0xFE, 0xCC, 0xCF)),  # 184 parts
    Colour(100, "Light Salmon", (0xFE, 0xBA, 0xBD)),  # 180 parts
    Colour(137, "Pearl Sand Blue", (0x79, 0x88, 0xA1)),  # 172 parts
    Colour(366, "Earth Orange", (0xFA, 0x9C, 0x1C)),  # 170 parts
    Colour(86, "Light Brown", (0x7C, 0x50, 0x3A)),  # 168 parts
    Colour(17, "Light Green", (0xC2, 0xDA, 0xB8)),  # 166 parts
    Colour(11, "Light Turquoise", (0x55, 0xA5, 0xAF)),  # 164 parts
    Colour(178, "Flat Dark Gold", (0xB4, 0x84, 0x55)),  # 141 parts
    Colour(232, "Sky Blue", (0x7D, 0xBF, 0xDD)),  # 131 parts
    Colour(69, "Light Purple", (0xCD, 0x62, 0x98)),  # 102 parts
    Colour(1065, "Reddish Gold", (0xAC, 0x82, 0x47)),  # 79 parts
    Colour(373, "Sand Purple", (0x84, 0x5E, 0x84)),  # 73 parts
    Colour(1063, "Pearl Copper", (0xB4, 0x6A, 0x00)),  # 72 parts
    Colour(125, "Light Orange", (0xF9, 0xBA, 0x61)),  # 66 parts
    Colour(1137, "Sienna Brown", (0x91, 0x5C, 0x3C)),  # 64 parts
    Colour(112, "Medium Bluish Violet", (0x68, 0x74, 0xCA)),  # 62 parts
    Colour(450, "Fabuland Brown", (0xB6, 0x7B, 0x50)),  # 56 parts
    Colour(1135, "Metal", (0xA5, 0xAD, 0xB4)),  # 55 parts
    Colour(1092, "Metallic Copper", (0x76, 0x4D, 0x3B)),  # 52 parts
    Colour(1093, "Light Lilac", (0x91, 0x95, 0xCA)),  # 51 parts
    Colour(1007, "Reddish Lilac", (0x8E, 0x55, 0x97)),  # 50 parts
]


TRANSPARENT: list[Colour] = [
    Colour(47, "Trans-Clear", (0xFC, 0xFC, 0xFC)),  # 47,633 parts
    Colour(41, "Trans-Light Blue", (0xAE, 0xEF, 0xEC)),  # 33,101 parts
    Colour(36, "Trans-Red", (0xC9, 0x1A, 0x09)),  # 20,613 parts
    Colour(182, "Trans-Orange", (0xF0, 0x8F, 0x1C)),  # 15,943 parts
    Colour(46, "Trans-Yellow", (0xF5, 0xCD, 0x2F)),  # 13,366 parts
    Colour(33, "Trans-Dark Blue", (0x00, 0x20, 0xA0)),  # 10,704 parts
    Colour(40, "Trans-Brown", (0x63, 0x5F, 0x52)),  # 8,657 parts
    Colour(42, "Trans-Neon Green", (0xF8, 0xF1, 0x84)),  # 6,803 parts
    Colour(45, "Trans-Dark Pink", (0xDF, 0x66, 0x95)),  # 5,762 parts
    Colour(57, "Trans-Neon Orange", (0xFF, 0x80, 0x0D)),  # 5,612 parts
    Colour(34, "Trans-Green", (0x84, 0xB6, 0x8D)),  # 5,449 parts
    Colour(35, "Trans-Bright Green", (0xD9, 0xE4, 0xA7)),  # 3,737 parts
    Colour(52, "Trans-Purple", (0xA5, 0xA5, 0xCB)),  # 3,092 parts
    Colour(1053, "Opal Trans-Light Blue", (0x68, 0xBC, 0xC5)),  # 1,015 parts
    Colour(1055, "Opal Trans-Clear", (0xFC, 0xFC, 0xFC)),  # 988 parts
    Colour(1095, "Trans-Black", (0x63, 0x5F, 0x52)),  # 935 parts
    Colour(143, "Trans-Medium Blue", (0xCF, 0xE2, 0xF7)),  # 704 parts
    Colour(230, "Trans-Pink", (0xE4, 0xAD, 0xC8)),  # 434 parts
    Colour(1059, "Opal Trans-Purple", (0x83, 0x20, 0xB7)),  # 321 parts
    Colour(1094, "Trans-Medium Purple", (0x8D, 0x73, 0xB3)),  # 258 parts
    Colour(1054, "Opal Trans-Dark Pink", (0xCE, 0x1D, 0x9B)),  # 253 parts
    Colour(114, "Glitter Trans-Dark Pink", (0xDF, 0x66, 0x95)),  # 234 parts
    Colour(43, "Trans-Very Lt Blue", (0xC1, 0xDF, 0xF0)),  # 232 parts
    Colour(117, "Glitter Trans-Clear", (0xFF, 0xFF, 0xFF)),  # 230 parts
    Colour(1061, "Opal Trans-Dark Blue", (0x00, 0x20, 0xA0)),  # 216 parts
    Colour(1004, "Trans-Flame Yellowish Orange", (0xFC, 0xB7, 0x6D)),  # 214 parts
    Colour(54, "Trans-Neon Yellow", (0xDA, 0xB0, 0x00)),  # 187 parts
    Colour(1060, "Opal Trans-Bright Green", (0x84, 0xB6, 0x8D)),  # 182 parts
    Colour(129, "Glitter Trans-Purple", (0xA5, 0xA5, 0xCB)),  # 169 parts
    Colour(1056, "Opal Trans-Brown", (0x58, 0x39, 0x27)),  # 140 parts
    Colour(294, "Glow In Dark Trans", (0xBD, 0xC6, 0xAD)),  # 131 parts
    Colour(1057, "Trans-Light Bright Green", (0xC9, 0xE7, 0x88)),  # 119 parts
    Colour(1003, "Glitter Trans-Light Blue", (0x68, 0xBC, 0xC5)),  # 91 parts
    Colour(1006, "Trans-Light Royal Blue", (0xB4, 0xD4, 0xF7)),  # 90 parts
    Colour(236, "Trans-Light Purple", (0x96, 0x70, 0x9F)),  # 71 parts
]


# Rebrickable colour ID -> LDraw colour code, matched by RGB against the
# official LDConfig.ldr. Where the two catalogues agree the code is the
# ID; where they collide, or where the colour is Rebrickable-only, it is
# the nearest LDraw colour of the same transparency.
LDRAW_CODE: dict[int, int] = {
    0: 0,
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    10: 10,
    11: 11,
    12: 12,
    13: 13,
    14: 14,
    15: 15,
    17: 17,
    18: 18,
    19: 19,
    20: 20,
    21: 494,  # Glow In Dark Opaque -> LDraw 494
    22: 22,
    25: 25,
    26: 26,
    27: 27,
    28: 28,
    29: 29,
    30: 30,
    31: 31,
    33: 33,
    34: 34,
    35: 35,
    36: 36,
    40: 40,
    41: 43,  # Trans-Light Blue -> LDraw 43
    42: 42,
    43: 43,
    45: 45,
    46: 46,
    47: 47,
    52: 52,
    54: 54,
    57: 57,
    69: 10022,  # Light Purple -> LDraw 10022
    70: 70,
    71: 71,
    72: 72,
    73: 73,
    74: 74,
    77: 77,
    78: 78,
    79: 15,  # Milky White -> LDraw 15
    80: 80,
    82: 82,
    84: 84,
    85: 85,
    86: 86,
    89: 89,
    92: 92,
    100: 100,
    110: 110,
    112: 112,
    114: 114,
    115: 115,
    117: 117,
    118: 118,
    125: 125,
    129: 129,
    132: 132,
    134: 134,
    135: 135,
    137: 137,
    143: 41,  # Trans-Medium Blue -> LDraw 41
    148: 148,
    151: 151,
    158: 326,  # Yellowish Green -> LDraw 326
    178: 178,
    179: 179,
    182: 57,  # Trans-Orange -> LDraw 57
    191: 191,
    212: 212,
    226: 226,
    230: 45,  # Trans-Pink -> LDraw 45
    232: 232,
    236: 44,  # Trans-Light Purple -> LDraw 44
    272: 272,
    288: 288,
    294: 294,
    297: 297,
    308: 308,
    313: 313,
    320: 320,
    321: 321,
    322: 322,
    323: 323,
    326: 330,  # Olive Green -> LDraw 330
    334: 334,
    335: 335,
    351: 351,
    366: 366,
    373: 373,
    378: 378,
    379: 379,
    383: 383,
    450: 450,
    462: 462,
    484: 484,
    503: 503,
    1000: 494,  # Glow in Dark White -> LDraw 494
    1003: 302,  # Glitter Trans-Light Blue -> LDraw 302
    1004: 231,  # Trans-Flame Yellowish Orange -> LDraw 231
    1006: 39,  # Trans-Light Royal Blue -> LDraw 39
    1007: 218,  # Reddish Lilac -> LDraw 218
    1050: 353,  # Coral -> LDraw 353
    1051: 322,  # Pastel Blue -> LDraw 322
    1053: 362,  # Opal Trans-Light Blue -> LDraw 362
    1054: 364,  # Opal Trans-Dark Pink -> LDraw 364
    1055: 360,  # Opal Trans-Clear -> LDraw 360
    1056: 10375,  # Opal Trans-Brown -> LDraw 10375
    1057: 227,  # Trans-Light Bright Green -> LDraw 227
    1059: 365,  # Opal Trans-Purple -> LDraw 365
    1060: 367,  # Opal Trans-Bright Green -> LDraw 367
    1061: 10366,  # Opal Trans-Dark Blue -> LDraw 10366
    1062: 14,  # Vibrant Yellow -> LDraw 14
    1063: 402,  # Pearl Copper -> LDraw 402
    1065: 189,  # Reddish Gold -> LDraw 189
    1088: 370,  # Medium Brown -> LDraw 370
    1089: 371,  # Warm Tan -> LDraw 371
    1092: 300,  # Metallic Copper -> LDraw 300
    1093: 220,  # Light Lilac -> LDraw 220
    1094: 44,  # Trans-Medium Purple -> LDraw 44
    1095: 10375,  # Trans-Black -> LDraw 10375
    1103: 316,  # Pearl Titanium -> LDraw 316
    1135: 296,  # Metal -> LDraw 296
    1136: 402,  # Reddish Orange -> LDraw 402
    1137: 422,  # Sienna Brown -> LDraw 422
    1146: 430,  # Warm Pink -> LDraw 430
    1147: 89,  # Blue Violet -> LDraw 89
}
