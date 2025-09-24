#!/usr/bin/env python3
"""
Generate city/type partner CSVs with the OpenAI API.

FEATURES:
- Default 41 cities worldwide (no cities file required)
- Resume capability: skips existing files
- Merge functionality: combines all CSVs with deduplication
- 100 contacts per city/type (600 per city total)
- Enhanced prompts for better contact quality

INPUTS:
- cities file: JSON array (optional - uses default cities if not provided)
- OpenAI API key via environment variable

OUTPUTS:
- ./out/<city_id>/<type>/contacts.csv
  header: name,email,country,language,city,instagram,phone,organization,type,notes

AUTH:
- export OPENAI_API_KEY=your_key_here

USAGE:
# Use default cities (41 cities worldwide)
python3 populate.py

# Custom cities file
python3 populate.py --cities cities.json

# Merge existing files
python3 populate.py --merge

# Custom settings
python3 populate.py --per-type 150 --delay 1.0
"""

import argparse, json, os, re, time, csv, sys
from typing import Dict, List, Tuple
from openai import OpenAI

PARTNER_TYPES = ["influencer", "podcaster", "journalist", "activist", "ngo", "other"]

# Default cities list
DEFAULT_CITIES = [
    "new_york_usa", "los_angeles_usa", "mexico_city_mexico", "sao_paulo_brazil", "buenos_aires_argentina",
    "london_england", "paris_france", "berlin_germany", "madrid_spain", "rome_italy",
    "moscow_russia", "istanbul_turkey", "cairo_egypt", "johannesburg_south_africa", "nairobi_kenya",
    "lagos_nigeria", "kinshasa_democratic_republic_of_the_congo", "dubai_united_arab_emirates",
    "mumbai_india", "delhi_india", "bangalore_india", "jakarta_indonesia", "bangkok_thailand",
    "manila_philippines", "tokyo_japan", "seoul_south_korea", "beijing_china", "shanghai_china",
    "hong_kong_china", "sydney_australia", "melbourne_australia", "toronto_canada", "vancouver_canada",
    "chicago_usa", "san_francisco_usa", "lima_peru", "bogota_colombia", "santiago_chile",
    "tehran_iran", "karachi_pakistan"
]

# Map the countries in your file -> ISO-3
ISO3 = {
    "usa":"USA","canada":"CAN","mexico":"MEX","brazil":"BRA","argentina":"ARG","peru":"PER","colombia":"COL","chile":"CHL",
    "england":"GBR","france":"FRA","germany":"DEU","spain":"ESP","italy":"ITA","russia":"RUS","turkey":"TUR",
    "egypt":"EGY","south_africa":"ZAF","kenya":"KEN","nigeria":"NGA","democratic_republic_of_the_congo":"COD",
    "united_arab_emirates":"ARE","iran":"IRN","pakistan":"PAK","india":"IND","indonesia":"IDN","thailand":"THA",
    "philippines":"PHL","japan":"JPN","south_korea":"KOR","china":"CHN","australia":"AUS"
}

# Normalize 2-letter languages from your JSON
LANG_MAP = {
    "en":"en","es":"es","pt":"pt","fr":"fr","de":"de","it":"it","ru":"ru","tr":"tr","ar":"ar","sw":"sw",
    "hi":"hi","id":"id","th":"th","ja":"ja","ko":"ko","zh":"zh","ph":"tl","fa":"fa","ur":"ur","tl":"tl"
}

CSV_HEADER = ["name","email","country","language","city","instagram","phone","organization","type","notes"]

JSON_SCHEMA = {
    "name": "contacts_payload",
    "schema": {
        "type":"object",
        "properties":{
            "contacts":{
                "type":"array",
                "minItems": 100,
                "items":{
                    "type":"object",
                    "additionalProperties": False,
                    "properties":{
                        "name":{"type":"string"},
                        "email":{"type":["string","null"]},
                        "country":{"type":"string"},       # ISO-3 you provide
                        "language":{"type":"string"},       # ISO-2 you provide
                        "city":{"type":"string"},           # free text city
                        "instagram":{"type":["string","null"]},
                        "phone":{"type":["string","null"]},
                        "organization":{"type":["string","null"]},
                        "type":{"type":"string","enum": PARTNER_TYPES},
                        "notes":{"type":["string","null"]}
                    },
                    "required":["name","country","language","city","type"],
                    "oneOf":[
                        {"required":["email"]},
                        {"required":["instagram"]}
                    ]
                }
            }
        },
        "required":["contacts"],
        "additionalProperties": False
    }
}

