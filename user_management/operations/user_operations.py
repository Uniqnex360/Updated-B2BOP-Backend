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

def saveDefaultMailTemplateForManufactureUnit(manufacture_unit_id):
    pipeline = [
    {"$match": {"is_default": True}},  
    {
        "$project": {
            "_id": 0,
            "code" : 1,
            "subject" : 1,
            "default_template": 1, 
        }
        }
    
    ]
    mail_template_list = list(mail_template.objects.aggregate(*pipeline))
    for ins in mail_template_list:
        ins['manufacture_unit_id_str'] = manufacture_unit_id
        DatabaseModel.save_documents(mail_template,ins)
    return True


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
        saveDefaultMailTemplateForManufactureUnit(data['manufacture_unit_id'])
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
                "logo" : 1,
                "industry" : 1,
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

import ast
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
    # user_list = DatabaseModel.list_documents(order.objects,{},["id","delivery_status","fulfilled_status","payment_status"])
    # for i in user_list:
    #     # # Convert the string to a Python list
    #     # try:
    #     #     # data_list = ast.literal_eval(i.short_description)

    #     #     # # Join the list elements into a single string
    #     #     # result = ', '.join(data_list)
    #     #     data_list = ast.literal_eval(i.breadcrumb)

    #     #     # Join the list elements into the desired format
    #     #     result = '>'.join(data_list)
    #     #     DatabaseModel.update_documents(product.objects,{"id" : i.id},{"breadcrumb" : result})
    #     # except:
    #     #     pass
    #     delivery_status = i.delivery_status[0].upper() + i.delivery_status[1:]
    #     fulfilled_status = i.fulfilled_status[0].upper() + i.fulfilled_status[1:]
    #     payment_status = i.payment_status[0].upper() + i.payment_status[1:]
    #     DatabaseModel.update_documents(order.objects,{"id" : i.id},{"delivery_status" : delivery_status,"fulfilled_status" : fulfilled_status,"payment_status": payment_status})

    # cartList = DatabaseModel.list_documents(user_cart_item.objects,{},['id','status'])

    # for j in cartList:
    #     status = j.status[0].upper() + j.status[1:]
    #     DatabaseModel.update_documents(user_cart_item.objects,{"id" : j.id},{"status" : status})



       
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
    
    username = json_request['username']
    password = json_request['username']
    manufacture_unit_id = json_request['manufacture_unit_id']
    role_name = json_request.get('role_name')
    # username = "Test 01"
    # password = "1"
    # email = "sivanandham.skks@gmail.com"
    email = json_request['email']
    user_creation_template_obj = DatabaseModel.get_document(mail_template.objects,{"code" : "user_creation","manufacture_unit_id_str" : manufacture_unit_id})
    if role_name != None and role_name == "super_admin":

        manufacture_admin_role_id = DatabaseModel.get_document(role.objects,{"name" : "manufacturer_admin"},['id']).id

        DatabaseModel.save_documents(user,{"first_name" : json_request['name'],"email" : json_request['email'],"username" : json_request['username'],"password"  : json_request['username'],"manufacture_unit_id" : ObjectId(manufacture_unit_id),"role_id" : manufacture_admin_role_id})
        roleName = "Manufacturer"

    else:
        dealer_admin_role_id = DatabaseModel.get_document(role.objects,{"name" : "dealer_admin"},['id']).id

        DatabaseModel.save_documents(user,{"first_name" : json_request['name'],"email" : json_request['email'],"username" : json_request['username'],"password"  : json_request['username'],"manufacture_unit_id" : ObjectId(manufacture_unit_id),"role_id" : dealer_admin_role_id})
        roleName = "Dealer"

    subject = user_creation_template_obj.subject.format(role=roleName)

    body = user_creation_template_obj.default_template.format(name = json_request['name'], role=roleName, email=email, username = username, password = password)

    send_email(email, subject, body)
    data['message'] = "User created and email sent!"

    return data

def getAddressFormat(address_id):
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
                    "country" : 1,
                    "is_default" : 1
            }
            }
            ]
    address_obj = list(address.objects.aggregate(*(pipeline)))
        
    return address_obj[0] 



