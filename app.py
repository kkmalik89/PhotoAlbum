
## To run: uvicorn app:app --reload
## To check in local: http://localhost:8000 

from typing import Union, List
from fastapi import FastAPI, Request, File, UploadFile, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
from common_code import az_storage_conn, az_data_lake, az_identity, az_management
import msal
import app_config
import logging, json, os
import jwt
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Body
import datetime
from starlette.middleware.sessions import SessionMiddleware
import asyncio
# from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

# from fastapi import Depends, HTTPException
# from fastapi_server_session import SessionManager, Session, BaseSessionInterface

app = FastAPI()
########################################### Session Management Start ############################### 

# # Initialize session manager with in-memory session interface
# session_manager = SessionManager(interface=BaseSessionInterface())

# # Protected endpoint
# @app.get("/protected")
# async def protected_endpoint(session: Session = Depends(session_manager.use_session)):
#     # Get or set session data
#     session_key = session.get("all_dir_list", "default_value")
#     # session["all_dir_list"] = "new_value"

#     return {"message": f"Session key: {session_key}"}

########################################### Session Management End ############################### 

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

if 'TENANT_ID' in os.environ:
    tenant_id=os.getenv('TENANT_ID')
else:
    tenant_id=app_config.TENANT_ID

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

if 'CLIENT_ID' in os.environ:
    client_id=os.getenv('CLIENT_ID')
else:
    client_id=app_config.CLIENT_ID

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

# app = FastAPI()
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

app.add_middleware(SessionMiddleware, secret_key="123456")

# # Custom middleware to override session data
# async def override_session(request: Request, call_next):
#     # Modify session data here (e.g., request.session["my_var"] = "new_value")
#     request.session["my_var"] = "11223"
#     response = await call_next(request)
#     return response

# app.middleware("http")(override_session)

# flow = {}
# user_name = ''
logger.info("App loaded !!!")
# print ("Printing main function ...")

credential = az_identity.get_token_credential(tenant_id, client_id, client_secret)
auth_client = az_management.get_AuthorizationManagementClient(credential=credential)
container_scope = az_management.get_scope()

################################################## Common Functions ################################################## 
def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        client_id=client_id, authority=authority,
        client_credential=client_secret, token_cache=None
        # msal.SerializableTokenCache()
        )

msal_cca= _build_msal_app(authority=authority)

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
                                            , prompt="select_account"
                                            )           

def create_cookie(response: Union[RedirectResponse,Jinja2Templates.TemplateResponse, Response], cookie_key: str, cookie_val: str):
    # content = {"message": "token cookie set"}
    response.set_cookie(key=cookie_key, value=cookie_val)
    return response
# <class 'starlette.templating._TemplateResponse'>
# <class 'starlette.responses.RedirectResponse'>

def get_cookie(request: Request,cookie_key: str):
    cookie_val = request.cookies.get(cookie_key)
    return cookie_val

def get_cookie1(request: Request,cookie_key: str):
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

def get_user_principal_id(token: jwt):
    decoded_token = decode_token(token)
    # accessTokenFormatted = json.dumps(decoded_token, indent=2)
    user_principal_id = decoded_token['oid']
    return user_principal_id

def validate_access_token(token: jwt):
    decoded_token = decode_token(token)
    epoch_exp_time = decoded_token["exp"]
    epoch_datetime_obj=datetime.fromtimestamp(epoch_exp_time)
    current_time = datetime.now()
    if epoch_datetime_obj > current_time:
        return True
    else:
        return False
    
def get_user_access_flag(user_principal_id: str):
    role_assignments =  az_management.get_user_role_assignments(auth_client, container_scope, user_principal_id)
    role_definition_list =  az_management.get_role_definitions(role_assignments)
    user_access_flag =  az_management.check_user_access(auth_client, role_definition_list)
    if user_access_flag:
        return 1
    else:
        return 0


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

# @app.post("/submit")
# async def submit(nm: str = Form(...), pwd: str = Form(...)):
#    return {"username": nm}

