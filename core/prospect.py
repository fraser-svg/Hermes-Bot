"""Hermes Prospector - Find businesses without websites via Google Maps.

Searches Google Places for a business category in a location,
filters for businesses with no website, extracts their details,
and saves them ready for website generation.

Usage:
    python3 prospect.py "electrician" "Edinburgh"
    python3 prospect.py "plumber" "Glasgow" --build-first
    python3 prospect.py "roofer" "Inverness" --limit 20

Requires GOOGLE_API_KEY in .env
"""

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError

BASE_DIR = Path(__file__).resolve().parent
DETAILS_PATH = BASE_DIR / "references" / "business_details.json"
PROSPECTS_DIR = BASE_DIR / "prospects"

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAILS_URL = "https://places.googleapis.com/v1/places"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def get_google_key() -> str:
    key = (
        os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("GOOGLE_MAPS_API")
        or load_env().get("GOOGLE_API_KEY")
        or load_env().get("GOOGLE_MAPS_API")
    )
    if not key:
        raise RuntimeError(
            "No Google API key found.\n"
            "Add GOOGLE_MAPS_API=your_key to .env\n"
            "Get one at: https://console.cloud.google.com/apis/credentials\n"
            "Enable 'Places API (New)' in your Google Cloud project."
        )
    return key


def search_places(category: str, location: str, api_key: str, limit: int = 20) -> list[dict]:
    """Search Google Places for businesses in a category and location.

    DO NOT MODIFY THIS FUNCTION. DO NOT REPLACE WITH DUMMY DATA.
    If the API fails, fix the API key or enable Places API (New) in Google Cloud.
    """
    query = f"{category} in {location}"
    print(f"Searching Google Maps: \"{query}\"")

    payload = json.dumps({
        "textQuery": query,
        "maxResultCount": min(limit, 20),
        "languageCode": "en",
    }).encode("utf-8")

    # Request fields we need - only pay for what we use
    field_mask = (
        "places.id,"
        "places.displayName,"
        "places.formattedAddress,"
        "places.nationalPhoneNumber,"
        "places.internationalPhoneNumber,"
        "places.websiteUri,"
        "places.googleMapsUri,"
        "places.rating,"
        "places.userRatingCount,"
        "places.reviews,"
        "places.primaryType,"
        "places.primaryTypeDisplayName,"
        "places.businessStatus"
    )

    req = Request(
        PLACES_TEXT_SEARCH_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": field_mask,
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"Google Places API error {e.code}: {error_body}") from e

    return body.get("places", [])


def extract_reviews(place: dict) -> list[dict]:
    """Extract review text and ratings from a place."""
    reviews = []
    for r in place.get("reviews", [])[:5]:
        text = r.get("text", {}).get("text", "")
        rating = r.get("rating", 5)
        if text:
            reviews.append({"rating": rating, "text": text})
    return reviews


