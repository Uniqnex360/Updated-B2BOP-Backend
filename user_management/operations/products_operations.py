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
    i = 0
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



@csrf_exempt
def productSearch(request):
    json_request = JSONParser().parse(request)
    search_query = json_request['search_query']
    manufacture_unit_id = json_request['manufacture_unit_id']
    pipeline = [
        {
            "$match": {
                "manufacture_unit_id" : ObjectId(manufacture_unit_id)
            }
        },
        {
            "$lookup": {
                "from": "product_sub_category",  # Collection name
                "localField": "product_sub_category_id",
                "foreignField": "_id",
                "as": "sub_category_info"
            }
        },
        {
            "$lookup": {
                "from": "brand",  # Collection name
                "localField": "brand_id",
                "foreignField": "_id",
                "as": "brand_info"
            }
        },
        {
            "$lookup": {
                "from": "product_category",  # Collection name
                "localField": "sub_category_info.product_category_id",
                "foreignField": "_id",
                "as": "category_info"
            }
        },
        {
            "$match": {
                "$or": [
                    {"name": {"$regex": search_query, "$options": "i"}},
                    {"description": {"$regex": search_query, "$options": "i"}},
                    {"tags": {"$regex": search_query, "$options": "i"}},
                    {"brand_info.name": {"$regex": search_query, "$options": "i"}},
                    {"sub_category_info.name": {"$regex": search_query, "$options": "i"}},
                    {"category_info.name": {"$regex": search_query, "$options": "i"}}
                ]
            }
        },
        {
            "$project": {
                "_id": {"$toString": "$_id"},  # Convert product _id to string
                "name": 1,
                "description": 1,
                "price": 1,
                "discount_price": 1,
                "is_available": 1,
                "currency": 1,
                "stock_quantity": 1,
                "primary_image": 1,
                "product_image_list": 1,
                "product_video_list": 1,
                "colour": 1,
                "height": 1,
                "weight": 1,
                "sku": 1,
                "rating": 1,
                "review_count": 1,
                "warranty_period": 1,
                "tags": 1,
                "brand_info": {
                    "name": {"$arrayElemAt": ["$brand_info.name", 0]},
                    "_id": {"$toString": {"$arrayElemAt": ["$brand_info._id", 0]}}  # Convert brand _id to string
                },
                "sub_category_info": {
                    "name": {"$arrayElemAt": ["$sub_category_info.name", 0]},
                    "_id": {"$toString": {"$arrayElemAt": ["$sub_category_info._id", 0]}}  # Convert sub-category _id to string
                },
                "category_info": {
                    "name": {"$arrayElemAt": ["$category_info.name", 0]},
                    "_id": {"$toString": {"$arrayElemAt": ["$category_info._id", 0]}}  # Convert category _id to string
                }
            }
        }
    ]
    results = list(products.objects.aggregate(pipeline))
    return results