################################################## Test Function to Read Cookie ################################################## 
@app.get("/read_cookie")
def read_cookie(request: Request, cookie_key: str = 'access_token'):
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
    # return RedirectResponse(url="/no-access")
    # logger.info(" Test login print statement")
    # print ("inside login ...", flush=True)
    # print ("Dumping scope .... ")
    # print (scope)
    flow = _build_auth_code_flow(scopes=scope, request=request)

    # print (" ...........................full url path ...........")
    # print (request.url._url)
    print ("printing auth_uri .........................")
    print (flow['auth_uri'])
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
    # if accounts:
    #     result = msal_cca.acquire_token_silent(scopes=scope, account=accounts[0])
    #     # print (result)
    #     if "access_token" in result:
    #         logger.info("Token silently acquired.")

    #         user_principal_id=get_user_principal_id(result['access_token'])
    #         user_access_flag = get_user_access_flag(user_principal_id)
    #         if user_access_flag == 0:
    #             return RedirectResponse(url="/no-access", status_code = 307)
    #         else:
    #             create_cookie(response, 'user_access_flag', user_access_flag)
    #         create_cookie(response, 'user_principal_id', user_principal_id)
    #         logger.info ("Access token to be saved in cookies")
    #         # print (type(response))
    #         create_cookie(response, 'access_token', result['access_token'])
    #         create_cookie(response, 'refresh_token', result['refresh_token'])
    #         user_first_name=get_user_name(result['access_token'])
    #         create_cookie(response, 'user_first_name', user_first_name)

    #         container_sas=az_storage_conn.create_service_sas_container(container_client=container_client,account_key=storage_account_key)
    #         container_sas="?"+container_sas
    #         create_cookie(response, 'container_sas', container_sas)

    #         return response
    #     print ("Finished till before redirect statement ....")
    #     else:
    #         return RedirectResponse(url=request.url_for('login_page'), status_code=307)
    # else:
    #     return RedirectResponse(url=request.url_for('login_page'), status_code=307)

    # print ("CheckMe ... ............. Pls ....................whats' going on")
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
    # if accounts:
        # response=RedirectResponse(url='/view-photos-root', status_code=307)
    #     result = msal_cca.acquire_token_silent(scope, account=accounts[0])
    #     # print (result)
    #     if "access_token" in result:
    #         logger.info("Token silently acquired.")
    #         user_principal_id=get_user_principal_id(result['access_token'])
    #         user_access_flag = get_user_access_flag(user_principal_id)
    #         if user_access_flag == 0:
    #             return RedirectResponse(url="/no-access", status_code = 307)
    #         else:
    #             create_cookie(response, 'user_access_flag', user_access_flag)
    #         create_cookie(response, 'user_principal_id', user_principal_id)
    #         logger.info ("Access token to be saved in cookies")
    #         # print (type(response))
    #         create_cookie(response, 'access_token', result['access_token'])
    #         create_cookie(response, 'refresh_token', result['refresh_token'])
    #         user_first_name=get_user_name(result['access_token'])
    #         create_cookie(response, 'user_first_name', user_first_name)
            
    #         container_sas=az_storage_conn.create_service_sas_container(container_client=container_client,account_key=storage_account_key)
    #         container_sas="?"+container_sas
    #         create_cookie(response, 'container_sas', container_sas)
    #         return response
    #     # print ("Finished till before redirect statement ....")
    #     else:
    #         return RedirectResponse(url="/login")
    # else:
    #     return RedirectResponse(url="/login")
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
    print (("Inside authorized - GET................................"))
    # print (request)
    # print (request.body)
    # print (json.dumps(request.json))
    # print ("printing code .......")
    # print (code)
    # print (request.query_params)
    # print (request.query_params.get("code"))
    # print ("printing flow .....")
    auth_code_flow_from_cookie = get_cookie(request, cookie_key='auth_code_flow')
    auth_code_flow = json.loads(auth_code_flow_from_cookie)
    # print ("printing auth code flow : ")
    # print (auth_code_flow)
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
    # print ("Dumping Result ....................................")
    # print (json.dumps(result))
    # id_token_claims=result.get("id_token_claims")
    # print (result)
    # print (str(cookie_set_result))
    # return templates.TemplateResponse('index.html',{"request": request})
    response = RedirectResponse(url="/view-photos-root", status_code=307)

    user_principal_id= get_user_principal_id(result['access_token'])
    user_access_flag =  get_user_access_flag(user_principal_id)
    if user_access_flag == 0:
        return RedirectResponse(url="/no-access", status_code = 307)
    else:
        create_cookie(response, 'user_access_flag', user_access_flag)
    create_cookie(response, 'user_principal_id', user_principal_id)
    logger.info ("Access token to be saved in cookies")
    # print (type(response))
    create_cookie(response, 'access_token', result['access_token'])
    create_cookie(response, 'refresh_token', result['refresh_token'])
    user_first_name= get_user_name(result['access_token'])
    create_cookie(response, 'user_first_name', user_first_name)
    
    container_sas= az_storage_conn.create_service_sas_container(container_client=container_client,account_key=storage_account_key)
    container_sas="?"+container_sas
    create_cookie(response, 'container_sas', container_sas)
    # response.set_cookie(key="kk_msal_token", value=result['access_token'])
    return response


################################################## Logout Function ################################################## 
@app.post("/logout")
def logout(request: Request):
    logger.info("Inside logout - POST")
    user_name =  get_cookie(request, cookie_key='user_first_name')
    logger.info(f"User {user_name} logged out.")
    # Clear token cache
    accounts = msal_cca.get_accounts()
    if accounts:
        msal_cca.remove_account(msal_cca.get_accounts()[0])
    response = templates.TemplateResponse('logout.html',{"request": request, "user_name": user_name})
    # Remove session cookie
    # response.delete_cookie("session")
    # remove_cookie(response, cookie_key="session")
    remove_cookie(response, cookie_key="access_token")
    remove_cookie(response, cookie_key="refresh_token")
    remove_cookie(response, cookie_key="user_first_name")
    remove_cookie(response, cookie_key="container_sas")
    remove_cookie(response, cookie_key="user_principal_id")
    remove_cookie(response, cookie_key="user_access_flag")
    remove_cookie(response, cookie_key="auth_code_flow")
    remove_cookie(response, cookie_key="all_dir_list")
    # Add Cache-Control header
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    # print (type(response))
    return response

################################################## Clear Cache ################################################## 

@app.get("/clear-cookies")
def clear_cookies(request: Request):
    logger.info("Inside clear cache")
    user_name =  get_cookie(request, cookie_key='user_first_name')
    directory_path=""
    path_list = az_data_lake.get_dl_directory_contents(file_system_client, directory_path)
    print (path_list)
    dir_path_list, img_path_list, video_path_list = az_data_lake.split_dir_and_img_files(path_list)
    blob_prefix_path = az_data_lake.get_blob_prefix_path(directory_path)
    # all_dir_list = az_data_lake.get_dl_directory_list(file_system_client)
    all_dir_list = ['/']
    container_sas= az_storage_conn.create_service_sas_container(container_client=container_client,account_key=storage_account_key)
    container_sas="?"+container_sas
    response = templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": directory_path, "all_dir_list": all_dir_list, "user_name": user_name, "video_path_list": video_path_list, "container_sas": container_sas}) 

    remove_cookie(response, cookie_key="access_token")
    remove_cookie(response, cookie_key="refresh_token")
    # remove_cookie(response, cookie_key="user_first_name")
    remove_cookie(response, cookie_key="container_sas")
    # remove_cookie(response, cookie_key="user_principal_id")
    # remove_cookie(response, cookie_key="user_access_flag")
    # remove_cookie(response, cookie_key="auth_code_flow")
    remove_cookie(response, cookie_key="all_dir_list")
  
    create_cookie(response, 'container_sas', container_sas)
    # create_cookie(response, cookie_key="all_dir_list", cookie_val=all_dir_list)
    # for path in img_path_list:
    #     print (path)
    return response

################################################## View Photos at root path (GET) ################################################## 

# # # # # # # # # # # # # # # # # # # 
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
        user_access_flag = get_cookie(request, cookie_key='user_access_flag')
        print ("values of user_access_flag : ", user_access_flag)
        if user_access_flag is None:
            print ("Inside blank user_access_Flag")
            return RedirectResponse(url="/login")
        if user_access_flag == "0":
            return RedirectResponse(url='/no-access')
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
    all_dir_list = get_cookie(request, cookie_key="all_dir_list")
    if not all_dir_list:
        all_dir_list = ['/']
    else:
        all_dir_list = eval(all_dir_list)
    container_sas = get_cookie(request, cookie_key='container_sas')
    response = templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": directory_path, "all_dir_list": all_dir_list, "user_name": user_name, "video_path_list": video_path_list, "container_sas": container_sas}) 
    # create_cookie(response, cookie_key="all_dir_list", cookie_val=all_dir_list)
    # for path in img_path_list:
    #     print (path)
    return response
    # return render_template('view_root.html',dir_path_list=dir_path_list, img_path_list=img_path_list, blob_prefix_path=blob_prefix_path, directory_path=directory_path)