def getBankDetailsFormat(bank_details_id):
    pipeline = [
            {
                "$match" : {"_id" : bank_details_id}
            },
            {
                "$limit" : 1
            },
            {
            "$project" :{
                "_id": 0,
                "bank_id" : {"$toString" : "$_id"},
                "ifsc_code": {"$ifNull": ["$ifsc_code", ""]},
                "iban": {"$ifNull": ["$iban", ""]},
                "swift_code": {"$ifNull": ["$swift_code", ""]},
                "bank_name": {"$ifNull": ["$bank_name", ""]},
                "account_number": {"$ifNull": ["$account_number", ""]},
                "branch": {"$ifNull": ["$branch", ""]},
                "currency": {"$ifNull": ["$currency", ""]},
                "images": {"$ifNull": ["$images", []]},
                "is_default" : 1,
            }
            }
            ]
    bank_details_obj = list(bank_details.objects.aggregate(*(pipeline)))
    return bank_details_obj[0] 


def obtainUserDetailsForProfile(request):
    data = dict()
    user_id = request.GET.get('user_id')
    pipeline = [
    {"$match": {"_id": ObjectId(user_id)}},  
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
            "bank_details_id_list" : {"$ifNull": ["$bank_details_id_list", []]},
            "ware_house_id_list" : {"$ifNull": ["$ware_house_id_list", []]},
            "website" : {"$ifNull": ["$website", ""]},
        }
        }
    
    ]
    user_obj = list(user.objects.aggregate(*pipeline))
    address_obj_list = []
    bank_details_obj_list = []
    ware_house_obj_list = []
    if user_obj != []:
        if user_obj[0]['default_address_id'] != None:
            default_add = getAddressFormat(user_obj[0]['default_address_id'])
            address_obj_list.append(default_add)


        if user_obj[0]['address_id_list'] != []:
            for i in user_obj[0]['address_id_list']:
               address_obj_list.append(getAddressFormat(i))
        
        if user_obj[0]['ware_house_id_list'] != []:
            for i in user_obj[0]['ware_house_id_list']:
               ware_house_obj_list.append(getAddressFormat(i))


        if user_obj[0]['bank_details_id_list'] != []:
            for i in user_obj[0]['bank_details_id_list']:
               bank_details_obj_list.append(getBankDetailsFormat(i))

        
        user_obj[0]['address_obj_list'] = address_obj_list
        user_obj[0]['bank_details_obj_list'] = bank_details_obj_list
        user_obj[0]['ware_house_obj_list'] = ware_house_obj_list

        del user_obj[0]['address_id_list']
        del user_obj[0]['default_address_id']
        del user_obj[0]['bank_details_id_list']
        del user_obj[0]['ware_house_id_list']
                

        data['user_obj'] = user_obj[0]
    else:
        data['user_obj'] = {}
    return data

def createOrUpdate(address_obj):
    if address_obj.get('id') != None:
        address_id = ObjectId(address_obj['id'])
        del address_obj['id']
        DatabaseModel.update_documents(address.objects,{"id" : address_id},address_obj)
    else:
        new_address_obj = DatabaseModel.save_documents(address,address_obj)
        address_id = new_address_obj.id

    return address_id


def createOrUpdateBank(bank_obj):
    if bank_obj.get('bank_id') != None:
        bank_id = ObjectId(bank_obj['bank_id'])
        del bank_obj['bank_id']
        DatabaseModel.update_documents(bank_details.objects,{"id" : bank_id},bank_obj)
    else:
        new_bank_obj = DatabaseModel.save_documents(bank_details,bank_obj)
        bank_id = new_bank_obj.id

    return bank_id


@csrf_exempt
def updateUserProfile(request):
    data = dict()
    json_request = JSONParser().parse(request)
    user_id =  json_request.get('user_id')
    user_obj = json_request['user_obj']
    # del user_obj['age']
    address_obj_list = json_request['address_obj_list']
    bank_details_obj_list = json_request.get('bank_details_obj_list')
    ware_house_obj_list = json_request.get('ware_house_obj_list')


    DatabaseModel.update_documents(user.objects,{"id" : user_id},user_obj)
    update_obj = dict()
    

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


    bank_id_list = []
    if bank_details_obj_list != None and bank_details_obj_list != []:
        for bank_ins in bank_details_obj_list:
            bank_id_list.append(createOrUpdateBank(bank_ins))
            
        update_obj['bank_details_id_list'] = bank_id_list

    ware_house_id_list = []
    if ware_house_obj_list != None and ware_house_obj_list != []:
        for ware_house_ins in ware_house_obj_list:
            ware_house_id_list.append(createOrUpdate(ware_house_ins))
            
        update_obj['ware_house_id_list'] = ware_house_id_list
        

    if update_obj != {}:
        DatabaseModel.update_documents(user.objects,{"id" : user_id},update_obj)
    data['is_updated'] = "Profile Updated Sucessfully"
    return data

