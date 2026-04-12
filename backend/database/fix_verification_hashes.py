# backend/database/fix_verification_hashes.py
# Re-seeds all verification_hash values using deterministic inputs only.
# Safe to run multiple times — uses UPDATE not INSERT.

import hashlib
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

MODEL_VERSION = "astrogeo-asteroid-v1.0"  # pin this forever


def compute_deterministic_hash(row: dict) -> str:
    """
    Deterministic inputs only — no timestamps, no randomness.
    This exact function must live in both this script AND main.py
    so Python can always recompute and verify.
    """
    hash_input = (
        f"{row['asteroid_id']}"
        f"{float(row['improved_risk_score']):.6f}"
        f"{float(row['anomaly_score']):.6f}"
        f"{int(row['cluster'])}"
        f"{str(row['is_anomaly'])}"
        f"{row['risk_category']}"
        f"{MODEL_VERSION}"
    )
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


def _engine():
    return create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD', '')}"
        f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
        f"/{os.getenv('DB_NAME')}",
        pool_pre_ping=True,
    )


def fix_hashes():
    engine = _engine()

    with engine.connect() as conn:
        print("Fetching all predictions...")
        rows = conn.execute(text("""
            SELECT asteroid_id, improved_risk_score, anomaly_score,
                   cluster, is_anomaly, risk_category
            FROM astronomy.asteroid_ml_predictions
        """)).fetchall()

        print(f"Re-seeding hashes for {len(rows):,} predictions...")
        updated = 0

        for row in rows:
            r        = dict(row._mapping)
            new_hash = compute_deterministic_hash(r)

            conn.execute(text("""
                UPDATE astronomy.asteroid_ml_predictions
                SET verification_hash = :hash,
                    verification_status = 'pending'
                WHERE asteroid_id = :aid
            """), {"hash": new_hash, "aid": r['asteroid_id']})
            updated += 1

            if updated % 1000 == 0:
                print(f"  {updated:,}/{len(rows):,} updated...")

        conn.commit()

    engine.dispose()
    print(f"\n✅ Re-seeded {updated:,} deterministic hashes")

    # ── Spot-check: recompute live and compare ────────────────
    engine2 = _engine()
    with engine2.connect() as conn:
        row = conn.execute(text("""
            SELECT asteroid_id, improved_risk_score, anomaly_score,
                   cluster, is_anomaly, risk_category, verification_hash
            FROM astronomy.asteroid_ml_predictions
            ORDER BY improved_risk_score DESC
            LIMIT 1
        """)).fetchone()
        r          = dict(row._mapping)
        recomputed = compute_deterministic_hash(r)
        match      = (recomputed == r['verification_hash'])
        print(f"\nSpot-check asteroid {r['asteroid_id']}:")
        print(f"  Stored:     {r['verification_hash'][:32]}...")
        print(f"  Recomputed: {recomputed[:32]}...")
        print(f"  Match: {'✅ TRUE TAMPER DETECTION WORKING' if match else '❌ MISMATCH — check field types'}")
    engine2.dispose()


if __name__ == '__main__':
    fix_hashes()
