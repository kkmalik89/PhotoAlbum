from azure.storage.blob import BlobServiceClient, ContainerClient, generate_container_sas, BlobSasPermissions
from datetime import datetime
from dateutil.relativedelta import relativedelta
# import configreader
# configDict = configreader.read_config()
from fastapi import UploadFile
import app_config
import os

# connect_str=configDict['Az-Storage']['AZURE_STORAGE_CONNECTION_STRING']
# container_name=configDict['Az-Storage']['CONTAINER_PATH']
# storage_account_name=configDict['Az-Storage']['STORAGE_ACCOUNT_NAME']
# storage_account_key=configDict['Az-Storage']['STORAGE_ACCOUNT_KEY']

# storage_account_name=app_config.STORAGE_ACCOUNT_NAME
# container_name=app_config.CONTAINER_NAME
# storage_account_key=storage_account_key=app_config.STORAGE_ACCOUNT_KEY

if 'STORAGE_ACCOUNT_NAME' in os.environ:
    storage_account_name=os.getenv('STORAGE_ACCOUNT_NAME')
else:
    storage_account_name=app_config.STORAGE_ACCOUNT_NAME

if 'CONTAINER_NAME' in os.environ:
    container_name=os.getenv('CONTAINER_NAME')
else:
    container_name=app_config.CONTAINER_NAME

if 'STORAGE_ACCOUNT_KEY' in os.environ:
    storage_account_key=os.getenv('STORAGE_ACCOUNT_KEY')
else:
   storage_account_key=app_config.STORAGE_ACCOUNT_KEY

def get_container_client():
    # blob_service_client = BlobServiceClient.from_connection_string(conn_str=connect_str) # create a blob service client to interact with the storage account
    account_url="{}://{}.blob.core.windows.net".format("https", storage_account_name)
    blob_service_client = BlobServiceClient(account_url=account_url, credential=storage_account_key)
    try:
        container_client = blob_service_client.get_container_client(container=container_name) # get container client to interact with the container in which images will be stored
        container_client.get_container_properties() # get properties of the container to force exception to be thrown if container does not exist
    except Exception as e:
        raise
        # container_client = blob_service_client.create_container(container_name) # create a container in the storage account if it does not exist
    return container_client

def upload_multiple_files_to_storage(container_client: ContainerClient, files_list: list[UploadFile], dir_name: str):
    filenames = ''
    count=0
    for _file in files_list:
        # print (_file.filename)
        if dir_name == "/":
            blob_file_name = _file.filename
        else:
            blob_file_name = dir_name + '/' + _file.filename
        container_client.upload_blob(blob_file_name, _file.file, overwrite=True) # upload the file to the container using the filename as the blob name
        filenames += _file.filename + "\n"
        count+=1
    filenames=filenames[:len(filenames)-1]
    return filenames, count

def create_service_sas_container(container_client: ContainerClient, account_key: str):
    # Create a SAS token that's valid for one day, as an example
    start_time = datetime.utcnow()
    expiry_time = start_time + relativedelta(days=1)
    #Generate Container SAS 
    sas_token = generate_container_sas(
        account_name=container_client.account_name,
        container_name=container_client.container_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
        start=start_time
    )
    return sas_token