from typing import Union, List
from fastapi import FastAPI, Request, File, UploadFile, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
from common_code import az_storage_conn, az_data_lake
import msal
import app_config
import logging, json, os
import jwt
from fastapi.middleware.cors import CORSMiddleware
import datetime
# from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

########################################### Extract variable values from environment / configuration file ############################### 

authority=app_config.AUTHORITY
endpoint=app_config.ENDPOINT
scope=app_config.SCOPE
session_type=app_config.SESSION_TYPE
msal_cache_dir=app_config.MSAL_CACHE_DIR

if 'AUTHORITY' in os.environ:
    authority=os.getenv('AUTHORITY')
else:
    authority=app_config.AUTHORITY

if 'CLIENT_ID' in os.environ:
    client_id=os.getenv('CLIENT_ID')
else:
    client_id=app_config.CLIENT_ID

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

if 'CLIENT_SECRET' in os.environ:
    client_secret=os.getenv('CLIENT_SECRET')
else:
    client_secret=app_config.CLIENT_SECRET

if 'REDIRECT_PATH' in os.environ:
    redirect_path=os.getenv('REDIRECT_PATH')
else:
    redirect_path=app_config.REDIRECT_PATH


################################################## Enable Logging ################################################## 
logging.basicConfig(format='%(asctime)s-%(levelname)s-%(message)s', datefmt='%d-%b-%y %H:%M:%S', filename='logs.txt')
logger = logging.getLogger('urllib3')
logger.setLevel(logging.INFO)
################################################## Complete ################################################## 

container_client=az_storage_conn.get_container_client()
# container_sas=az_storage_conn.create_service_sas_container(container_client=container_client,account_key=storage_account_key)
# container_sas="?"+container_sas
# print (container_sas)
service_client=az_data_lake.get_dl_service_client()
file_system_client=az_data_lake.get_dl_file_system(service_client)
directory_path=""

app = FastAPI()
app.mount("/static",StaticFiles(directory="static"),name="static")
templates = Jinja2Templates(directory="templates", autoescape=False, auto_reload=True)
# app.add_middleware(HTTPSRedirectMiddleware)

# Adding CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# flow = {}
# user_name = ''
logger.info("App loaded !!!")
# print ("Printing main function ...")

################################################## Common Functions ################################################## 
def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        client_id=client_id, authority=authority,
        client_credential=client_secret, token_cache=None
        # msal.SerializableTokenCache()
        )

msal_cca=_build_msal_app(authority=authority)

def _build_auth_code_flow(authority=None, scopes=None,request: Union[Request, None] = None):
    logger.info ("Inside _build_auth_code_flow .....")
    return msal_cca.initiate_auth_code_flow(scopes or [],
                                    # redirect_uri=app_config.REDIRECT_PATH)
                                            #  redirect_uri=app.url_path_for('view_photos_root')
                                            # redirect_uri=view_photos_root(Request).get("raw_url")
                                            # redirect_uri="http://localhost:8000/authorized"
                                            # redirect_uri=request.url_for('authorized')  ## WORKS
                                            # redirect_uri=str(request.url_for('authorized')).replace("http://","https://") ## WORKS
                                            # redirect_uri="https://fastapiphotoalbum-app.azurewebsites.net/authorized" ## WORKS
                                            redirect_uri=redirect_path
                                            )           

def create_cookie(response: Union[RedirectResponse,Jinja2Templates.TemplateResponse], cookie_key: str, cookie_val: str):
    # content = {"message": "token cookie set"}
    response.set_cookie(key=cookie_key, value=cookie_val)
    return response
# <class 'starlette.templating._TemplateResponse'>
# <class 'starlette.responses.RedirectResponse'>

def get_cookie(request: Request,cookie_key: str):
    cookie_val = request.cookies.get(cookie_key)
    return cookie_val

def remove_cookie(response: Union[RedirectResponse,Jinja2Templates.TemplateResponse], cookie_key: str):
    response.delete_cookie(key=cookie_key)
    return True

def decode_token(token: jwt):
    alg = jwt.get_unverified_header(token)['alg']
    decoded_token = jwt.decode(token, algorithms=[alg], options={"verify_signature": False})
    return decoded_token

