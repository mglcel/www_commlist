# Communication List Generator

Generate city/type partner CSVs using OpenAI's API for outreach campaigns focused on climate change, environmental protection, peace initiatives, nature conservation, and geopolitics.

## Features

- **Default Cities**: Runs by default on 41 major cities worldwide
- **Smart Resume**: Checks for existing files and skips them, allowing you to stop and resume
- **Duplicate Detection**: Prevents duplicates within and across files
- **Merge Functionality**: Combines all generated CSVs into one deduplicated file
- **Improved Prompts**: Enhanced to include national partners with local relevance
- **High Volume**: Generates 100 partners per city/type combination

## Default Cities List

The script includes 41 major cities across all continents:

**Americas**: New York, Los Angeles, Chicago, San Francisco, Toronto, Vancouver, Mexico City, São Paulo, Buenos Aires, Lima, Bogotá, Santiago

**Europe**: London, Paris, Berlin, Madrid, Rome, Moscow, Istanbul

**Africa**: Cairo, Johannesburg, Nairobi, Lagos, Kinshasa

**Middle East**: Dubai, Tehran

**Asia**: Mumbai, Delhi, Bangalore, Karachi, Jakarta, Bangkok, Manila, Tokyo, Seoul, Beijing, Shanghai, Hong Kong

**Oceania**: Sydney, Melbourne

## Usage

### Basic Usage (Default Cities)
```bash
python3 populate.py
```

### Specific Cities
```bash
# Single city
python3 populate.py --cities paris

# Multiple cities
python3 populate.py --cities paris london tokyo

# Cities with spaces (use quotes)
python3 populate.py --cities "new york" "san francisco"
```

### Custom Options
```bash
python3 populate.py --per-type 150 --delay 1.0 --out output_dir
```

### Merge Existing Files
```bash
python3 populate.py --merge --merge-output all_contacts.csv
```

## Command Line Options

- `--cities`: List of city names to process (optional, uses default cities if not provided)
- `--out`: Output root directory (default: "out")
- `--model`: OpenAI model to use (default: "gpt-4o")
- `--per-type`: Number of contacts per city/type (default: 100)
- `--delay`: Seconds between API calls (default: 0.6)
- `--merge`: Merge all existing CSV files into one
- `--merge-output`: Output file for merged results (default: "merged_contacts.csv")
- `--find-twitter`: Find missing Twitter accounts for existing contacts
- `--batch-size`: Number of contacts to process per API call when finding Twitter (default: 20)

## Partner Types

The script generates contacts for these categories:
- **influencer**: Social media influencers and content creators
- **podcaster**: Podcast hosts and audio content creators
- **journalist**: Reporters, editors, and media professionals
- **activist**: Environmental and social activists
- **ngo**: Non-governmental organization representatives
- **other**: Other relevant contacts

## Output Format

### Directory Structure
```
out/
├── new_york_usa/
│   ├── influencer/
│   │   └── contacts.csv
│   ├── podcaster/
│   │   └── contacts.csv
│   └── ...
└── london_england/
    ├── influencer/
    │   └── contacts.csv
    └── ...
```

### CSV Format
Each CSV contains these fields:
- `name`: Contact's full name
- `email`: Public email address (if available)
- `country`: ISO-3 country code
- `language`: ISO-2 language code
- `city`: City name
- `instagram`: Instagram handle
- `twitter`: Twitter/X handle
- `phone`: Phone number (if available)
- `organization`: Organization or company
- `type`: Partner type category
- `notes`: Additional information

## Authentication

Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your_api_key_here
```

## Resume Capability

The script automatically checks for existing files and skips them. This means you can:
1. Start the script
2. Stop it at any time (Ctrl+C)
3. Restart it later - it will continue from where it left off

## Examples

### Generate contacts for default cities with custom settings
```bash
python3 populate.py --per-type 200 --delay 0.8
```

### Generate contacts for specific cities and merge results
```bash
python3 populate.py --cities paris london berlin --per-type 150
python3 populate.py --merge --merge-output final_contacts.csv
```

### Only merge existing files (no generation)
```bash
python3 populate.py --merge
```

### Find missing Twitter accounts for existing contacts
```bash
# Uses batch processing (20 contacts per API call by default)
python3 populate.py --find-twitter

# Custom batch size to control API usage
python3 populate.py --find-twitter --batch-size 30
```

**Note**: The search marks accounts as:
- `@username` - Verified match found
- `not_found` - No Twitter account exists
- `not_sure` - Multiple similar accounts or ambiguous match (requires manual verification)

## City Name Matching

When specifying cities with `--cities`, the script matches city names flexibly:

- **Partial matches**: "paris" matches "paris_france"
- **Case insensitive**: "TOKYO" matches "tokyo_japan"
- **Space/dash handling**: "new york" matches "new_york_usa"
- **Multiple matches**: if a name matches multiple cities, all matches are included

If no cities match your input, the script will show available city options.

## Performance

- **Volume**: 100 contacts per city/type = 600 contacts per city
- **Total Default**: 41 cities × 600 contacts = ~24,600 contacts
- **Deduplication**: Automatic removal of duplicates by email/Instagram
- **Rate Limiting**: Built-in delay between API calls to respect limits