################################################## View photos at root path ################################################## 
@app.post("/view-photos-root", response_class=HTMLResponse)
def view_photos_root(request: Request):
    # Code to check whether user has storage access
    logger.info("Inside view-photos-root - POST")
    try:
        user_name = get_cookie(request, cookie_key='user_first_name')
        user_access_flag = get_cookie(request, cookie_key='user_access_flag')
        print ("values of user_access_flag : ", user_access_flag)
        if user_access_flag is None:
            print ("Inside blank user_access_Flag")
            return RedirectResponse(url="/login")
        if user_access_flag == "0":
            return RedirectResponse(url='/no-access')
    
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
    all_dir_list = get_cookie(request, cookie_key="all_dir_list")
    if not all_dir_list:
        all_dir_list = ['/']
    else:
        all_dir_list = eval(all_dir_list)
    container_sas = get_cookie(request, cookie_key='container_sas')
    response = templates.TemplateResponse('view.html', {"request": request, "dir_path_list": dir_path_list, "img_path_list": img_path_list, "blob_prefix_path": blob_prefix_path, "directory_path": directory_path, "all_dir_list": all_dir_list, "user_name": user_name, "video_path_list": video_path_list, "container_sas": container_sas}) 
    # create_cookie(response, cookie_key="all_dir_list", cookie_val=all_dir_list)
    # for path in img_path_list:
    #     print (path)
    return response
    # return render_template('view_root.html',dir_path_list=dir_path_list, img_path_list=img_path_list, blob_prefix_path=blob_prefix_path, directory_path=directory_path)


################################################## View Photos at chosen path ################################################## 
@app.post("/view-selected-folder")
def view_selected_folder(request: Request, dir_name: str = Form(...)):
    logger.info("Inside view-selected-folder - POST")
    # print (dir_name)
    path_list = az_data_lake.get_dl_directory_contents(file_system_client, dir_name)
    dir_path_list, img_path_list, video_path_list = az_data_lake.split_dir_and_img_files(path_list)
    blob_prefix_path = az_data_lake.get_blob_prefix_path()
    all_dir_list = get_cookie(request, cookie_key="all_dir_list")
    if not all_dir_list:
        all_dir_list = ['/']
    else:
        all_dir_list = eval(all_dir_list)
    if not all_dir_list:
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
    all_dir_list = get_cookie(request, cookie_key="all_dir_list")
    if not all_dir_list:
        all_dir_list = ['/']
    else:
        all_dir_list = eval(all_dir_list)
    if not all_dir_list:
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
        alg =  jwt.get_unverified_header(access_token)['alg']
        decoded_token =  jwt.decode(access_token, algorithms=[alg], options={"verify_signature": False})
    except:
        return RedirectResponse(url=request.url_for('/'), status_code=307)
    # dir_path_list=az_data_lake.get_dl_directory_list(file_system_client)
    all_dir_list = get_cookie(request, cookie_key="all_dir_list")
    if not all_dir_list:
        all_dir_list = ['/']
    else:
        all_dir_list = eval(all_dir_list)
    created_dir=""
    # print ("Dir path list: ")
    # print (dir_path_list)
    return templates.TemplateResponse('upload.html', {"request": request, "dir_path_list": all_dir_list, "created_dir": created_dir, "user_name": user_name, "directory_path":"","filenames": ""})

################################################## Upload Photos at chosen path ################################################## 
@app.post("/upload-photos")
def upload_photos(request: Request,dir_name: str = Form(...), photos_file: List[UploadFile] = File(...)):
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
    filenames, count = az_storage_conn.upload_multiple_files_to_storage(container_client, photos_file, dir_name, user_name)
    all_dir_list = get_cookie(request, cookie_key="all_dir_list")
    if not all_dir_list:
        all_dir_list = ['/']
    else:
        all_dir_list = eval(all_dir_list)
    # print (filenames)
    # print (count)
    logger.info(f"Uploaded {count} files in {dir_name}. File names are {filenames}.")
    # return templates.TemplateResponse('upload_result.html', {"request": request, "filenames": filenames, "count": count, "user_name": user_name, "directory_path": dir_name})    
    return templates.TemplateResponse('upload.html', {"request": request, "dir_path_list": all_dir_list, "created_dir": "", "user_name": user_name, "directory_path":dir_name, "filenames": filenames, "fileCount": count})



# @app.post("/upload-photos")
# def upload_photos(request: Request,dir_name: str = Form(...), photos_file: List[UploadFile] = File(...)):
#     logger.info("Inside upload_photos - POST")
#     user_name = get_cookie(request, cookie_key='user_first_name')
#     # print (dir_name)
#     # print (photos_file.filename)
#     # print (len(photos_file))
#     # for _file in photos_file:
#     #     print (_file.filename)
#     #     print (_file.file)
#     #     print (_file)
#     #     print (type(_file), type(_file.file),type(_file.filename))
#     filenames, count = az_storage_conn.upload_multiple_files_to_storage(container_client, photos_file, dir_name)
#     # print (filenames)
#     # print (count)
#     logger.info(f"Uploaded {count} files in {dir_name}. File names are {filenames}.")
#     return templates.TemplateResponse('upload_result.html', {"request": request, "filenames": filenames, "count": count, "user_name": user_name})

################################################## Create a new folder at chosen path ##################################################    
@app.post("/new-folder")
def new_folder(request: Request, dir_name: str = Form(...), new_folder: str = Form(...)):
    logger.info("Inside new_folder - POST")
    created_dir = az_data_lake.create_directory(file_system_client, dir_name, new_folder)
    logger.info(f"Created folder {new_folder} inside {dir_name}")
    dir_path_list= az_data_lake.get_dl_directory_list(file_system_client)
    user_name = get_cookie(request, cookie_key='user_first_name')

    response = templates.TemplateResponse('upload.html', {"request": request, "dir_path_list": dir_path_list, "created_dir": created_dir, "user_name": user_name, "filenames":""})
    # create_cookie(response, cookie_key="all_dir_list", cookie_val=dir_path_list)

    # print ("Dir path list: ")
    # print (dir_path_list)
    return response


################################################## About ##################################################    
@app.get("/about")
def new_folder(request: Request):
    logger.info("Inside About - GET")
    return templates.TemplateResponse('about.html', {"request": request})