def get_user_name(token: jwt):
    decoded_token = decode_token(token)
    # accessTokenFormatted = json.dumps(decoded_token, indent=2)
    user_full_name = decoded_token['name']
    user_first_name = user_full_name.split(" ")[0]
    return user_first_name

def validate_access_token(token: jwt):
    decoded_token = decode_token(token)
    epoch_exp_time = decoded_token["exp"]
    epoch_datetime_obj=datetime.fromtimestamp(epoch_exp_time)
    current_time = datetime.now()
    if epoch_datetime_obj > current_time:
        return True
    else:
        return False


# @app.get("/cookie")
# def create_cookie_set():
#     content = {"message": "cookie set"}
#     response = JSONResponse(content=content)
#     response.set_cookie(key="kk_msal_token", value="admin")
#     return response

# @app.get("/read_cookie")
# async def read_cookie(access_token: str):
#     return {"access_token": access_token} 

################################################## Bootstrap Test ################################################## 
# @app.get("/bs-test")
# async def bs_test(request: Request):
#     response = templates.TemplateResponse('bs_test.html',{"request": request})
#     return response


# @app.get("/submit")
# async def submit(nm: str = Form(...), pwd: str = Form(...)):
#    return {"username": nm}

@app.post("/submit")
async def submit(nm: str = Form(...), pwd: str = Form(...)):
   return {"username": nm}

################################################## Test Function to Read Cookie ################################################## 
@app.get("/read_cookie")
async def read_cookie(request: Request, cookie_key: str = 'access_token'):
    return {cookie_key: request.cookies.get(cookie_key) }

# @app.get("/delete_cookie")
# def delete_cookie(response, token):
#     content = {"message": "token cookie delete"}
#     response = JSONResponse(content=content)
#     response.delete_cookie(key="kk_msal_token")
#     return response

################################################## Login Functions (GET and POST) ################################################## 
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    logger.info("Inside login - GET")
    # logger.info(" Test login print statement")
    # print ("inside login ...", flush=True)
    print ("Dumping scope .... ")
    print (scope)
    flow = _build_auth_code_flow(scopes=scope, request=request)
    # print (json.dumps(flow))
    # print (flow)
    # print (type(flow))

    # print (" ...........................full url path ...........")
    # print (request.url._url)
    response = RedirectResponse(flow['auth_uri'])
    create_cookie(response, 'auth_code_flow', json.dumps(flow))
    return response
    # return templates.TemplateResponse('login.html',{"request": request, "auth_url":flow['auth_uri']})

@app.post("/login", response_class=HTMLResponse)
def login_page_post(request: Request):
    logger.info("Inside login - POST")
    # logger.info(" Test login print statement")
    # print ("inside login ...", flush=True)
    flow = _build_auth_code_flow(scopes=scope, request=request)
    print (flow)
    # print (" ...........................full url path ...........")
    # print (request.url._url)
    response = RedirectResponse(flow['auth_uri'])
    create_cookie(response, 'auth_code_flow', json.dumps(flow))
    # remove_cookie(response, cookie_key="access_token")
    # remove_cookie(response, cookie_key="refresh_token")
    # remove_cookie(response, cookie_key="user_first_name")
    return response
    # return templates.TemplateResponse('login.html',{"request": request, "auth_url":flow['auth_uri']})

################################################## Home Page Function (GET) ################################################## 

@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    # print ("In home /")
    logger.info("Inside / - GET")
    logger.info ("Checking if accounts exist to acquire token silently")
    accounts = msal_cca.get_accounts()
    # print (request.url_for("view_photos_root")
    # for a in accounts:
    #     print (a)
    # print ("printing cookie val: ", get_cookie(request, cookie_key='access_token'))
    # response=RedirectResponse(url=request.url_for('view_photos_root'), status_code=307)
    response=RedirectResponse(url='/view-photos-root', status_code=307)
    if accounts:
        result = msal_cca.acquire_token_silent(scopes=scope, account=accounts[0])
        # print (result)
        if "access_token" in result:
            logger.info("Token silently acquired.")
            create_cookie(response, 'access_token', result["access_token"])

            user_first_name=get_user_name(result['access_token'])
            create_cookie(response, 'user_first_name', user_first_name)

            container_sas=az_storage_conn.create_service_sas_container(container_client=container_client,account_key=storage_account_key)
            container_sas="?"+container_sas
            create_cookie(response, 'container_sas', container_sas)
            # print (result["access_token"])
        #    return RedirectResponse(url="/view-photos-root")
            return response
        # print ("Finished till before redirect statement ....")
    else:
        return RedirectResponse(url=request.url_for('login_page'), status_code=307)
        # return RedirectResponse(url=request.url_for('login_page_post'), status_code=307)
    # return "{Hello World}"
    # return RedirectResponse(url="/login",status_code=200)
    # return templates.TemplateResponse('index.html',{"request": request})
    # return {"Hello": "World"}

