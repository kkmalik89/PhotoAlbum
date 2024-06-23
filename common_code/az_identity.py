from azure.identity import ClientSecretCredential, DefaultAzureCredential
import app_config
import os

if 'TENANT_ID' in os.environ:
    tenant_id=os.getenv('TENANT_ID')
else:
    tenant_id=app_config.TENANT_ID

if 'CLIENT_ID' in os.environ:
    client_id=os.getenv('CLIENT_ID')
else:
    client_id=app_config.CLIENT_ID

if 'CLIENT_SECRET' in os.environ:
    client_secret=os.getenv('CLIENT_SECRET')
else:
    client_secret=app_config.CLIENT_SECRET

def get_token_credential(tenant_id: str, application_id: str, application_secret: str):
    return ClientSecretCredential(tenant_id, application_id, application_secret)