@csrf_exempt
def deleteAddress(request):
    data = dict()
    json_request = JSONParser().parse(request)
    address_id = json_request.get('address_id')
    is_default = json_request.get('is_default')
    user_id = json_request.get('user_id')
    ware_house = json_request.get('ware_house')
    if address_id != None:
        if ware_house == True:
            DatabaseModel.update_documents(user.objects,{"id" : user_id},{"pull__ware_house_id_list" : ObjectId(address_id)})
            DatabaseModel.delete_documents(address.objects,{"id" : address_id})
        elif is_default != None and is_default == True:
            DatabaseModel.update_documents(user.objects,{"id" : user_id},{"unset__default_address_id" : ""})
            DatabaseModel.delete_documents(address.objects,{"id" : address_id})
        else:
            DatabaseModel.update_documents(user.objects,{"id" : user_id},{"pull__address_id_list" : ObjectId(address_id)})
            DatabaseModel.delete_documents(address.objects,{"id" : address_id})
        data['is_deleted'] = "Address deleted successfully."
    return data

@csrf_exempt
def deleteBankDetails(request):
    data = dict()
    json_request = JSONParser().parse(request)
    bank_id = json_request.get('bank_id')
    user_id = json_request.get('user_id')
    if bank_id != None:
        DatabaseModel.delete_documents(bank_details.objects,{"id" : bank_id})
        DatabaseModel.update_documents(user.objects,{"id" : user_id},{"pull__bank_details_id_list" : ObjectId(bank_id)})
        data['is_deleted'] = "Bank Details deleted successfully."
    return data

def obtainAllMailTemplateForManufactureUnit(request):
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    pipeline = [
    {"$match": {"manufacture_unit_id_str": manufacture_unit_id}},  
    {
        "$project": {
            "_id": 0,
            "id": {"$toString": "$_id"},
            "code" : 1,
            "subject" : 1,
            "default_template": 1, 
        }
        }
    
    ]
    mail_template_list = list(mail_template.objects.aggregate(*pipeline))
    return mail_template_list

@csrf_exempt
def updateMailTemplate(request):
    data = dict()
    json_request = JSONParser().parse(request)
    id = json_request['update_obj']['id']
    del json_request['update_obj']['id']
    DatabaseModel.update_documents(mail_template.objects,{"id" : id},json_request['update_obj'])
    data["is_updated"] = "Mail Template update sucessfully"
    return data


