import msal
import requests
from urllib import parse
import app_config

CLIENT_ID = app_config.CLIENT_ID # Application (client) ID of app registration
CLIENT_SECRET = app_config.CLIENT_SECRET # Placeholder - for use ONLY during testing.
AUTHORITY = app_config.AUTHORITY
REDIRECT_PATH = app_config.REDIRECT_PATH # Used for forming an absolute URL to your redirect URI.
SCOPE = app_config.SCOPE

# Cache
cache = msal.SerializableTokenCache()

# Build msal app
app = msal.ConfidentialClientApplication(
    CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET,
    token_cache=cache)

# Initiate auth code flow
session = requests.Session()
session.flow = app.initiate_auth_code_flow(scopes=SCOPE, redirect_uri=REDIRECT_PATH)

# Navigate to Microsoft login page and authenticate

# After navigation back to your application you should use this flow object as you did in your example
result = app.acquire_token_by_auth_code_flow(auth_code_flow=session.flow, auth_response=dict(parse.parse_qsl(parse.urlsplit(REDIRECT_PATH).query)))

print (result)
