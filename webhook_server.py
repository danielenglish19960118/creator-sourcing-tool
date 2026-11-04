"""
Multi-Channel Automated Payment & Tenant Provisioning Microservice.

Supports:
- Local (Taiwan): ECPay (綠界), NewebPay (藍新), LINE Pay
- Global: Stripe, Lemon Squeezy (MoR), Gumroad, PayPal
"""

import os
import secrets
from fastapi import FastAPI, Request, HTTPException
from supabase import create_client, Client

app = FastAPI(title="SaaS Payment Webhook Automation Server")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None


def upgrade_user_tier(email: str, tier: str = "pro", provider: str = "unknown"):
    """Automatically update or create user tier in Supabase upon successful payment."""
    if not supabase:
        print(f"[{provider.upper()}] Supabase client not configured.")
        return

    try:
        res = supabase.table("tenants").select("*").eq("email", email).execute()
        
        if res.data:
            supabase.table("tenants").update({
                "tier": tier,
                "ai_limit": 9999,
                "is_active": True
            }).eq("email", email).execute()
            print(f"[{provider.upper()} Automation] Upgraded existing user {email} to {tier.upper()}")
        else:
            tenant_token = f"saas_{tier}_{secrets.token_hex(16)}"
            supabase.table("tenants").insert({
                "email": email,
                "api_token": tenant_token,
                "tier": tier,
                "provider": provider,
                "ai_usage": 0,
                "ai_limit": 9999,
                "is_active": True
            }).execute()
            print(f"[{provider.upper()} Automation] Created new Pro tenant for {email}")
    except Exception as e:
        print(f"[{provider.upper()} Error] Failed to update database: {e}")


# ==================== LOCAL PAYMENT CHANNELS (TAIWAN) ====================

@app.post("/webhook/ecpay")
async def webhook_ecpay(request: Request):
    form_data = await request.form()
    data = dict(form_data)
    if data.get("RtnCode") == "1":
        email = data.get("CustomField1", "customer@example.com")
        tier = data.get("CustomField2", "pro")
        upgrade_user_tier(email, tier, provider="ecpay")
        return "1|OK"
    raise HTTPException(status_code=400, detail="ECPay payment unverified")


@app.post("/webhook/newebpay")
async def webhook_newebpay(request: Request):
    form_data = await request.form()
    data = dict(form_data)
    if data.get("Status") == "SUCCESS":
        email = data.get("Email", "customer@example.com")
        upgrade_user_tier(email, "pro", provider="newebpay")
        return "SUCCESS"
    raise HTTPException(status_code=400, detail="NewebPay payment failed")


@app.post("/webhook/linepay")
async def webhook_linepay(request: Request):
    body = await request.json()
    if body.get("returnCode") == "0000":
        email = body.get("info", {}).get("email", "linepay_user@example.com")
        upgrade_user_tier(email, "pro", provider="linepay")
        return {"status": "ok"}
    raise HTTPException(status_code=400, detail="LINE Pay failed")


# ==================== GLOBAL PAYMENT CHANNELS ====================

@app.post("/webhook/stripe")
async def webhook_stripe(request: Request):
    event = await request.json()
    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email") or session.get("customer_details", {}).get("email")
        tier = session.get("metadata", {}).get("tier", "pro")
        upgrade_user_tier(email, tier, provider="stripe")
        return {"status": "success"}
    return {"status": "ignored"}


@app.post("/webhook/lemonsqueezy")
async def webhook_lemonsqueezy(request: Request):
    body = await request.json()
    event_name = body.get("meta", {}).get("event_name")
    if event_name in ["order_created", "subscription_created"]:
        attributes = body.get("data", {}).get("attributes", {})
        email = attributes.get("user_email") or attributes.get("customer_email")
        if email:
            upgrade_user_tier(email, tier="pro", provider="lemonsqueezy")
            return {"status": "success"}
    return {"status": "ignored"}


@app.post("/webhook/gumroad")
async def webhook_gumroad(request: Request):
    form_data = await request.form()
    data = dict(form_data)
    email = data.get("email")
    if email:
        upgrade_user_tier(email, tier="pro", provider="gumroad")
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Invalid Gumroad payload")


@app.post("/webhook/paypal")
async def webhook_paypal(request: Request):
    body = await request.json()
    event_type = body.get("event_type")
    if event_type in ["PAYMENT.SALE.COMPLETED", "BILLING.SUBSCRIPTION.CREATED", "BILLING.SUBSCRIPTION.ACTIVATED"]:
        resource = body.get("resource", {})
        email = (
            resource.get("subscriber", {}).get("email_address") or 
            resource.get("payer", {}).get("email_address")
        )
        if email:
            upgrade_user_tier(email, tier="pro", provider="paypal")
            return {"status": "success"}
    return {"status": "ignored"}