def obtainDealerDetails(request):
    data = dict()
    user_id = request.GET.get('user_id')
    pipeline = [
    {"$match": {"_id": ObjectId(user_id)}},  
    {
        "$project": {
            "_id": 0,
            "id": {"$toString": "$_id"},
            "first_name" : {"$ifNull": ["$first_name", ""]},
            "last_name" : {"$ifNull": ["$last_name", ""]},
            "email": {"$ifNull": ["$email", ""]}, 
            "mobile_number": {"$ifNull": ["$mobile_number", ""]},
            # "age" : {"$ifNull": ["$age", ""]},
            "date_of_birth" : {"$ifNull": ["$date_of_birth", ""]},
            "profile_image" : {"$ifNull": ["$profile_image", ""]},
            "company_name" : {"$ifNull": ["$company_name", ""]},
            # "default_address_id" : {"$ifNull": ["$default_address_id", None]},
            # "address_id_list" : {"$ifNull": ["$address_id_list", []]},
            # "bank_details_id_list" : {"$ifNull": ["$bank_details_id_list", []]},
        }
        }
    
    ]
    user_obj = list(user.objects.aggregate(*pipeline))
    data['user_details'] = user_obj[0]
    pipeline =[
        {
            "$match" : {
                "customer_id" : ObjectId(user_id)
            }
        },
        {
            "$lookup" :{
                "from" : "user_cart_item",
                "localField" : "order_items",
                "foreignField" : "_id",
                "as" : "cart_ins"
            }
        },
        {"$unwind" : "$cart_ins"},
        {
            "$lookup" :{
                "from" : "product",
                "localField" : "cart_ins.product_id",
                "foreignField" : "_id",
                "as" : "products_ins"
            }
        },
        {"$unwind" : "$products_ins"},
        {
        "$group" :{
                "_id": "$_id",
                "order_id" : {"$first" : "$order_id"},
                "amount" : {"$first" : "$amount"},
                "currency" : {"$first" : "$currency"}, 
                "product_list" : {"$push" : {
                "product_name" : "$products_ins.product_name",
                "primary_image" : {"$first":"$products_ins.images"},
                "sku_number" : "$products_ins.sku_number_product_code_item_number",
                "mpn_number" : "$products_ins.mpn",
                "brand_name" : "$products_ins.brand_name",
                "price" : "$products_ins.list_price",
                "currency" : "$products_ins.currency",
                "quantity" : "$cart_ins.quantity",
                "total_price" : "$cart_ins.price"
                                            }}
        }
        },
        {
        "$project" :{
                "_id": 0,
                "id": {"$toString":"$_id"},
                "order_id" : "$order_id",
                "amount" : {"$concat" : [{"$toString":"$amount"},"$currency"]},
                "product_list" : "$product_list"
        }
        }
    ]
    order_list = list(order.objects.aggregate(*(pipeline)))
    data['order_list'] = order_list
    return data


def obtainDashboardDetailsForManufactureAdmin(request):
    data = dict()
    manufacture_unit_id = request.GET.get('manufacture_unit_id')

    pipeline = [
    {
            "$match": {
                "manufacture_unit_id_str" : manufacture_unit_id,
                "payment_status": {"$in" : ["Completed"]}
            }
        },
    {
        "$group": {
            "_id": None,
            'total_amount': {'$sum': '$amount'},
        }
    },
    {
        "$project": {
            "_id": 0,
            'total_amount': "$total_amount",
        }
        }
    ]
    total_sales_result = list(order.objects.aggregate(*(pipeline)))
    data['total_sales'] = round(total_sales_result[0]['total_amount'] if total_sales_result else 0,2)

    pipeline = [
    {"$match": {"manufacture_unit_id": ObjectId(manufacture_unit_id)}},
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
        }
    },
    {
        "$match" : {
            "role_ins.name" : "dealer_admin"
        }
    },
    {
            "$count": "total_count"
    }
    ]
    total_count_result = list(user.objects.aggregate(*(pipeline)))
    data['dealer_count'] = total_count_result[0]['total_count'] if total_count_result else 0


    pipeline = [
    {
        "$match": {
            "manufacture_unit_id_str": manufacture_unit_id
                 }
    },
    {
        "$lookup" :{
            "from" : "product",
            "localField" : "product_id",
            "foreignField" : "_id",
            "as" : "products_ins"
        }
    },
    {"$unwind" : "$products_ins"},
    {
        "$lookup" :{
            "from" : "brand",
            "localField" : "products_ins.brand_id",
            "foreignField" : "_id",
            "as" : "brand_ins"
        }
    },
    {"$unwind" : "$brand_ins"},
    {"$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "product_id" : {"$toString" : "$product_id"},
                "product_name" : "$name",
                "primary_image" : {"$first":"$products_ins.images"},
                "sku_number" : "$products_ins.sku_number_product_code_item_number",
                "brand_name" : 1,
                "brand_logo" : "$brand_ins.logo",
                "total_sales" : 1,
                "units_sold" : 1,
                "last_updated" : {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$last_updated",
                    }
                    },
    }},
    {
        "$sort" : {"units_sold" : -1}
    },
    {"$limit" : 10}
    ]
    data['top_selling_products'] = list(top_selling_product.objects.aggregate(*(pipeline)))


    pipeline = [
    {
        "$match": {
            "manufacture_unit_id_str": manufacture_unit_id
                 }
    },
    {"$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "brand_name" : 1,
                "category" : 1, 
                "total_sales" : 1,
                "units_sold" :1,
                "last_updated" : {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$last_updated",
                    }
                    }
    }},
    {
        "$sort" : {"units_sold" : -1}
    },
    {"$limit" : 10}
    ]
    data['top_selling_brands'] = list(top_selling_brand.objects.aggregate(*(pipeline)))

    pipeline = [
    {
        "$match": {
            "manufacture_unit_id_str": manufacture_unit_id
                 }
    },
    {"$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "category_name" : 1,
                "total_sales" : 1,
                "units_sold" :1,
                "last_updated" : {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$last_updated",
                    }
                    }
    }},
    {
        "$sort" : {"units_sold" : -1}
    },
    {"$limit" : 10}
    ]
    data['top_selling_categorys'] = list(top_selling_category.objects.aggregate(*(pipeline)))
    
    pipeline = [
        {
            "$match": {
                "manufacture_unit_id_str" : manufacture_unit_id
            }
        },
        {
            "$count": "total_count"
    }
    ]
    total_order_count_result = list(order.objects.aggregate(*(pipeline)))
    data['total_order_count'] = total_order_count_result[0]['total_count'] if total_order_count_result else 0

    pipeline = [
    {"$match": {
        "manufacture_unit_id_str": manufacture_unit_id,
        "is_reorder" : True
        }
    },
    {
            "$count": "total_count"
    }
    ]
    re_order_count_result = list(order.objects.aggregate(*(pipeline)))
    data['re_order_count'] = re_order_count_result[0]['total_count'] if re_order_count_result else 0

    pipeline = [
        {
            "$match": {
                "manufacture_unit_id_str" : manufacture_unit_id,
                "payment_status": {"$in" : ["Pending", "Paid", "Failed" ]}
            }
        },
        {
            "$count": "total_count"
    }
    ]
    pending_order_count_result = list(order.objects.aggregate(*(pipeline)))
    data['pending_order_count'] = pending_order_count_result[0]['total_count'] if pending_order_count_result else 0

    return data