SYSTEM = (
    "You are a precise research assistant for outreach list building.\n"
    "Return only JSON that matches the provided JSON Schema. No prose.\n"
    "Rules:\n"
    "- Do not invent emails. Only include an email if clearly public; otherwise leave it null and prefer Instagram handle.\n"
    "- Use Instagram handles or official org accounts when available. If neither exists, leave instagram null.\n"
    "- Avoid duplicates by email or instagram within a single response.\n"
    "- Prefer accounts relevant to the specified city. Include national partners if they have significant influence or presence in the region.\n"
    "- For national organizations, include those with local chapters, regional offices, or strong ties to the city.\n"
    "- Fill 'organization' briefly if the row is a person. Put the show name for podcasters when relevant.\n"
    "- Focus on contacts who would be interested in climate change, environmental protection, peace initiatives, nature conservation, or geopolitics.\n"
    "- Include diverse voices from different backgrounds, ages, and sectors within each category.\n"
)

def sanitize(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s.strip())

def to_iso3(country_slug: str) -> str:
    return ISO3.get(country_slug.lower(), country_slug.upper()[:3])

def to_lang2(lang_code: str) -> str:
    return LANG_MAP.get(lang_code.lower(), lang_code.lower()[:2])

def load_cities(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def write_csv(path: str, rows: List[Dict]) -> None:
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER)
        w.writeheader()
        for r in rows:
            out = {k: r.get(k, "") or "" for k in CSV_HEADER}
            w.writerow(out)

def dedupe(rows: List[Dict]) -> List[Dict]:
    seen: set = set()
    out = []
    for r in rows:
        key = (r.get("email") or "").lower().strip() or ("ig:" + (r.get("instagram") or "").lower().strip())
        if key and key not in seen:
            seen.add(key)
            out.append(r)
    return out

def city_display(city_obj: dict) -> str:
    # human city from id, e.g., "paris_france" -> "Paris"
    cid = city_obj.get("id","")
    name = cid.split("_")[0] if "_" in cid else cid
    return name.replace("-", " ").replace(".", " ").replace("/", " ").title()

def build_user_prompt(city: dict, partner_type: str, iso3: str, lang2: str) -> str:
    pieces = [
        f"Task: Propose at least 100 '{partner_type}' contacts in or strongly tied to {city_display(city)}.",
        "They must be plausible relays for WorldWideWaves announcements on climate, peace, nature, or geopolitics.",
        "Return only JSON per the schema. Use the provided codes exactly for 'country' and 'language'.",
        f"City metadata: id={city.get('id')}, country_slug={city.get('country')}, tz={city.get('timeZone')}, "
        f"instagramAccount={city.get('instagramAccount')}, hashtag={city.get('instagramHashtag')}.",
        f"Hard constraints: country={iso3}, language={lang2}, type={partner_type}.",
        "If unsure about an email, set email = null and prefer instagram."
    ]
    return "\n".join(pieces)

