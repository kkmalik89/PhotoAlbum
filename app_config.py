# Storage parameters
STORAGE_ACCOUNT_NAME="kkphotostoragedl"
CONTAINER_NAME="pictures"
# CONTAINER_NAME="animal-photos"
STORAGE_ACCOUNT_KEY=""
TENANT_ID=""
SUBSCRIPTION_ID=""
RESOURCE_GROUP_NAME="photo-gallery"

# Azure Application related settings required for Authentication
CLIENT_ID = "" # Application (client) ID of app registration
CLIENT_SECRET = "" # Placeholder - for use ONLY during testing.
AUTHORITY = "https://login.microsoftonline.com/f0810adb-cc95-47b3-8733-1e42bd72619d"
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

RECYCLE_BIN_DIRECTORY="RecycleBin-ToBeDeleted"
# "https://None@cxp-insights-album.scm.azurewebsites.net/cxp-insights-album.git"
# https://learn.microsoft.com/en-us/azure/app-service/deploy-local-git?tabs=cli

# [Logger]
# logfilepath = <Path to log file>
# logfilename = <Name of log file>
# loglevel = Debug
# format = (message)