def manufactureDashboardEachDealerOrderValue(request):
    data = dict()
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    pipeline = [
    {"$match": {"manufacture_unit_id": ObjectId(manufacture_unit_id)}},
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
        }
    },
    {
        "$match" : {
            "role_ins.name" : "dealer_admin"
        }
    },
    # {
    #         "$count": "total_count"
    # }
    {
        "$project" : {
            "_id" : 0,
            "id" : {"$toString" : "$_id"},
            "name" : {"$concat" : ["$first_name",{"$ifNull" : ["$last_anme",""]}]}
        }
    }
    ]
    total_dealer_list = list(user.objects.aggregate(*(pipeline)))

    for ins in total_dealer_list:
        pipeline = [
        {
            "$match": {
                "customer_id": ObjectId(ins['id']),
                "payment_status": "Completed"
            }
        },
        {
            "$group": {
                "_id": None,
                'total_amount': {'$sum': '$amount'},
            }
        },
        {
            "$project": {
                "_id": 0,
                'total_amount': "$total_amount",
            }
            }
        ]

        order_amount_obj = list(order.objects.aggregate(*(pipeline)))
        ins['order_value'] = order_amount_obj[0]['total_amount'] if order_amount_obj else 0
    if total_dealer_list != []:
        total_dealer_list = (sorted(total_dealer_list, key=lambda x: x["order_value"], reverse=True))[0:10]
    data['total_dealer_list'] = total_dealer_list
    return data    


