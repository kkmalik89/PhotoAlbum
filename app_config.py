# Storage parameters
STORAGE_ACCOUNT_NAME="name"
CONTAINER_NAME="pictures"
STORAGE_ACCOUNT_KEY=""

# Azure Application related settings required for Authentication
CLIENT_ID = "" # Application (client) ID of app registration
CLIENT_SECRET = "" # Placeholder - for use ONLY during testing.
AUTHORITY = "https://login.microsoftonline.com/<Tenant Id>"
REDIRECT_PATH = "http://localhost:8000/authorized"  # Used for forming an absolute URL to your redirect URI.
                              # The absolute URL must match the redirect URI you set
                              # in the app's registration in the Azure portal.
ENDPOINT = 'https://graph.microsoft.com/v1.0/users'  # This resource requires no admin consent
# You can find the proper permission names from this document
# https://docs.microsoft.com/en-us/graph/permissions-reference
SCOPE_STORAGE = ["https://storage.azure.com/user_impersonation"]
SCOPE = ["User.Read","User.ReadBasic.All","https://storage.azure.com/user_impersonation"]
SESSION_TYPE = "filesystem"  # Specifies the token cache should be stored in server-side session
MSAL_CACHE_DIR = ".fastapi_cache/msalcache"