################################################## Contact ##################################################    
@app.get("/contact")
def new_folder(request: Request):
    logger.info("Inside Contact - GET")
    return templates.TemplateResponse('contact.html', {"request": request})

################################################## Raise Issue ##################################################    
@app.get("/report-issue")
def new_folder(request: Request):
    logger.info("Inside Report Issue - GET")
    return templates.TemplateResponse('report_issue.html', {"request": request})

################################################## No Access Message - GET ##################################################    
@app.get("/no-access")
def no_access_func(request: Request):
    logger.info("Inside No Access function - GET")
    return templates.TemplateResponse('no_access_msg.html', {"request": request})

################################################## No Access Message - POST ##################################################    
@app.post("/no-access")
def no_access_func(request: Request):
    logger.info("Inside No Access function - POST")
    return templates.TemplateResponse('no_access_msg.html', {"request": request})

################################################## Convert heif files to jpeg root - POST ##################################################    
@app.post("/convert-heic-files-root")
def convert_heic_files_jo_jpeg_root(request: Request):
    logger.info("Inside convert_heic_files_jo_jpeg - POST")
    user_name = get_cookie(request, cookie_key='user_first_name')
    try:
        access_token = get_cookie(request, cookie_key='access_token')
        alg =  jwt.get_unverified_header(access_token)['alg']
        decoded_token =  jwt.decode(access_token, algorithms=[alg], options={"verify_signature": False})
    except:
        return RedirectResponse(url=request.url_for('/'), status_code=307)
    all_dir_list = get_cookie(request, cookie_key="all_dir_list")
    if not all_dir_list:
        all_dir_list = ['/']
    else:
        all_dir_list = eval(all_dir_list)
    # heic_files_list=az_data_lake.get_particular_type_files_list(file_system_client, directory_path="/", file_type=".heic")
    response = templates.TemplateResponse('convert_heif_format.html', {"request": request, "user_name": user_name, "all_dir_list":all_dir_list, "no_dir_selected": 1})
    remove_cookie(response, cookie_key="heic_files_list")
    remove_cookie(response, cookie_key='heic_dir')
    return response

################################################## Convert heif files to jpeg - POST ##################################################    

@app.post("/convert-heic-files")
def convert_heic_files_jo_jpeg(request: Request, dir_name: str = Form(...)):
    logger.info("Inside convert_heic_files_jo_jpeg - POST")
    user_name = get_cookie(request, cookie_key='user_first_name')
    try:
        access_token = get_cookie(request, cookie_key='access_token')
        alg =  jwt.get_unverified_header(access_token)['alg']
        decoded_token =  jwt.decode(access_token, algorithms=[alg], options={"verify_signature": False})
    except:
        return RedirectResponse(url=request.url_for('/'), status_code=307)
    all_dir_list = get_cookie(request, cookie_key="all_dir_list")
    if not all_dir_list:
        all_dir_list = ['/']
    else:
        all_dir_list = eval(all_dir_list)
    heic_files_list=az_data_lake.get_particular_type_files_list(file_system_client, directory_path=dir_name, file_type=".heic")
    print (heic_files_list)
    response = templates.TemplateResponse('convert_heif_format.html', {"request": request, "user_name": user_name, "all_dir_list":all_dir_list, "heic_files_list": heic_files_list, "dir_name":dir_name, "no_dir_selected": 0})
    create_cookie(response, 'heic_files_list', heic_files_list)
    create_cookie(response, 'heic_dir', dir_name)
    return response

@app.post("/convert-selected-files-to-jpeg")
def convert_selected_heic_files_jo_jpeg(request: Request):
    logger.info("Inside convert_selected_heic_files_to_jpeg - POST")
    user_name = get_cookie(request, cookie_key='user_first_name')
    try:
        access_token = get_cookie(request, cookie_key='access_token')
        alg =  jwt.get_unverified_header(access_token)['alg']
        decoded_token =  jwt.decode(access_token, algorithms=[alg], options={"verify_signature": False})
    except:
        return RedirectResponse(url=request.url_for('/'), status_code=307)

    all_dir_list = get_cookie(request, cookie_key="all_dir_list")
    if not all_dir_list:
        all_dir_list = ['/']
    else:
        all_dir_list = eval(all_dir_list)
    heic_files_list_from_cookie = get_cookie(request, cookie_key='heic_files_list')
    heic_files_list_to_be_deleted = eval(heic_files_list_from_cookie)
    dir_name = get_cookie(request, cookie_key='heic_dir')
    print (heic_files_list_to_be_deleted)
    az_data_lake.overwrite_heic_file_list(file_system_client=file_system_client, heic_files_list=heic_files_list_to_be_deleted)
    response = templates.TemplateResponse('convert_heif_format.html', {"request": request, "user_name": user_name,  "all_dir_list":all_dir_list, "heic_files_list_deleted": heic_files_list_to_be_deleted,"dir_name":dir_name, "no_dir_selected": 1, "conversion_flag": 1})
    remove_cookie(response, cookie_key="heic_files_list")
    remove_cookie(response, cookie_key='heic_dir')
    return response
    

################################################## Delete & Move Files  ##################################################  

@app.post("/move-files-to-bin")
def move_files_to_bin(fileList: list = Body(...)):
    logger.info("Inside move-files-to-bin function ")
    all_files_moved = az_data_lake.move_files_to_recycle_bin(file_system_client=file_system_client, fileList=fileList)
    if all_files_moved:
        return {"FilesMovedToBin": fileList}
    else:
        return {"ErrorInMovingFilesToBin": fileList}
    
@app.post("/delete-folder-recursively")
def delete_folder_recursively(folderName: str = Body(...)):
    logger.info("Inside delete-folder-recursively function ")
    logging.info("Permanently deleting folder: " + folderName)
    folderDeleteStatus = az_data_lake.permanently_delete_files(file_system_client=file_system_client, folderName=folderName)
    if (folderDeleteStatus):
        logging.info("Permanently deleted folder: " + folderName)
        return (folderName)
    # all_files_moved = az_data_lake.move_files_to_recycle_bin(file_system_client=file_system_client, fileList=fileList)
    # if all_files_moved:
    #     return {"FilesMovedToBin": fileList}
    # else:
    #     return {"ErrorInMovingFilesToBin": fileList}

    
class clsMoveFiles(BaseModel):
    fileList: list
    moveToFolder: str
    