def call_openai(client: OpenAI, model: str, system: str, user: str) -> dict:
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role":"system","content":system},
            {"role":"user","content":user},
        ],
        response_format={"type":"json_schema","json_schema":JSON_SCHEMA},
        temperature=0.2,
    )
    # Parse response from chat completions API
    data = None
    raw_content = None
    try:
        # For OpenAI chat completions with structured output
        if hasattr(resp, "parsed") and resp.parsed:
            data = resp.parsed
        elif hasattr(resp, "choices") and resp.choices and len(resp.choices) > 0:
            message = resp.choices[0].message
            if hasattr(message, "parsed") and message.parsed:
                data = message.parsed
            elif hasattr(message, "content") and message.content:
                raw_content = message.content
                # Try to fix common JSON issues before parsing
                cleaned_content = raw_content.strip()
                if cleaned_content and not cleaned_content.endswith('}'):
                    # If JSON appears truncated, try to find the last complete contact and close the JSON
                    last_complete = cleaned_content.rfind('"}')
                    if last_complete > -1:
                        # Find the start of the incomplete contact
                        incomplete_start = cleaned_content.rfind(',{', 0, last_complete + 2)
                        if incomplete_start > -1:
                            cleaned_content = cleaned_content[:incomplete_start] + ']}'
                        else:
                            cleaned_content = cleaned_content[:last_complete + 2] + ']}'

                data = json.loads(cleaned_content)
            else:
                raise RuntimeError("No content found in response")
        else:
            raise RuntimeError("No valid response structure found")
    except json.JSONDecodeError as e:
        # Try to provide more helpful error context
        error_msg = f"Failed to parse JSON response: {e}"
        if raw_content:
            error_msg += f" (Response length: {len(raw_content)} chars)"
            # Show a snippet around the error location if possible
            if hasattr(e, 'pos') and e.pos:
                start = max(0, e.pos - 50)
                end = min(len(raw_content), e.pos + 50)
                snippet = raw_content[start:end]
                error_msg += f" Near: ...{snippet}..."
        raise RuntimeError(error_msg)
    except Exception as e:
        raise RuntimeError(f"Failed to parse model output: {e}")

    if not isinstance(data, dict) or "contacts" not in data:
        raise RuntimeError("Model did not return expected JSON with 'contacts'.")
    return data

def enforce_and_trim(rows: List[Dict], needed: int, iso3: str, lang2: str, city_name: str, partner_type: str) -> List[Dict]:
    normalized = []
    for r in rows:
        item = {
            "name": (r.get("name") or "").strip(),
            "email": (r.get("email") or None),
            "country": iso3,
            "language": lang2,
            "city": city_name,
            "instagram": (r.get("instagram") or None),
            "phone": (r.get("phone") or None),
            "organization": (r.get("organization") or None),
            "type": partner_type,
            "notes": (r.get("notes") or None)
        }
        # Require either email or instagram
        if not (item["email"] or item["instagram"]):
            continue
        # Skip blanks
        if not item["name"]:
            continue
        normalized.append(item)
    normalized = dedupe(normalized)
    return normalized[:needed]

def file_exists(out_root: str, city_id: str, partner_type: str) -> bool:
    """Check if the CSV file already exists for a city/type combination."""
    out_path = os.path.join(out_root, sanitize(city_id), partner_type, "contacts.csv")
    return os.path.exists(out_path)

def create_default_cities() -> List[dict]:
    """Create city objects from default city list with inferred country and language."""
    cities = []
    for city_id in DEFAULT_CITIES:
        parts = city_id.split("_")
        if len(parts) >= 2:
            country = "_".join(parts[1:])  # Everything after the first underscore
            # Infer language from country
            lang = "en"  # default
            if country in ["mexico", "spain", "argentina", "colombia", "peru", "chile"]:
                lang = "es"
            elif country in ["brazil"]:
                lang = "pt"
            elif country in ["france"]:
                lang = "fr"
            elif country in ["germany"]:
                lang = "de"
            elif country in ["italy"]:
                lang = "it"
            elif country in ["russia"]:
                lang = "ru"
            elif country in ["turkey"]:
                lang = "tr"
            elif country in ["egypt"]:
                lang = "ar"
            elif country in ["india"]:
                lang = "hi"
            elif country in ["indonesia"]:
                lang = "id"
            elif country in ["thailand"]:
                lang = "th"
            elif country in ["japan"]:
                lang = "ja"
            elif country in ["south_korea"]:
                lang = "ko"
            elif country in ["china", "hong_kong_china"]:
                lang = "zh"
            elif country in ["iran"]:
                lang = "fa"
            elif country in ["pakistan"]:
                lang = "ur"
            elif country in ["philippines"]:
                lang = "tl"

            city_obj = {
                "id": city_id,
                "country": country,
                "map": {"language": lang}
            }
            cities.append(city_obj)
    return cities

