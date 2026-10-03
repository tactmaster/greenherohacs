"""Constants for the Green Hero integration."""
from datetime import timedelta

DOMAIN = "greenhero"

# API
API_BASE = "https://app.greenhero.com/api"

# Auth0 (custom domain). These are PUBLIC values from the SPA, not secrets.
AUTH0_DOMAIN = "https://login.greenhero.com"
AUTH0_TOKEN_URL = f"{AUTH0_DOMAIN}/oauth/token"
AUTH0_DEVICE_CODE_URL = f"{AUTH0_DOMAIN}/oauth/device/code"
# Backend accepts tokens whose iss is the canonical tenant; send this header.
OPENID_ISSUER = "https://login.greenhero.com/"
AUTH0_SCOPE = "openid profile email offline_access"
AUTH0_REDIRECT_URI = "https://app.greenhero.com"

# TODO: fill from the login.greenhero.com/authorize request (public values).
AUTH0_CLIENT_ID = "s37BNkGesz6HLgWo8vLtVZcFl3iL5eUa"
AUTH0_AUDIENCE = ""

UPDATE_INTERVAL = timedelta(minutes=5)
CONF_REFRESH_TOKEN = "refresh_token"

# Units (Swedish market)
CURRENCY = "SEK"
PRICE_UNIT = "SEK/kWh"
