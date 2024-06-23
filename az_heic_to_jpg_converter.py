import os, uuid, sys
# from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
# from azure.core._match_conditions import MatchConditions
# from azure.storage.filedatalake._models import ContentSettings
# import configreader
# configDict = configreader.read_config()
import app_config
from PIL import Image
import pillow_heif
import io

from azure.storage.blob import BlobServiceClient, ContainerClient, generate_container_sas, BlobSasPermissions
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fastapi import UploadFile

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
    acceptble_img_format=['JPEG','JPG','GIF','PNG','TIFF','TIF','BMP','EPS','RAW','CR2','NEF','ORF','SR2','WDP','HEIC']
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

def get_particular_type_files_list(file_system_client, directory_path="", file_type=".heic"):
    particular_type_file_list = []
    dir_path_list = [directory_path]
    file_type = file_type.upper()
    while (True):
        if len(dir_path_list) == 0: #First time the loop starts
            dir_path_list.append("")
        path_list = get_dl_directory_contents(file_system_client=file_system_client, directory_path=dir_path_list[0]) 
        print (f"Running for {dir_path_list[0]}")
        for path,is_dir in path_list:
            if is_dir == True:
                dir_path_list.append(path)
            if is_dir == False:
                if path.upper().endswith(file_type):
                    particular_type_file_list.append(path)
        del dir_path_list[0]
        if len(dir_path_list) <= 0:
            break
    return particular_type_file_list


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

def copy_heic_file_to_jpeg(file_system_client: DataLakeServiceClient.get_file_system_client, directory, file):
    try:
        directory_client = file_system_client.get_directory_client(directory)
        file_client_read = directory_client.get_file_client(file)
        #file_path = open(file_client_read,'r')
        #file_contents = file_path.read()

        fileNameSplit = file.split(".")
        # print (fileNameSplit[0])
        fileNamePrefix = fileNameSplit[0]

        download = file_client_read.download_file()
        downloaded_bytes = download.readall()
        print ("File downloaded")
        heif_file = pillow_heif.read_heif(downloaded_bytes)
        # print (heif_file.mode)
        # print (heif_file.size)
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw",
        )
        width, height = image.size
        # print (width, height)
        # Adjust Image size by reducing width and corresponding height
        TARGET_WIDTH = 1000
        coefficient = width / TARGET_WIDTH
        new_height = height / coefficient
        new_file = fileNamePrefix + ".jpeg"
        print (new_file)
        # print (TARGET_WIDTH, new_height)
        # TARGET_WIDTH = 1020
        # new_height = 720
        optimalSizeImage = image.resize((int(TARGET_WIDTH),int(new_height)),Image.LANCZOS)
        print (type(optimalSizeImage))
        imgByteArr = io.BytesIO()
        # imgByteArr = optimalSizeImage.tobytes("xbm", "rgb")
        # imgByteArr = optimalSizeImage.tobytes("raw")
        optimalSizeImage.save(imgByteArr, format("jpeg"),quality=50)
        imagedata = imgByteArr.getvalue()
        # print (type(downloaded_bytes), type(imgByteArr), type(imagedata))
        
        file_client_write = directory_client.create_file(new_file)
        file_client_write.upload_data(imagedata, overwrite=True)

    except Exception as e:
        print(e)
        raise


def copy_heic_file_list(file_system_client: DataLakeServiceClient.get_file_system_client, heic_files_list):
    heic_files_list_len = len(heic_files_list)
    print ("Number of heic files to be converted: ", heic_files_list_len)
    for file_name in heic_files_list:
        file_name_partition = file_name.rpartition("/")
        print (file_name_partition[0], file_name_partition[2])
        print (type(file_name_partition))
        copy_heic_file_to_jpeg(file_system_client=file_system_client, directory=file_name_partition[0], file=file_name_partition[2])    

def move_files_to_recycle_bin(file_system_client: DataLakeServiceClient.get_file_system_client, fileList):
    bin_directory_client = file_system_client.get_directory_client("RecycleBin-ToBeDeleted")
    for filePath in fileList:
        print (filePath)
        file_name_partition = filePath.rpartition("/")
        # print (file_name_partition[0], file_name_partition[2])
        directory = file_name_partition[0]
        file = file_name_partition[2]

        directory_client = file_system_client.get_directory_client(directory)
        file_client_read = directory_client.get_file_client(file)

        downloadedFile = file_client_read.download_file()
        # downloaded_bytes = download.readall()

        file_client_write = bin_directory_client.create_file(file)
        file_client_write.upload_data(downloadedFile, overwrite=True)

        file_client_read.delete_file()

        # heif_file = pillow_heif.read_heif(downloaded_bytes)
        # # print (heif_file.mode)
        # # print (heif_file.size)
        # image = Image.frombytes(
        #     heif_file.mode,
        #     heif_file.size,
        #     heif_file.data,
        #     "raw",
        # )
        # width, height = image.size
        # # print (width, height)
        # # Adjust Image size by reducing width and corresponding height
        # TARGET_WIDTH = 1000
        # coefficient = width / TARGET_WIDTH
        # new_height = height / coefficient
        # new_file = fileNamePrefix + ".jpeg"
        # # print (new_file)
        # optimalSizeImage = image.resize((int(TARGET_WIDTH),int(new_height)),Image.LANCZOS)
        # # print (type(optimalSizeImage))
        # imgByteArr = io.BytesIO()
        # optimalSizeImage.save(imgByteArr, format("jpeg"),quality=50)
        # imagedata = imgByteArr.getvalue()
        # # print (type(downloaded_bytes), type(imgByteArr), type(imagedata))
        
        # file_client_write = directory_client.create_file(new_file)
        # file_client_write.upload_data(imagedata, overwrite=True)
        # if delete_heic_file_flag == 1:
        #     file_client_read.delete_file()
        #     # print ("Deleted File: ", file)

service_client=get_dl_service_client()
file_system_client=get_dl_file_system(service_client)
fileList = ["Mix/Friends/WhatsApp Image 2023-11-04 at 11.39.50.jpeg", "Mix/Friends/WhatsApp Image 2023-11-04 at 11.41.19.jpeg"]
move_files_to_recycle_bin(file_system_client, fileList)


# allHeicFiles = get_particular_type_files_list(file_system_client,"Mix/Friends", file_type=".heic")

# print (allHeicFiles)
# print (len(allHeicFiles))
# copy_heic_file_with_jpeg(file_system_client, "Mix/Friends", "20231205_200637.heic", container_client)
# copy_heic_file_list(file_system_client, allHeicFiles)
# import json
# a="['Mix/Friends/20231205_200637.heic'\054 'Mix/Friends/20231205_200638.heic']"
# print (a, type(a))

# b=list(a)
# print (b, type(b))
# c = a.split(",")
# print (c, type(c))

# d=eval(a)
# print (d, type(d))

print ("The End")

#
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