@app.post("/move-files-to-another-folder")
def move_files_to_bin(objMoveFiles: clsMoveFiles):
    # print (objMoveFiles.fileList)
    # print (objMoveFiles.moveToFolder)
    logger.info("Inside move-files-to-another-folder function ")
    fileList = objMoveFiles.fileList
    folderName = objMoveFiles.moveToFolder
    all_files_moved = az_data_lake.move_files_to_another_folder(file_system_client=file_system_client, fileList=fileList, folderName=folderName)
    if all_files_moved:
        return {"FilesMovedToAnotherFolder": fileList}
    else:
        return {"ErrorInMovingFilesToAnotherFolder": fileList}

@app.post("/get-all-dir-list")
def get_all_dir_list(response: Response):
    logger.info("Inside /get-all-dir-list function ")
    all_dir_list = az_data_lake.get_dl_directory_list(file_system_client)
    # create_cookie(response, 'all_dir_list', all_dir_list)
    print ("all_dir_list cookie created")
    return {"all_dir_list": all_dir_list}

@app.post("/get-all-dir-local-storage")
def get_all_dir_list_storage(request: Request, response: Response):
    logger.info("Inside /get-all-dir-list function ")
    all_dir_list = az_data_lake.get_dl_directory_list(file_system_client)
    # print (all_dir_list)
    # all_dir_list = ['/', '2019', '2019/Diwali 2019', '2019/First Car - Seltos - 2019', '2019/Food fest delhi', '2019/Impact day 2019', '2019/Ishu Wedding', '2019/Nestle-OfficeTrip-Nov 2019', '2019/Office-Manager Milestone - 2019', '2019/Pune Mumbai Goa 2019', '2019/Shruti bday 2019']
    # all_dir = request.session.get("allDirList")
    # print ("printing from session storage :  : : ")
    # print (all_dir)
    # return {"all_dir_list": all_dir_list}
    return all_dir_list

# # @app.middleware("http")
# @app.get("/a")
# async def a(request: Request):
#     request.session["my_var"] = "1235"
#     all_dir_list = ['/', '2019', '2019/Diwali 2019', '2019/First Car - Seltos - 2019', '2019/Food fest delhi', '2019/Impact day 2019', '2019/Ishu Wedding', '2019/Nestle-OfficeTrip-Nov 2019', '2019/Office-Manager Milestone - 2019', '2019/Pune Mumbai Goa 2019', '2019/Shruti bday 2019', '2019/Sirsa Oct 2019', '2019/Smaash - Games & Fun', '2019/Trip Dec 2019', '2020', '2020/Agroha Dec 2020 Ftbd', '2020/Anniversary 2020', '2020/Diwali 2020', '2020/Fatehabad 2020', '2020/Holi 2020 Ftbd', '2020/Hyd Office Trip-Jan 20', '2020/Kanishk bday 2020', '2020/Karwachauth 2020', '2020/Lockdown 2020', '2020/Shruti bday 2020', '2021', '2021/Anniversary 2021', '2021/Anu Marriage Nov 2021', '2021/Arshu Dec 2021', '2021/Arshu birth Cloudnine', '2021/Babyshower Sep 2021', '2021/Dev and Raju Meet - Before Corona Time', '2021/Diwali 2021', '2021/Housewarming and outing', '2021/Jitu Shaadi', '2021/Karwachauth 2021', '2021/Shailley bro wedding', '2021/Sumi visit - Feb 8', '2022', '2022/Amritsar trip Aug 2022', '2022/Anniversary 2022', '2022/April 2022', '2022/Arshu 1st Birthday', '2022/Arshu 1st Birthday/Arshu 1st bday home camera', '2022/Arshu Jan 2022', '2022/Arshu Namkaran 13Mar22', '2022/Arshu-Random', '2022/Chacha home', '2022/Dhanteras 2022', '2022/Diwali 2022', '2022/Fatehabad Aug 2022', '2022/Fatehabad Mar 2022', '2022/Fatehabad May 2022', '2022/Fatehabad Nov 2022', '2022/July Aug 2022', '2022/June 2022', '2022/Karwachauth 2022', '2022/Kerala trip 2022', '2022/March 2022', '2022/Maruti Family Day', '2022/May 2022', '2022/Nainital trip 2022', '2022/Nov 2022', '2022/Oct 2022', '2022/Panchgaon', '2022/Rakhi 2022', '2022/Sahoo Shaadi', '2022/Sep 2022', '2022/Shruti Bday 2022', '2022/Tanu Bhai Shaadi', '2022/Vasundhara Jan Feb 22', '2023', '2023/Anniversary 2023', '2023/Anusha 1st birthday', '2023/Arshu 2nd birthday', '2023/BLR ofc trip March 23', '2023/Bangalore Office Trip - October 23', '2023/Bangalore Office Trip - October 23/Ex-Deloitte Dinner', '2023/Bangalore Office Trip - October 23/Office Colleague Photos', '2023/Bangla sahib mughal grdn feb 2023', "2023/Choti cousin Sanya's shadi Mar 23", '2023/Dec - Sham chacha visit', '2023/December - Arshu', '2023/Deloitte-LWD-Jan 5, 2023', '2023/Diwali', '2023/Feb 2023', '2023/Holi 2023', '2023/Jan 2023', '2023/Kanishk bday 2023', '2023/Karwachauth', '2023/March 2023', '2023/Meenu Gurgaon Trip', '2023/Mussorie & Haridwar Trip', '2023/Mussorie & Haridwar Trip - May 23', '2023/Mussorie & Haridwar Trip - May 23/Haridwar', '2023/Mussorie & Haridwar Trip - May 23/Sahasradhara', '2023/Nuppy visit to India - Delhi (AIIMS) - 30 April, 2023', '2023/Rishabh marriage', '2023/Sahu visit to Ggn - December, 2023', '2023/Shaivi Gurgaon Trip - October', '2023/Shubham Marriage', '2023/Sikkim-Darjeeling Trip', '2023/Sikkim-Darjeeling Trip/24-Sept', '2023/Sikkim-Darjeeling Trip/25-Sept', '2023/Sikkim-Darjeeling Trip/26-Sep', '2023/Sikkim-Darjeeling Trip/27-Sep', '2023/Sikkim-Darjeeling Trip/28-Sep', '2023/Sikkim-Darjeeling Trip/29-Sep', '2023/Sikkim-Darjeeling Trip/30-Sep', '2023/Sikkim-Darjeeling Trip/Airport', '2024', '2024/26-Jan - Fun with camera', '2024/April- May : Arshu', '2024/BLR Office Trip - Feb 24', '2024/Feb - Fatehabad home', '2024/Jan-Feb Arshu', '2024/June - Elan mall visit', '2024/June - Noida office', '2024/Kanishk birthday', '2024/March - Sham chacha home visit', '2024/March - club house', '2024/May - Big B visit', 'Mix', 'Mix/Friends', 'Mix/Gurgaon Misc', 'Mix/Oldies', 'Mix/Random', 'RecycleBin-ToBeDeleted', 'RecycleBin-ToBeDeleted/2024_02_18_01_28_23_281473', 'RecycleBin-ToBeDeleted/2024_02_18_01_29_16_375277', 'RecycleBin-ToBeDeleted/2024_02_18_12_50_15_414959', 'RecycleBin-ToBeDeleted/abcd', 'RecycleBin-ToBeDeleted/abcd/def']
#     request.session["all_dir_list"] = all_dir_list
#     # response = await call_next(request)
#     # return response
#     return {"message": "Session variable my_var and all_dir_list set"}

