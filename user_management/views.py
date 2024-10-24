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


def obtainProductCategoryList(request):
    # manufacture_unit_id = obtainManufactureIdFromToken(request)
    manufacture_unit_id = request.GET.get('manufacture_unit_id')

    pipeline =[
        {
            "$match" : {
                "manufacture_unit_id_str" : manufacture_unit_id
            }
        },
        {
           "$project" :{
            "_id":0,
            "id":{"$toString" : "$_id"},
            "name" : 1,
           }
        }
    ]
    product_category_list = list(product_category.objects.aggregate(*(pipeline)))
    return product_category_list


def obtainProductSubCategoryList(request):
    product_category_id = request.GET.get('product_category_id')
    # manufacture_unit_id = obtainManufactureIdFromToken(request)
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    pipeline =[
        {
            "$match" : {
                "manufacture_unit_id_str" : manufacture_unit_id,
                "product_category_id" : ObjectId(product_category_id)
            }
        },
        {
           "$project" :{
            "_id":0,
            "id":{"$toString" : "$_id"},
            "name" : 1,
           }
        }
    ]
    product_sub_category_list = list(product_sub_category.objects.aggregate(*(pipeline)))
    return product_sub_category_list


def obtainbrandList(request):
    product_sub_category_id = request.GET.get('product_sub_category_id')
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    pipeline =[
        {
            "$match" : {
                "product_sub_category_id_str" : product_sub_category_id,
                "manufacture_unit_id_str" : manufacture_unit_id
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
    # manufacture_unit_id = obtainManufactureIdFromToken(request)
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
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
    # user_id = obtainUserIdFromToken(request)
    user_id = request.GET.get('user_id')
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
    # user_id = obtainUserIdFromToken(request)
    user_id = request.GET.get('user_id')
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
    pass


@csrf_exempt
def upload_file(request):
    data = dict()
    manufacture_unit_id = request.POST['manufacture_unit_id']

    data['status'] = False
    data['error'] = ""
    if 'file' not in request.FILES:
        data['error'] = "No file uploaded."
        return data

    file = request.FILES['file']
    try:
        if file.name.endswith('.xlsx'):
            df = pd.read_excel(file, header=1)
        elif file.name.endswith('.csv') or file.name.endswith('.txt'):
            df = pd.read_csv(file)
        else:
            data['error'] = "Unsupported file format."
            return data
    except Exception as e:
        data['error'] = f"Error reading file: {str(e)}"
        return data
    i=0
    try:
        for i in range(len(df)):
            row_dict = df.iloc[i]
            
            # Product Category Mapping
            product_category_obj = DatabaseModel.get_document(
                product_category.objects, {"name": row_dict[0],"manufacture_unit_id_str" : manufacture_unit_id}
            )
            if product_category_obj is None:
                product_category_obj = DatabaseModel.save_documents(
                    product_category, {
                        "name": row_dict[0],
                        "description": str(row_dict[1]) if row_dict[1] else "",
                        "code": str(row_dict[2]) if row_dict[2] else "",
                        "manufacture_unit_id_str" : manufacture_unit_id
                    }
                )

            # Product Sub-Category Mapping
            product_sub_category_obj = DatabaseModel.get_document(
                product_sub_category.objects, {"name": row_dict[3],"manufacture_unit_id_str" : manufacture_unit_id}
            )
            if product_sub_category_obj is None:
                product_sub_category_obj = DatabaseModel.save_documents(
                    product_sub_category, {
                        "name": row_dict[3],
                        "description": str(row_dict[4]) if row_dict[4] else "",
                        "code": str(row_dict[5]) if row_dict[5] else "",
                        "product_category_id": product_category_obj.id,
                        "manufacture_unit_id_str" : manufacture_unit_id
                    }
                )

            # Brand Mapping
            brand_obj = DatabaseModel.get_document(
                brand.objects, {"name": row_dict[6],"manufacture_unit_id_str" : manufacture_unit_id}
            )
            if brand_obj is None:
                brand_obj = DatabaseModel.save_documents(
                    brand, {
                        "name": row_dict[6],
                        "code": str(row_dict[7]) if row_dict[7] else "",
                        "logo": str(row_dict[8]) if row_dict[8] else "",
                        "product_sub_category_id_str": str(product_sub_category_obj.id),
                        "manufacture_unit_id_str" : manufacture_unit_id
                    }
                )

            # Product Mapping
            products_obj = DatabaseModel.get_document(
                products.objects, {"name": row_dict[9], "manufacture_unit_id": ObjectId(manufacture_unit_id)}
            )
            if products_obj is None:
                products_obj = DatabaseModel.save_documents(
                    products, {
                        "name": row_dict[9],
                        "description": str(row_dict[10]) if row_dict[10] else "",
                        "price": float(row_dict[11]) if row_dict[11] else 0.0,
                        "discount_price": float(row_dict[12]) if row_dict[12] else None,
                        "currency": row_dict[13] if row_dict[13] else "USD",
                        "stock_quantity": int(row_dict[14]) if row_dict[14] else 0,
                        "primary_image": str(row_dict[15]) if row_dict[15] else "",
                        "product_image_list": row_dict[16].split(",") if pd.notna(row_dict[16]) else [],
                        "product_video_list": row_dict[17].split(",") if pd.notna(row_dict[17]) else [],
                        "colour": row_dict[18] if row_dict[18] else "",
                        "height": float(row_dict[19]) if row_dict[19] else None,
                        "weight": float(row_dict[20]) if row_dict[20] else None,
                        "dimensions": row_dict[21] if row_dict[21] else "",
                        "rating": float(row_dict[22]) if row_dict[22] else 0.0,
                        "warranty_period": row_dict[23] if row_dict[23] else "",
                        "tags": row_dict[24].split(",") if pd.notna(row_dict[24]) else [],
                        "sku": row_dict[25] if row_dict[25] else "",
                        "mpin": row_dict[26] if row_dict[26] else "",
                        "product_sub_category_id": product_sub_category_obj.id,
                        "manufacture_unit_id": ObjectId(manufacture_unit_id),
                        "brand_id": brand_obj.id,
                    }
                )
        
        data['status'] = True
    except Exception as e:
        data['error'] = f"{i+3}th row have has {e}"
    
    return data
