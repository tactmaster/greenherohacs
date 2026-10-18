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

# Tariff options (set per grid company under Configure). Per-kWh rates are in
# öre/kWh including VAT, as private-customer price lists show them.
CONF_TRANSFER_FEE = "transfer_fee"  # grid company överföringsavgift
CONF_ENERGY_TAX = "energy_tax"  # energiskatt
CONF_FIXED_GRID_FEE = "fixed_grid_fee"  # grid company fast avgift, SEK/month
CONF_EXPORT_COMPENSATION = "export_compensation"  # nätnytta + supplier bonus
VAT_RATE = 0.25
DEFAULT_OPTIONS = {
    CONF_TRANSFER_FEE: 0.0,
    CONF_ENERGY_TAX: 45.0,  # 2026: 36.0 öre + 25% VAT
    CONF_FIXED_GRID_FEE: 0.0,
    CONF_EXPORT_COMPENSATION: 0.0,
}
