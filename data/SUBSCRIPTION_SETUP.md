# Subscription System Setup Guide

## Overview
A subscription system has been integrated into Iqbal AI with Stripe payment processing. Users start on the Free tier and can upgrade to Pro or Pro Plus plans.

## What Was Implemented

### 1. Database Changes
- Added `subscription_tier` field to User model (default: 'free')
- Added `stripe_customer_id` field for Stripe customer tracking
- Added `stripe_subscription_id` field for subscription tracking
- Added `subscription_status` field for subscription status (active, canceled, etc.)
- Automatic migration script included in `app/utils/db.py` to add these columns to existing databases

### 2. UI Changes
- Replaced "Logout" button with "Settings" button in the sidebar
- Settings button opens the subscription management page
- Created a beautiful subscription page with three tiers:
  - **Free** - Default tier for all new users
  - **Pro** - $19.99/month (available for upgrade)
  - **Pro Plus** - $49.99/month (Coming Soon)

### 3. Routes Created
- `/subscription/settings` - Main settings/subscription page
- `/subscription/api/subscription/plans` - Get available plans
- `/subscription/api/subscription/create-checkout` - Create Stripe checkout session
- `/subscription/checkout-success` - Handle successful payment
- `/subscription/api/subscription/cancel` - Cancel subscription
- `/subscription/webhook/stripe` - Stripe webhook handler

### 4. Stripe Integration
- Stripe keys configured in `app/config.py`
- Stripe.js loaded in settings page for secure payment processing
- Webhook handler for subscription updates

## Setup Instructions

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```
The `stripe` package has been added to requirements.txt.

### Step 2: Stripe Product IDs (Already Configured)

The Stripe Product IDs have been configured in `app/config.py`:
- **Pro Product ID**: `prod_TaPSD7B5zRAeKb`
- **Pro Plus Product ID**: `prod_TaPShi2ENfvmO3`

The system will automatically fetch the active price from these products when creating checkout sessions. Make sure each product has at least one active recurring price configured in your Stripe Dashboard.

If you need to change these, update them in `app/config.py` or set environment variables:
```env
STRIPE_PRO_PRODUCT_ID=prod_TaPSD7B5zRAeKb
STRIPE_PRO_PLUS_PRODUCT_ID=prod_TaPShi2ENfvmO3
```

### Step 3: Set Up Stripe Webhook

1. Go to https://dashboard.stripe.com/test/webhooks
2. Click "Add endpoint"
3. Set the endpoint URL to: `https://yourdomain.com/subscription/webhook/stripe`
4. Select events to listen for:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
5. Copy the webhook signing secret
6. Add it to your `.env` file:
```env
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

### Step 4: Run Database Migration

The migration will run automatically when you start the app. It will:
- Add subscription columns to existing users table
- Set all existing users to 'free' tier
- Set new users to 'free' tier by default

### Step 5: Test the Integration

1. Start your Flask application
2. Log in as a user
3. Click the "Settings" button (replaces logout button)
4. You should see the subscription page with three plans
5. Try upgrading to Pro (will redirect to Stripe checkout)
6. Complete a test payment using Stripe test card: `4242 4242 4242 4242`

## Stripe Test Cards

For testing payments:
- Success: `4242 4242 4242 4242`
- Decline: `4000 0000 0000 0002`
- Requires 3D Secure: `4000 0025 0000 3155`

Use any future expiry date, any 3-digit CVC, and any ZIP code.

## Features

### Free Tier
- Basic AI chat functionality
- Limited messages per day
- Standard response speed
- Community support

### Pro Tier ($19.99/month)
- Unlimited messages
- Priority response speed
- Advanced AI models
- Email support
- Export conversations

### Pro Plus Tier ($49.99/month) - Coming Soon
- Everything in Pro
- API access
- Custom integrations
- Priority support
- Advanced analytics

## Current Configuration

Stripe keys are currently configured in `app/config.py`:
- **Publishable Key**: `pk_test_51SdENKR3GHwhdSflEXLb8vuJCGAwrUsjAYOvpbviKHNfVEjSKDZrBFqS92bIt1GuXPyzRO8DzwsK2ZecfyV0hlCy00hS7JJVz4`
- **Secret Key**: `sk_test_51SdENKR3GHwhdSflTCjLB5h83eDa8G4oZOLySliNfIduAeizo10wrhOZsnlfsslD5530mboYRii8MdXLTFIVNQEQ003sVSsIS1`

**Important**: For production, move these to environment variables in `.env` file for security.

## Files Modified/Created

### Modified Files:
- `app/models/database_models.py` - Added subscription fields to User model
- `app/models/models.py` - Updated create_user to set default subscription_tier
- `app/config.py` - Added Stripe configuration
- `app/__init__.py` - Registered subscription blueprint
- `app/utils/db.py` - Added migration for subscription columns
- `templates/chat.html` - Replaced logout with settings button
- `requirements.txt` - Added stripe package

### New Files:
- `app/routes/subscription.py` - Subscription routes and Stripe integration
- `templates/settings.html` - Subscription management page

## Next Steps

1. Create Stripe products and prices in dashboard
2. Set up webhook endpoint
3. Test the payment flow
4. Move Stripe keys to environment variables for production
5. Update Pro Plus features when ready to launch
6. Configure production Stripe keys (replace test keys)

## Troubleshooting

### Payment not processing?
- Check that Stripe price IDs are correctly configured
- Verify webhook endpoint is accessible
- Check Stripe dashboard for error logs

### Subscription not updating?
- Verify webhook secret is correct
- Check webhook events are being received in Stripe dashboard
- Ensure webhook endpoint URL is correct

### Database errors?
- The migration runs automatically on app start
- If issues occur, you may need to manually add columns:
  ```sql
  ALTER TABLE users ADD COLUMN subscription_tier VARCHAR(50) DEFAULT 'free';
  ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(255);
  ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(255);
  ALTER TABLE users ADD COLUMN subscription_status VARCHAR(50);
  ```

