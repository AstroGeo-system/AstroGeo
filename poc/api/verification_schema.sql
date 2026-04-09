-- ============================================================================
-- Evidence Chain Schema (Section 5.3 from AstroGeo POC Docs)
-- Adds verification columns to astronomy.asteroid_ml_predictions
-- to power the "Verify Predictions" screen in the full React frontend.
-- ============================================================================

SET search_path TO astronomy;

-- Add verification columns
ALTER TABLE asteroid_ml_predictions
    ADD COLUMN IF NOT EXISTS verified_by        VARCHAR(100),
    ADD COLUMN IF NOT EXISTS verified_at        TIMESTAMP,
    ADD COLUMN IF NOT EXISTS verification_hash  VARCHAR(128),
    ADD COLUMN IF NOT EXISTS verification_status VARCHAR(20)
        DEFAULT 'pending';  -- pending / verified / disputed

-- ============================================================================
-- Populate verification_hash for all existing rows
-- SHA-256 of: asteroid_id || improved_risk_score || anomaly_score || cluster || NOW()
-- Creates the cryptographic proof chain shown in UI mockups.
-- ============================================================================

UPDATE asteroid_ml_predictions
SET verification_hash = encode(
    sha256(
        (
            COALESCE(asteroid_id, '')            || '|' ||
            COALESCE(improved_risk_score::text, '') || '|' ||
            COALESCE(anomaly_score::text, '')    || '|' ||
            COALESCE(cluster::text, '')          || '|' ||
            NOW()::text
        )::bytea
    ),
    'hex'
),
verification_status = 'pending'
WHERE verification_hash IS NULL;

-- ============================================================================
-- Create index for fast "pending" lookups
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_verification_status
    ON asteroid_ml_predictions(verification_status);

CREATE INDEX IF NOT EXISTS idx_verified_by
    ON asteroid_ml_predictions(verified_by)
    WHERE verified_by IS NOT NULL;

-- ============================================================================
-- Verify
-- ============================================================================

SELECT
    verification_status,
    COUNT(*) as count
FROM asteroid_ml_predictions
GROUP BY verification_status;

SELECT
    asteroid_id,
    improved_risk_score,
    verification_hash,
    verification_status
FROM asteroid_ml_predictions
ORDER BY improved_risk_score DESC
LIMIT 5;
