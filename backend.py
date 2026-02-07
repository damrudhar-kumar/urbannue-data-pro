from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
import shopify
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Shopify Settings
API_KEY = os.getenv("SHOPIFY_API_KEY")
API_SECRET = os.getenv("SHOPIFY_API_SECRET")
SCOPES = ['read_orders', 'read_products']
REDIRECT_URI = "http://localhost:8000/auth/callback"

@app.get("/install")
def install(shop: str):
    """Redirects the user to Shopify's permission page."""
    shopify.Session.setup(api_key=API_KEY, secret=API_SECRET)
    permission_url = shopify.Session(shop, "2024-01").create_permission_url(SCOPES, REDIRECT_URI)
    return RedirectResponse(permission_url)

@app.get("/auth/callback")
def callback(shop: str, code: str):
    """Receives the access token from Shopify."""
    session = shopify.Session(shop, "2024-01")
    access_token = session.request_token({"code": code})
    
    # PREMIUM STEP: Save 'access_token' and 'shop' to Supabase here
    # For now, let's just redirect to the dashboard
    return RedirectResponse(f"http://localhost:8501?shop={shop}&token={access_token}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
