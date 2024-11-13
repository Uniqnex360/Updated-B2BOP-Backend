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
    if json_request.get('manufacture_unit_id') != None and json_request.get('manufacture_unit_id') != "":
        DatabaseModel.update_documents(manufacture_unit.objects,{"id" : json_request['manufacture_unit_id']},json_request['manufacture_unit_obj'])
        data['is_updated'] = True
        data['manufacture_unit_id'] = json_request['manufacture_unit_id']
    else:
        manufacture_obj = DatabaseModel.save_documents(manufacture_unit,json_request['manufacture_unit_obj'])
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
                "location" : 1,
                "logo" : 1
        }
        }
    ]
    manufacture_unit_list = list(manufacture_unit.objects.aggregate(*(pipeline)))
    if len(manufacture_unit_list) > 0:
        data['manufacture_unit_obj'] = manufacture_unit_list[0] 
    else:
        data['manufacture_unit_obj'] = {} 
    return data


def obtainUserListForManufactureUnit(request):
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    
    pipeline = [
    {
        "$match": {
            "manufacture_unit_id": ObjectId(manufacture_unit_id),
        }
    },
    {
        "$lookup": {
            "from": "address",
            "localField": "default_address_id",
            "foreignField": "_id",
            "as": "address_ins"
        }
    },
    {
        "$unwind": {
            "path": "$address_ins",
            "preserveNullAndEmptyArrays": True  # Allow documents without an address
        }
    },
    {
        "$lookup": {
            "from": "role",
            "localField": "role_id",
            "foreignField": "_id",
            "as": "role_ins"
        }
    },
    {
        "$unwind": {
            "path": "$role_ins",
            "preserveNullAndEmptyArrays": True  # Allow documents without a role (optional if roles can be missing)
        }
    },
    {
        "$project": {
            "_id": 0,
            'id': {"$toString": "$_id"},
            "username": {
                "$concat": [
                    "$first_name",
                    { "$ifNull": ["$last_name", ""] }
                ]
            },
            "email": 1,
            "mobile_number": 1,
            "company_name": 1,
            "address": {
                "street": "$address_ins.street",
                "city": "$address_ins.city",
                "state": "$address_ins.state",
                "country": "$address_ins.country",
                "zipCode": "$address_ins.zipCode"
            },
            "role_name": "$role_ins.name"
        }
    }
    ]

    user_list = list(user.objects.aggregate(*(pipeline)))
    return user_list



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
    # l =[]
    # user_list = DatabaseModel.list_documents(product_category.objects,{},["name"])
    # for i in user_list:
    #     first_name = i.name
    #     if first_name not in l:
    #         l.append(first_name)
       
    # data['l'] =l
   ###########UPDATE order collection "order_id" field###############
   # Assuming DatabaseModel and order objects are already defined

    # # Fetch the list of orders
    # order_list = DatabaseModel.list_documents(order.objects,{},['id'])

    # # Initialize the order_id as an integer
    # order_id = 1

    # # Loop through each order and update its order_id
    # for i in order_list:
    #     # Format order_id with leading zeros (e.g., "0001", "0002", etc.)
    #     formatted_order_id = f"{order_id:04d}"  # This will format the number with leading zeros (4 digits)

    #     # Update the order with the formatted order_id
    #     DatabaseModel.update_documents(order.objects, {"id": i.id}, {"order_id": formatted_order_id})

    #     # Increment the order_id for the next iteration
    #     order_id += 1

    ##########UPDATE order collection "shipping_address_id" field###############
#    # Step 1: Get all addresses from the Address collection
#     addresses = address.objects()  # Retrieve all address documents

#     #Step 2: If no addresses exist, handle gracefully
#     if not addresses:
#         print("No addresses found in the database.")
#         return

#    # Step 4: Get all orders from the Order collection
#     orders = DatabaseModel.list_documents(order.objects,{},['id'])  # Retrieve all order documents

#     # Step 5: Update each order's shipping_address_id with the random address ID
#     for order_ins in orders:
#         # Update each order's shipping_address_id field
#         # order.update(set__shipping_address_id=random_address_id)
#         random_address = random.choice(addresses)  # Choose a random address document
#         random_address_id = random_address.id  # Get the ObjectId of the randomly chosen address
#         # delivery_statuss = ["pending", "shipped", "completed", "canceled"]
#         # fulfilled_statuss = ["fulfilled", "unfulfilled", "partially fulfilled" ]
#         # payment_statuss = ["Pending", "Paid", "Failed" ]
#         # delivery_status = random.choice(delivery_statuss)
#         # fulfilled_status = random.choice(fulfilled_statuss)
#         # payment_status = random.choice(payment_statuss)
#         # total_items = random.randint(1, 999)
#         DatabaseModel.update_documents(order.objects, {"id": order_ins.id}, {"set__shipping_address_id": random_address_id})
        

    return data


