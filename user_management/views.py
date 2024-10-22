from django.shortcuts import render
from .models import *
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
    print("jsonRequest",jsonRequest,"\n\n\n\n\n\n")
    user_data_obj = list(user.objects(**jsonRequest)) 
    token = ''
    valid = False
    if user_data_obj:
        user_data_obj = user_data_obj[0]
        manufacture_unit_id = ''
        role_name = user_data_obj.role_id.name
        if role_name != "admin":
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
    else:
        response = createJsonResponse(request, token)
        valid = False   
        response.data['data']['valid'] = valid
        response.data['data']['role'] = ""
        response.data['_c1'] = ''
    return response


def obtainProductCategoryList(request):
    manufacture_unit_id = obtainManufactureIdFromToken(request)
    pipeline =[
        {
            "$match" : {
                "manufacture_unit_id" : ObjectId(manufacture_unit_id)
            }
        },
        {
        '$lookup': {
            'from': 'product_category',
            'localField': 'product_category_list',
            'foreignField': '_id',
            'as': 'product_category_ins'
        }
        },
        {"$unwind" : "$product_category_ins"},
        {
           "$project" :{
            "_id":0,
            "id":{"$toString" : "$product_category_ins._id"},
            "name" : "$product_category_ins.name",
           }
        }
    ]
    product_category_list = list(manufacture_unit_product_category_config.objects.aggregate(*(pipeline)))
    return product_category_list


def obtainProductSubCategoryList(request):
    product_category_id = request.GET.get('product_category_id')
    manufacture_unit_id = obtainManufactureIdFromToken(request)
    pipeline =[
        {
            "$match" : {
                "manufacture_unit_id" : ObjectId(manufacture_unit_id),
                "product_category_id" : ObjectId(product_category_id)
            }
        },
        {
        '$lookup': {
            'from': 'product_sub_category',
            'localField': 'product_sub_category_list',
            'foreignField': '_id',
            'as': 'product_sub_category_ins'
        }
        },
        {"$unwind" : "$product_sub_category_ins"},
        {
           "$project" :{
            "_id":0,
            "id":{"$toString" : "$product_sub_category_ins._id"},
            "name" : "$product_sub_category_ins.name",
           }
        }
    ]
    product_sub_category_list = list(product_category_product_sub_category_config.objects.aggregate(*(pipeline)))
    return product_sub_category_list


def obtainbrandList(request):
    product_sub_category_id = request.GET.get('product_sub_category_id')
    pipeline =[
        {
            "$match" : {
                "product_sub_category_id_str" : product_sub_category_id
            }
        },
        {
           "$project" :{
            "_id":0,
            "id" : {"$toString" : "$_id"},
            "name" : 1
           }
        }
    ]
    product_list = list(brand.objects.aggregate(*(pipeline)))
    return product_list


def obtainProductsList(request):
    product_sub_category_id = request.GET.get('product_sub_category_id')
    brand_id = request.GET.get('brand_id')
    manufacture_unit_id = obtainManufactureIdFromToken(request)
    if brand_id != None:
        match = {
                "manufacture_unit_id" : ObjectId(manufacture_unit_id),
                "product_sub_category_id" : ObjectId(product_sub_category_id),
                "brand_id" : ObjectId(brand_id)
            }
    else:
        match = {
                "manufacture_unit_id" : ObjectId(manufacture_unit_id),
                "product_sub_category_id" : ObjectId(product_sub_category_id),
            }
    pipeline =[
        {
            "$match" : match
        },
        {
           "$project" :{
            "_id":0,
            "id" : {"$toString" : "$_id"},
            "name" : 1,
            "description" : 1,
            "price" : 1,
            "is_avaliable" : 1,
            "currency" : 1,
            "stock_quantity" :1,
            "product_image_list" : 1,
            "product_video_list" :1,
            "colour" : 1,
            'height' : 1,
            'weight' : 1,
           }
        }
    ]
    product_list = list(products.objects.aggregate(*(pipeline)))
    return product_list



@csrf_exempt
def createOrUpdateUserCartItem(request):
    data = dict()
    json_request = JSONParser().parse(request)
    json_request['user_id'] = ObjectId(json_request.get('user_id'))
    json_request['product_id'] = ObjectId(json_request.get('product_id'))
    pipeline =[
        {
            "$match" : {
                "user_id" : json_request['user_id'],
                "product_id" : json_request['product_id']
            }
        },
        {
           "$project" :{
                "_id":1
           }
        }
    ]
    user_cart_item_obj = list(user_cart_item.objects.aggregate(*(pipeline)))
    if user_cart_item_obj != []:
        user_cart_item.objects(id = user_cart_item_obj[0]['_id']).update(inc__quantity = json_request['quantity'])
        data['is_updated'] = True
    else:
        user_cart_item(**json_request).save()
        data['is_created'] = True
    return data

def obtainUserCartItemList(request):
    user_id = obtainUserIdFromToken(request)
    pipeline =[
        {
            "$match" : {
                "user_id" : ObjectId(user_id),
                "status" : "pending"
            }
        },
        {
            "$lookup" :{
                "from" : "products",
                "localField" : "product_id",
                "foreignField" : "_id",
                "as" : "products_ins"
            }
        },
        {"$unwind" : "$products_ins"},
        {
           "$project" :{
                "_id": 0,
                "id" : {"$toString" : "$_id"},
                "name" : "$products_ins.name",
                "description" : "$products_ins.description",
                "price" : "$products_ins.price",
                "currency" : "$products_ins.currency",
                "primary_image" : "$products_ins.primary_image",
                "colour" : "$products_ins.colour",
                "quantity" : 1
           }
        }
    ]
    user_cart_item_list = list(user_cart_item.objects.aggregate(*(pipeline)))
    return user_cart_item_list

@csrf_exempt
def updateOrDeleteUserCartItem(request):
    data = dict()
    json_request = JSONParser().parse(request)
    if json_request['is_delete'] == True:
        user_cart_item.objects(id = json_request['id']).delete()
        data['is_deleted'] = True
    else:
        user_cart_item.objects(id = json_request['id']).update(inc__quantity = json_request['quantity'])
        data['is_updated'] = True
    return data

def totalCheckOutAmount(request):
    user_id = obtainUserIdFromToken(request)
    pipeline = [
        {
            "$match" : {
                "user_id" : ObjectId(user_id),
                "status" : "pending"
            }
        },
        {
           "$group" :{
                "_id": None,
                'total_amount': {'$sum': '$price'}
           }
        },
        {
           "$project" :{
                "_id": 0,
                'total_amount': "$total_amount"
           }
        }
    ]
    user_cart_item_list = list(user_cart_item.objects.aggregate(*(pipeline)))
    return user_cart_item_list


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
    role_name = obtainUserRoleFromToken(request)
    print("role_name", role_name ,"\n\n\n")
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
    role_name = obtainUserRoleFromToken(request)
    json_request = JSONParser().parse(request)
    manufacture_unit_id = obtainManufactureIdFromToken(request)
    if role_name == "admin":
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
    role_name = obtainUserRoleFromToken(request)
    if role_name == "admin":
        match = {"name" : {"$ne" : "role_name"}}
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
    manufacture_unit_id = obtainManufactureIdFromToken(request)
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