def obtainDashboardDetailsForDealer(request):
    data = dict()
    user_id = request.GET.get('user_id')
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    pipeline = [
    {
            "$match": {
                "customer_id" : ObjectId(user_id),
                "manufacture_unit_id_str" : manufacture_unit_id,
                "payment_status": {"$in" : ["Completed", "Paid" ]}
            }
        },
    {
        "$group": {
            "_id": None,
            'total_amount': {'$sum': '$amount'},
        }
    },
    {
        "$project": {
            "_id": 0,
            'total_amount': "$total_amount",
        }
        }
    ]
    total_count_result = list(order.objects.aggregate(*(pipeline)))
    data['total_spend'] = total_count_result[0]['total_amount'] if total_count_result else 0


    pipeline = [
    {
        "$match": {
            "manufacture_unit_id_str": manufacture_unit_id
                 }
    },
    {
        "$lookup" :{
            "from" : "product",
            "localField" : "product_id",
            "foreignField" : "_id",
            "as" : "products_ins"
        }
    },
    {"$unwind" : "$products_ins"},
    {
        "$lookup" :{
            "from" : "brand",
            "localField" : "products_ins.brand_id",
            "foreignField" : "_id",
            "as" : "brand_ins"
        }
    },
    {"$unwind" : "$brand_ins"},
    {"$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "product_id" : {"$toString" : "$product_id"},
                "product_name" : "$name",
                "primary_image" : {"$first":"$products_ins.images"},
                "sku_number" : "$products_ins.sku_number_product_code_item_number",
                "brand_name" : 1,
                "brand_logo" : "$brand_ins.logo",
                "category_name" : 1,
                "total_sales" : 1,
                "units_sold" : 1,
                "last_updated" : {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$last_updated",
                    }
                    },
    }},
    {
        "$sort" : {"units_sold" : -1}
    },
    {"$limit" : 10}
    ]
    data['top_selling_products'] = list(top_selling_product.objects.aggregate(*(pipeline)))


    pipeline = [
    {
        "$match": {
            "manufacture_unit_id_str": manufacture_unit_id
                 }
    },
    {"$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "brand_name" : 1,
                "category" : 1, 
                "total_sales" : 1,
                "units_sold" :1,
                "last_updated" : {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$last_updated",
                    }
                    }
    }},
    {
        "$sort" : {"units_sold" : -1}
    },
    {"$limit" : 10}
    ]
    data['top_selling_brands'] = list(top_selling_brand.objects.aggregate(*(pipeline)))

    pipeline = [
    {
        "$match": {
            "manufacture_unit_id_str": manufacture_unit_id
                 }
    },
    {"$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "category_name" : 1,
                "total_sales" : 1,
                "units_sold" :1,
                "last_updated" : {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$last_updated",
                    }
                    }
    }},
    {
        "$sort" : {"units_sold" : -1}
    },
    {"$limit" : 10}
    ]
    data['top_selling_categorys'] = list(top_selling_category.objects.aggregate(*(pipeline)))


    pipeline = [
    {"$match": {
        "customer_id" : ObjectId(user_id),
        "manufacture_unit_id_str": manufacture_unit_id,
        }
    },
    {
            "$count": "total_count"
    }
    ]
    total_order_count_result = list(order.objects.aggregate(*(pipeline)))
    data['total_order_count'] = total_order_count_result[0]['total_count'] if total_order_count_result else 0

    pipeline = [
        {
            "$match": {
                "customer_id" : ObjectId(user_id),
                "manufacture_unit_id_str" : manufacture_unit_id,
                "payment_status": {"$in" : ["Pending", "Failed" ]}
            }
        },
        {
            "$count": "total_count"
    }
    ]
    pending_order_count_result = list(order.objects.aggregate(*(pipeline)))
    data['pending_order_count'] = pending_order_count_result[0]['total_count'] if pending_order_count_result else 0

    pipeline = [
        {
            "$match": {
                "customer_id" : ObjectId(user_id),
                "manufacture_unit_id_str" : manufacture_unit_id,
                "is_reorder": True
            }
        },
        {
            "$count": "total_count"
    }
    ]
    re_order_count_result = list(order.objects.aggregate(*(pipeline)))
    data['re_order_count'] = re_order_count_result[0]['total_count'] if re_order_count_result else 0

    pipeline = [
    {"$match": {
        "customer_id" : ObjectId(user_id),
        "manufacture_unit_id_str": manufacture_unit_id,
        }
    },
    {"$project" : {
                "_id" : 0,
                "id" : {"$toString" : "$_id"},
                "order_id" : 1,
                "payment_status" : 1,
                "amount" :1,
                "order_date" : {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$creation_date",
                    }
                    }
    }},
    {
        "$sort" : {"id" : -1}
    },
    {"$limit" : 5}
    ]
    data['recent_orders'] = list(order.objects.aggregate(*(pipeline)))
    return data