def send_email(to_email, subject, body):
    message = Mail(
        from_email='contactdigicommerce@gmail.com',
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
    if json_request['role_name'] == "super_admin":
        DatabaseModel.save_documents(user,{"first_name" : json_request['name'],"email" : json_request['email'],"username" : json_request['username'],"password"  : json_request['username'],"manufacture_unit_id" : ObjectId(manufacture_unit_id),"role_id" : ObjectId('670e3b206569d56ed4d4a759')})
    elif json_request['role_name'] == "manufacturer_admin":
        DatabaseModel.save_documents(user,{"first_name" : json_request['name'],"email" : json_request['email'],"username" : json_request['username'],"password"  : json_request['username'],"manufacture_unit_id" : ObjectId(manufacture_unit_id),"role_id" : ObjectId('670e3c616569d56ed4d4a75b')})


    # Send a welcome email
    subject = "Your B2B-OP Dealer Account Has Been Created - Start Shopping!"
    body = f"""
    Dear {json_request['name']},

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

def getAddressFormat(address_id,is_default):
    pipeline = [
            {
                "$match" : {"_id" : address_id}
            },
            {
                "$limit" : 1
            },
            {
            "$project" :{
                    "_id": 0,
                    "address_id" : {"$toString" : "$_id"},
                    "street" : 1,
                    "city" : 1,
                    "state" : 1,
                    "zipCode" : 1,
                    "country" : 1
            }
            }
            ]
    address_obj = list(address.objects.aggregate(*(pipeline)))
    if address_obj != []:
        if is_default == True:
            address_obj[0]['is_default'] = True
        else:
            address_obj[0]['is_default'] = False
    return address_obj[0] 


def obtainUserDetailsForProfile(request):
    data = dict()
    user_id = request.GET.get('user_id')
    pipeline = [
    {"$match": {"_id": ObjectId(user_id)}},  
     {
        "$lookup": {
            "from": "bank_details",  
            "localField": "bank_details_id",
            "foreignField": "_id", 
            "as": "bank_details_ins" 
        }
    },
    {
        "$unwind": {
            "path": "$bank_details_ins", 
            "preserveNullAndEmptyArrays": True
        }
    },
    {
        "$project": {
            "_id": 0,
            "id": {"$toString": "$_id"},
            "first_name" : {"$ifNull": ["$first_name", ""]},
            "last_name" : {"$ifNull": ["$last_name", ""]},
            "email": {"$ifNull": ["$email", ""]}, 
            "mobile_number": {"$ifNull": ["$mobile_number", ""]},
            "age" : {"$ifNull": ["$age", ""]},
            "date_of_birth" : {"$ifNull": ["$date_of_birth", ""]},
            "profile_image" : {"$ifNull": ["$profile_image", ""]},
            "company_name" : {"$ifNull": ["$company_name", ""]},
            "default_address_id" : {"$ifNull": ["$default_address_id", None]},
            "address_id_list" : {"$ifNull": ["$address_id_list", []]},
            "bank_details": {
                "ifsc_code": {"$ifNull": ["$bank_details_ins.ifsc_code", ""]},
                "iban": {"$ifNull": ["$bank_details_ins.iban", ""]},
                "swift_code": {"$ifNull": ["$bank_details_ins.swift_code", ""]},
                "bank_name": {"$ifNull": ["$bank_details_ins.bank_name", ""]},
                "account_number": {"$ifNull": ["$bank_details_ins.account_number", ""]},
                "branch": {"$ifNull": ["$bank_details_ins.branch", ""]},
                "currency": {"$ifNull": ["$bank_details_ins.currency", ""]},
                "images": {"$ifNull": ["$bank_details_ins.images", []]}
            }
        }
        }
    
    ]
    user_obj = list(user.objects.aggregate(*pipeline))
    address_obj_list = []
    if user_obj != []:
        if user_obj[0]['default_address_id'] != None:
            default_add = getAddressFormat(user_obj[0]['default_address_id'],True)
            address_obj_list.append(default_add)
        if user_obj[0]['address_id_list'] != []:
            for i in user_obj[0]['address_id_list']:
               other_add = getAddressFormat(i,False)
               address_obj_list.append(other_add)
        
        user_obj[0]['address_obj_list'] = address_obj_list
        del user_obj[0]['address_id_list']
        del user_obj[0]['default_address_id']
                

        data['user_obj'] = user_obj[0]
    else:
        data['user_obj'] = {}
    return data

def createOrUpdate(address_obj):
    if address_obj.get('id') != None:
        address_id = ObjectId(address_obj['id'])
        del address_obj['id']
        del address_obj['is_default']
        DatabaseModel.update_documents(address.objects,{"id" : address_id},address_obj)
    else:
        del address_obj['is_default']
        new_address_obj = DatabaseModel.save_documents(address,address_obj)
        address_id = new_address_obj.id

    return address_id


@csrf_exempt
def updateUserProfile(request):
    data = dict()
    json_request = JSONParser().parse(request)
    print("USer DETAILS", json_request, "\n\n\n")
    user_id =  json_request.get('user_id')
    user_obj = json_request['user_obj']
    address_obj_list = json_request['address_obj_list']
    bank_details_obj = json_request['bank_details_obj']


    DatabaseModel.update_documents(user.objects,{"id" : user_id},user_obj)
    update_obj = dict()
    if bank_details_obj != {}:

        if bank_details_obj.get('id') != None:
            bank_id = ObjectId(bank_details_obj['id'])
            del bank_details_obj['id']
            DatabaseModel.update_documents(bank_details.objects,{"id" : bank_id},bank_details_obj)
        else:
            bank_obj = DatabaseModel.save_documents(bank_details,bank_details_obj)
            bank_id = bank_obj.id
        update_obj['bank_details_id'] = bank_id
    

    address_id_list = []
    if address_obj_list != []:
        for address_ins in address_obj_list:
            if address_ins['is_default'] == True:
                default_address_id = createOrUpdate(address_ins)
            else:
                other_address_id = createOrUpdate(address_ins)
                address_id_list.append(other_address_id)
        update_obj['default_address_id'] = default_address_id
        update_obj['address_id_list'] = address_id_list
        

    if update_obj != {}:
        DatabaseModel.update_documents(user.objects,{"id" : user_id},update_obj)
    data['is_updated'] = "Profile Updated Sucessfully"
    return data