# @app.get("/b")
# async def b(request: Request):
#     logger.info("Inside /get-session-var function ")
#     all_dir = request.session.get("all_dir_list")
#     print ("printing from session storage :  : : ")
#     print (all_dir)
#     return {"Dir": all_dir, "my_var": request.session.get("my_var")}

# @app.get("/c")
# async def c(request: Request):
#     # Update a value in session
#     request.session["my_var"] = "1236"
#     all_dir_list = ['/', '2019', '2019/Diwali 2019', '2019/First Car - Seltos - 2019', '2019/Food fest delhi', '2019/Impact day 2019', '2019/Ishu Wedding', '2019/Nestle-OfficeTrip-Nov 2019', '2019/Office-Manager Milestone - 2019', '2019/Pune Mumbai Goa 2019', '2019/Shruti bday 2019', '2019/Sirsa Oct 2019', '2019/Smaash - Games & Fun', '2019/Trip Dec 2019', '2020', '2020/Agroha Dec 2020 Ftbd', '2020/Anniversary 2020', '2020/Diwali 2020', '2020/Fatehabad 2020', '2020/Holi 2020 Ftbd', '2020/Hyd Office Trip-Jan 20', '2020/Kanishk bday 2020', '2020/Karwachauth 2020', '2020/Lockdown 2020', '2020/Shruti bday 2020', '2021', '2021/Anniversary 2021', '2021/Anu Marriage Nov 2021', '2021/Arshu Dec 2021', '2021/Arshu birth Cloudnine', '2021/Babyshower Sep 2021', '2021/Dev and Raju Meet - Before Corona Time', '2021/Diwali 2021', '2021/Housewarming and outing', '2021/Jitu Shaadi', '2021/Karwachauth 2021', '2021/Shailley bro wedding', '2021/Sumi visit - Feb 8', '2022', '2022/Amritsar trip Aug 2022', '2022/Anniversary 2022', '2022/April 2022', '2022/Arshu 1st Birthday', '2022/Arshu 1st Birthday/Arshu 1st bday home camera', '2022/Arshu Jan 2022', '2022/Arshu Namkaran 13Mar22', '2022/Arshu-Random', '2022/Chacha home', '2022/Dhanteras 2022', '2022/Diwali 2022', '2022/Fatehabad Aug 2022', '2022/Fatehabad Mar 2022', '2022/Fatehabad May 2022', '2022/Fatehabad Nov 2022', '2022/July Aug 2022', '2022/June 2022', '2022/Karwachauth 2022', '2022/Kerala trip 2022', '2022/March 2022', '2022/Maruti Family Day', '2022/May 2022', '2022/Nainital trip 2022', '2022/Nov 2022', '2022/Oct 2022', '2022/Panchgaon', '2022/Rakhi 2022', '2022/Sahoo Shaadi', '2022/Sep 2022', '2022/Shruti Bday 2022', '2022/Tanu Bhai Shaadi', '2022/Vasundhara Jan Feb 22', '2023', '2023/Anniversary 2023', '2023/Anusha 1st birthday', '2023/Arshu 2nd birthday', '2023/BLR ofc trip March 23', '2023/Bangalore Office Trip - October 23', '2023/Bangalore Office Trip - October 23/Ex-Deloitte Dinner', '2023/Bangalore Office Trip - October 23/Office Colleague Photos', '2023/Bangla sahib mughal grdn feb 2023', "2023/Choti cousin Sanya's shadi Mar 23", '2023/Dec - Sham chacha visit', '2023/December - Arshu', '2023/Deloitte-LWD-Jan 5, 2023', '2023/Diwali', '2023/Feb 2023', '2023/Holi 2023', '2023/Jan 2023', '2023/Kanishk bday 2023', '2023/Karwachauth', '2023/March 2023', '2023/Meenu Gurgaon Trip', '2023/Mussorie & Haridwar Trip', '2023/Mussorie & Haridwar Trip - May 23', '2023/Mussorie & Haridwar Trip - May 23/Haridwar', '2023/Mussorie & Haridwar Trip - May 23/Sahasradhara', '2023/Nuppy visit to India - Delhi (AIIMS) - 30 April, 2023', '2023/Rishabh marriage', '2023/Sahu visit to Ggn - December, 2023', '2023/Shaivi Gurgaon Trip - October', '2023/Shubham Marriage', '2023/Sikkim-Darjeeling Trip', '2023/Sikkim-Darjeeling Trip/24-Sept', '2023/Sikkim-Darjeeling Trip/25-Sept', '2023/Sikkim-Darjeeling Trip/26-Sep', '2023/Sikkim-Darjeeling Trip/27-Sep', '2023/Sikkim-Darjeeling Trip/28-Sep', '2023/Sikkim-Darjeeling Trip/29-Sep', '2023/Sikkim-Darjeeling Trip/30-Sep', '2023/Sikkim-Darjeeling Trip/Airport', '2024', '2024/26-Jan - Fun with camera', '2024/April- May : Arshu', '2024/BLR Office Trip - Feb 24', '2024/Feb - Fatehabad home', '2024/Jan-Feb Arshu', '2024/June - Elan mall visit', '2024/June - Noida office', '2024/Kanishk birthday', '2024/March - Sham chacha home visit', '2024/March - club house', '2024/May - Big B visit', 'Mix', 'Mix/Friends', 'Mix/Gurgaon Misc', 'Mix/Oldies', 'Mix/Random', 'RecycleBin-ToBeDeleted', 'RecycleBin-ToBeDeleted/2024_02_18_01_28_23_281473', 'RecycleBin-ToBeDeleted/2024_02_18_01_29_16_375277', 'RecycleBin-ToBeDeleted/2024_02_18_12_50_15_414959', 'RecycleBin-ToBeDeleted/abcd', 'RecycleBin-ToBeDeleted/abcd/def']
#     all_dir_str = ",".join(str(element) for element in all_dir_list)
#     request.session["all_dir_list"] = all_dir_str
#     return {"message": "Session variable updated"}

