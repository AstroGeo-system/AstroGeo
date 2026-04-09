from sqlalchemy import create_engine, text
from backend.config import settings

db_url = settings.DATABASE_URL
engine = create_engine(db_url)

def check_asteroid(name):
    print(f"Checking for '{name}'...")
    with engine.connect() as conn:
        # Exact match
        query = text("SELECT asteroid_id FROM astronomy.asteroid_ml_predictions WHERE asteroid_id = :name")
        result = conn.execute(query, {'name': name}).fetchone()
        if result:
            print(f"  ✅ Exact match found: {result[0]}")
        else:
            print("  ❌ No exact match")
            
        # ILIKE match
        query = text("SELECT asteroid_id FROM astronomy.asteroid_ml_predictions WHERE asteroid_id ILIKE :name")
        result = conn.execute(query, {'name': f"%{name}%"}).fetchall()
        if result:
            print(f"  ✅ Fuzzy matches found: {[r[0] for r in result]}")
        else:
            print("  ❌ No fuzzy match")
            
        # Check without spaces
        no_space = name.replace(" ", "")
        query = text("SELECT asteroid_id FROM astronomy.asteroid_ml_predictions WHERE asteroid_id ILIKE :name")
        result = conn.execute(query, {'name': f"%{no_space}%"}).fetchall()
        if result:
             print(f"  ✅ No-space matches found: {[r[0] for r in result]}")

print("--- DB CHECK ---")
check_asteroid("2019 JQ2")
check_asteroid("2025 YC")
check_asteroid("99942") # Control check (Apophis)
print("----------------")