@app.post("/", response_class=HTMLResponse)
def home_page_post(request: Request):
    logger.info("Inside / - POST")
    # print ("In home /")
    accounts = msal_cca.get_accounts()
    response=RedirectResponse(url='/view-photos-root', status_code=307)
    if accounts:
        result = msal_cca.acquire_token_silent(scope, account=accounts[0])
        # print (result)
        if "access_token" in result:
            logger.info("Token silently acquired.")
            # print (result["access_token"])
            create_cookie(response, 'access_token', result["access_token"])

            user_first_name=get_user_name(result['access_token'])
            create_cookie(response, 'user_first_name', user_first_name)
            
            container_sas=az_storage_conn.create_service_sas_container(container_client=container_client,account_key=storage_account_key)
            container_sas="?"+container_sas
            create_cookie(response, 'container_sas', container_sas)
            return response
        # print ("Finished till before redirect statement ....")
    else:
        return RedirectResponse(url="/login")
#     # return RedirectResponse(url="/login",status_code=200)
#     # return templates.TemplateResponse('index.html',{"request": request})
#     # return {"Hello": "World"}

# @app.get("/verify-token")
# def verify_token(request: Request):
#     access_token = get_cookie(request, cookie_key='access_token')
#     result = msal_cca.verify_token(access_token, app_config.SCOPE)
#     return result

################################################## Authorize Function to receive token (GET) ################################################## 

@app.get("/authorized", response_class=HTMLResponse)
def authorized(request: Request):
    logger.info("Inside authorized - GET")
    # print (request)
    # print (request.body)
    # print (json.dumps(request.json))
    # print ("printing code .......")
    # print (code)
    # print (request.query_params)
    # print (request.query_params.get("code"))
    # print ("printing flow .....")
    auth_code_flow = json.loads(get_cookie(request, cookie_key='auth_code_flow'))
    print ("printing auth code flow : ")
    print (auth_code_flow)
    # flow = _build_auth_code_flow(scopes=app_config.SCOPE)
    # print (flow1)
    # code = request.query_params.get("code")
    code_dict={
        "code":request.query_params.get("code"),
        "client_info":request.query_params.get("client_info"),
        "state":request.query_params.get("state"),
        "session_state":request.query_params.get("session_state")
    }
    # print (" ........ printing flow and code type ........")
    # print (type(flow1))
    # print (type(request.query_params))
    # print (" ........ acquire_token_by_auth_code_flow call ........")
    logger.info("acquire_token_by_auth_code_flow call ...")
    result = msal_cca.acquire_token_by_auth_code_flow(auth_code_flow, code_dict)
    if "error" in result:
        return "An error occured in acquire_token_by_auth_code_flow... "
    print ("Dumping Result ....................................")
    print (json.dumps(result))
    # id_token_claims=result.get("id_token_claims")
    # print (result)
    # print (str(cookie_set_result))
    # return templates.TemplateResponse('index.html',{"request": request})
    response = RedirectResponse(url="/view-photos-root", status_code=307)
    logger.info ("Access token to be saved in cookies")
    # print (type(response))
    create_cookie(response, 'access_token', result['access_token'])
    create_cookie(response, 'refresh_token', result['refresh_token'])
    user_first_name=get_user_name(result['access_token'])
    create_cookie(response, 'user_first_name', user_first_name)
    container_sas=az_storage_conn.create_service_sas_container(container_client=container_client,account_key=storage_account_key)
    container_sas="?"+container_sas
    create_cookie(response, 'container_sas', container_sas)
    # response.set_cookie(key="kk_msal_token", value=result['access_token'])
    return response


