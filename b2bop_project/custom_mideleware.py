from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import status
import jwt
from rest_framework.renderers import JSONRenderer
from datetime import timedelta
from django.http import HttpResponse,JsonResponse
import json
import pytz
import datetime
from django.conf import settings





SIMPLE_JWT = {
  'ACCESS_TOKEN_LIFETIME': timedelta(minutes=500),
  'ALGORITHM': 'HS256',
  'SIGNING_KEY': settings.SECRET_KEY,
  'SESSION_COOKIE_DOMAIN' : '192.168.30.148',
  'SESSION_COOKIE_MAX_AGE' : 12000000,
  'AUTH_COOKIE': 'access_token',  # Cookie name. Enables cookies if value is set.
  'AUTH_COOKIE_SECURE': True,    # Whether the auth cookies should be secure (https:// only).
  'AUTH_COOKIE_SAMESITE': 'None',  # Whether to set the flag restricting cookie leaks on cross-site requests. This can be 'Lax', 'Strict', or 'None' to disable the flag.
}

def obtainManufactureIdFromToken(request): 
    token = ""
    c1 = request.COOKIES.get('_c1')
    c2 = request.COOKIES.get('_c2')
    if(c1 and c2):    token = c1 + "." + c2
    validationObjJWT = None
    try:
        validationObjJWT = jwt.decode(token, SIMPLE_JWT['SIGNING_KEY'], algorithms=[SIMPLE_JWT['ALGORITHM']])
        return validationObjJWT['manufacture_unit_id']
    except Exception as e:
        return validationObjJWT
    

def obtainUserIdFromToken(request): 
    token = ""
    c1 = request.COOKIES.get('_c1')
    c2 = request.COOKIES.get('_c2')
    if(c1 and c2):    token = c1 + "." + c2
    validationObjJWT = None
    try:
        validationObjJWT = jwt.decode(token, SIMPLE_JWT['SIGNING_KEY'], algorithms=[SIMPLE_JWT['ALGORITHM']])
        return validationObjJWT['id']
    except Exception as e:
        return validationObjJWT
    

def obtainUserRoleFromToken(request): 
    token = ""
    c1 = request.COOKIES.get('_c1')
    c2 = request.COOKIES.get('_c2')
    if(c1 and c2):    token = c1 + "." + c2
    validationObjJWT = None
    try:
        validationObjJWT = jwt.decode(token, SIMPLE_JWT['SIGNING_KEY'], algorithms=[SIMPLE_JWT['ALGORITHM']])
        return validationObjJWT['role_name']
    except Exception as e:
        return validationObjJWT



def skip_for_paths():
    """
    decorator for skipping middleware based on path
    """
    def decorator(f):
        def check_if_health(self, request):
            l = ["loginUser","exportOrders","forgotPassword",'changePassword']
            k = request.path.split("/")
            for i in k:
                if i in  l:
                    response = self.get_response(request)
                    return response
            return f(self, request)
        return check_if_health
    return decorator

def createJsonResponse(request, token = None):
    c1 = ''
    if token:
        header,payload1,signature = str(token).split(".")
        c1 = header+'.'+payload1
    else:
        c1=request.COOKIES.get('_c1')
    data_map = dict()
    data_map['data'] = dict()
    response = Response(content_type = 'application/json') 
    response.data = data_map
    response.accepted_renderer = JSONRenderer()
    response.accepted_media_type = "application/json"
    response.renderer_context = {}
    response.data['message'] = 'success'
    response.data['status'] = True
    response.data['token'] = c1
    response.status_code = 200
    return response

def createCookies(token,response):
    header,payload,signature = str(token).split(".")
    response.set_cookie(
        key = "_c1",
        value = header+"."+payload,
        max_age = SIMPLE_JWT['SESSION_COOKIE_MAX_AGE'],
        secure = SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly = False,
        samesite = SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        # domain = SIMPLE_JWT['SESSION_COOKIE_DOMAIN'],
    )
    response.set_cookie(
        key = "_c2",
        value = signature,
        expires = SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
        secure = SIMPLE_JWT['AUTH_COOKIE_SECURE'],
        httponly = True,
        samesite = SIMPLE_JWT['AUTH_COOKIE_SAMESITE'],
        # domain = SIMPLE_JWT['SESSION_COOKIE_DOMAIN'],
    )
    return response

def check_authentication(request):
    token=""
    c1=request.COOKIES.get('_c1')
    c2=request.COOKIES.get('_c2')
    if(c1 and c2): token = c1+"."+c2
    validationObjJWT = None
    try:
        validationObjJWT = jwt.decode(token, SIMPLE_JWT['SIGNING_KEY'], algorithms=[SIMPLE_JWT['ALGORITHM']])
        return validationObjJWT
    except Exception as e:
        return validationObjJWT

def refresh_cookies(request,response):
    token=""
    c1=request.COOKIES.get('_c1')
    c2=request.COOKIES.get('_c2')
    if(c1 and c2):    token = c1+"."+c2
    createCookies(token, response)


class customMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    @skip_for_paths()
    def __call__(self, request):
        response = createJsonResponse(request)

        res = self.get_response(request)

        # ✅ If it's already an HttpResponse (404, 500, etc.), return as is
        from django.http import HttpResponseBase
        if isinstance(res, HttpResponseBase):
            return res

        # ✅ Otherwise, wrap into JSON response
        if isinstance(res, Response):
            response.data['data'] = res.data
        else:
            response.data['data'] = res

        response.accepted_renderer = JSONRenderer()
        response.accepted_media_type = "application/json"
        response.renderer_context = {}
        response.render()
        return response
