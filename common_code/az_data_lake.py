import os, uuid, sys
# from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
# from azure.core._match_conditions import MatchConditions
# from azure.storage.filedatalake._models import ContentSettings
# import configreader
# configDict = configreader.read_config()
import app_config

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

def get_dl_service_client():  
    try:  
        # global service_client
        service_client = DataLakeServiceClient(account_url="{}://{}.dfs.core.windows.net".format(
            "https", storage_account_name), credential=storage_account_key)
    except Exception as e:
        print(e)
    return service_client

def get_dl_file_system(service_client):
    file_system_client = service_client.get_file_system_client(file_system=container_name)
    if not file_system_client.exists():
        file_system_client = service_client.create_file_system(file_system=container_name)
    return file_system_client

def get_dl_directory_contents(file_system_client, directory_path):
    paths = file_system_client.get_paths(path=directory_path, recursive=False)
    path_list=[]
    for path in paths:
        path_list.append([path.name,path.is_directory])
    return path_list

def split_dir_and_img_files(path_list):
    dir_path_list=[]
    img_path_list=[]
    video_path_list=[]
    acceptble_img_format=['JPEG','JPG','GIF','PNG','TIFF','TIF','BMP','EPS','RAW','CR2','NEF','ORF','SR2','WDP']
    acceptble_video_format=['MP4','MOV','WMV','FLV','AVI','AVCHD','WebM','MKV']
    for path,is_dir in path_list:
        if is_dir == True:
            dir_path_list.append(path)
        if is_dir == False:
            file_format=(path.split('.')[-1]).upper()
            # print (file_format)
            if file_format in acceptble_img_format:
                img_path_list.append(path)
            if file_format in acceptble_video_format:
                video_path_list.append(path)
    # print (dir_path_list, img_path_list, video_path_list)
    return dir_path_list, img_path_list, video_path_list

def get_blob_prefix_path(directory_path="/"):
    # if not directory_path:
    #      return f"https://{storage_account_name}.blob.core.windows.net/{container_name}/"
    # return f"https://{storage_account_name}.blob.core.windows.net/{container_name}/{directory_path}/"
    return f"https://{storage_account_name}.blob.core.windows.net/{container_name}/"

def get_dl_directory_list(file_system_client, directory_path="/"):
    paths = file_system_client.get_paths(path=directory_path, recursive=True)
    path_list=['/']
    for path in paths:
        if path.is_directory:
            path_list.append(path.name)
    return path_list

def create_directory(file_system_client, parent_directory, new_directory):
    if parent_directory == "/":
        dir_path = new_directory
    else:
        dir_path = parent_directory + "/" + new_directory
    file_system_client.create_directory(dir_path)
    return dir_path

# def upload_image_to_directory(file_system_client, directory_path, image_to_upload):
#     directory_client = file_system_client.get_directory_client(directory_path)
#     file_client = directory_client.create_file("IMG-20191119-WA0007-renamed.jpg")
#     local_file = open(image_to_upload,'r')
#     file_contents = local_file.read()
#     file_client.upload_data(file_contents, overwrite=True)
#     return True 

# def upload_file_to_directory(service_client,file_system_client, directory_path):
#     directory_client = file_system_client.get_directory_client(directory_path)
#     file_client = directory_client.create_file("uploaded-file.txt")
#     local_file = open("C:\Users\kanishkmalik\Documents\Personal\DCIM\Food fest delhi\IMG-20191119-WA0007.jpg",'r')
#     file_contents = local_file.read()
#     file_client.append_data(data=file_contents, offset=0, length=len(file_contents))
#     file_client.flush_data(len(file_contents))

# def create_dl_file_system(service_client,file_system_name="my-file-system"):
#     try:
#         # global file_system_client
#         file_system_client = service_client.create_file_system(file_system=file_system_name)
#     except Exception as e:
#         raise
#         print(e)
#     return file_system_name

# def create_directory(file_system_client):
#     try:
#         file_system_client.create_directory("my-directory")
#     except Exception as e:
#         print(e)
#     return True
    
# def rename_directory(service_client,file_system_name="my-file-system"):
#     try:
       
#        file_system_client = service_client.get_file_system_client(file_system=file_system_name)
#        directory_client = file_system_client.get_directory_client("my-directory")
       
#        new_dir_name = "my-directory-renamed"
#        directory_client.rename_directory(new_name=directory_client.file_system_name + '/' + new_dir_name)

#     except Exception as e:
#      print(e)

# def delete_directory(service_client,file_system_name="my-file-system"):
#     try:
#         file_system_client = service_client.get_file_system_client(file_system=file_system_name)
#         directory_client = file_system_client.get_directory_client("my-directory")

#         directory_client.delete_directory()
#     except Exception as e:
#         print(e)

# def get_dl_directory_contents(service_client,file_system_client, directory_path):
#     file_system_client = service_client.get_file_system_client(file_system="my-file-system")
#     paths = file_system_client.get_paths(path=directory_path)
#     path_dict=[]
#     for path in paths:
#         path_dict.append(path)


# def upload_file_to_directory():
#     try:

#         file_system_client = service_client.get_file_system_client(file_system="my-file-system")

#         directory_client = file_system_client.get_directory_client("my-directory")
        
#         file_client = directory_client.create_file("uploaded-file.txt")
#         local_file = open("C:\\file-to-upload.txt",'r')

#         file_contents = local_file.read()

#         file_client.append_data(data=file_contents, offset=0, length=len(file_contents))

#         file_client.flush_data(len(file_contents))

#     except Exception as e:
#       print(e)


# def download_file_from_directory():
#     try:
#         file_system_client = service_client.get_file_system_client(file_system="my-file-system")

#         directory_client = file_system_client.get_directory_client("my-directory")
        
#         local_file = open("C:\\file-to-download.txt",'wb')

#         file_client = directory_client.get_file_client("uploaded-file.txt")

#         download = file_client.download_file()

#         downloaded_bytes = download.readall()

#         local_file.write(downloaded_bytes)

#         local_file.close()

#     except Exception as e:
#      print(e)

# def list_directory_contents():
#     try:
        
#         file_system_client = service_client.get_file_system_client(file_system="my-file-system")

#         paths = file_system_client.get_paths(path="my-directory")

#         for path in paths:
#             print(path.name + '\n')

#     except Exception as e:
#      print(e)