################################################## Logout Function ################################################## 
@app.post("/logout")
def logout(request: Request):
    logger.info("Inside logout - POST")
    user_name = get_cookie(request, cookie_key='user_first_name')
    logger.info(f"User {user_name} logged out.")
    # Clear token cache
    msal_cca.remove_account(msal_cca.get_accounts()[0])
    response = templates.TemplateResponse('logout.html',{"request": request, "user_name": user_name})
    # Remove session cookie
    # response.delete_cookie("session")
    # remove_cookie(response, cookie_key="session")
    remove_cookie(response, cookie_key="access_token")
    remove_cookie(response, cookie_key="refresh_token")
    remove_cookie(response, cookie_key="user_first_name")
    # Add Cache-Control header
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    # print (type(response))
    return response


################################################## View photos at root path ################################################## 
@app.post("/view-photos-root", response_class=HTMLResponse)
def view_photos_root(request: Request):
    logger.info("Inside view-photos-root - POST")
    try:
        user_name = get_cookie(request, cookie_key='user_first_name')
        # alg = jwt.get_unverified_header(access_token)['alg']
        # decoded_token = jwt.decode(access_token, algorithms=[alg], options={"verify_signature": False})
        # accessTokenFormatted = json.dumps(decoded_token, indent=2)
        # # decoded_token = jwt.decode(access_token, verify=False, algorithms=['HS256'])
        # global user_name
        # # if user_name == '':
        # user_name = decoded_token['name']
        logger.info(f"User {user_name} is logged in.")
        logger.info("User name derived from access token")
        # print (decoded_token)
        # print ("---------------------------------")
        # print (accessTokenFormatted)
    except:
        return RedirectResponse(url=request.url_for('login_page'))
    logger.info("Browsing photos at root path")
    directory_path=""
    path_list = az_data_lake.get_dl_directory_contents(file_system_client, directory_path)
    dir_path_list, img_path_list, video_path_list = az_data_lake.split_dir_and_img_files(path_list)
    blob_prefix_path = az_data_lake.get_blob_prefix_path(directory_path)
    all_dir_list = az_data_lake.get_dl_directory_list(file_system_client)
    container_sas = get_cookie(request, cookie_key='container_sas')
    # for path in img_path_list:
    #     print (path)
    return templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": directory_path, "all_dir_list": all_dir_list, "user_name": user_name, "video_path_list": video_path_list, "container_sas": container_sas}) 
    # return render_template('view_root.html',dir_path_list=dir_path_list, img_path_list=img_path_list, blob_prefix_path=blob_prefix_path, directory_path=directory_path)


################################################## View Photos at root path (GET) ################################################## 
@app.get("/view-photos-root", response_class=HTMLResponse)
def view_photos_root(request: Request):
    logger.info("Inside view-photos-root - GET")
    try:
        # access_token = get_cookie(request, cookie_key='access_token')
        # alg = jwt.get_unverified_header(access_token)['alg']
        # decoded_token = jwt.decode(access_token, algorithms=[alg], options={"verify_signature": False})
        # accessTokenFormatted = json.dumps(decoded_token, indent=2)
        # # decoded_token = jwt.decode(access_token, verify=False, algorithms=['HS256'])
        # global user_name
        # # if user_name == '':
        # user_name = decoded_token['name']
        user_name = get_cookie(request, cookie_key='user_first_name')
        logger.info(f"User {user_name} is logged in.")
        logger.info("User name derived from access token")
        # print (decoded_token)
        # print ("---------------------------------")
        # print (accessTokenFormatted)
    except:
        return RedirectResponse(url=request.url_for('login_page'))
    logger.info("Browsing photos at root path")
    directory_path=""
    path_list = az_data_lake.get_dl_directory_contents(file_system_client, directory_path)
    print (path_list)
    dir_path_list, img_path_list, video_path_list = az_data_lake.split_dir_and_img_files(path_list)
    blob_prefix_path = az_data_lake.get_blob_prefix_path(directory_path)
    all_dir_list = az_data_lake.get_dl_directory_list(file_system_client)
    container_sas = get_cookie(request, cookie_key='container_sas')
    # for path in img_path_list:
    #     print (path)
    return templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": directory_path, "all_dir_list": all_dir_list, "user_name": user_name, "video_path_list": video_path_list, "container_sas": container_sas}) 
    # return render_template('view_root.html',dir_path_list=dir_path_list, img_path_list=img_path_list, blob_prefix_path=blob_prefix_path, directory_path=directory_path)