def place_to_business_details(place: dict, category: str, city: str) -> dict:
    """Convert a Google Places result into our business_details.json format."""
    name = place.get("displayName", {}).get("text", "Unknown Business")
    phone = place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber", "")
    address = place.get("formattedAddress", city)
    rating = place.get("rating", 0)
    review_count = place.get("userRatingCount", 0)
    reviews = extract_reviews(place)
    maps_url = place.get("googleMapsUri", "")

    # Infer services from category. Covers trades + professional services.
    # Any unlisted category gets a sensible generic set - Gemini will
    # generate proper service descriptions from whatever is provided.
    service_map = {
        # Trades
        "electrician": ["Electrical repairs", "Installations", "Rewiring", "Emergency callouts", "Lighting", "Fuse board upgrades"],
        "plumber": ["Emergency repairs", "Boiler installation", "Bathroom fitting", "Leak detection", "Drain unblocking", "Radiator installation"],
        "roofer": ["Roof repairs", "Full re-roofing", "Chimney repairs", "Flat roofing", "Guttering", "Storm damage repair"],
        "hvac": ["Boiler servicing", "Central heating installation", "Air conditioning", "Underfloor heating", "Radiator fitting", "Emergency heating repair"],
        "cleaner": ["Domestic cleaning", "Deep cleaning", "End of tenancy cleaning", "Office cleaning", "Carpet cleaning", "Window cleaning"],
        "painter": ["Interior painting", "Exterior painting", "Wallpapering", "Wood staining", "Commercial painting", "Decorating"],
        "locksmith": ["Emergency lockouts", "Lock replacement", "Key cutting", "UPVC lock repair", "Security upgrades", "Safe opening"],
        "mover": ["House removals", "Office removals", "Packing services", "Storage solutions", "Man and van", "Piano moving"],
        "pest control": ["Rat removal", "Mouse control", "Wasp nest removal", "Bed bug treatment", "Ant control", "Bird proofing"],
        "landscaper": ["Garden design", "Lawn care", "Tree surgery", "Fencing", "Patio laying", "Hedge trimming"],
        "builder": ["Extensions", "Renovations", "New builds", "Conversions", "Structural work", "Project management"],
        "carpenter": ["Bespoke joinery", "Kitchen fitting", "Door hanging", "Flooring", "Staircase building", "Timber framing"],
        "tiler": ["Bathroom tiling", "Kitchen splashbacks", "Floor tiling", "Mosaic work", "Re-grouting", "Wet room installation"],
        "plasterer": ["Plastering", "Rendering", "Skimming", "Coving", "Artex removal", "Damp proofing"],
        "glazier": ["Double glazing", "Window repairs", "Glass replacement", "Conservatories", "Mirrors", "Shopfront glazing"],
        "garage door": ["Garage door installation", "Repairs", "Automation", "Roller doors", "Sectional doors", "Maintenance"],
        # Professional services
        "lawyer": ["Family law", "Conveyancing", "Wills & probate", "Employment law", "Personal injury", "Commercial law"],
        "solicitor": ["Family law", "Conveyancing", "Wills & probate", "Employment law", "Personal injury", "Commercial law"],
        "accountant": ["Tax returns", "Bookkeeping", "Payroll", "VAT returns", "Company accounts", "Business advisory"],
        "dentist": ["Check-ups & cleaning", "Fillings & crowns", "Teeth whitening", "Implants", "Orthodontics", "Emergency dental care"],
        "physiotherapist": ["Sports injuries", "Back & neck pain", "Post-surgery rehab", "Joint mobilisation", "Massage therapy", "Exercise programmes"],
        "chiropractor": ["Spinal adjustments", "Back pain treatment", "Neck pain relief", "Sports injuries", "Posture correction", "Sciatica treatment"],
        "optician": ["Eye tests", "Glasses fitting", "Contact lenses", "Children's eye care", "Eye health screening", "Designer frames"],
        "veterinarian": ["Consultations", "Vaccinations", "Surgery", "Dental care", "Emergency treatment", "Pet health plans"],
        "vet": ["Consultations", "Vaccinations", "Surgery", "Dental care", "Emergency treatment", "Pet health plans"],
        "tutor": ["Maths tutoring", "English tutoring", "Science tutoring", "Exam preparation", "11+ preparation", "Online sessions"],
        "driving instructor": ["Beginner lessons", "Intensive courses", "Motorway lessons", "Test preparation", "Refresher courses", "Automatic lessons"],
        "photographer": ["Wedding photography", "Portrait sessions", "Event coverage", "Commercial shoots", "Family photography", "Headshots"],
        "personal trainer": ["1-to-1 training", "Online coaching", "Weight loss programmes", "Strength training", "Nutrition planning", "Group sessions"],
        "beauty salon": ["Facials", "Manicures & pedicures", "Waxing", "Lash extensions", "Skin treatments", "Bridal packages"],
        "hairdresser": ["Cuts & styling", "Colouring", "Highlights", "Bridal hair", "Hair treatments", "Men's grooming"],
        "barber": ["Haircuts", "Beard trims", "Hot towel shaves", "Skin fades", "Hair styling", "Walk-ins welcome"],
        "dog groomer": ["Full groom", "Puppy groom", "Bath & dry", "Nail trimming", "De-shedding", "Breed-specific styling"],
        "caterer": ["Wedding catering", "Corporate events", "Private dining", "Buffets", "Canapes", "Dietary accommodations"],
        "florist": ["Wedding flowers", "Funeral tributes", "Bouquets & arrangements", "Event flowers", "Subscriptions", "Same-day delivery"],
        "mechanic": ["MOT testing", "Full servicing", "Brake repairs", "Diagnostics", "Tyre fitting", "Clutch replacement"],
        "car wash": ["Exterior wash", "Full valet", "Interior cleaning", "Wax & polish", "Engine bay clean", "Ceramic coating"],
        "tailor": ["Suit alterations", "Dress alterations", "Bespoke tailoring", "Wedding attire", "Curtain making", "Repairs"],
        "estate agent": ["Property sales", "Lettings", "Property management", "Valuations", "Mortgage advice", "New developments"],
        "architect": ["Residential design", "Planning applications", "Extensions", "Conversions", "Interior design", "Project management"],
        "surveyor": ["Building surveys", "Homebuyer reports", "Valuations", "Party wall surveys", "Drone surveys", "Defect analysis"],
        "financial advisor": ["Retirement planning", "Investment advice", "Mortgage advice", "Life insurance", "Tax planning", "Inheritance planning"],
        "insurance broker": ["Home insurance", "Business insurance", "Motor insurance", "Life cover", "Liability insurance", "Claims support"],
        "it support": ["Computer repair", "Network setup", "Cybersecurity", "Cloud services", "Data recovery", "Managed IT"],
        "web designer": ["Website design", "E-commerce", "SEO", "Hosting", "Maintenance", "Branding"],
        "marketing agency": ["Social media management", "Google Ads", "SEO", "Brand strategy", "Content creation", "Email marketing"],
        "printing": ["Business cards", "Flyers & leaflets", "Banners & signage", "Brochures", "Large format printing", "Custom merchandise"],
    }
    services = service_map.get(category.lower(), [
        f"{category.title()} consultations",
        f"{category.title()} services",
        f"Emergency {category.lower()} support",
        "Free initial assessment",
        "Ongoing support & maintenance",
        "Specialist referrals",
    ])

    return {
        "business_name": name,
        "business_category": category.lower(),
        "city": city,
        "address": address,
        "phone_number": phone,
        "services_offered": services,
        "google_reviews": reviews,
        "rating": rating,
        "review_count": review_count,
        "google_maps_url": maps_url,
        "_source": "google_maps_prospector",
    }