# @app.get("/set_session")
# async def set_session(request: Request):
#     # Set a value in session
#     request.session["my_var"] = "Hello, session ... hi !"
#     all_dir_list = ['/', '2019', '2019/Diwali 2019', '2019/First Car - Seltos - 2019', '2019/Food fest delhi', '2019/Impact day 2019', '2019/Ishu Wedding', '2019/Nestle-OfficeTrip-Nov 2019', '2019/Office-Manager Milestone - 2019', '2019/Pune Mumbai Goa 2019', '2019/Shruti bday 2019', '2019/Sirsa Oct 2019', '2019/Smaash - Games & Fun', '2019/Trip Dec 2019', '2020', '2020/Agroha Dec 2020 Ftbd', '2020/Anniversary 2020', '2020/Diwali 2020', '2020/Fatehabad 2020', '2020/Holi 2020 Ftbd', '2020/Hyd Office Trip-Jan 20', '2020/Kanishk bday 2020', '2020/Karwachauth 2020', '2020/Lockdown 2020', '2020/Shruti bday 2020', '2021', '2021/Anniversary 2021', '2021/Anu Marriage Nov 2021', '2021/Arshu Dec 2021', '2021/Arshu birth Cloudnine', '2021/Babyshower Sep 2021', '2021/Dev and Raju Meet - Before Corona Time', '2021/Diwali 2021', '2021/Housewarming and outing', '2021/Jitu Shaadi', '2021/Karwachauth 2021', '2021/Shailley bro wedding', '2021/Sumi visit - Feb 8', '2022', '2022/Amritsar trip Aug 2022', '2022/Anniversary 2022', '2022/April 2022', '2022/Arshu 1st Birthday', '2022/Arshu 1st Birthday/Arshu 1st bday home camera', '2022/Arshu Jan 2022', '2022/Arshu Namkaran 13Mar22', '2022/Arshu-Random', '2022/Chacha home', '2022/Dhanteras 2022', '2022/Diwali 2022', '2022/Fatehabad Aug 2022', '2022/Fatehabad Mar 2022', '2022/Fatehabad May 2022', '2022/Fatehabad Nov 2022', '2022/July Aug 2022', '2022/June 2022', '2022/Karwachauth 2022', '2022/Kerala trip 2022', '2022/March 2022', '2022/Maruti Family Day', '2022/May 2022', '2022/Nainital trip 2022', '2022/Nov 2022', '2022/Oct 2022', '2022/Panchgaon', '2022/Rakhi 2022', '2022/Sahoo Shaadi', '2022/Sep 2022', '2022/Shruti Bday 2022', '2022/Tanu Bhai Shaadi', '2022/Vasundhara Jan Feb 22', '2023', '2023/Anniversary 2023', '2023/Anusha 1st birthday', '2023/Arshu 2nd birthday', '2023/BLR ofc trip March 23', '2023/Bangalore Office Trip - October 23', '2023/Bangalore Office Trip - October 23/Ex-Deloitte Dinner', '2023/Bangalore Office Trip - October 23/Office Colleague Photos', '2023/Bangla sahib mughal grdn feb 2023', "2023/Choti cousin Sanya's shadi Mar 23", '2023/Dec - Sham chacha visit', '2023/December - Arshu', '2023/Deloitte-LWD-Jan 5, 2023', '2023/Diwali', '2023/Feb 2023', '2023/Holi 2023', '2023/Jan 2023', '2023/Kanishk bday 2023', '2023/Karwachauth', '2023/March 2023', '2023/Meenu Gurgaon Trip', '2023/Mussorie & Haridwar Trip', '2023/Mussorie & Haridwar Trip - May 23', '2023/Mussorie & Haridwar Trip - May 23/Haridwar', '2023/Mussorie & Haridwar Trip - May 23/Sahasradhara', '2023/Nuppy visit to India - Delhi (AIIMS) - 30 April, 2023', '2023/Rishabh marriage', '2023/Sahu visit to Ggn - December, 2023', '2023/Shaivi Gurgaon Trip - October', '2023/Shubham Marriage', '2023/Sikkim-Darjeeling Trip', '2023/Sikkim-Darjeeling Trip/24-Sept', '2023/Sikkim-Darjeeling Trip/25-Sept', '2023/Sikkim-Darjeeling Trip/26-Sep', '2023/Sikkim-Darjeeling Trip/27-Sep', '2023/Sikkim-Darjeeling Trip/28-Sep', '2023/Sikkim-Darjeeling Trip/29-Sep', '2023/Sikkim-Darjeeling Trip/30-Sep', '2023/Sikkim-Darjeeling Trip/Airport', '2024', '2024/26-Jan - Fun with camera', '2024/April- May : Arshu', '2024/BLR Office Trip - Feb 24', '2024/Feb - Fatehabad home', '2024/Jan-Feb Arshu', '2024/June - Elan mall visit', '2024/June - Noida office', '2024/Kanishk birthday', '2024/March - Sham chacha home visit', '2024/March - club house', '2024/May - Big B visit', 'Mix', 'Mix/Friends', 'Mix/Gurgaon Misc', 'Mix/Oldies', 'Mix/Random', 'RecycleBin-ToBeDeleted', 'RecycleBin-ToBeDeleted/2024_02_18_01_28_23_281473', 'RecycleBin-ToBeDeleted/2024_02_18_01_29_16_375277', 'RecycleBin-ToBeDeleted/2024_02_18_12_50_15_414959', 'RecycleBin-ToBeDeleted/abcd', 'RecycleBin-ToBeDeleted/abcd/def']
#     # all_dir_str = ",".join(str(element) for element in all_dir_list)
#     request.session["all_dir_list"] = all_dir_list
#     return {"message": "Session variable set"}

# @app.get("/get_session")
# async def get_session(request: Request):
#     # Retrieve a value from session
#     my_var = request.session.get("my_var", None)
#     my_dir = request.session.get("all_dir_list", None)
#     return {"my_var": my_var, "my_dir": my_dir}

