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
from b2bop_project.settings import SENDGRID_API_KEY
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import random


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

def getUserName(manufacture_unit_name, name):
    number = random.randint(0, 999)
    username = f"{manufacture_unit_name[0:4]}{name}{number}"
    return username


def generateUserName(request):
    data = dict()

    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    name = request.GET.get('name')

    manufacture_unit_name = DatabaseModel.get_document(manufacture_unit.objects,{"id" : manufacture_unit_id},['name']).name

    username = getUserName(manufacture_unit_name, name)
    user_obj = DatabaseModel.get_document(user.objects,{"username" : username})
    while user_obj != None:
        username = getUserName(manufacture_unit_name, name)
        user_obj = DatabaseModel.get_document(user.objects,{"username" : username})

    data['username'] = username
    return data


def send_email(to_email, subject, body):
    message = Mail(
        from_email='siva@kmdigicommerce.com',
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        print(f"Email sent successfully! Status Code: {response.status_code}")
    except Exception as e:
        print(f"Failed to send email: {e}")

@csrf_exempt
def createUser(request):
    data = dict()
    json_request = JSONParser().parse(request)
    
    print("json_request",json_request,"\n\n\n")
    username = json_request['username']
    password = json_request['username']
    manufacture_unit_id = json_request['manufacture_unit_id']
    # username = "Test 01"
    # password = "1"
    # email = "sivanandham.skks@gmail.com"
    email = json_request['email']
    DatabaseModel.save_documents(user,{"first_name" : json_request['name'],"email" : json_request['email'],"username" : json_request['username'],"password"  : json_request['username'],"manufacture_unit_id" : ObjectId(manufacture_unit_id),"role_id" : ObjectId('670e3c616569d56ed4d4a75b')})

    # Send a welcome email
    subject = "Your B2B-OP Dealer Account Has Been Created - Start Shopping!"
    body = f"""
    Dear {username},

    We are pleased to inform you that your dealer account has been successfully created. You can now log in to shop for products tailored to your needs!
    
    *Email:* {email}
    *Username:* {username}
    *Password:*  {password}
    
    Please ensure that you keep your login credentials confidential. If you have any questions or need assistance, don't hesitate to contact us.

    Best regards,
    Service Team
    """
    
    send_email(email, subject, body)
    data['message'] = "User created and email sent!"

    return data