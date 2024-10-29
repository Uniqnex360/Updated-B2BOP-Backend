from django.shortcuts import render
from user_management.models import *
from django.http import JsonResponse
from b2bop_project.custom_mideleware import SIMPLE_JWT, createJsonResponse, createCookies,obtainManufactureIdFromToken, obtainUserIdFromToken, obtainUserRoleFromToken
from rest_framework.decorators import api_view
from django.middleware import csrf
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
import jwt
from bson import ObjectId
import pandas as pd
from b2bop_project.crud import DatabaseModel


@api_view(('GET', 'POST'))
@csrf_exempt
def loginUser(request):
    jsonRequest = JSONParser().parse(request)
    user_data_obj = list(user.objects(**jsonRequest)) 
    token = ''
    valid = False
    if user_data_obj:
        user_data_obj = user_data_obj[0]
        manufacture_unit_id = ''
        role_name = user_data_obj.role_id.name
        if role_name != "super_admin":
            manufacture_unit_id = str(user_data_obj.manufacture_unit_id.id)
        payload = {
            'id': str(user_data_obj.id),
            'name': user_data_obj.username,
            'email': user_data_obj.email,
            'role_name': user_data_obj.role_id.name,
            # 'max_age': SIMPLE_JWT['SESSION_COOKIE_MAX_AGE'],
            'manufacture_unit_id' : manufacture_unit_id
        }
        token = jwt.encode(payload, SIMPLE_JWT['SIGNING_KEY'], algorithm=SIMPLE_JWT['ALGORITHM'])
        valid = True
        response = createJsonResponse(request, token)

        response = createCookies(token, response)
        # csrf.get_token(request)
        response.data['data']['valid'] = valid
        response.data['data']['role'] = user_data_obj.role_id.name
        response.data['data'] = {
            'valid' : valid,
            'id': str(user_data_obj.id),
            'name': user_data_obj.username,
            'email': user_data_obj.email,
            'role_name': user_data_obj.role_id.name,
            # 'max_age': SIMPLE_JWT['SESSION_COOKIE_MAX_AGE'],
            'manufacture_unit_id' : manufacture_unit_id
        }
    else:
        response = createJsonResponse(request, token)
        valid = False   
        response.data['data']['valid'] = valid
        response.data['data']['role'] = ""
        response.data['_c1'] = ''
    return response


@csrf_exempt
def createORUpdateManufactureUnit(request):
    data = dict()
    json_request = JSONParser().parse(request)
    
    if json_request['manufacture_unit_id'] != "":
        DatabaseModel.update_documents(manufacture_unit.objects,{"id" : json_request['manufacture_unit_id']},json_request['manufacture_unit_obj'])
        data['is_updated'] = True
        data['manufacture_unit_id'] = json_request['manufacture_unit_id']
    else:
        manufacture_obj = DatabaseModel.save_documents(user,json_request['manufacture_unit_obj'])
        data['is_created'] = True
        data['manufacture_unit_id'] = str(manufacture_obj.id)
    return data

def obtainManufactureUnitList(request):
    # role_name = obtainUserRoleFromToken(request)
    
    data = dict()
    manufacture_unit_list = list()
    # if role_name == "admin":
    pipeline = [
        {
        "$project" :{
                "_id": 0,
                "id" : {"$toString" : "$_id"},
                "name" : 1,
                "logo" : 1
        }
        }
    ]
    manufacture_unit_list = list(manufacture_unit.objects.aggregate(*(pipeline)))
    data['manufacture_unit_list'] = manufacture_unit_list 
    return data

def obtainManufactureUnitDetails(request):
    data = dict()
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    pipeline = [
        {
            "$match" : {"_id" : ObjectId(manufacture_unit_id)}
        },
        {"$limit" : 1},
        {
        "$project" :{
                "_id": 0,
                "id" : {"$toString" : "$_id"},
                "name" : 1,
                "description" : 1,
                "location" : 1
        }
        }
    ]
    manufacture_unit_list = list(manufacture_unit.objects.aggregate(*(pipeline)))
    if len(manufacture_unit_list) > 0:
        data['manufacture_unit_obj'] = manufacture_unit_list[0] 
    else:
        data['manufacture_unit_obj'] = {} 
    return data

@csrf_exempt
def createORUpdateUser(request):
    data = dict()
    json_request = JSONParser().parse(request)
    # role_name = obtainUserRoleFromToken(request)
    # manufacture_unit_id = obtainManufactureIdFromToken(request)
    # if role_name == "admin":
    manufacture_unit_id = ObjectId(json_request['manufacture_unit_id'])
        
    
    json_request['user_obj']['role_id'] = ObjectId(json_request['user_obj']['role_id'])
    
    if json_request['user_id'] != "":
        DatabaseModel.update_documents(user.objects,{"id" : json_request['user_id']},json_request['user_obj'])
        data['is_updated'] = True
    else:
        json_request['user_obj']['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
        DatabaseModel.save_documents(user,json_request['user_obj'])
        data['is_created'] = True
    return data



def obtainRolesForCreatingUser(request):
    # role_name = obtainUserRoleFromToken(request)
    role_name = request.GET.get('role_name')
    if role_name == "admin":
        match = {"name" : {"$ne" : role_name}}
    elif role_name == "manufacturers/distributors":
        match = {"name" : {"$nin" : ["manufacturers/distributors", 'admin']}}
    pipeline = [
        {
            "$match" : match
        },
        {
           "$project" :{
                "_id": 0,
                "id" : {"$toString" : "$_id"},
                "name" : 1
           }
        }
    ]
    role_list = list(role.objects.aggregate(*(pipeline)))
    return role_list
    

def checkEmailExistOrNot(request):
    email = request.GET.get('email')
    data = dict()
    pipeline = [
        {
            "$match" : {"email" : email}
        },
        {
            "$limit" : 1
        },
        {
           "$project" :{
                "_id": 1
           }
        }
    ]
    email_obj = list(user.objects.aggregate(*(pipeline)))
    if email_obj != None:
        data['is_exist'] = True
    else:
        data['is_exist'] = False
    return data

@csrf_exempt
def createORUpdateUser(request):
    data = dict()
    json_request = JSONParser().parse(request)
    json_request['user_obj']['role_id'] = ObjectId(json_request['user_obj']['role_id'])
    
    if json_request['user_id'] != "":
        DatabaseModel.update_documents(user.objects,{"id" : json_request['user_id']},json_request['user_obj'])
        data['is_updated'] = True
    else:
        json_request['user_obj']['manufacture_unit_id'] = ObjectId(json_request['user_obj']['manufacture_unit_id'])
        DatabaseModel.save_documents(user,json_request['user_obj'])
        data['is_created'] = True
    return data



@csrf_exempt
def updateUserProfile(request):
    data = dict()
    json_request = JSONParser().parse(request)
    user_id =  json_request.get('user_id')

    user_obj = DatabaseModel.update_documents(user.objects,{"id" : user_id},json_request['user_obj'])
    if json_request.get('address_obj'):
        user_obj = DatabaseModel.update_documents(address.objects,{"id" : user_id},json_request['user_obj'])