def prospect(category: str, location: str, limit: int = 20) -> list[dict]:
    """Find businesses without websites. Returns list of prospects."""
    api_key = get_google_key()
    places = search_places(category, location, api_key, limit)

    print(f"Found {len(places)} businesses total.\n")

    with_website = []
    without_website = []

    for place in places:
        name = place.get("displayName", {}).get("text", "?")
        website = place.get("websiteUri", "")
        status = place.get("businessStatus", "")
        rating = place.get("rating", 0)
        review_count = place.get("userRatingCount", 0)

        if status == "CLOSED_PERMANENTLY":
            continue

        if website:
            with_website.append(name)
        else:
            without_website.append(
                place_to_business_details(place, category, location)
            )

    print(f"With website ({len(with_website)}): not prospects")
    for name in with_website[:5]:
        print(f"  - {name}")
    if len(with_website) > 5:
        print(f"  ... and {len(with_website) - 5} more")

    print(f"\nNO WEBSITE ({len(without_website)}): PROSPECTS")
    for i, biz in enumerate(without_website):
        stars = f"{biz['rating']}/5" if biz['rating'] else "no rating"
        reviews = f"{biz['review_count']} reviews" if biz['review_count'] else "no reviews"
        phone = biz['phone_number'] or "no phone"
        print(f"  [{i+1}] {biz['business_name']}")
        print(f"      {stars} | {reviews} | {phone}")
        print(f"      {biz['address']}")
        if biz.get('google_maps_url'):
            print(f"      {biz['google_maps_url']}")
        print()

    return without_website


def save_prospects(prospects: list[dict], category: str, location: str):
    """Save all prospects to a JSON file."""
    PROSPECTS_DIR.mkdir(exist_ok=True)
    slug = f"{category.lower()}-{location.lower().replace(' ', '-')}"
    path = PROSPECTS_DIR / f"{slug}.json"
    path.write_text(json.dumps(prospects, indent=2))
    print(f"Saved {len(prospects)} prospects to {path}")
    return path


def select_and_build(prospects: list[dict], index: int = 0):
    """Select a prospect and save as business_details.json for building."""
    if not prospects:
        print("No prospects found.")
        return

    if index < 0 or index >= len(prospects):
        print(f"Invalid index. Choose 1-{len(prospects)}")
        return

    chosen = prospects[index]
    DETAILS_PATH.parent.mkdir(exist_ok=True)
    DETAILS_PATH.write_text(json.dumps(chosen, indent=2))
    print(f"\nSaved {chosen['business_name']} to {DETAILS_PATH}")
    print(f"Run 'python3 hermes.py --auto' to build their website.")


def main():
    args = sys.argv[1:]

    if len(args) < 2:
        print("Usage: python3 prospect.py <category> <location> [--limit N] [--build-first]")
        print()
        print("Examples:")
        print('  python3 prospect.py "electrician" "Edinburgh"')
        print('  python3 prospect.py "plumber" "Glasgow" --limit 20')
        print('  python3 prospect.py "roofer" "Inverness" --build-first')
        print()
        print("Categories: electrician, plumber, roofer, hvac, cleaner,")
        print("            painter, locksmith, mover, pest control, landscaper")
        sys.exit(1)

    category = args[0]
    location = args[1]
    limit = 20
    build_first = False

    i = 2
    while i < len(args):
        if args[i] == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
            i += 2
        elif args[i] == "--build-first":
            build_first = True
            i += 1
        else:
            i += 1

    print("=" * 50)
    print("  HERMES PROSPECTOR")
    print(f"  Finding {category}s in {location} without a website")
    print("=" * 50)
    print()

    prospects = prospect(category, location, limit)
    if not prospects:
        print("No prospects found. Every business in this search has a website.")
        sys.exit(0)

    save_prospects(prospects, category, location)

    if build_first:
        select_and_build(prospects, 0)
        print("\nBuilding website...")
        import subprocess
        subprocess.run([sys.executable, str(BASE_DIR / "hermes.py"), "--auto"], cwd=str(BASE_DIR))
    else:
        print("\nTo build a website for a prospect:")
        print(f"  python3 prospect.py \"{category}\" \"{location}\" --build-first")
        print("  OR select one manually:")
        try:
            choice = input("\nPick a number (or Enter to skip): ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                select_and_build(prospects, idx)
        except (EOFError, KeyboardInterrupt):
            print()


if __name__ == "__main__":
    main()
