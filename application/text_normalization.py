"""Small, deterministic Vietnamese-to-English catalog vocabulary (not machine translation)."""

import re
import unicodedata


ALIASES = {
    "giay chay bo": "running shoes", "giay the thao": "shoes",
    "giay di bo": "walking shoes", "giay vai": "canvas shoes",
    "ao phong": "shirt", "ao thun": "shirt", "ao so mi": "shirt",
    "binh nuoc": "water bottle", "chai nuoc": "water bottle",
    "binh giu nhiet": "insulated bottle", "tui vai": "tote",
    "tui xach": "bags", "ba lo": "backpack", "balo": "backpack",
    "xanh duong": "blue", "xanh nuoc bien": "blue", "xanh da troi": "blue",
    "xanh la cay": "green", "xanh la": "green", "do": "red",
    "den": "black", "trang": "white", "giay": "shoes", "ao": "shirt",
    "tui": "bags", "binh": "bottle", "chay bo": "running",
    "di bo": "walking", "leo nui": "hiking", "quan ao": "clothing",
    "tim cho toi": "", "cho toi xem": "", "toi muon tim": "",
    "toi muon": "", "tim kiem": "", "san pham": "", "mau": "", "tim": "",
}
_PATTERN = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in sorted(ALIASES, key=len, reverse=True)) + r")\b")


def normalize_search_text(text: str) -> str:
    normalized = " ".join(text.lower().split())
    folded = "".join(c for c in unicodedata.normalize("NFD", normalized.replace("đ", "d"))
                     if unicodedata.category(c) != "Mn")
    return " ".join(_PATTERN.sub(lambda match: ALIASES[match.group()], folded).split())
