from azure.mgmt.authorization import AuthorizationManagementClient
import app_config
import os
from azure.identity import ClientSecretCredential

if 'SUBSCRIPTION_ID' in os.environ:
    subscription_id=os.getenv('SUBSCRIPTION_ID')
else:
    subscription_id=app_config.SUBSCRIPTION_ID

if 'RESOURCE_GROUP_NAME' in os.environ:
    resource_group=os.getenv('RESOURCE_GROUP_NAME')
else:
    resource_group=app_config.RESOURCE_GROUP_NAME

if 'STORAGE_ACCOUNT_NAME' in os.environ:
    storage_account_name=os.getenv('STORAGE_ACCOUNT_NAME')
else:
    storage_account_name=app_config.STORAGE_ACCOUNT_NAME

if 'CONTAINER_NAME' in os.environ:
    container_name=os.getenv('CONTAINER_NAME')
else:
    container_name=app_config.CONTAINER_NAME

if 'CLIENT_ID' in os.environ:
    client_id=os.getenv('CLIENT_ID')
else:
    client_id=app_config.CLIENT_ID

if 'CLIENT_SECRET' in os.environ:
    client_secret=os.getenv('CLIENT_SECRET')
else:
    client_secret=app_config.CLIENT_SECRET

def get_AuthorizationManagementClient(credential: ClientSecretCredential):
    client = AuthorizationManagementClient(credential, subscription_id)
    return client

def get_scope():
    scope = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Storage/storageAccounts/{storage_account_name}/blobServices/default/containers/{container_name}"
    return scope

def get_role_assignments(client: AuthorizationManagementClient, scope: str):
    role_assignments = client.role_assignments.list_for_scope(scope=scope)
    return role_assignments

def get_user_role_assignments(client: AuthorizationManagementClient, scope: str, user_principal_id: str):
    role_assignments = client.role_assignments.list_for_scope(scope=scope, filter=f"principalId eq '{user_principal_id}'")
    return role_assignments

def get_role_definitions(role_assignments: AuthorizationManagementClient.role_assignments):
    role_definition_list = [assignment.role_definition_id for assignment in role_assignments]
    return role_definition_list

def check_user_access(client: AuthorizationManagementClient, role_definition_list: list):
    check_read_action=False
    for role_definition_id in role_definition_list:
        role_def = client.role_definitions.get_by_id(role_definition_id)
        role_def_dict = role_def.as_dict()
        actions_list = role_def_dict['permissions'][0]['data_actions']
        check_read_action = any('read' in action for action in actions_list)
        if check_read_action:
            return True
    return check_read_action
    