################################################## View Photos at chosen path ################################################## 
# @app.post("/view-photos-dyn/test123", response_class=HTMLResponse)
# def view_photos_dyn(request: Request, directory_path: str = "test123"):
#     logger.info("Inside view-photos-dyn - POST")
#     print ("Directory Path:" + directory_path)
#     path_list = az_data_lake.get_dl_directory_contents(file_system_client, directory_path)
#     dir_path_list, img_path_list = az_data_lake.split_dir_and_img_files(path_list)
#     blob_prefix_path = az_data_lake.get_blob_prefix_path(directory_path)
#     all_dir_list = az_data_lake.get_dl_directory_list(file_system_client)
#     logger.info(f"Browsing photos at this path --> {directory_path}")
#     # for path in img_path_list:
#     #     print (path)
#     return templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": directory_path, "all_dir_list": all_dir_list, "user_name": user_name}) 


# Direct call of this method was resulting in CSS and JS not rendering. Hence, a new funtion /view-selected-subfolder is created as a work-around.
# @app.post("/view-photos-dyn/{directory_path:path}", response_class=HTMLResponse)
# def view_photos_dyn(request: Request, directory_path: str):
#     logger.info("Inside view-photos-dyn - POST")
#     print ("Directory Path:" + directory_path)
#     path_list = az_data_lake.get_dl_directory_contents(file_system_client, directory_path)
#     # print (path_list)
#     dir_path_list, img_path_list, video_path_list = az_data_lake.split_dir_and_img_files(path_list)
#     blob_prefix_path = az_data_lake.get_blob_prefix_path(directory_path)
#     all_dir_list = az_data_lake.get_dl_directory_list(file_system_client)
#     user_name = get_cookie(request, cookie_key='user_first_name')
#     container_sas = get_cookie(request, cookie_key='container_sas')
#     logger.info(f"Browsing photos at this path --> {directory_path}")
#     # for path in img_path_list:
#     #     print (path)
#     return templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": directory_path, "all_dir_list": all_dir_list, "user_name": user_name, "video_path_list": video_path_list, "container_sas": container_sas}) 
#     # return templates.TemplateResponse('view.html', {"request": request})

# @app.get("/view-photos-dyn/{directory_path:path}", response_class=HTMLResponse)
# def view_photos_dyn(request: Request, directory_path: str):
#     print ("Printing directory path : ")
#     print (directory_path)
#     if "static" in directory_path:
#         return
#     path_list = az_data_lake.get_dl_directory_contents(file_system_client, directory_path)
#     dir_path_list, img_path_list = az_data_lake.split_dir_and_img_files(path_list)
#     blob_prefix_path = az_data_lake.get_blob_prefix_path(directory_path)
#     all_dir_list = az_data_lake.get_dl_directory_list(file_system_client)
#     logger.info(f"Browsing photos at this path (GET) --> {directory_path}")
#     # for path in img_path_list:
#     #     print (path)
#     return templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": directory_path, "all_dir_list": all_dir_list, "user_name": user_name}) 
#     # return render_template('view_root.html',dir_path_list=dir_path_list, img_path_list=img_path_list, blob_prefix_path=blob_prefix_path, directory_path=directory_path)

# Removed this line from dir_path_list loop in view.html <!-- {% set href_path = url_for('view_photos_dyn',directory_path=path_without_space) %} -->

################################################## Select photos to upload at chosen path ################################################## 
@app.post("/upload", response_class=HTMLResponse)
def upload(request: Request):
    logger.info("Inside upload - POST")
    user_name = get_cookie(request, cookie_key='user_first_name')
    try:
        access_token = get_cookie(request, cookie_key='access_token')
        alg = jwt.get_unverified_header(access_token)['alg']
        decoded_token = jwt.decode(access_token, algorithms=[alg], options={"verify_signature": False})
    except:
        return RedirectResponse(url=request.url_for('/'), status_code=307)
    dir_path_list=az_data_lake.get_dl_directory_list(file_system_client)
    created_dir=""
    # print ("Dir path list: ")
    # print (dir_path_list)
    return templates.TemplateResponse('upload.html', {"request": request, "dir_path_list": dir_path_list, "created_dir": created_dir, "user_name": user_name})

