import sqlite3
import zipfile
from tqdm import tqdm


FN_ALL = "data/allCountries.zip"
FN_ALT = "data/alternateNamesV2.zip"
DB = "data/geonames.sqlite3"


def create_tables(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS places(
            geonameid INTEGER PRIMARY KEY,
            parent_id INTEGER,
            name TEXT,
            feature_code TEXT,
            country_code TEXT,
            admin1 TEXT,
            admin2 TEXT,
            admin3 TEXT,
            admin4 TEXT,
            lat REAL,
            lon REAL
        );
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS names(
            geonameid INTEGER,
            lang TEXT,
            name TEXT,
            isPreferred INTEGER,
            isShort INTEGER
        );
    """
    )
    conn.commit()


def create_indexes(conn):
    cur = conn.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_places_parent ON places(parent_id);")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_places_feature ON places(feature_code);"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_places_country ON places(country_code);"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_places_admin1234 ON places(country_code, admin1, admin2, admin3, admin4);"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_names_geoname ON names(geonameid);")
    conn.commit()


def load_all_countries(conn):
    with zipfile.ZipFile(FN_ALL) as z:
        with z.open("allCountries.txt") as f:
            for line in tqdm(f, desc="allCountries"):
                parts = line.decode("utf-8").strip().split("\t")
                geonameid = int(parts[0])
                name = parts[1]
                lat = float(parts[4])
                lon = float(parts[5])
                feature_code = parts[7]
                country_code = parts[8]

                admin1 = parts[10] if len(parts) > 10 else None
                admin2 = parts[11] if len(parts) > 11 else None
                admin3 = parts[12] if len(parts) > 12 else None
                admin4 = parts[13] if len(parts) > 13 else None

                # column 16 in allCountries is assumed to be parent geonameid if numeric
                parent_id = None
                if len(parts) > 16 and parts[16].isdigit():
                    parent_id = int(parts[16])

                conn.execute(
                    "INSERT INTO places VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        geonameid,
                        parent_id,
                        name,
                        feature_code,
                        country_code,
                        admin1,
                        admin2,
                        admin3,
                        admin4,
                        lat,
                        lon,
                    ),
                )
    conn.commit()


def load_alternatenames(conn):
    with zipfile.ZipFile(FN_ALT) as z:
        with z.open("alternateNamesV2.txt") as f:
            for line in tqdm(f, desc="altNames"):
                parts = line.decode("utf-8").strip().split("\t")

                # must have at least id + geonameid + lang + name
                if len(parts) < 4:
                    continue

                try:
                    geonameid = int(parts[1])
                except:
                    continue

                lang = parts[2] if parts[2] != "" else None
                name = parts[3] if parts[3] != "" else None

                isColloquial = parts[4] if len(parts) > 4 else "0"
                isHistoric = parts[5] if len(parts) > 5 else "0"
                isPreferred = parts[6] if len(parts) > 6 and parts[6] != "" else "0"
                isShort = parts[7] if len(parts) > 7 and parts[7] != "" else "0"

                if isColloquial == "1" or isHistoric == "1":
                    continue

                conn.execute(
                    "INSERT INTO names VALUES (?, ?, ?, ?, ?)",
                    (geonameid, lang, name, int(isPreferred), int(isShort)),
                )
    conn.commit()


def build_hierarchy(conn):
    cur = conn.cursor()
    # 1. countries: all feature_code = "PCLI" are root nodes
    cur.execute("UPDATE places SET parent_id = NULL WHERE feature_code = 'PCLI'")

    # 2. admin1: parent is country
    cur.execute(
        """
        UPDATE places AS c
        SET parent_id = p.geonameid
        FROM places AS p
        WHERE c.feature_code = 'ADM1'
          AND p.feature_code = 'PCLI'
          AND c.country_code = p.country_code
    """
    )

    # 3. admin2: parent is admin1
    cur.execute(
        """
        UPDATE places AS c
        SET parent_id = p.geonameid
        FROM places AS p
        WHERE c.feature_code = 'ADM2'
          AND p.feature_code = 'ADM1'
          AND c.country_code = p.country_code
          AND c.admin1 = p.admin1
    """
    )

    # 4. admin3: parent is admin2
    cur.execute(
        """
        UPDATE places AS c
        SET parent_id = p.geonameid
        FROM places AS p
        WHERE c.feature_code = 'ADM3'
          AND p.feature_code = 'ADM2'
          AND c.country_code = p.country_code
          AND c.admin1 = p.admin1
          AND c.admin2 = p.admin2
    """
    )

    # 5. admin4: parent is admin3
    cur.execute(
        """
        UPDATE places AS c
        SET parent_id = p.geonameid
        FROM places AS p
        WHERE c.feature_code = 'ADM4'
          AND p.feature_code = 'ADM3'
          AND c.country_code = p.country_code
          AND c.admin1 = p.admin1
          AND c.admin2 = p.admin2
          AND c.admin3 = p.admin3
    """
    )

    # 6. cities: PPL* attach to nearest admin
    cur.execute(
        """
        UPDATE places AS c
        SET parent_id = p.geonameid
        FROM places AS p
        WHERE c.feature_code LIKE 'PPL%'
          AND p.feature_code = 'ADM3'
          AND c.country_code = p.country_code
          AND c.admin1 = p.admin1
          AND c.admin2 = p.admin2
          AND c.admin3 = p.admin3
    """
    )
    conn.commit()


def main():
    print("🔧 Starting Geonames import...")
    conn = sqlite3.connect(DB)
    create_tables(conn)
    print("📦 Tables created")
    print("⏳ Loading allCountries...")
    load_all_countries(conn)
    print("✅ allCountries loaded")
    print("⏳ Loading alternateNames...")
    load_alternatenames(conn)
    print("✅ alternateNames loaded")
    print("🕸 Building hierarchy...")
    build_hierarchy(conn)
    print("📈 Creating indexes...")
    create_indexes(conn)
    print("📊 Indexes created")
    print("🏁 Hierarchy built successfully!")
    print("💾 Database written to", DB)
    conn.close()


if __name__ == "__main__":
    main()
