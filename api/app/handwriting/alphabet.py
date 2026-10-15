"""Character set used by the sjvasquez Graves checkpoint.

Uppercase Q, X and Z are not in the trained alphabet. They are mapped to the
lowercase letters, which the model did see. Unknown marks become a space.
Digits are kept as characters, so leading zeros survive.
"""
from __future__ import annotations

ALPHABET = [
    "\x00", " ", "!", '"', "#", "'", "(", ")", ",", "-", ".",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ":", ";",
    "?", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K",
    "L", "M", "N", "O", "P", "R", "S", "T", "U", "V", "W", "Y",
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l",
    "m", "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x",
    "y", "z",
]
ALPHA_TO_INDEX = {char: index for index, char in enumerate(ALPHABET)}
_FALLBACK = {
    "Q": "q", "X": "x", "Z": "z",
    "q": "q", "x": "x", "z": "z",
    "\n": " ", "\t": " ",
    "/": "-", "+": "-", "=": "-", "_": "-",
    "@": "a", "&": "a",
}


def encode(text: str) -> list[int]:
    indexes = []
    for char in text:
        mapped = char
        if mapped not in ALPHA_TO_INDEX:
            mapped = _FALLBACK.get(mapped, mapped.lower() if mapped.isalpha() else " ")
        indexes.append(ALPHA_TO_INDEX.get(mapped, ALPHA_TO_INDEX[" "]))
    indexes.append(0)
    return indexes
