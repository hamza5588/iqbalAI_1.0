-- Simple script to create a single coupon
-- Usage: psql -U myuser -d mydatabase -f create_single_coupon.sql
-- Or modify the values below and run: psql postgresql://myuser:mypassword@localhost:5432/mydatabase -f create_single_coupon.sql

-- Modify these values as needed:
-- CODE: The coupon code (must be unique, will be converted to uppercase)
-- TIER: 'pro' or 'pro_plus'
-- DESCRIPTION: Optional description
-- MAX_USES: NULL for unlimited, or a number for limited uses
-- EXPIRES_AT: NULL for never expires, or a timestamp like '2025-12-31 23:59:59'

INSERT INTO coupons (code, subscription_tier, description, max_uses, used_count, is_active, created_at)
VALUES (
    'PROMO2024',                    -- CODE: Change this to your desired coupon code
    'pro',                          -- TIER: 'pro' or 'pro_plus'
    'Promotional Pro subscription', -- DESCRIPTION: Optional description
    NULL,                           -- MAX_USES: NULL = unlimited, or set a number
    0,                              -- used_count: Always start at 0
    true,                           -- is_active: true = active, false = inactive
    NOW()                           -- created_at: Auto-set to current timestamp
)
ON CONFLICT (code) DO UPDATE SET
    subscription_tier = EXCLUDED.subscription_tier,
    description = EXCLUDED.description,
    max_uses = EXCLUDED.max_uses,
    is_active = EXCLUDED.is_active;

-- Verify the coupon was created
SELECT id, code, subscription_tier, description, max_uses, used_count, expires_at, is_active, created_at
FROM coupons
WHERE code = 'PROMO2024';









