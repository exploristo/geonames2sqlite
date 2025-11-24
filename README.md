# 🌍 Geonames → SQLite Hierarchical Import

This tool converts Geonames data (`allCountries.zip` and `alternateNamesV2.zip`) into a clean, structured SQLite database with a proper administrative hierarchy.

## Features

- Reads both datasets directly from ZIP archives (no extraction required)
- Stores core geospatial entities in a `places` table
- Stores all alternative names in a separate `names` table
- Generates a valid hierarchical parent→child structure using administrative levels (ADM1–ADM4)
- Supports recursive tree queries (SQLite `WITH RECURSIVE`)
- Suitable for geographic apps, routing systems, map backends, knowledge graphs, entity linking and place normalization

---

## Database Schema

### `places`

| Field        | Type    | Description                         |
| ------------ | ------- | ----------------------------------- |
| geonameid    | INTEGER | Primary ID from Geonames            |
| parent_id    | INTEGER | Parent geonameid (or NULL for root) |
| name         | TEXT    | Default English name                |
| feature_code | TEXT    | Geonames feature classification     |
| country_code | TEXT    | Two-letter ISO country code         |
| admin1       | TEXT    | First-level admin code              |
| admin2       | TEXT    | Second-level admin code             |
| admin3       | TEXT    | Third-level admin code              |
| admin4       | TEXT    | Fourth-level admin code             |
| lat          | REAL    | Latitude                            |
| lon          | REAL    | Longitude                           |

### `names`

| Field     | Type    | Description          |
| --------- | ------- | -------------------- |
| geonameid | INTEGER | FK to places         |
| lang      | TEXT    | Language or ISO code |
| name      | TEXT    | Alternative name     |

---

## How It Builds the Hierarchy

Hierarchy is created based on:

- `feature_code`
- `country_code`
- `admin1–admin4`

Processing:

1. `PCLI` → Countries → no parent  
2. `ADM1` → belongs to a country  
3. `ADM2` → belongs to ADM1  
4. `ADM3` → belongs to ADM2  
5. `ADM4` → belongs to ADM3  
6. `PPL*` → assigned to nearest ADM3  

Result:  
Germany → Nordrhein-Westfalen → Kreis → municipality → town

---

## Usage

Place files in:

data/allCountries.zip
data/alternateNamesV2.zip

Run import:

python3 convert.py

This creates:

geonames.db

---

## Example: Retrieve full tree of Germany

```sql
WITH RECURSIVE r(geonameid, parent_id, name, level) AS (
    SELECT geonameid, parent_id, name, 0 FROM places WHERE name='Germany'
    UNION ALL
    SELECT p.geonameid, p.parent_id, p.name, r.level + 1
    FROM places p
    JOIN r ON p.parent_id = r.geonameid
)
SELECT * FROM r ORDER BY level, name;


⸻

Example: Retrieve cities under a specific ADM3

WITH RECURSIVE r(id) AS (
    SELECT geonameid FROM places WHERE geonameid=XXXXXX
    UNION ALL
    SELECT geonameid FROM places WHERE parent_id IN r
)
SELECT * FROM places
WHERE geonameid IN r AND feature_code LIKE 'PPL%';


⸻

Performance Notes
	•	Initial import is large (10–20M rows)
	•	SQLite handles it, but consider migrating later to:
	•	Postgres
	•	DuckDB
	•	ClickHouse

⸻

Future improvements
	•	Population data integration
	•	Time zones
	•	Elevation
	•	OSM polygon cross-linking
	•	Entity deduplication and normalization

⸻

License

Use freely. Data provided under Geonames open license:
http://www.geonames.org/export/

⸻

Attribution

This import tool is optimized for real-world geospatial systems and knowledge-graph applications. If you use it, consider attribution, but it’s optional. Contributions welcome.