def merge_csvs(out_root: str, merge_output: str = "merged_contacts.csv") -> None:
    """Merge all CSV files in the output directory into one big CSV, checking for duplicates."""
    all_contacts = []
    seen_keys = set()

    print(f"Scanning {out_root} for CSV files...")

    # Walk through all subdirectories and find contacts.csv files
    for root, dirs, files in os.walk(out_root):
        if "contacts.csv" in files:
            csv_path = os.path.join(root, "contacts.csv")
            try:
                with open(csv_path, "r", encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Create a unique key for deduplication
                        email = (row.get("email") or "").lower().strip()
                        instagram = (row.get("instagram") or "").lower().strip()
                        key = email or ("ig:" + instagram)

                        if key and key not in seen_keys:
                            seen_keys.add(key)
                            all_contacts.append(row)

                print(f"Processed {csv_path}")
            except Exception as e:
                print(f"Error reading {csv_path}: {e}", file=sys.stderr)

    # Write merged file
    if all_contacts:
        with open(merge_output, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()
            for contact in all_contacts:
                # Ensure all fields are present
                row = {k: contact.get(k, "") or "" for k in CSV_HEADER}
                writer.writerow(row)

        print(f"Merged {len(all_contacts)} unique contacts into {merge_output}")
    else:
        print("No contacts found to merge.")

def run_for_city(client: OpenAI, model: str, city: dict, per_type: int, delay: float, out_root: str):
    iso3 = to_iso3(city.get("country",""))
    lang2 = to_lang2((city.get("map") or {}).get("language","en"))
    city_id = city.get("id")
    city_name = city_display(city)

    for i, ptype in enumerate(PARTNER_TYPES, 1):
        # Check if file already exists and skip if it does
        if file_exists(out_root, city_id, ptype):
            print(f"  [{i}/{len(PARTNER_TYPES)}] Skipping {ptype} - file already exists")
            continue

        print(f"  [{i}/{len(PARTNER_TYPES)}] Processing {ptype}...")
        need = per_type
        collected: List[Dict] = []
        attempts = 0
        seen_keys: set = set()

        while len(collected) < need and attempts < 4:
            prompt = build_user_prompt(city, ptype, iso3, lang2)
            data = call_openai(client, model, SYSTEM, prompt)
            rows = enforce_and_trim(data.get("contacts", []), need*2, iso3, lang2, city_name, ptype)
            # Local de-dup across attempts
            new_batch = []
            for r in rows:
                key = (r.get("email") or "").lower().strip() or ("ig:" + (r.get("instagram") or "").lower().strip())
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    new_batch.append(r)
            collected.extend(new_batch)
            attempts += 1
            time.sleep(delay)

        collected = collected[:need]
        # Write CSV
        out_dir = os.path.join(out_root, sanitize(city_id), ptype)
        out_path = os.path.join(out_dir, "contacts.csv")
        write_csv(out_path, collected)
        print(f"    Wrote {len(collected):3d} → {out_path}")

def main():
    ap = argparse.ArgumentParser(description="Generate city/type partner CSVs with OpenAI")
    ap.add_argument("--cities", help="Path to cities JSON. If not provided, uses default cities list.")
    ap.add_argument("--out", default="out", help="Output root directory.")
    ap.add_argument("--model", default="gpt-4o", help="OpenAI model.")
    ap.add_argument("--per-type", type=int, default=100, help="Minimum rows per city/type.")
    ap.add_argument("--delay", type=float, default=0.6, help="Seconds between API calls.")
    ap.add_argument("--merge", action="store_true", help="Merge all existing CSV files into one.")
    ap.add_argument("--merge-output", default="merged_contacts.csv", help="Output file for merged results.")
    args = ap.parse_args()

    # If merge flag is set, just merge existing files and exit
    if args.merge:
        merge_csvs(args.out, args.merge_output)
        return

    # Load cities
    if args.cities:
        cities = load_cities(args.cities)
        if not isinstance(cities, list):
            print("Cities file must be a JSON array.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Using default cities list...")
        cities = create_default_cities()

    print(f"Processing {len(cities)} cities...")

    client = OpenAI()

    for i, city in enumerate(cities, 1):
        try:
            city_id = city.get("id", "unknown")
            print(f"[{i}/{len(cities)}] Processing {city_id}...")
            run_for_city(client, args.model, city, args.per_type, args.delay, args.out)
        except Exception as e:
            cid = city.get("id","unknown")
            print(f"[warn] {cid}: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()