# @app.get("/update_session")
# async def update_session(request: Request):
#     # Update a value in session
#     request.session["my_var"] = "Updated value 2" 
#     request.session["all_dir_list"] = ['/', '2019', '2019/Diwali 2019', '2019/First Car - Seltos - 2019', '2019/Food fest delhi', '2019/Impact day 2019', '2019/Ishu Wedding', '2019/Nestle-OfficeTrip-Nov 2019', '2019/Office-Manager Milestone - 2019', '2019/Pune Mumbai Goa 2019', '2019/Shruti bday 2019', '2019/Sirsa Oct 2019', '2019/Smaash - Games & Fun', '2019/Trip Dec 2019', '2020', '2020/Agroha Dec 2020 Ftbd', '2020/Anniversary 2020', '2020/Diwali 2020', '2020/Fatehabad 2020', '2020/Holi 2020 Ftbd', '2020/Hyd Office Trip-Jan 20', '2020/Kanishk bday 2020', '2020/Karwachauth 2020', '2020/Lockdown 2020', '2020/Shruti bday 2020', '2021', '2021/Anniversary 2021', '2021/Anu Marriage Nov 2021', '2021/Arshu Dec 2021', '2021/Arshu birth Cloudnine', '2021/Babyshower Sep 2021', '2021/Dev and Raju Meet - Before Corona Time', '2021/Diwali 2021', '2021/Housewarming and outing', '2021/Jitu Shaadi', '2021/Karwachauth 2021', '2021/Shailley bro wedding', '2021/Sumi visit - Feb 8', '2022', '2022/Amritsar trip Aug 2022', '2022/Anniversary 2022', '2022/April 2022', '2022/Arshu 1st Birthday', '2022/Arshu 1st Birthday/Arshu 1st bday home camera', '2022/Arshu Jan 2022', '2022/Arshu Namkaran 13Mar22', '2022/Arshu-Random', '2022/Chacha home', '2022/Dhanteras 2022', '2022/Diwali 2022', '2022/Fatehabad Aug 2022', '2022/Fatehabad Mar 2022', '2022/Fatehabad May 2022', '2022/Fatehabad Nov 2022', '2022/July Aug 2022', '2022/June 2022', '2022/Karwachauth 2022', '2022/Kerala trip 2022', '2022/March 2022', '2022/Maruti Family Day', '2022/May 2022', '2022/Nainital trip 2022', '2022/Nov 2022', '2022/Oct 2022', '2022/Panchgaon', '2022/Rakhi 2022', '2022/Sahoo Shaadi', '2022/Sep 2022', '2022/Shruti Bday 2022', '2022/Tanu Bhai Shaadi', '2022/Vasundhara Jan Feb 22', '2023', '2023/Anniversary 2023', '2023/Anusha 1st birthday', '2023/Arshu 2nd birthday', '2023/BLR ofc trip March 23', '2023/Bangalore Office Trip - October 23', '2023/Bangalore Office Trip - October 23/Ex-Deloitte Dinner', '2023/Bangalore Office Trip - October 23/Office Colleague Photos', '2023/Bangla sahib mughal grdn feb 2023', "2023/Choti cousin Sanya's shadi Mar 23", '2023/Dec - Sham chacha visit', '2023/December - Arshu', '2023/Deloitte-LWD-Jan 5, 2023', '2023/Diwali', '2023/Feb 2023', '2023/Holi 2023', '2023/Jan 2023', '2023/Kanishk bday 2023', '2023/Karwachauth', '2023/March 2023', '2023/Meenu Gurgaon Trip', '2023/Mussorie & Haridwar Trip', '2023/Mussorie & Haridwar Trip - May 23', '2023/Mussorie & Haridwar Trip - May 23/Haridwar', '2023/Mussorie & Haridwar Trip - May 23/Sahasradhara', '2023/Nuppy visit to India - Delhi (AIIMS) - 30 April, 2023', '2023/Rishabh marriage', '2023/Sahu visit to Ggn - December, 2023', '2023/Shaivi Gurgaon Trip - October', '2023/Shubham Marriage', '2023/Sikkim-Darjeeling Trip', '2023/Sikkim-Darjeeling Trip/24-Sept', '2023/Sikkim-Darjeeling Trip/25-Sept', '2023/Sikkim-Darjeeling Trip/26-Sep', '2023/Sikkim-Darjeeling Trip/27-Sep', '2023/Sikkim-Darjeeling Trip/28-Sep', '2023/Sikkim-Darjeeling Trip/29-Sep', '2023/Sikkim-Darjeeling Trip/30-Sep', '2023/Sikkim-Darjeeling Trip/Airport', '2024', '2024/26-Jan - Fun with camera', '2024/April- May : Arshu', '2024/BLR Office Trip - Feb 24', '2024/Feb - Fatehabad home', '2024/Jan-Feb Arshu', '2024/June - Elan mall visit', '2024/June - Noida office', '2024/Kanishk birthday', '2024/March - Sham chacha home visit', '2024/March - club house', '2024/May - Big B visit', 'Mix', 'Mix/Friends', 'Mix/Gurgaon Misc', 'Mix/Oldies', 'Mix/Random', 'RecycleBin-ToBeDeleted', 'RecycleBin-ToBeDeleted/2024_02_18_01_28_23_281473', 'RecycleBin-ToBeDeleted/2024_02_18_01_29_16_375277', 'RecycleBin-ToBeDeleted/2024_02_18_12_50_15_414959', 'RecycleBin-ToBeDeleted/abcd', 'RecycleBin-ToBeDeleted/abcd/def']


@app.post("/sample-js-python")
def post_data(imageList: list = Body(...)):
  # Return the received data as JSON
#   return {"name": name}
    return {"imageList":imageList}


################################################## All routes defined. Program Ends here.  ##################################################  

@app.get("/check-cookie")
def get_possible_cookies(request: Request):
    user_access_flag = get_cookie(request, cookie_key='user_access_flag')
    user_access_flag1 = get_cookie(request, cookie_key='user_access_flag1')
    if user_access_flag1:
        print ("It is not None")
    else:
        print ("It is none")
    user_first_name = get_cookie(request, cookie_key='user_first_name')
    # return [
    #     {"user_access_flag": user_access_flag},
    #     {"user_access_flag1": user_access_flag1},
    #     {"user_first_name": user_first_name }
    # ]
    return {"user_access_flag": user_access_flag,
            "user_access_flag1": user_access_flag1
           }
    # return "hi there"


    # content_assignment = photos_file.read()
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