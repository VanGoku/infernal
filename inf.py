#!/usr/bin/env python3
"""
Infernal Lexicon — v0.1
Deterministic fantasy-language word renderer for a D&D campaign.

This is a flavor cipher, NOT cryptographic encryption. It preserves punctuation
and whitespace, and maps the same normalized word to the same infernal word.
The output is intentionally not reversible in this first version.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import json
from pathlib import Path
from dataclasses import dataclass


# Fixed 29-letter writing system: deliberately neither English (26) nor Russian
# (33). The renderer only emits these Latin letters.
ALPHABET = "abcdefghijklmnopqrstuvxyzæøþ"
VOWELS = "aeiouyø"
CONSONANTS = "".join(ch for ch in ALPHABET if ch not in VOWELS)

# Onsets, nuclei and codas are chosen to produce repeatable, pronounceable forms.
# ONSETS = (
#     "", "v", "z", "th", "kh", "gr", "dr", "vr", "sh", "zh",
#     "kr", "sk", "m", "n", "r", "l", "d", "g", "x",
# )

ONSETS = (
    "", "", "v", "z", "th", "kh", "gr", "dr",
    "vr", "sh", "zh", "kr", "sk", "m", "n", "r",
)

# NUCLEI = ("a", "e", "i", "o", "u", "y", "ae", "ia", "oi", "ou", "ø")

NUCLEI = ("a", "e", "i", "o", "u", "y", "ae", "ia")

# CODAS = ("", "", "n", "r", "s", "th", "k", "x", "m", "z", "sh")

CODAS = ("", "", "", "n", "r", "s", "k", "x", "th")

# A token is a run of letters, including Russian letters and ё.
WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d\_]+)*", re.UNICODE)


@dataclass(frozen=True)
class InfernalLexicon:
    """Stable word-to-word renderer with a configurable campaign seed."""

    seed: str = "infernal-lexicon-v1"
    DICTIONARY_FILE = Path("dictionary.json")

    def _digest(self, word: str) -> bytes:
        payload = (self.seed + "\0" + word.casefold()).encode("utf-8")
        return hashlib.blake2b(payload, digest_size=32).digest()

    @staticmethod
    def _number(data: bytes, offset: int, modulo: int) -> int:
        # Read two bytes at a time for a little more variety than one-byte picks.
        pos = offset % (len(data) - 1)
        return int.from_bytes(data[pos:pos + 2], "big") % modulo

    def encode_word(self, word: str) -> str:
        """Return one stable, language-like infernal token for a source word."""

        if not word or not any(ch.isalpha() for ch in word):
            return word

        normalized = word.casefold()
        dictionary = self._load_dictionary()

        if normalized in dictionary:
            return dictionary[normalized]

        digest = self._digest(word)

        syllables = 1 + digest[0] % 2

        parts: list[str] = []

        for i in range(syllables):
            base = (i * 5 + 1) % (len(digest) - 2)

            onset = ONSETS[self._number(digest, base, len(ONSETS))]
            nucleus = NUCLEI[self._number(digest, base + 2, len(NUCLEI))]
            coda = CODAS[self._number(digest, base + 4, len(CODAS))]

            parts.append(onset + nucleus + coda)

        result = "".join(parts)

        endings = ("", "", "a", "ir", "eth", "um")
        result += endings[digest[7] % len(endings)]

        result = result or "az"

        if result[0] in VOWELS:
            result = "v" + result

        self._save_word(normalized, result)

        return result

    def encode(self, text: str) -> str:
        """Transform words while leaving punctuation, digits and spacing intact."""
        return WORD_RE.sub(lambda match: self._match_case(
            match.group(0), self.encode_word(match.group(0))
        ), text)

    @staticmethod
    def _match_case(source: str, result: str) -> str:
        if source.isupper():
            return result.upper()
        if source[:1].isupper():
            return result[:1].upper() + result[1:]
        return result

    def _load_dictionary(self) -> dict[str, str]:
        if not self.DICTIONARY_FILE.exists():
            return {}

        with self.DICTIONARY_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save_word(self, source: str, translated: str) -> None:
        dictionary = self._load_dictionary()
        dictionary[source.casefold()] = translated

        with self.DICTIONARY_FILE.open("w", encoding="utf-8") as file:
            json.dump(
                dictionary,
                file,
                ensure_ascii=False,
                indent=2
            )

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render Russian or other text as the Infernal Lexicon."
    )
    parser.add_argument("text", nargs="?", help="Text to transform")
    parser.add_argument("--seed", default="infernal-lexicon-v1",
                        help="Campaign seed; same seed gives stable output")
    args = parser.parse_args()

    lexicon = InfernalLexicon(seed=args.seed)
    if args.text is not None:
        print(lexicon.encode(args.text))
    else:
        print("Infernal Lexicon v0.1 — enter text; Ctrl+C to exit.")
        try:
            while True:
                line = input("> ")
                print(lexicon.encode(line))
        except (EOFError, KeyboardInterrupt):
            print()


def test():
    from collections import defaultdict
    import json

    with open("russian.txt", "r", encoding="cp1251") as file:
        words = [line.strip() for line in file if line.strip()]

    dictionary = defaultdict(list)
    lexicon = InfernalLexicon(seed="infernal-lexicon-v1")

    for word in words:
        dictionary[lexicon.encode(word)].append(word)   #type: ignore

    with open("dictionary.json", "w", encoding="utf-8") as file:
        json.dump(
            dict(dictionary),
            file,
            ensure_ascii=False,
            indent=2
        )

        print(f"Уникальных результатов: {len(dictionary)}")


if __name__ == "__main__":
    main()