################################################## Upload Photos at chosen path ################################################## 
@app.post("/upload-photos")
async def upload_photos(request: Request,dir_name: str = Form(...), photos_file: List[UploadFile] = File(...)):
    logger.info("Inside upload_photos - POST")
    user_name = get_cookie(request, cookie_key='user_first_name')
    # print (dir_name)
    # print (photos_file.filename)
    # print (len(photos_file))
    # for _file in photos_file:
    #     print (_file.filename)
    #     print (_file.file)
    #     print (_file)
    #     print (type(_file), type(_file.file),type(_file.filename))
    filenames, count = az_storage_conn.upload_multiple_files_to_storage(container_client, photos_file, dir_name)
    # print (filenames)
    # print (count)
    logger.info(f"Uploaded {count} files in {dir_name}. File names are {filenames}.")
    return templates.TemplateResponse('upload_result.html', {"request": request, "filenames": filenames, "count": count, "user_name": user_name})

################################################## View Photos at chosen path ################################################## 
@app.post("/view-selected-folder")
def view_selected_folder(request: Request, dir_name: str = Form(...)):
    logger.info("Inside view-selected-folder - POST")
    # print (dir_name)
    path_list = az_data_lake.get_dl_directory_contents(file_system_client, dir_name)
    dir_path_list, img_path_list, video_path_list = az_data_lake.split_dir_and_img_files(path_list)
    blob_prefix_path = az_data_lake.get_blob_prefix_path()
    all_dir_list = az_data_lake.get_dl_directory_list(file_system_client)
    user_name = get_cookie(request, cookie_key='user_first_name')
    # for path in img_path_list:
    #     print (path)
    # print (video_path_list)
    container_sas = get_cookie(request, cookie_key='container_sas')
    logger.info(f"Browsing photos at this path --> {dir_name}")
    if dir_name == "/":
        return templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": "", "all_dir_list": all_dir_list, "user_name": user_name, "video_path_list": video_path_list, "container_sas": container_sas}) 
    else:
        return templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": dir_name, "all_dir_list": all_dir_list, "user_name": user_name, "video_path_list": video_path_list, "container_sas": container_sas}) 


@app.post("/view-selected-subfolder")
def view_selected_folder(request: Request, dyn_dir_name: str = Form(...)):
    logger.info("Inside view-selected-subfolder - POST")
    dir_name = dyn_dir_name
    print ("dir_name: " + dir_name)
    path_list = az_data_lake.get_dl_directory_contents(file_system_client, dir_name)
    # print (path_list)
    dir_path_list, img_path_list, video_path_list = az_data_lake.split_dir_and_img_files(path_list)
    blob_prefix_path = az_data_lake.get_blob_prefix_path()
    all_dir_list = az_data_lake.get_dl_directory_list(file_system_client)
    user_name = get_cookie(request, cookie_key='user_first_name')
    # for path in img_path_list:
    #     print (path)
    # print (video_path_list)
    container_sas = get_cookie(request, cookie_key='container_sas')
    logger.info(f"Browsing photos at this path --> {dir_name}")
    if dir_name == "/":
        return templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": "", "all_dir_list": all_dir_list, "user_name": user_name, "video_path_list": video_path_list, "container_sas": container_sas}) 
    else:
        # return dyn_dir_name
        return templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": dir_name, "all_dir_list": all_dir_list, "user_name": user_name, "video_path_list": video_path_list, "container_sas": container_sas}) 


################################################## Create a new folder at chosen path ##################################################    
@app.post("/new-folder")
async def new_folder(request: Request, dir_name: str = Form(...), new_folder: str = Form(...)):
    logger.info("Inside new_folder - POST")
    created_dir = az_data_lake.create_directory(file_system_client, dir_name, new_folder)
    logger.info(f"Created folder {new_folder} inside {dir_name}")
    dir_path_list=az_data_lake.get_dl_directory_list(file_system_client)
    user_name = get_cookie(request, cookie_key='user_first_name')
    # print ("Dir path list: ")
    # print (dir_path_list)
    return templates.TemplateResponse('upload.html', {"request": request, "dir_path_list": dir_path_list, "created_dir": created_dir, "user_name": user_name})

