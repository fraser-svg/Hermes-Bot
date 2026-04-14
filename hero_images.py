"""Industry-relevant hero + about photo resolver.

Maps a business_category (plus keyword fallbacks) to a deterministic Unsplash
photo pair. Shared by generate.py (Gemini pipeline) and
_workspace/template/fill_template.py (static template pipeline) so every site
gets an on-industry hero image — no Gemini guesswork, no generic fallback.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HeroPhotos:
    hero: str
    about: str
    matched_category: str


_W_HERO = "w=1600&h=1000&fit=crop&auto=format&q=80"
_W_ABOUT = "w=800&h=600&fit=crop&auto=format&q=80"


def _u(photo_id: str, params: str = _W_HERO) -> str:
    return f"https://images.unsplash.com/{photo_id}?{params}"


# Canonical category -> (hero_id, about_id). One source of truth.
_CATEGORY_PHOTOS: dict[str, tuple[str, str]] = {
    "electrician":       ("photo-1558618666-fcd25c85f82e", "photo-1504328345606-18bbc8c9d7d1"),
    "plumber":           ("photo-1585704032915-c3400ca199e7", "photo-1581578731548-c64695cc6952"),
    "roofer":            ("photo-1632935190508-bdddba1b30b5", "photo-1574359411659-15573a27fd0c"),
    "builder":           ("photo-1504307651254-35680f356dfd", "photo-1574359411659-15573a27fd0c"),
    "hvac":              ("photo-1621905252472-e8de8f80d2a9", "photo-1581094794329-c8112a89af12"),
    "cleaner":           ("photo-1581578731548-c64695cc6952", "photo-1527515637462-cff94eecc1ac"),
    "painter":           ("photo-1562259949-e8e7689d7828", "photo-1589939705384-5185137a7f0f"),
    "locksmith":         ("photo-1555624399-5b4fbd20fa9d", "photo-1558002038-1055907df827"),
    "mover":             ("photo-1600518464441-9154a4dea21b", "photo-1587582423116-ec07293f0395"),
    "pest control":      ("photo-1604014237800-1c9102c219da", "photo-1587582423116-ec07293f0395"),
    "landscaper":        ("photo-1558904541-efa843a96f01", "photo-1416879595882-3373a0480b5b"),
    "gardener":          ("photo-1558904541-efa843a96f01", "photo-1416879595882-3373a0480b5b"),
    "mechanic":          ("photo-1487754180451-c456f719a1fc", "photo-1619642751034-765dfdf7c58e"),
    "accountant":        ("photo-1554224155-6726b3ff858f", "photo-1560472355-536de3962603"),
    "bookkeeper":        ("photo-1554224155-6726b3ff858f", "photo-1560472355-536de3962603"),
    "financial adviser": ("photo-1554224155-6726b3ff858f", "photo-1560472355-536de3962603"),
    "lawyer":            ("photo-1589829545856-d10d557cf95f", "photo-1556157382-97eda2d62296"),
    "solicitor":         ("photo-1589829545856-d10d557cf95f", "photo-1556157382-97eda2d62296"),
    "dentist":           ("photo-1629909613654-28e377c37b09", "photo-1612349317150-e413f6a5b16d"),
    "doctor":            ("photo-1576091160550-2173dba999ef", "photo-1612349317150-e413f6a5b16d"),
    "physio":            ("photo-1588776814546-1ffcf47267a5", "photo-1571019614242-c5c5dee9f50b"),
    "vet":               ("photo-1548199973-03cce0bbc87b", "photo-1587300003388-59208cc962cb"),
    "hairdresser":       ("photo-1560066984-138dadb4c035", "photo-1522337360788-8b13dee7a37e"),
    "barber":            ("photo-1585747860715-2ba37e788b70", "photo-1503951914875-452162b0f3f1"),
    "beauty":            ("photo-1560066984-138dadb4c035", "photo-1522337360788-8b13dee7a37e"),
    "personal trainer":  ("photo-1517836357463-d25dfeac3438", "photo-1571019613454-1cb2f99b2d8b"),
    "therapist":         ("photo-1573497491765-dccce02b29df", "photo-1573497491208-6b1acb260507"),
    "tutor":             ("photo-1580582932707-520aed937b7b", "photo-1522202176988-66273c2fd55f"),
    "photographer":      ("photo-1452587925148-ce544e77e70d", "photo-1554048612-b6a482bc67e5"),
    "restaurant":        ("photo-1517248135467-4c7edcad34c4", "photo-1556910103-1c02745aae4d"),
    "cafe":              ("photo-1559305616-3f99cd43e353", "photo-1556910103-1c02745aae4d"),
    "caterer":           ("photo-1555244162-803834f70033", "photo-1556910103-1c02745aae4d"),
    "it":                ("photo-1518770660439-4636190af475", "photo-1573164713714-d95e436ab8d6"),
    "web":               ("photo-1498050108023-c5249f4df085", "photo-1573164713714-d95e436ab8d6"),
}

# Keyword routing for unlisted categories. Ordered — first match wins.
_KEYWORD_ROUTES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("electric", "electrical"), "electrician"),
    (("plumb",), "plumber"),
    (("roof",), "roofer"),
    (("build", "construction", "renovat", "carpent", "joiner"), "builder"),
    (("hvac", "heating", "boiler", "air con", "aircon", "ac repair"), "hvac"),
    (("clean", "housekeep"), "cleaner"),
    (("paint", "decorat"), "painter"),
    (("locksmith", "lock"), "locksmith"),
    (("remov", "mover", "moving"), "mover"),
    (("pest", "exterm"), "pest control"),
    (("landscape", "garden", "lawn", "tree"), "landscaper"),
    (("mechanic", "garage", "mot", "auto repair", "car repair"), "mechanic"),
    (("accountant", "book-keep", "bookkeep", "tax", "payroll"), "accountant"),
    (("ifa", "financial", "wealth", "adviser", "advisor"), "financial adviser"),
    (("solicitor", "lawyer", "law", "barrister", "legal"), "lawyer"),
    (("dentist", "dental", "ortho"), "dentist"),
    (("gp", "doctor", "clinic", "medical", "surgery"), "doctor"),
    (("physio", "chiro", "osteopath"), "physio"),
    (("vet", "animal", "pet"), "vet"),
    (("hair", "salon", "stylist"), "hairdresser"),
    (("barber",), "barber"),
    (("beauty", "nail", "spa", "aesthetic", "lash", "brow"), "beauty"),
    (("trainer", "coach", "fitness", "gym"), "personal trainer"),
    (("therap", "counsel", "psycholog"), "therapist"),
    (("tutor", "teach", "education"), "tutor"),
    (("photograph", "videograph"), "photographer"),
    (("restaurant", "bistro", "eatery"), "restaurant"),
    (("cafe", "coffee"), "cafe"),
    (("cater",), "caterer"),
    (("web develop", "web design", "digital agency", "software"), "web"),
    (("it ", "tech support", "managed service", "msp"), "it"),
)

# Universal last-resort. Architectural workspace photo, not a stock handshake.
_FALLBACK = ("photo-1497366216548-37526070297c", "photo-1556157382-97eda2d62296")


def resolve(business_category: str | None) -> HeroPhotos:
    """Resolve category → HeroPhotos. Never returns None.

    Match order: exact → keyword route → fallback. Case-insensitive.
    """
    key = (business_category or "").strip().lower()

    if key in _CATEGORY_PHOTOS:
        hero_id, about_id = _CATEGORY_PHOTOS[key]
        return HeroPhotos(_u(hero_id), _u(about_id, _W_ABOUT), key)

    for needles, target in _KEYWORD_ROUTES:
        if any(n in key for n in needles):
            hero_id, about_id = _CATEGORY_PHOTOS[target]
            return HeroPhotos(_u(hero_id), _u(about_id, _W_ABOUT), target)

    hero_id, about_id = _FALLBACK
    return HeroPhotos(_u(hero_id), _u(about_id, _W_ABOUT), "generic")


def resolve_urls(business_category: str | None) -> tuple[str, str]:
    """Convenience: returns (hero_url, about_url)."""
    photos = resolve(business_category)
    return photos.hero, photos.about