################################################## About ##################################################    
@app.get("/about")
async def new_folder(request: Request):
    logger.info("Inside About - GET")
    return templates.TemplateResponse('about.html', {"request": request})

################################################## Contact ##################################################    
@app.get("/contact")
async def new_folder(request: Request):
    logger.info("Inside Contact - GET")
    return templates.TemplateResponse('contact.html', {"request": request})

################################################## Raise Issue ##################################################    
@app.get("/report-issue")
async def new_folder(request: Request):
    logger.info("Inside Report Issue - GET")
    return templates.TemplateResponse('report_issue.html', {"request": request})

################################################## All routes defined. Program Ends here.  ##################################################  

    # content_assignment = await photos_file.read()
    # for file in request.files.getlist("photos"):
    #     print (file)
    # return templates.TemplateResponse('upload_photos.html', {"request": request})
                                                    
# @app.route("/view-photos-root", methods=['POST','GET'])
# def view_photos_root():
#     directory_path=""
#     path_list = az_data_lake.get_dl_directory_contents(service_client, file_system_client, directory_path)
#     dir_path_list, img_path_list = az_data_lake.split_dir_and_img_files(path_list)
#     blob_prefix_path = az_data_lake.get_blob_prefix_path(directory_path)
#     for path in img_path_list:
#         print (path)
#     return render_template('view_root.html',dir_path_list=dir_path_list, img_path_list=img_path_list, blob_prefix_path=blob_prefix_path, directory_path=directory_path)

# @app.route("/view-photos-dyn/<path:directory_path>", methods=['POST','GET'])
# def view_photos_dyn(directory_path):
#     path_list = az_data_lake.get_dl_directory_contents(service_client, file_system_client, directory_path)
#     dir_path_list, img_path_list = az_data_lake.split_dir_and_img_files(path_list)
#     blob_prefix_path = az_data_lake.get_blob_prefix_path(directory_path)
#     for path in img_path_list:
#         print (path)
#     return render_template('view.html',dir_path_list=dir_path_list, img_path_list=img_path_list, blob_prefix_path=blob_prefix_path, directory_path=directory_path)

# @app.route("/view-photos", methods=['POST','GET'])
# def view_photos():
#     img_html = ""
#     count=0
#     blob_url=[]
#     blob_items = container_client.list_blobs() # list all the blobs in the container
#     for blob in blob_items:
#         blob_client = container_client.get_blob_client(blob=blob.name) # get blob client to interact with the blob and get blob url
#         # img_html += "<img src='{}' width='auto' height='200'/>".format(blob_client.url) # get the blob url and append it to the html
#         blob_url.append(blob_client.url)
#         count+=1
#     return "<p>{}".format(blob_url)

# @app.route("/view-photos", methods=['POST','GET'])
# def view_photos():
#     blob_items = container_client.list_blobs()
#     return render_template('view.html',container_client=container_client)

# @app.route("/upload-photos", methods=["POST"])
# def upload_photos():
#     filenames = ""
#     total_files = 0
#     for file in request.files.getlist("photos"):
#         try:
#             container_client.upload_blob(file.filename, file, overwrite=True) # upload the file to the container using the filename as the blob name
#             filenames += file.filename + "\n" 
#             total_files+=1
#         except Exception as e:
#             print(e)
#             print("Ignoring duplicate filenames") # ignore duplicate filenames
    
#     filenames=filenames[:len(filenames)-1]
#     print (f"<p>Uploaded: {filenames}</p>")
#     return render_template('upload.html', total_files=total_files, filenames=f"{filenames}") 


# @app.get("/items")

# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: Union[str, None] = None):
#     return {"item_id": item_id, "q": q} 

# @app.put("/items/{item_id}")
# def update_item(item_id: int, item: Item):
#     return {"item_name": item.name, "item_id": item_id}



# uvicorn main:app --reload

# if __name__ == '__main__':
    # uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True )
    # uvicorn.run("app:app", port=8000, reload=True )
# -- In console, run---> uvicorn app:app --reload

# result = app.acquire_token_by_refresh_token(refresh_token="your_refresh_token", scopes=["https://graph.microsoft.com/.default"])
# access_token = result["access_token"]