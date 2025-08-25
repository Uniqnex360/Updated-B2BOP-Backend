from user_management.models import *
from django.http import JsonResponse
from b2bop_project.custom_mideleware import SIMPLE_JWT
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from bson import ObjectId
import pandas as pd
from b2bop_project.crud import DatabaseModel
import ast
from spellchecker import SpellChecker
from mongoengine import DoesNotExist
from django.core.files.storage import FileSystemStorage
from django.conf import settings
import json
import math
import os


def obtainProductCategoryList(request):
    # Retrieve parameters from the request
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    product_category_id = request.GET.get('product_category_id')
    industry_id_str = request.GET.get('industry_id')

    # If product_category_id is None, return level 1 categories
    if not product_category_id:
        match = {
            "manufacture_unit_id_str": manufacture_unit_id,
            "level": 1
        }
        if industry_id_str:
            match["industry_id_str"] = industry_id_str

        pipeline = [
            {"$match": match},
            {
                "$project": {
                    "_id": 0,
                    "id": {"$toString": "$_id"},
                    "name": 1,
                    "is_parent": {
                        "$cond": {
                            "if": {"$ne": ["$child_categories", []]},
                            "then": True,
                            "else": False
                        }
                    }
                }
            }
        ]
        product_category_list = list(product_category.objects.aggregate(*pipeline))
    else:
        # Validate product_category_id
        try:
            category_oid = ObjectId(product_category_id)
        except Exception as e:
            # Handle invalid ObjectId
            return []

        # Build the match criteria for the starting category
        match_starting_category = {
            "id": category_oid,
            "manufacture_unit_id_str": manufacture_unit_id
        }
        if industry_id_str:
            match_starting_category["industry_id_str"] = industry_id_str

        try:
            # Fetch the starting category
            starting_category = product_category.objects.get(**match_starting_category)
        except DoesNotExist:
            # Starting category does not exist
            return []

        # Initialize the list to collect categories
        product_category_list = []

        # If the starting category is an end-level category, return it
        if starting_category.end_level:
            product_category_list.append({
                "id": str(starting_category.id),
                "name": starting_category.name,
                "is_parent": False  # Since it's an end-level category
            })
        else:
            # Use $graphLookup to find all descendant end-level categories
            pipeline = [
                {"$match": {"_id": category_oid}},
                {
                    "$graphLookup": {
                        "from": "product_category",
                        "startWith": "$_id",
                        "connectFromField": "_id",
                        "connectToField": "parent_category_id",
                        "as": "descendants",
                        "maxDepth": 10,  # Adjust as needed
                        "depthField": "depth"
                    }
                },
                # Unwind the descendants to treat each descendant separately
                {"$unwind": "$descendants"},
                # Match only the end-level categories
                {"$match": {"descendants.end_level": True}},
                {
                    "$match": {
                        "descendants.manufacture_unit_id_str": manufacture_unit_id,
                        **({"descendants.industry_id_str": industry_id_str} if industry_id_str else {})
                    }
                },
                # Project the required fields
                {
                    "$project": {
                        "_id": 0,
                        "id": {"$toString": "$descendants._id"},
                        "name": "$descendants.name",
                        "is_parent": {"$literal": False}  # Use $literal to assign False
                    }
                }
            ]

            # Execute the aggregation pipeline
            descendants_list = list(product_category.objects.aggregate(*pipeline))
            product_category_list.extend(descendants_list)

    # Return the result as a JsonResponse
    return product_category_list


# def obtainProductCategoryList(request):
#     # manufacture_unit_id = obtainManufactureIdFromToken(request)
#     manufacture_unit_id = request.GET.get('manufacture_unit_id')
#     product_category_id = request.GET.get('product_category_id')
#     industry_id_str = request.GET.get('industry_id')
    
#     match = dict()
#     match['manufacture_unit_id_str'] = manufacture_unit_id
#     if industry_id_str != None and industry_id_str != "":
#         match['industry_id_str'] = industry_id_str
#     parent_category_obj = None
#     if product_category_id == None:
#         match['level'] = 1
#     else:
#         match['parent_category_id'] = ObjectId(product_category_id)
#         pipeline =[
#         {
#             "$match" : {"_id" : ObjectId(product_category_id)}
#         },
#         {
#            "$project" :{
#             "_id":0,
#             "id":{"$toString" : "$_id"},
#             "name" : 1,
#             "parent_category" : True,
#             "is_parent": { 
#                 "$cond": { 
#                     "if": { "$ne": ["$child_categories", []] }, 
#                     "then": True, 
#                     "else": False 
#                 } 
#             }
#            }
#         }
#         ]
#         parent_category_obj = (list(product_category.objects.aggregate(*(pipeline))))[0]


#     pipeline =[
#         {
#             "$match" : match
#         },
#         {
#            "$project" :{
#             "_id":0,
#             "id":{"$toString" : "$_id"},
#             "name" : 1,
#             "is_parent": { 
#                 "$cond": { 
#                     "if": { "$ne": ["$child_categories", []] }, 
#                     "then": True, 
#                     "else": False 
#                 } 
#             }
#            }
#         }
#     ]
#     product_category_list = list(product_category.objects.aggregate(*(pipeline)))
#     if product_category_list != [] and parent_category_obj != None:
#         product_category_list.append(parent_category_obj)

#     return product_category_list

def obtainIndustryListForDealer(request):
    user_id = request.GET.get("user_id")
    pipeline =[
        {
            "$match" : {
                "user_id_str" : user_id
            }
        },
        {
        "$lookup" :{
            "from" : "industry",
            "localField" : "allowed_industry_list",
            "foreignField" : "_id",
            "as" : "industry_ins"
        }
        },
        {"$unwind" : "$industry_ins"},
        {"$project" : {
                    "_id" : 0,
                    "id" : {"$toString" : "$industry_ins._id"},
                    "name" : "$industry_ins.name"
        }},
        {
            "$sort" : {"name" : 1}
        }
    ]
    industry_list = list(user_industry_config.objects.aggregate(*(pipeline)))
    return industry_list


def obtainProductCategoryListForDealer(request):
    # manufacture_unit_id = obtainManufactureIdFromToken(request)
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    industry_id_str = request.GET.get('industry_id')
    match = dict()
    match['manufacture_unit_id_str'] = manufacture_unit_id
    match['end_level'] = True
    if industry_id_str != None and industry_id_str != "":
        match['industry_id_str'] = industry_id_str
    pipeline =[
        {
            "$match" : match
        },
        {
           "$project" :{
            "_id":0,
            "id":{"$toString" : "$_id"},
            "name" : 1
           }
        }
    ]
    product_category_list = list(product_category.objects.aggregate(*(pipeline)))
    return product_category_list


def obtainEndlevelcategoryList(request):
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    pipeline =[
        {
            "$match" : {
                "manufacture_unit_id_str" : manufacture_unit_id,
                "end_level" : True
            }
        },
        {
           "$project" :{
            "_id":0,
            "id":{"$toString" : "$_id"},
            "name" : 1
           }
        }
    ]
    product_category_list = list(product_category.objects.aggregate(*(pipeline)))
    return product_category_list

# def obtainbrandList(request):
#     manufacture_unit_id = request.GET.get('manufacture_unit_id')
#     industry_id = request.GET.get('industry_id')
#     product_category_id = request.GET.get('product_category_id')
#     role_name = request.GET.get('role_name')
#     is_parent = request.GET.get('is_parent')
#     if is_parent != None and is_parent != "":
#         is_parent = True

#     # Build the match conditions for the brand collection
#     match = {"manufacture_unit_id_str": manufacture_unit_id}
#     if industry_id:
#         match["industry_id_str"] = industry_id

#     # Build the match conditions for the lookup pipeline
#     lookup_match_conditions = []
#     # Always match on brand_id using the variable from 'let'
#     lookup_match_conditions.append({"$expr": {"$eq": ["$brand_id", "$$brand_id"]}})
#     # If role_name is not provided, include 'visible': True
#     if not role_name:
#         lookup_match_conditions.append({"visible": True})
#     # If product_category_id is provided, add a condition to match 'category_id'
#     if product_category_id:
#         try:
#             category_oid = ObjectId(product_category_id)
#             lookup_match_conditions.append({"$expr": {"$eq": ["$category_id", category_oid]}})
#         except Exception as e:
#             # Handle invalid ObjectId
#             return []

#     # Combine the match conditions into a single match object
#     if lookup_match_conditions:
#         match_obj = {"$match": {"$and": lookup_match_conditions}}
#     else:
#         match_obj = {"$match": {}}
    
#     pipeline = [
#         {"$match": match},
#         {
#             "$lookup": {
#                 "from": "product",
#                 "let": {"brand_id": "$_id"},
#                 "pipeline": [
#                     match_obj,
#                     {"$count": "total_count"},
#                 ],
#                 "as": "products_count",
#             }
#         },
#         {
#             "$addFields": {
#                 "products_count": {
#                     "$ifNull": [{"$arrayElemAt": ["$products_count.total_count", 0]}, 0],
#                 }
#             }
#         },
#         # Filter out brands with zero products when product_category_id is provided
#         # This ensures only brands associated with the provided category are included
#         {
#             "$match": {
#                 "$or": [
#                     {"products_count": {"$gt": 0}},
#                     {"$expr": {"$eq": [product_category_id, None]}}
#                 ]
#             }
#         },
#         {
#             "$project": {
#                 "_id": 0,
#                 "id": {"$toString": "$_id"},
#                 "name": 1,
#                 "products_count": 1,
#             }
#         },
#     ]

#     brand_list = list(brand.objects.aggregate(*pipeline))
#     return brand_list


@csrf_exempt
def obtainbrandList(request):
    # Retrieve parameters from the request
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    industry_id = request.GET.get('industry_id')
    product_category_id = request.GET.get('product_category_id')
    role_name = request.GET.get('role_name')
    is_parent = request.GET.get('is_parent')
    if is_parent not in [None, "", False, "false", "False"]:
        is_parent = True
    else:
        is_parent = False

    # Build the match conditions for the brand collection
    match = {"manufacture_unit_id_str": manufacture_unit_id}
    if industry_id:
        match["industry_id_str"] = industry_id

    # Build the match conditions for the lookup pipeline
    lookup_match_conditions = []
    lookup_match_conditions.append({"$expr": {"$eq": ["$brand_id", "$$brand_id"]}})
    if role_name != "manufacturer_admin":
        lookup_match_conditions.append({"visible": True})

    if product_category_id:
        try:
            category_oid = ObjectId(product_category_id)

            if is_parent:
                end_level_category_ids = get_end_level_category_ids(category_oid)
                if not end_level_category_ids:
                    return []
                lookup_match_conditions.append({
                    "$expr": {"$in": ["$category_id", end_level_category_ids]}
                })
            else:
                lookup_match_conditions.append({
                    "$expr": {"$eq": ["$category_id", category_oid]}
                })
        except Exception as e:
            return []

    if lookup_match_conditions:
        match_obj = {"$match": {"$and": lookup_match_conditions}}
    else:
        match_obj = {"$match": {}}

    pipeline = [
        {"$match": match},
        {
            "$lookup": {
                "from": "product",
                "let": {"brand_id": "$_id"},
                "pipeline": [
                    match_obj,
                    {"$count": "total_count"},
                ],
                "as": "products_count",
            }
        },
        {
            "$addFields": {
                "products_count": {
                    "$ifNull": [{"$arrayElemAt": ["$products_count.total_count", 0]}, 0],
                }
            }
        },
        {
            "$match": {
                "$or": [
                    {"products_count": {"$gt": 0}},
                    {"$expr": {"$eq": [product_category_id, None]}}
                ]
            }
        },
        {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$_id"},
                # "name": 1,   # ❌ old field projection (commented)
                # "products_count": 1,  # kept
                # "brand_name": 1,      # ❌ not in DB
                # "brand_logo": 1,      # ❌ not in DB
                "name": {"$ifNull": ["$name", ""]},
                "logo": {"$ifNull": ["$logo", ""]},    # The brand without logo or photo or name,it won't break.   
                "products_count": 1
            }
        },
        {"$sort": {"name": 1}}  # ✅ added sorting by name
    ]

    brand_list = list(brand.objects.aggregate(*pipeline))
    return JsonResponse({"data": brand_list, "message": "success", "status": True, "token": None})


def get_end_level_category_ids(category_oid):
    pipeline = [
            {"$match": {"_id": category_oid}},
            {
                "$project": {
                    "_id": 0,
                    "end_level": 1
                }
            }
        ]

        # Execute the aggregation pipeline
    product_category_obj = list(product_category.objects.aggregate(*pipeline))
    if product_category_obj == []:
        return []

    if product_category_obj[0]['end_level'] == True:
        return [category_oid]
    else:
        # Use $graphLookup to find all descendant end-level categories
        pipeline = [
            {"$match": {"_id": category_oid}},
            {
                "$graphLookup": {
                    "from": "product_category",
                    "startWith": "$_id",
                    "connectFromField": "_id",
                    "connectToField": "parent_category_id",
                    "as": "descendants",
                    "maxDepth": 10,  # Adjust as needed
                    "depthField": "depth"
                }
            },
            # Unwind the descendants to treat each descendant separately
            {"$unwind": "$descendants"},
            # Match only the end-level categories
            {"$match": {"descendants.end_level": True}},
            # Group to collect all end-level category IDs
            {
                "$group": {
                    "_id": None,
                    "end_level_category_ids": {"$addToSet": "$descendants._id"}
                }
            }
        ]

        # Execute the aggregation pipeline
        result = list(product_category.objects.aggregate(*pipeline))
        if result:
            return result[0]['end_level_category_ids']
        else:
            return []


@csrf_exempt
def obtainProductsList(request):
    json_request = JSONParser().parse(request)
    manufacture_unit_id = json_request['manufacture_unit_id']
    sort_by = json_request.get('sort_by')
    sort_by_value = json_request.get('sort_by_value')
    product_category_id = json_request.get('product_category_id')
    filters = json_request.get('filters')
    is_parent = json_request.get('is_parent')
    price_from = json_request.get('price_from')
    price_to = json_request.get('price_to')
    industry_id_str = json_request.get('industry_id')
    brand_id_list = json_request.get('brand_id_list')
    category_name = json_request.get('collection_name')
    category_filters = json_request.get('category_filters', [])
    if category_name != None and category_name != "":
        if not category_name:
            return {"error": "category_name is required"}
        category_id = DatabaseModel.get_document(product_category.objects, {"name": category_name},['id']).id
        match_conditions = {
            "category_id": category_id,
            "manufacture_unit_id": ObjectId(manufacture_unit_id),
            # "availability": True
        }

        for filter_name,filter_value in category_filters.items():
            # filter_name = filter.get('name')
            # filter_value = filter.get('value')
            if filter_name and filter_value:
                if isinstance(filter_value, list):
                    match_conditions[f"attributes.{filter_name}"] = {"$in": filter_value}
                else:
                    match_conditions[f"attributes.{filter_name}"] = filter_value
        pipeline = [
            {"$match": match_conditions},
            {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$_id"},
                "product_name": {"$ifNull": ["$product_name", "N/A"]},
                "logo": {"$ifNull": [{"$first": "$images"}, "http://example.com/"]},
                "sku_number_product_code_item_number": {"$ifNull": ["$sku_number_product_code_item_number", "N/A"]},
                "mpn": {"$ifNull": ["$mpn", "N/A"]},
                "msrp": {"$ifNull": [{"$round": ["$msrp", 2]}, 0.0]},
                "was_price": {"$ifNull": [{"$round": ["$was_price", 2]}, 0.0]},
                "brand_name": {"$ifNull": ["$brand_name", "N/A"]},
                "visible": {"$ifNull": ["$visible", False]},
                "end_level_category": {"$ifNull": ["$product_category_ins.name", "N/A"]},
                # "brand_logo": {"$ifNull": ["$brand_ins.logo", ""]},
                "price": {"$ifNull": [{"$round": ["$list_price", 2]}, 0.0]},
                "currency": {"$ifNull": ["$currency", "N/A"]},
                "availability": {"$ifNull": ["$availability", False]},
                "discount": {"$ifNull": ["$discount", 0]},
                "quantity": {"$ifNull": ["$quantity", 0]},
                "upc_ean": {"$ifNull": ["$upc_ean", "N/A"]},
            }
            },
            {
                "$sort" : {
                    "id" : -1
            }}
        ]

        products = list(product.objects.aggregate(pipeline))
        return products
    if brand_id_list != None and brand_id_list != "" and brand_id_list != []:
        brand_id_list = [ObjectId(ins) for ins in brand_id_list]
    
    product_list = []

    match = {}
    match['manufacture_unit_id'] = ObjectId(manufacture_unit_id)

    if product_category_id != None and product_category_id != "":
        match['category_id'] = ObjectId(product_category_id)
    if filters != None and filters != "all" and filters != "":
        match['availability'] = True if filters == "In-stock" else False

    if industry_id_str != None and industry_id_str != "":
        match['industry_id_str'] = industry_id_str

    if (is_parent != None and is_parent == '') or is_parent == False:
        pipeline =[
            {
                "$match" : match
            },
            {
                "$lookup": {
                    "from": "product_category",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "product_category_ins"
                }
            },
            {"$unwind" : "$product_category_ins"},
            {
                "$addFields": {
                    "end_level_category": "$product_category_ins.name"
                }
            },
            {
                "$lookup": {
                    "from": "brand",
                    "localField": "brand_id",
                    "foreignField": "_id",
                    "as": "brand_ins"
                }
            },
            {
            "$unwind": {
                "path": "$brand_ins", 
                "preserveNullAndEmptyArrays": True
            }
            }]
        price_match = dict()
        if brand_id_list != None and brand_id_list != "" and brand_id_list != []:
            price_match['brand_ins._id'] = {"$in": brand_id_list}
        if (price_from != None and price_from != "") and (price_to != None and price_to != ""):
            if price_to > 0:
                price_to = int(price_to) + 1
            price_match['list_price'] = {
                "$gte": int(price_from),
                "$lte": price_to
            }
        if price_match != {}:
            brand_match = {
                "$match" : price_match
            }
            pipeline.append(brand_match)
        project_stage = {
            "$project" :{
                "_id":0,
                "id" : {"$toString" : "$_id"},
                "product_name" : "$product_name",
                "logo" : {"$ifNull" : [{"$first":"$images"},"http://example.com/"]},
                "sku_number_product_code_item_number" : "$sku_number_product_code_item_number",
                "mpn" : 1,
                "msrp" : {"$round":["$msrp",2]},
                "was_price" :{"$round":["$was_price",2]},
                "brand_name" : 1,
                "visible" : 1,
                "end_level_category" : 1,
                "price" : {"$round":["$list_price",2]},
                "currency" : 1,
                "availability" : 1,
                "quantity" : 1
            }
            }
        pipeline.append(project_stage)
        if sort_by != None and sort_by != "":
            sorting_pipeline = {
                    "$sort": {
                        sort_by: int(sort_by_value)
                    }
                }
        else:
            sorting_pipeline = {
                    "$sort": {
                        "id": -1
                    }
                }
        pipeline.append(sorting_pipeline)
        product_list = list(product.objects.aggregate(*(pipeline)))

    elif is_parent != None and is_parent != "" and is_parent == True:
        pipeline = [
        {
            "$match": {
                "_id": ObjectId(product_category_id)
            }
        },
        {
            "$graphLookup": {
                "from": "product_category",
                "startWith": "$_id",
                "connectFromField": "_id",
                "connectToField": "parent_category_id",
                "as": "all_categories",
                "maxDepth": 5
            }
        },
        {
            "$project": {
                "category_ids": {
                    "$map": {
                        "input": "$all_categories",
                        "as": "category",
                        "in": "$$category._id"
                    }
                }
            }
        },
        {"$unwind": "$category_ids"},
        {
            "$lookup": {
                "from": "product",
                "localField": "category_ids",
                "foreignField": "category_id",
                "as": "product_ins"
            }
        },
        {"$unwind": "$product_ins"},
        {
            "$lookup": {
                "from": "product_category",
                "localField": "product_ins.category_id",
                "foreignField": "_id",
                "as": "product_category_ins"
            }
        },
        {"$unwind": "$product_category_ins"},
         {
            "$addFields": {
                "end_level_category": "$product_category_ins.name"
            }
        },
        {
            "$lookup": {
                "from": "brand",
                "localField": "product_ins.brand_id",
                "foreignField": "_id",
                "as": "brand_ins"
            }
            },
            {
            "$unwind": {
                "path": "$brand_ins", 
                "preserveNullAndEmptyArrays": True
            }
        }]
        price_match = dict()
        if brand_id_list != None and brand_id_list != "" and brand_id_list != []:
            price_match['brand_ins._id'] = {"$in": brand_id_list}
        if (price_from != None and price_from != "") and (price_to != None and price_to != ""):
            if price_to > 0:
                price_to = int(price_to) + 1
            price_match['product_ins.list_price'] = {
                "$gte": int(price_from),
                "$lte": price_to
            }
        if price_match != {}:
            brand_match = {
                "$match" : price_match
            }
            pipeline.append(brand_match)
        project_stage = {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$product_ins._id"},
                "product_name": "$product_ins.product_name",
                "logo": {"$ifNull" : [{"$first": "$product_ins.images"},"http://example.com/"]},
                "sku_number_product_code_item_number": "$product_ins.sku_number_product_code_item_number",
                "mpn": "$product_ins.mpn",
                "msrp": {"$round":["$product_ins.msrp",2]},
                "was_price": {"$round":["$product_ins.was_price",2]},
                "brand_name": "$product_ins.brand_name",
                "visible": "$product_ins.visible",
                "end_level_category": 1,
                "price": {"$round":["$product_ins.list_price",2]},
                "currency": "$product_ins.currency",
                "availability": "$product_ins.availability",
                "quantity" : "$product_ins.quantity"
            }
        }
        pipeline.append(project_stage)
        
        if sort_by != None and sort_by != "":
            sorting_pipeline = {
                    "$sort": {
                        sort_by: int(sort_by_value)
                    }
                }
            
        else:
            sorting_pipeline = {
                    "$sort": {
                        "id": -1
                    }
                }
        pipeline.append(sorting_pipeline)
        product_list = list(product_category.objects.aggregate(pipeline))

    return product_list


@csrf_exempt
def obtainProductsListForDealer(request):
    json_request = JSONParser().parse(request)
    product_category_id = json_request.get('product_category_id')
    manufacture_unit_id = json_request.get('manufacture_unit_id')
    industry_id_str = json_request.get('industry_id')
    skip = int(json_request.get("skip"))
    limit = int(json_request.get("limit"))

    filters = json_request.get('filters')
    sort_by = json_request.get('sort_by')
    sort_by_value = json_request.get('sort_by_value')

    brand_id_list = json_request.get('brand_id_list')
    if brand_id_list != None and brand_id_list != "" and brand_id_list != []:
        brand_id_list = [ObjectId(ins) for ins in brand_id_list]
    price_from = json_request.get('price_from')
    price_to = json_request.get('price_to')

    match = {}
    match['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
    match['visible'] = True

    if product_category_id != "":
        match['category_id'] = ObjectId(product_category_id)
    if filters != None and filters != "all" and filters != "":
        match['availability'] = True if filters == "true" else False
    if industry_id_str != None and industry_id_str != "":
        match['industry_id_str'] = industry_id_str

    if product_category_id == "":
        pipeline =[
            {
                "$match" : match
            },
            {
                "$lookup": {
                    "from": "product_category",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "product_category_ins"
                }
            },
            {"$unwind" : "$product_category_ins"},
            {
                "$lookup": {
                    "from": "brand",
                    "localField": "brand_id",
                    "foreignField": "_id",
                    "as": "brand_ins"
                }
            },
            {
            "$unwind": {
                "path": "$brand_ins", 
                "preserveNullAndEmptyArrays": True
            }
            },
            {
                "$lookup": {
                    "from": "wishlist",
                    "localField": "_id",
                    "foreignField": "product_id",
                    "as": "wishlist_ins"
                }
            },
            {
            "$unwind": {
                "path": "$wishlist_ins", 
                "preserveNullAndEmptyArrays": True
            }
            }
            ]
        price_match = dict()
        if brand_id_list != None and brand_id_list != "" and brand_id_list != []:
            price_match['brand_ins._id'] = {"$in": brand_id_list}
        if (price_from != None and price_from != "") and (price_to != None and price_to != ""):
            if price_to > 0:
                price_to = int(price_to) + 1
            price_match['list_price'] = {
                "$gte": int(price_from),
                "$lte": price_to
            }
        if price_match != {}:
            brand_match = {
                "$match" : price_match
            }
            pipeline.append(brand_match)
        project_stage = {
            "$project" :{
                "_id":0,
                "id" : {"$toString" : "$_id"},
                "name" : "$product_name",
                "logo" : {"$ifNull" : [{"$first":"$images"},"http://example.com/"]},
                "sku_number" : "$sku_number_product_code_item_number",
                "mpn" : 1,
                "msrp" : {"$round" : ["$msrp",2]},
                "was_price" :{"$round" : ["$was_price",2]},
                "brand_name" : 1,
                "visible" : 1,
                "end_level_category" : "$product_category_ins.name",
                "brand_logo" : {"$ifNull" : ["$brand_ins.logo",""]},
                "price" : {"$round":["$list_price",2]},
                "currency" : 1,
                "availability" : 1,
                "discount" : 1,
                "quantity" : 1,
                "is_wishlist": {
                "$cond": {
                    "if": {"$ne": [{"$type": "$wishlist_ins"}, "missing"]},
                    "then": True,
                    "else": False
                }
                },
                "wishlist_id": {
                    "$cond": {
                        "if": {"$ne": [{"$type": "$wishlist_ins"}, "missing"]},
                        "then": {"$toString":"$wishlist_ins._id"}, 
                        "else": None
                    }
                }
            }
            }
            
        pipeline.append(project_stage)
        if sort_by != None and sort_by != "":
            sorting_pipeline = [{
                    "$sort": {
                        sort_by: int(sort_by_value)
                    }
                },
                {
                    "$skip": skip
                },
                {
                    "$limit": limit
                }]
            pipeline.extend(sorting_pipeline)
        product_list = list(product.objects.aggregate(*(pipeline)))

    elif product_category_id != "":
        match = {}
        match['product_ins.manufacture_unit_id'] = ObjectId(manufacture_unit_id)
        match['product_ins.visible'] = True
        if filters != None and filters != "all" and filters != "":
            match['product_ins.availability'] = True if filters == "true" else False
        pipeline = [
        {
            "$match": {
                "_id": ObjectId(product_category_id)
            }
        },
        # {
        #     "$graphLookup": {
        #         "from": "product_category",
        #         "startWith": "$_id",
        #         "connectFromField": "_id",
        #         "connectToField": "parent_category_id",
        #         "as": "all_categories",
        #         "maxDepth": 5
        #     }
        # },
        # {
        #     "$project": {
        #         "category_ids": {
        #             "$map": {
        #                 "input": "$all_categories",
        #                 "as": "category",
        #                 "in": "$$category._id"
        #             }
        #         }
        #     }
        # },
        # {"$unwind": "$category_ids"},
        {
            "$lookup": {
                "from": "product",
                "localField": "_id",
                "foreignField": "category_id",
                "as": "product_ins"
            }
        },
        {"$unwind": "$product_ins"},
        {
                "$match" : match
        },
        # {
        #     "$lookup": {
        #         "from": "product_category",
        #         "localField": "product_ins.category_id",
        #         "foreignField": "_id",
        #         "as": "product_category_ins"
        #     }
        # },
        # {"$unwind": "$product_category_ins"},
        #  {
        #     "$addFields": {
        #         "end_level_category": "$product_category_ins.name"
        #     }
        # },
        {
            "$lookup": {
                "from": "brand",
                "localField": "product_ins.brand_id",
                "foreignField": "_id",
                "as": "brand_ins"
            }
        },
        {"$unwind": "$brand_ins"},
         {
                "$lookup": {
                    "from": "wishlist",
                    "localField": "product_ins._id",
                    "foreignField": "product_id",
                    "as": "wishlist_ins"
                }
            },
            {
            "$unwind": {
                "path": "$wishlist_ins", 
                "preserveNullAndEmptyArrays": True
            }
            }
        ]
        price_match = dict()
        if brand_id_list != None and brand_id_list != "" and brand_id_list != []:
            price_match['brand_ins._id'] = {"$in": brand_id_list}
        if (price_from != None and price_from != "") and (price_to != None and price_to != ""):
            if price_to > 0:
                price_to = int(price_to) + 1

            price_match['product_ins.list_price'] = {
                "$gte": int(price_from),
                "$lte": price_to
            }
        if price_match != {}:
            brand_match = {
                "$match" : price_match
            }
            pipeline.append(brand_match)
        project_stage = {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$product_ins._id"},
                "name": "$product_ins.product_name",
                "logo": {"$ifNull" : [{"$first": "$product_ins.images"},"http://example.com/"]},
                "sku_number": "$product_ins.sku_number_product_code_item_number",
                "mpn": "$product_ins.mpn",
                "msrp": {"$round":["$product_ins.msrp",2]},
                "was_price": {"$round":["$product_ins.was_price",2]},
                "brand_name": "$product_ins.brand_name",
                "visible": "$product_ins.visible",
                "end_level_category": "$name",
                "brand_logo" : {"$ifNull" : ["$brand_ins.logo",""]},
                "price": {"$round":["$product_ins.list_price",2]},
                "currency": "$product_ins.currency",
                "availability": "$product_ins.availability",
                "discount" : {"$round": ["$product_ins.discount", 2]}, 
                "quantity" : "$product_ins.quantity",
                "is_wishlist": {
                "$cond": {
                    "if": {"$ne": [{"$type": "$wishlist_ins"}, "missing"]},
                    "then": True,
                    "else": False
                }
                },
                "wishlist_id": {
                    "$cond": {
                        "if": {"$ne": [{"$type": "$wishlist_ins"}, "missing"]},
                        "then": {"$toString":"$wishlist_ins._id"}, 
                        "else": None
                    }
                }
            }
        }
        pipeline.append(project_stage)
        if sort_by != None and sort_by != "":
            sorting_pipeline = [{
                    "$sort": {
                        sort_by: int(sort_by_value)
                    }
                },
                {
                    "$skip": skip
                },
                {
                    "$limit": limit
                }]
            pipeline.extend(sorting_pipeline)
        product_list = list(product_category.objects.aggregate(pipeline))

    return product_list

@csrf_exempt
def productCountForDealer(request):
    json_request = JSONParser().parse(request)
    product_category_id = json_request.get('product_category_id')
    manufacture_unit_id = json_request.get('manufacture_unit_id')
    filters = json_request.get('filters')
    industry_id_str = json_request.get('industry_id')
    brand_id_list = json_request.get('brand_id_list')
    price_from = json_request.get('price_from')
    price_to = json_request.get('price_to')
    
    

    match = {"manufacture_unit_id" : ObjectId(manufacture_unit_id),"visible" : True}

    if product_category_id != None and product_category_id != "":
        match['category_id'] = ObjectId(product_category_id)
    if filters != None and filters != "all":
        match['availability'] = True if filters == "true" else False
    if industry_id_str != None and industry_id_str != "":
        match['industry_id_str'] = industry_id_str
    if brand_id_list != None and brand_id_list != "" and brand_id_list != []:
        brand_id_list = [ObjectId(ins) for ins in brand_id_list]
        match['brand_id'] = {"$in": brand_id_list}

    if (price_from != None and price_from != "") and (price_to != None and price_to != ""):
            if price_to > 0:
                price_to = int(price_to) + 1
            match['list_price'] = {
                "$gte": int(price_from),
                "$lte": price_to
            }
    
    
    # if product_category_id == "":

    count_pipeline = [
        {
            "$match": match
        },
        {
            "$count": "total_count"
        }
    ]

    # Execute the count pipeline to get the total count
    total_count_result = list(product.objects.aggregate(*(count_pipeline)))
    total_count = total_count_result[0]['total_count'] if total_count_result else 0
    # elif product_category_id != None and product_category_id != "":
        # match = {}
        # match['product_ins.manufacture_unit_id'] = ObjectId(manufacture_unit_id)
        # match['product_ins.visible'] = True
        # if filters is not None and filters != "all" and filters != "":
        #     match['product_ins.availability'] = True if filters == "true" else False

        # pipeline = [
        #     {
        #         "$match": {
        #             "_id": ObjectId(product_category_id)
        #         }
        #     },
        #     {
        #         "$graphLookup": {
        #             "from": "product_category",
        #             "startWith": "$_id",
        #             "connectFromField": "_id",
        #             "connectToField": "parent_category_id",
        #             "as": "all_categories",
        #             "maxDepth": 5
        #         }
        #     },
        #     {
        #         "$project": {
        #             "category_ids": {
        #                 "$map": {
        #                     "input": "$all_categories",
        #                     "as": "category",
        #                     "in": "$$category._id"
        #                 }
        #             }
        #         }
        #     },
        #     {"$unwind": "$category_ids"},
        #     {
        #         "$lookup": {
        #             "from": "product",
        #             "localField": "category_ids",
        #             "foreignField": "category_id",
        #             "as": "product_ins"
        #         }
        #     },
        #     {"$unwind": "$product_ins"},
        #     {
        #         "$match": match
        #     },
        #     {
        #         "$count": "total_products"
        #     }
        # ]
        # total_count_result = list(product_category.objects.aggregate(*(pipeline)))
        # pipeline = [
        #     {
        #         "$match": match
        #     },
            
        #     {
        #         "$count": "total_products"
        #     }
        # ]
        # total_count_result = list(product.objects.aggregate(*(pipeline)))
        # total_count = total_count_result[0]['total_products'] if total_count_result else 0

    return total_count

def obtainProductDetails(request):
    product_id = request.GET.get('product_id')
    product_list = {}
    pipeline =[
        {
            "$match" : {
                "_id" : ObjectId(product_id),
            }
        },
        {
                "$lookup": {
                    "from": "product_category",
                    "localField": "category_id",
                    "foreignField": "_id",
                    "as": "product_category_ins"
                }
            },
            {"$unwind" : "$product_category_ins"},
         {
            "$lookup": {
                "from": "brand",
                "localField": "brand_id",
                "foreignField": "_id",
                "as": "brand_ins"
            }
        },
        {
        "$unwind": {
            "path": "$brand_ins", 
            "preserveNullAndEmptyArrays": True
        }
        },
        {
           "$project" :{
            "_id":0,
            "id" : {"$toString" : "$_id"},
            "product_name" : {"$ifNull": ["$product_name", "N/A"]},
            "sku_number_product_code_item_number" : {"$ifNull": ["$sku_number_product_code_item_number", "N/A"]},
            "model" : {"$ifNull": ["$model", "N/A"]},
            "mpn" : {"$ifNull": ["$mpn", "N/A"]},
            "upc_ean" : {"$ifNull": ["$upc_ean", "N/A"]},
            "logo" : {"$ifNull" : [{"$first":"$images"},"http://example.com/"]},
            "long_description" : {"$ifNull": ["$long_description", "N/A"]},
            "short_description" : {"$ifNull": ["$short_description", "N/A"]},
            "list_price" : {"$ifNull": ["$list_price", 0.0]},
            "msrp" : {"$ifNull" : ["$msrp",0.0]},
            "was_price" : {"$ifNull" : ["$was_price",0.0]},
            "discount": { 
            "$concat": [
                { "$toString": { "$round": [{"$ifNull": ["$discount", 0]}, 2] } }, 
                "%" 
            ] 
            },
            "brand_name" : {"$ifNull": ["$brand_name", "N/A"]},
            "brand_logo" : {"$ifNull" : ["$brand_ins.logo",""]},
            "currency" : {"$ifNull": ["$currency", "N/A"]},
            "quantity" : {"$ifNull": ["$quantity", 0]},
            "availability" : {"$ifNull": ["$availability", False]},
            "images" : {"$ifNull": ["$images", []]},
            "attributes" : {"$ifNull": ["$attributes", {}]},
            "features" : {"$ifNull": ["$features", []]},
            "from_the_manufacture" : {"$ifNull": ["$from_the_manufacture", "N/A"]},
            "visible" : {"$ifNull": ["$visible", False]},
            "end_level_category" : {"$ifNull": ["$product_category_ins.name", "N/A"]},
            "industry_id_str" : {"$ifNull": ["$industry_id_str",""]}
           }
        }
    ]
    product_list = list(product.objects.aggregate(*(pipeline)))
    if len(product_list) > 0:
        if product_list[0]['industry_id_str'] != "":
            product_list[0]['industry_name'] = DatabaseModel.get_document(industry.objects,{"id" :product_list[0]['industry_id_str']},['name']).name
        else:
            product_list[0]['industry_name'] = "N/A"
        product_list = product_list[0]
    def replace_nan_with_none(d):
        for key, value in d.items():
            if isinstance(value, dict):
                replace_nan_with_none(value)
            elif isinstance(value, float) and math.isnan(value):
                d[key] = None

    replace_nan_with_none(product_list)
    return product_list




@csrf_exempt
def upload_file(request):
    
    general_fields = ['skuNumber code itemNumber', 'model', 'mpn', 'upc ean', 'level1 category', 'level2 category', 'level3 category', 'level4 category', 'level5 category', 'level6 category', 'breadcrumb', 'brandName', "brandlogo", "vendorName", 'productName', 'long description', 'short description', 'features', 'images', 'attributes', 'tags', 'msrp', 'currency', 'was price', 'list price', 'discount', 'quantity', 'quantityPrice', 'availability', 'return applicable']

    image_list = ['image_1', 'image_2', 'image_3', 'image_4', 'image_5','image_6', 'image_7', 'image_8', 'image_9', 'image_10']

    feature_list = ['feature_1', 'feature_2', 'feature_3', 'feature_4', 'feature_5', 'feature_6', 'feature_7', 'feature_8', 'feature_9', 'feature_10', 'feature_11', 'feature_12', 'feature_13', 'feature_14', 'feature_15']

    attribute_list = ['attribute_name_1', 'attribute_value_1', 'attribute_name_2', 'attribute_value_2', 'attribute_name_3', 'attribute_value_3', 'attribute_name_4', 'attribute_value_4', 'attribute_name_5', 'attribute_value_5', 'attribute_name_6', 'attribute_value_6', 'attribute_name_7', 'attribute_value_7', 'attribute_name_8', 'attribute_value_8', 'attribute_name_9', 'attribute_value_9', 'attribute_name_10', 'attribute_value_10', 'attribute_name_11', 'attribute_value_11', 'attribute_name_12', 'attribute_value_12', 'attribute_name_13', 'attribute_value_13', 'attribute_name_14', 'attribute_value_14', 'attribute_name_15', 'attribute_value_15', 'attribute_name_16', 'attribute_value_16']
    
    data = dict()
    data['status'] = False
    data['error'] = ""
    if 'file' not in request.FILES:
        data['error'] = "No file uploaded."
        return data

    file = request.FILES['file']
    try:
        if file.name.endswith('.xlsx'):
            df = pd.read_excel(file, header = 0)
            # if len(df.iloc[0]) != 47:
            #     data['error'] = "File having Missing columns"
            #     return data 
        elif file.name.endswith('.csv') or file.name.endswith('.txt'):
            df = pd.read_csv(file)
        else:
            data['error'] = "Unsupported file format."
            return data
    except Exception as e:
        data['error'] = f"Error reading file: {str(e)}"
        return data
    original_headers = df.columns
    fields_list = []

    for ins in original_headers:
        change = False
        normalized_field = ins.replace(" ", "").lower()
        pattern = re.sub(r'\s+', r'\\s+', re.escape(normalized_field.lower()))
        regex = re.compile(pattern)
        for field in general_fields:
            field1 = field.replace(" ", "").lower()
            if regex.search(field1.lower()):
                if "level1 category" in fields_list and field == "level1 category":
                    fields_list.append("level2 category")
                else:
                    fields_list.append(field)
                change = True
                break
        

        if change == False:
            for field in general_fields:
                if regex.search(field.lower()):
                    change = True
                    if "level1 category" in fields_list and field == "level1 category":
                        fields_list.append("level2 category")
                    else:
                        fields_list.append(field)
                    break
        
        
        if change == False:
            if ' ' in ins:
                given_prefix = ins.split()[0].lower()  # Get the first word and make it lowercase
            else:
                given_prefix = ins.split("/")[0].lower()

            pattern = re.sub(r'\s+', r'\\s+', re.escape(given_prefix.lower()))
            regex = re.compile(pattern)
            for field in general_fields:
                if regex.search(field.lower()):
                    if "level1 category" in fields_list and field == "level1 category":
                        fields_list.append("level2 category")
                    else:
                        fields_list.append(field)
                    break

            else:
                fields_list.append(ins)
    i = 0
    validation_error = list()
    xl_data = list()
    
    xl_contains_error_count = 0
    for i in range(len(df)):
        row_dict = df.iloc[i]
        error_dict = dict()
        xl_dict = dict()
        error_dict['row'] = i+1
        error_dict['error'] = list()
        xl_dict['product_obj'] = dict()
        xl_dict['product_obj']['features'] = list()
        xl_dict['product_obj']['images'] = list()
        xl_dict['product_obj']['attributes'] = dict()
        xl_dict['category_obj'] = dict()
        xl_dict['vendor_obj'] = dict()
        xl_dict['brand_obj'] = dict()
        brand_name_exist = False
        

        for j in range(len(row_dict)):
            if fields_list[j] == 'skuNumber code itemNumber':
                if pd.notnull(row_dict[j]):
                    xl_dict['product_obj']['sku_number_product_code_item_number'] = str(row_dict[j])
                else:
                    error_dict['error'].append(f"SKU number/Product Code/Item number Should be present")

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'model':
                xl_dict['product_obj']['model'] = str(row_dict[j])

            elif fields_list[j] == 'mpn':
                if pd.notnull(row_dict[j]):
                    xl_dict['product_obj']['mpn'] = str(row_dict[j])
                else:
                    error_dict['error'].append(f"MPN Should be present")

            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'upc ean' or fields_list[j] == "unspsc"):
                xl_dict['product_obj']['upc_ean'] = str(row_dict[j])


            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'level1 category' or fields_list[j] ==  "category_1"):
                xl_dict['category_obj']['level 1'] = str(row_dict[j])

            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'level2 category' or fields_list[j] ==  "category_2"):
                xl_dict['category_obj']['level 2'] = str(row_dict[j])
            
            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'level3 category' or fields_list[j] ==  "category_3"):
                xl_dict['category_obj']['level 3'] = str(row_dict[j])

            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'level4 category' or fields_list[j] ==  "category_4"):
                xl_dict['category_obj']['level 4'] = str(row_dict[j])

            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'level5 category' or fields_list[j] ==  "category_5"):
                xl_dict['category_obj']['level 5'] = str(row_dict[j])

            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'level6 category' or fields_list[j] ==  "category_6"):
                xl_dict['category_obj']['level 6'] = str(row_dict[j])


            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'breadcrumb' or fields_list[j] == "taxonomy"):
                if "[" in row_dict[j]:
                    try:
                        data_list = ast.literal_eval(row_dict[j])
                        result = ' > '.join(data_list)
                        xl_dict['product_obj']['breadcrumb'] = result
                    except:
                        xl_dict['product_obj']['breadcrumb'] = ""
                else:
                    xl_dict['product_obj']['breadcrumb'] = str(row_dict[10]) 

            
            elif fields_list[j] == 'brandName' or fields_list[j] == 'manufacturer':
                if pd.notnull(row_dict[j]):
                    brand_name_exist = True
                    xl_dict['brand_obj']['name'] = str(row_dict[j])
                    xl_dict['product_obj']['brand_name'] = str(row_dict[j])
                else:
                    if brand_name_exist == False:
                        error_dict['error'].append(f"Brand Name Should be present")
            
            elif pd.notnull(row_dict[j]) and fields_list[j] == 'brandlogo':
                xl_dict['brand_obj']['logo'] = str(row_dict[j])

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'vendorName':
                xl_dict['vendor_obj']['name'] = str(row_dict[j])


            elif fields_list[j] == 'productName':
                if pd.notnull(row_dict[j]):
                    xl_dict['product_obj']['product_name'] = str(row_dict[j]).replace('"',"")
                else:
                    error_dict['error'].append(f"Product Name Should be present") 

            elif fields_list[j] == 'long description':
                if pd.notnull(row_dict[j]):
                    xl_dict['product_obj']['long_description'] = str(row_dict[j])
                else:
                    error_dict['error'].append(f"Long Description Should be present")


            elif pd.notnull(row_dict[j]) and fields_list[j] == 'short description':
                try:
                    data_list = ast.literal_eval(row_dict[j])
                    result = ', '.join(data_list)
                    xl_dict['product_obj']['short_description'] = result
                except:
                    xl_dict['product_obj']['short_description'] = str(row_dict[j])
                # else:
                #     xl_dict['product_obj']['short_description'] = str(row_dict[j])
                
            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'features' or fields_list[j] in feature_list):
                try:
                    try:
                        xl_dict['product_obj']['features'].extend(ast.literal_eval(row_dict[j]))
                    except:
                        xl_dict['product_obj']['features'].append(row_dict[j])
                except:
                    xl_dict['product_obj']['features'] = str(row_dict[16]).split(",")

            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'images' or fields_list[j] in image_list):
                try:
                    try:
                        xl_dict['product_obj']['images'].extend(ast.literal_eval(row_dict[j]))
                    except:
                        xl_dict['product_obj']['images'].extend(str(row_dict[j]).split(","))
                except:
                    xl_dict['product_obj']['images'].append(row_dict[j])
            
            elif pd.notnull(row_dict[j]) and (fields_list[j] == 'attributes' or fields_list[j] in attribute_list):
                try:
                    if "{" in row_dict[j]:
                        try:
                            xl_dict['product_obj']['attributes'] = ast.literal_eval(row_dict[j])
                        except:
                            pass
                    else:
                        found_empty_key = False
                        for key in xl_dict['product_obj']['attributes']:
                            if xl_dict['product_obj']['attributes'][key] == "":
                                # Update the empty key with "attribute"
                                xl_dict['product_obj']['attributes'][key] = row_dict[j]
                                found_empty_key = True
                                break
                        
                        # If no empty key was found, create a new one
                        if not found_empty_key:
                            # new_key = f"attribute_{len(sample) + 1}"
                            xl_dict['product_obj']['attributes'][row_dict[j]] = ""
                except:
                    found_empty_key = False
                    for key in xl_dict['product_obj']['attributes']:
                        if xl_dict['product_obj']['attributes'][key] == "":
                            # Update the empty key with "attribute"
                            xl_dict['product_obj']['attributes'][key] = row_dict[j]
                            found_empty_key = True
                            break
                    
                    # If no empty key was found, create a new one
                    if not found_empty_key:
                        # new_key = f"attribute_{len(sample) + 1}"
                        xl_dict['product_obj']['attributes'][row_dict[j]] = ""
                    

            elif fields_list[j] == 'msrp' or fields_list[j] == "unit_price":
                if pd.notnull(row_dict[j]):
                    value = str(row_dict[j])
                    try:
                        numbers = re.findall(r"\d+\.\d+|\d+", value)
                        result = ''.join(numbers)
                        xl_dict['product_obj']['msrp'] = float(result)
                    except:
                        xl_dict['product_obj']['msrp'] = 0.0
                else:
                    error_dict['error'].append(f"MSRP Should be present")

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'was price':
                value = str(row_dict[j])
                try:
                    numbers = re.findall(r"\d+\.\d+|\d+", value)
                    result = ''.join(numbers)
                    xl_dict['product_obj']['was_price'] = float(result)
                except:
                    xl_dict['product_obj']['was_price'] = 0.0
                

            elif fields_list[j] == 'list price' or fields_list[j] == "online_price":
                if pd.notnull(row_dict[j]):
                    value = str(row_dict[j])
                    try:
                        numbers = re.findall(r"\d+\.\d+|\d+", value)
                        result = ''.join(numbers)
                        xl_dict['product_obj']['list_price'] = float(result)
                    except:
                        xl_dict['product_obj']['list_price'] = 0.0
                else:
                    error_dict['error'].append(f"List Price Should be present")

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'discount':
                try:
                    xl_dict['product_obj']['discount'] = float(row_dict[j].replace("%", ""))
                except:
                    xl_dict['product_obj']['discount'] = float(row_dict[j])

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'currency':
                xl_dict['product_obj']['currency'] = row_dict[j]

            elif fields_list[j] == 'quantity':
                if pd.notnull(row_dict[j]):
                    xl_dict['product_obj']['quantity'] = int(row_dict[j]) 
                else:
                    error_dict['error'].append(f"Quantity Should be present")

            elif fields_list[j] == 'availability':
                if pd.notnull(row_dict[j]):
                    if str(row_dict[j]).lower() == "out of stock":
                        xl_dict['product_obj']['availability'] = False
                    else:
                        xl_dict['product_obj']['availability'] = True
                else:
                    error_dict['error'].append(f"Availability Should be present")

            elif fields_list[j] == 'return applicable':
                if pd.notnull(row_dict[j]):
                    if str(row_dict[j]).lower() == "no":
                        xl_dict['product_obj']['return_applicable'] = False
                    else:
                        xl_dict['product_obj']['return_applicable'] = True
                else:
                    error_dict['error'].append(f"Return Applicable or not Should be present")
            
            elif pd.notnull(row_dict[j]) and fields_list[j] == 'tags':
                xl_dict['product_obj']['tags'] = str(row_dict[j]).split(",")
                
                

        if len(xl_dict['category_obj']) < 2:  
            error_dict['error'].append(f"At least a two-level of categorys should be present") 
        if len(xl_dict['product_obj']['images']) == 0:
            error_dict['error'].append(f"Images Link list Should be present")
        if len(xl_dict['product_obj']['attributes']) < 2:
            error_dict['error'].append(f"At least a two-level of Attributes should be present")

        if len(error_dict['error']) > 0:
            xl_contains_error_count += 1
        validation_error.append(error_dict)
        xl_data.append(xl_dict)
    
    data['validation_error'] = validation_error
    data['xl_contains_error'] = False
    if xl_contains_error_count == 0:
        data['status'] = True
        data['xl_data'] = xl_data
    else:
        data['xl_contains_error'] = True
    return data


def saveProductCategory(manufacture_unit_id,name,level,parent_id,industry_id_str):

    pipeline = [
    {"$match": {"name": name,
                "manufacture_unit_id_str" : manufacture_unit_id,
                "industry_id_str" :  industry_id_str}},
    {
        "$project": {
            "_id": 1
        }
        },
        {
            "$limit" : 1
        }
    
    ]
    product_category_obj = list(product_category.objects.aggregate(*pipeline))
    if product_category_obj != []:
        product_category_id = product_category_obj[0]['_id']
    if product_category_obj == []:
        product_category_obj = DatabaseModel.save_documents(
            product_category, {
                "name": name,
                "level": level,
                "manufacture_unit_id_str" : manufacture_unit_id,
                "industry_id_str" : industry_id_str
            }
        )
        product_category_id = product_category_obj.id
    if parent_id != None:
        DatabaseModel.update_documents(product_category.objects,{"id" : product_category_id},{"parent_category_id" : ObjectId(parent_id)})

        DatabaseModel.update_documents(product_category.objects,{"id" : parent_id},{"add_to_set__child_categories" : product_category_id})

    return product_category_id


@csrf_exempt
def save_file(request):
    data = dict()
    json_request = JSONParser().parse(request)
    manufacture_unit_id = json_request['manufacture_unit_id']
    industry_id_str = json_request['industry_id']
    xl_data = json_request['xl_data']
    duplicate_products = list()
    allow_duplicate = json_request.get('allow_duplicate')
    
    for i in xl_data:
        
        level1_obj = None
        level2_obj = None
        level3_obj = None
        level4_obj = None
        level5_obj = None
        level6_obj = None

        for key,value in i['category_obj'].items():
            if key == "level 1":
                level1_obj = saveProductCategory(manufacture_unit_id,value,1,None,industry_id_str)
            elif key == "level 2" and value != "nan":
                level2_obj = saveProductCategory(manufacture_unit_id,value,2,level1_obj,industry_id_str)
            elif key == "level 3" and value != "nan":
                level3_obj = saveProductCategory(manufacture_unit_id,value,3,level2_obj,industry_id_str)
            elif key == "level 4" and value != "nan":
                level4_obj = saveProductCategory(manufacture_unit_id,value,4,level3_obj,industry_id_str)
            elif key == "level 5" and value != "nan":
                level5_obj = saveProductCategory(manufacture_unit_id,value,5,level4_obj,industry_id_str)
            elif key == "level 6" and value != "nan":
                level6_obj = saveProductCategory(manufacture_unit_id,value,6,level5_obj,industry_id_str)

        if level6_obj != None:
            category_id = level6_obj
        elif level5_obj != None:
            category_id = level5_obj
        elif level4_obj != None:
            category_id = level4_obj
        elif level3_obj != None:
            category_id = level3_obj
        elif level2_obj != None:
            category_id = level2_obj
        elif level1_obj != None:
            category_id = level1_obj


        DatabaseModel.update_documents(product_category.objects,{"id" : category_id},{"end_level" : True})

        # Brand Mapping
        pipeline = [
        {"$match": {"name": i['brand_obj']['name'],
                    "manufacture_unit_id_str" : manufacture_unit_id,
                    "industry_id_str" : industry_id_str
                    }},  
        {
            "$project": {
                "_id": 1
            }
            },
            {
                "$limit" :1
            }
        
        ]
        brand_obj = list(brand.objects.aggregate(*pipeline))
        if brand_obj != []:
            brand_id = brand_obj[0]['_id']

        if brand_obj == []:
            brand_obj = DatabaseModel.save_documents(
                brand, {
                    "name": i['brand_obj']['name'],
                    "manufacture_unit_id_str" : manufacture_unit_id,
                    "industry_id_str" : industry_id_str
                }
            )
            brand_id = brand_obj.id

        # Vendor Mapping
        vendor_id = None
        if i['vendor_obj'].get('name'):
            pipeline = [
            {"$match": {"name": i['vendor_obj']['name'],
                        "manufacture_unit_id_str" : manufacture_unit_id}},  
            {
                "$project": {
                    "_id": 1
                }
                },
                {
                    "$limit" :1
                }
            
            ]
            vendor_obj = list(vendor.objects.aggregate(*pipeline))
            if vendor_obj != []:
                vendor_id = vendor_obj[0]['_id']

            if vendor_obj == []:
                vendor_obj = DatabaseModel.save_documents(
                    vendor, {
                        "name": i['vendor_obj']['name'],
                        "manufacture_unit_id_str" : manufacture_unit_id
                    }
                )
                vendor_id = vendor_obj.id

        # Product Mapping
        pipeline = [
            {"$match": {"product_name": i['product_obj']['product_name'],
                        "manufacture_unit_id" : ObjectId(manufacture_unit_id),
                        "industry_id_str" : industry_id_str
                        }},  
            {
            "$project": {
                "_id": 1
            }
            },
            {
                "$limit" :1
            }
            
            ]
        products_obj = list(product.objects.aggregate(*pipeline))
        if products_obj != []:
            products_id = products_obj[0]['_id']
        
        try:
            del i['product_obj']['quantity_price']
        except:
            pass
        if products_obj == []:
            
            i['product_obj']['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
            i['product_obj']['brand_id'] = brand_id
            if vendor_id != None:
                i['product_obj']['vendor_id'] = vendor_id 
            i['product_obj']['category_id'] = category_id
            i['product_obj']['industry_id_str'] = industry_id_str

            # Ensure no keys contain '.'
            def sanitize_keys(d):
                if isinstance(d, dict):
                    return {k.replace('.', '_'): sanitize_keys(v) for k, v in d.items()}
                elif isinstance(d, list):
                    return [sanitize_keys(i) for i in d]
                else:
                    return d

            i['product_obj'] = sanitize_keys(i['product_obj'])
            products_obj = DatabaseModel.save_documents(product, i['product_obj'])
        else:
            if allow_duplicate != None and allow_duplicate == True:
                i['product_obj']['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
                i['product_obj']['brand_id'] = brand_id
                if vendor_id != None:
                    i['product_obj']['vendor_id'] = vendor_id 
                i['product_obj']['category_id'] = category_id
                i['product_obj']['industry_id_str'] = industry_id_str
                DatabaseModel.update_documents(product.objects,{"id" : products_id},i['product_obj'])
            else:
                duplicate_products.append(i)
    
    data['status'] = True
    data['duplicate_products'] = duplicate_products
    data['industry_id'] = industry_id_str
    return data



@csrf_exempt
def productSearch(request):
    """
    Complete product search API with filters, sorting, pagination, and wishlist status.
    """
    # ------------------------------
    # Get request data
    # ------------------------------
    if request.method == "GET":
        search_query = request.GET.get("search_query", "").strip()
        manufacture_unit_id = request.GET.get("manufacture_unit_id")
        role_name = request.GET.get("role_name")
        sort_by = request.GET.get("sort_by")
        sort_by_value = request.GET.get("sort_by_value")
        skip = int(request.GET.get("skip", 0))
        limit = int(request.GET.get("limit", 10))
        product_category_id = request.GET.get("product_category_id")
        brand_id = request.GET.get("brand_id")
        price_from = request.GET.get("price_from")
        price_to = request.GET.get("price_to")
    else:
        json_request = JSONParser().parse(request)
        search_query = re.escape(json_request.get("search_query", "").strip())
        manufacture_unit_id = json_request.get("manufacture_unit_id")
        role_name = json_request.get("role_name")
        sort_by = json_request.get("sort_by")
        sort_by_value = json_request.get("sort_by_value")
        skip = int(json_request.get("skip", 0))
        limit = int(json_request.get("limit", 10))
        product_category_id = json_request.get("product_category_id")
        brand_id = json_request.get("brand_id")
        price_from = json_request.get("price_from")
        price_to = json_request.get("price_to")

    regex_query = ".*" if not search_query else f".*{search_query}.*"

    # ------------------------------
    # Build base conditions
    # ------------------------------
    base_conditions = []

    # role-based visibility
    if role_name == "buyer":
        base_conditions.append({"visible": True})
    elif role_name == "seller" and manufacture_unit_id:
        try:
            base_conditions.append({"manufacture_unit_id": ObjectId(manufacture_unit_id)})
        except:
            pass

    # brand filter
    if brand_id:
        try:
            base_conditions.append({"brand_id": ObjectId(brand_id)})
        except:
            return JsonResponse({"data": [], "message": "Invalid brand_id", "status": False, "token": None})

    # category filter (including children)
    if product_category_id:
        try:
            category_obj_id = ObjectId(product_category_id)
            category_doc = product_category.objects(id=category_obj_id).first()
            if not category_doc:
                return JsonResponse({"data": [], "message": "Invalid product_category_id", "status": False, "token": None})
            
            category_ids = [category_obj_id]
            children = getattr(category_doc, "child_categories", []) or []
            for c in children:
                try:
                    category_ids.append(ObjectId(c))
                except:
                    continue
            base_conditions.append({"category_id": {"$in": category_ids}})
        except Exception as e:
            return JsonResponse({"data": [], "message": f"Invalid category_id: {str(e)}", "status": False, "token": None})

    # price filter
    if price_from and price_to:
        base_conditions.append({"list_price": {"$gte": int(price_from), "$lte": int(price_to)}})
    elif price_from:
        base_conditions.append({"list_price": {"$gte": int(price_from)}})
    elif price_to:
        base_conditions.append({"list_price": {"$lte": int(price_to)}})

    # search query filter
    if search_query:
        base_conditions.append({
            "$or": [
                {"brand_name": {"$regex": regex_query, "$options": "i"}},
                {"product_name": {"$regex": regex_query, "$options": "i"}},
                {"sku_number_product_code_item_number": {"$regex": regex_query, "$options": "i"}},
                {"mpn": {"$regex": regex_query, "$options": "i"}},
                {"model": {"$regex": regex_query, "$options": "i"}},
                {"long_description": {"$regex": regex_query, "$options": "i"}},
                {"short_description": {"$regex": regex_query, "$options": "i"}},
                {"features": {"$regex": regex_query, "$options": "i"}},
                {"tags": {"$regex": regex_query, "$options": "i"}},
            ]
        })

    if not base_conditions:
        base_conditions = [{}]  # no filters, return all

    # ------------------------------
    # Build aggregation pipeline
    # ------------------------------
    pipeline = [
        {"$match": {"$and": base_conditions}},
        # Category details
        {
            "$lookup": {
                "from": "product_category",
                "localField": "category_id",
                "foreignField": "_id",
                "as": "category_info"
            }
        },
        {"$unwind": {"path": "$category_info", "preserveNullAndEmptyArrays": True}},
        # Brand details
        {
            "$lookup": {
                "from": "brand",
                "localField": "brand_id",
                "foreignField": "_id",
                "as": "brand_info"
            }
        },
        {"$unwind": {"path": "$brand_info", "preserveNullAndEmptyArrays": True}},
        # Wishlist details
        {
            "$lookup": {
                "from": "wishlist",
                "localField": "_id",
                "foreignField": "product_id",
                "as": "wishlist_info"
            }
        },
        {"$unwind": {"path": "$wishlist_info", "preserveNullAndEmptyArrays": True}},
        # Project all required fields
        {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$_id"},
                "product_name": 1,
                "sku_number_product_code_item_number": 1,
                "mpn": 1,
                "price": "$list_price",
                "was_price": 1,
                "msrp": 1,
                "discount": 1,
                "currency": 1,
                "quantity": 1,
                "availability": 1,
                "long_description": 1,
                "short_description": 1,
                "features": 1,
                "tags": 1,
                "model": 1,
                "brand_name": "$brand_info.name",
                "brand_logo": "$brand_info.logo",
                "category_id": {"$ifNull": [{"$toString": "$category_id"}, ""]},
                "category_name": {"$ifNull": ["$category_info.name", ""]},
                "logo": {"$ifNull": [{"$first": "$images"}, ""]},
                "is_wishlist": {"$cond": [{"$gt": [{"$type": "$wishlist_info"}, "missing"]}, True, False]},
                "wishlist_id": {"$cond": [{"$gt": [{"$type": "$wishlist_info"}, "missing"]}, {"$toString": "$wishlist_info._id"}, None]}
            }
        }
    ]

    # Sorting
    if sort_by:
        pipeline.append({"$sort": {sort_by: int(sort_by_value)}})
    else:
        pipeline.append({"$sort": {"_id": -1}})

    # Pagination
    if skip:
        pipeline.append({"$skip": max(skip - 1, 0)})
    if limit:
        pipeline.append({"$limit": limit})

    results = list(product.objects.aggregate(pipeline))
    return JsonResponse({"data": results, "message": "success", "status": True, "token": None})



@csrf_exempt
def productSuggestions(request):
    """
    Autocomplete suggestions with full product details.
    Typing 'a' → returns top products starting with 'a' along with key details.
    """
    if request.method == "GET":
        search_query = request.GET.get("search_query", "").strip()
        manufacture_unit_id = request.GET.get("manufacture_unit_id")
        role_name = request.GET.get("role_name")
        limit = int(request.GET.get("limit", 10))  # default: 10 suggestions
    else:
        json_request = JSONParser().parse(request)
        search_query = json_request.get("search_query", "").strip()
        manufacture_unit_id = json_request.get("manufacture_unit_id")
        role_name = json_request.get("role_name")
        limit = int(json_request.get("limit", 10))

    if not search_query:
        return JsonResponse({"data": [], "message": "empty query", "status": True, "token": None})

    regex_query = f"^{search_query}.*"

    match_conditions = {}
    if role_name == "buyer":
        match_conditions["visible"] = True
    if role_name == "seller" and manufacture_unit_id:
        try:
            match_conditions["manufacture_unit_id"] = ObjectId(manufacture_unit_id)
        except Exception:
            pass

    pipeline = [
        {"$match": match_conditions},
        {"$match": {
            "$or": [
                {"product_name": {"$regex": regex_query, "$options": "i"}},
                {"brand_name": {"$regex": regex_query, "$options": "i"}},
                {"sku_number_product_code_item_number": {"$regex": regex_query, "$options": "i"}},
                {"mpn": {"$regex": regex_query, "$options": "i"}}
            ]
        }},
        {"$project": {
            "_id": 0,
            "id": {"$toString": "$_id"},
            "product_name": 1,
            "brand_name": 1,
            "logo": {"$ifNull": [{"$first": "$images"}, ""]},
            "mpn": 1,
            "sku_number_product_code_item_number": 1,
            "category_name": 1,
            "price": 1,
            "was_price": 1,
            "discount": 1,
            "availability": 1,
            "currency": 1,
            "msrp": 1
        }},
        {"$sort": {"product_name": 1}},
        {"$limit": limit}
    ]

    suggestions = list(product.objects.aggregate(pipeline))
    return JsonResponse({"data": suggestions, "message": "success", "status": True, "token": None})



def getProductsByTopLevelCategory(request):
    product_category_id = request.GET.get('product_category_id')
    # limit = int(request.GET.get('limit', 100))  # Default to 100, configurable
    # skip = int(request.GET.get('skip', 0))      # Default to 0 for pagination

    pipeline = [
        {
            "$match": {
                "_id": ObjectId(product_category_id)
            }
        },
        {
            "$graphLookup": {
                "from": "product_category",
                "startWith": "$_id",
                "connectFromField": "_id",
                "connectToField": "parent_category_id",
                "as": "all_categories",
                "maxDepth": 5
            }
        },
        {
            "$project": {
                "category_ids": {
                    "$map": {
                        "input": "$all_categories",
                        "as": "category",
                        "in": "$$category._id"
                    }
                }
            }
        },
        {"$unwind": "$category_ids"},
        {
            "$lookup": {
                "from": "product",
                "localField": "category_ids",
                "foreignField": "category_id",
                "as": "product_ins"
            }
        },
        {"$unwind": "$product_ins"},
        {
            "$lookup": {
                "from": "product_category",
                "localField": "product_ins.category_id",
                "foreignField": "_id",
                "as": "product_category_ins"
            }
        },
        {"$unwind": "$product_category_ins"},
        {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$product_ins._id"},
                "name": "$product_ins.product_name",
                "logo": {"$first": "$product_ins.images"},
                "sku_number": "$product_ins.sku_number_product_code_item_number",
                "mpn": "$product_ins.mpn",
                "msrp": "$product_ins.msrp",
                "was_price": "$product_ins.was_price",
                "brand_name": "$product_ins.brand_name",
                "visible": "$product_ins.visible",
                "end_level_category": "$product_category_ins.name",
                "price": "$product_ins.list_price",
                "currency": "$product_ins.currency",
                "availability": "$product_ins.availability"
            }
        },
        # {"$skip": skip},
        # {"$limit": limit}
    ]

    # Execute the pipeline with an index check and efficient memory management
    results = list(product_category.objects.aggregate(pipeline))
    return results





@csrf_exempt
def updateProduct(request):
    data = dict()
    data['is_updated'] = False
    json_request = JSONParser().parse(request)
    product_id = json_request['id']
    product_obj = DatabaseModel.get_document(product.objects,{"id" : product_id},['id'])
    if product_obj != None:
        del json_request['id']
        data['is_updated'] = DatabaseModel.update_documents(product.objects,{"id" : product_id},json_request)
    return data

@csrf_exempt
def updateBulkProduct(request):
    data = dict()
    data['is_updated'] = False
    json_request = JSONParser().parse(request)
    product_list = json_request['product_list']
    discount_percentage = json_request.get('discount_percentage')
    discount_price = json_request.get('discount_price')
    for i in product_list:
        product_obj = {}
        if 'list_price' in i:
            product_obj['list_price'] = i['list_price']
            if discount_percentage != None and discount_percentage != "":
                percentage = abs(discount_percentage)
                product_obj['discount'] = percentage
                product_obj['list_price'] = round(i['list_price'] + (i['list_price'] * (-percentage / 100)),2)
                product_obj['was_price'] = i['list_price']
            elif discount_price != None and discount_price != "":
                price = abs(discount_price)
                product_obj['discount'] = round((price / i['list_price']) * 100,2)
                if i['list_price'] < discount_price:
                    list_price = 0.0
                else:
                    list_price = i['list_price'] + (-discount_price)
                product_obj['list_price'] = round(list_price,2)
                product_obj['was_price'] = i['list_price']
        if 'visible' in i:
            product_obj['visible'] = i['visible']
        if 'msrp' in i:
            product_obj['msrp'] = i['msrp']
        if 'was_price' in i:
            product_obj['was_price'] = i['was_price']
            if (discount_percentage != None and discount_percentage != "") or (discount_price != None and discount_price != ""):
                product_obj['was_price'] = i['list_price']
        DatabaseModel.update_documents(product.objects,{"id" : i['id']},product_obj)
        data['is_updated'] = True
    return data



@csrf_exempt
def getColumnFormExcel(request):
    data = dict()
    data['status'] = False
    if 'file' not in request.FILES:
        data['error'] = "No file uploaded."
        return data

    file = request.FILES['file']
    try:
        if file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
        elif file.name.endswith('.csv') or file.name.endswith('.txt'):
            df = pd.read_csv(file)
        else:
            data['error'] = "Unsupported file format."
            return data
    except Exception as e:
        data['error'] = f"Error reading file: {str(e)}"
        return data
    data['status'] = True
    k=df.columns
    data['user_columns'] = k
    data['general_columns'] = ['sku_number_product_code_item_number','model','mpn','upc_ean','breadcrumb','brand_name','product_name','long_description','short_description','features','images','attributes','tags','msrp','currency','was_price','list_price','discount','quantity_price','quantity','availability','return_applicable']
    return data


@csrf_exempt
def productCompare(request):
    json_request = JSONParser().parse(request)
    product_list = json_request['product_list']
    if product_list != []:
        product_list = [ObjectId(ins) for ins in product_list]
    pipeline =[
        {
            "$match" : {
                "_id" : {"$in" : product_list},
            }
        },
         {
            "$lookup": {
                "from": "brand",
                "localField": "brand_id",
                "foreignField": "_id",
                "as": "brand_ins"
            }
        },
        {
        "$unwind": {
            "path": "$brand_ins", 
            "preserveNullAndEmptyArrays": True
        }
        },
        {
           "$project" :{
            "_id":0,
            "id" : {"$toString" : "$_id"},
            "product_name" : 1,
            "sku_number_product_code_item_number" : 1,
            "model" : 1,
            "mpn" : 1,
            "upc_ean" : 1,
            "logo" : {"$ifNull" : [{"$first":"$images"},"http://example.com/"]},
            "long_description" : 1,
            "short_description" : 1,
            "list_price" : 1,
            "msrp" : {"$ifNull" : ["$msrp",0.0]},
            "was_price" : {"$ifNull" : ["$was_price",0.0]},
            "discount": { 
            "$concat": [
                { "$toString": { "$round": ["$discount", 2] } }, 
                "%" 
            ] 
            },
            "brand_name" : 1,
            "brand_logo" : {"$ifNull" : ["$brand_ins.logo",""]},
            "currency" : 1,
            "quantity" : 1,
            "availability" : 1,
            "images" : 1,
            "attributes" : 1,
            "features" : 1,
            "from_the_manufacture" : 1,
            "visible" : 1
           }
        }
    ]
    product_list = list(product.objects.aggregate(*(pipeline)))
    return product_list



def get_related_products(request):
    # Get the product_id and manufacture_unit_id from the request
    product_id = request.GET.get('product_id')
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    product_object_id = ObjectId(product_id)

    # Fetch the current product's details from the database
    current_product = DatabaseModel.get_document(
        product.objects,
        {"id": product_object_id},  # Using '_id' for MongoDB queries
        ['brand_id', 'category_id', 'list_price']
    )

    # Extract plain values for use in the pipeline
    current_brand_id = str(current_product.brand_id.id) if current_product.brand_id else None
    current_category_id = str(current_product.category_id.id) if current_product.category_id else None
    current_price = current_product.list_price if current_product.list_price else 0

    # MongoDB aggregation pipeline
    pipeline = [
        {
            "$match": {
                "_id": {"$ne": product_object_id},  # Exclude the current product
                "visible": True,                    # Only include visible products
                "availability": True,               # Only include available products
                "manufacture_unit_id": ObjectId(manufacture_unit_id),  # Ensure proper ID usage
                "brand_id": ObjectId(current_brand_id),   # Same brand
                "category_id": ObjectId(current_category_id),  # Same category
                # "list_price": {"$gte": current_price * 0.8, "$lte": current_price * 1.2}  # Price range (±20%)
            }
        },
        {
            "$sample": {"size": 10}  # Randomly select 10 products
        },
        {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$_id"},
                "name": "$product_name",
                "logo": {"$ifNull": [{"$first": "$images"}, "http://example.com/"]},
                "sku_number": "$sku_number_product_code_item_number",
                "mpn": 1,
                "msrp": {"$round": ["$msrp", 2]},
                "was_price": {"$round": ["$was_price", 2]},
                "brand_name": 1,
                "visible": 1,
                "end_level_category": "$product_category_ins.name",
                "brand_logo": {"$ifNull": ["$brand_ins.logo", ""]},
                "price": {"$round": ["$list_price", 2]},
                "currency": 1,
                "availability": 1,
                "discount": 1,
                "quantity": 1,
                "upc_ean": 1,
            }
        }
    ]

    # Execute the pipeline and return the result
    related_products = list(product.objects.aggregate(*pipeline))    
    # You can format the response as needed, for example, using Django's JsonResponse
    return related_products


def get_highest_priced_product(request):
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    role_name = request.GET.get('role_name')
    if role_name in ["dealer_admin","dealer_user"]:
        match = {
            "$match": {
                "manufacture_unit_id": ObjectId(manufacture_unit_id),
                "visible": True,
                "availability": True
            }
        }
    else:
        match = {
            "$match": {
                "manufacture_unit_id": ObjectId(manufacture_unit_id)
            }
        }

        
    pipeline = [
        match,
        {
            "$sort": {
                "list_price": -1
            }
        },
        {
            "$limit": 1
        },
        {
            "$project": {
                "_id": 0,
                "price": {"$round": ["$list_price", 2]},
                "currency": 1,
            }
        }
    ]

    highest_priced_product = list(product.objects.aggregate(pipeline))
    return highest_priced_product[0] if highest_priced_product else {}



@csrf_exempt
def upload_file_new(request):
    data = dict()
    data['status'] = False

    if 'file' not in request.FILES:
        data['error'] = "No file uploaded."
        return data

    file = request.FILES['file']
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    industry_id_str = request.GET.get('industry_id_str')

    try:
        if file.name.endswith('.xlsx'):
            df = pd.read_excel(file, header=0)
        elif file.name.endswith('.csv') or file.name.endswith('.txt'):
            df = pd.read_csv(file)
        else:
            data['error'] = "Unsupported file format."
            return data
    except Exception as e:
        data['error'] = f"Error reading file: {str(e)}"
        return data

    # Extract headers from the file
    original_headers = df.columns.tolist()

    # Initialize field lists as per your previous code
    general_fields = ['sku_number_product_code_item_number', 'model', 'mpn', 'upc_ean',
                      'level1 category', 'level2 category', 'level3 category',
                      'level4 category', 'level5 category', 'level6 category',
                      'breadcrumb', 'brand_name',"brandlogo", "vendorName",
                      'product_name', 'long_description', 'short_description',
                      'tags', 'msrp', 'currency', 'was_price', 'list_price', 'discount',
                      'quantity', 'availability', 'return_applicable']

    # Now, normalize the headers as per your original code logic
    fields_list = []
    for ins in original_headers:
        new_ins = ins.lower()
        if not new_ins.startswith(("att", "ima", "fea")):
            change = False
            normalized_field = ins.replace(" ", "").lower()
            pattern = re.sub(r'\s+', r'\\s+', re.escape(normalized_field.lower()))
            regex = re.compile(pattern)
            for field in general_fields:
                field1 = field.replace(" ", "").lower()
                if regex.search(field1.lower()):
                    if "level1 category" in fields_list and field == "level1 category":
                        fields_list.append("level2 category")
                    else:
                        fields_list.append(field)
                    change = True
                    break

            if not change:
                fields_list.append(ins)

    data['extract_list'] = fields_list  # Original headers for mapping

    # Retrieve existing field mapping from the database
    xl_mapping_obj = DatabaseModel.get_document(
        unit_wise_field_mapping.objects,
        {"manufacture_unit_id": manufacture_unit_id}
    )

    data['Database_list'] = []  # Existing field mappings
    if xl_mapping_obj:
        data['Database_list'] = xl_mapping_obj.attributes

    # List of your database fields (excluding 'images', 'features', 'attributes')
    data['Database_options'] = general_fields  # Excluding 'images', 'features', 'attributes'

    # Save the file and get the file path
    fs = FileSystemStorage()
    file_path = fs.save(file.name, file)
    file_path = os.path.join(settings.MEDIA_ROOT, file_path)
    data['file_path'] = file_path
    data['industry_id_str'] = industry_id_str

    data['status'] = True
    return data



def saveProductCategory(manufacture_unit_id, name, level, parent_id, industry_id_str):
    pipeline = [
        {"$match": {"name": name,
                    "manufacture_unit_id_str": manufacture_unit_id,
                    "industry_id_str": industry_id_str}},
        {
            "$project": {
                "_id": 1
            }
        },
        {
            "$limit": 1
        }
    ]
    product_category_obj = list(product_category.objects.aggregate(*pipeline))
    if product_category_obj:
        product_category_id = product_category_obj[0]['_id']
    else:
        product_category_obj = DatabaseModel.save_documents(
            product_category, {
                "name": name,
                "level": level,
                "manufacture_unit_id_str": manufacture_unit_id,
                "industry_id_str": industry_id_str
            }
        )
        product_category_id = product_category_obj.id
    if parent_id:
        DatabaseModel.update_documents(
            product_category.objects,
            {"id": product_category_id},
            {"parent_category_id": ObjectId(parent_id)}
        )
        DatabaseModel.update_documents(
            product_category.objects,
            {"id": parent_id},
            {"add_to_set__child_categories": product_category_id}
        )
    return product_category_id



@csrf_exempt
def save_xl_data_new(request):
    data = dict()
    data['status'] = False

    # Parse the JSON request
    json_request = JSONParser().parse(request)
    manufacture_unit_id = json_request.get('manufacture_unit_id')
    field_data = json_request.get('field_data')  # This is the field mapping
    file_path = json_request.get('file_path')
    allow_duplicate = json_request.get('allow_duplicate', False)
    industry_id_str = json_request.get('industry_id_str')
    field_data = json.loads(field_data)
    if not all([manufacture_unit_id, field_data, file_path]):
        data['error'] = "Required parameters are missing."
        return data

    # Save or update the field mapping in the database
    xl_mapping_obj = DatabaseModel.get_document(
        unit_wise_field_mapping.objects,
        {'manufacture_unit_id': ObjectId(manufacture_unit_id)}
    )
    if xl_mapping_obj:
        DatabaseModel.update_documents(
            unit_wise_field_mapping.objects,
            {'manufacture_unit_id': ObjectId(manufacture_unit_id)},
            {'attributes': field_data}
        )
    else:
        DatabaseModel.save_documents(
            unit_wise_field_mapping,
            {'attributes': field_data, 'manufacture_unit_id': ObjectId(manufacture_unit_id)}
        )

    # Read the Excel file
    try:
        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path, header=0)
        elif file_path.endswith('.csv') or file_path.endswith('.txt'):
            df = pd.read_csv(file_path)
        else:
            data['error'] = "Unsupported file format."
            return data
    except Exception as e:
        data['error'] = f"Error reading file: {str(e)}"
        return data

    # Initialize variables for error tracking
    validation_error = []
    xl_data = []
    xl_contains_error_count = 0

    # Process each row in the DataFrame
    for index, row in df.iterrows():
        row_dict = row.to_dict()
        error_dict = dict()
        xl_dict = dict()
        error_dict['row'] = index + 1
        error_dict['error'] = []
        xl_dict['product_obj'] = dict()
        xl_dict['product_obj']['features'] = []
        xl_dict['product_obj']['images'] = []
        xl_dict['product_obj']['attributes'] = {}
        xl_dict['category_obj'] = {}
        xl_dict['vendor_obj'] = {}
        xl_dict['brand_obj'] = {}
        brand_name_exist = False

        # Process general fields using field_data mapping
        for db_field, excel_field in field_data.items():
            value = row_dict.get(excel_field)
            # Handle missing or NaN values
            if isinstance(value, float) and math.isnan(value):
                value = None
            # Process general fields based on db_field
            if db_field == 'sku_number_product_code_item_number':
                if value:
                    xl_dict['product_obj']['sku_number_product_code_item_number'] = str(value)
                else:
                    error_dict['error'].append("SKU number/Product Code/Item number should be present")

            elif db_field == 'model':
                if value:
                    xl_dict['product_obj']['model'] = str(value)

            elif db_field == 'mpn':
                if value:
                    xl_dict['product_obj']['mpn'] = str(value)
                else:
                    error_dict['error'].append("MPN should be present")

            elif db_field == 'upc_ean':
                if value:
                    xl_dict['product_obj']['upc_ean'] = str(value)

            
            elif 'category' in db_field:
                if value:
                    xl_dict['category_obj'][db_field] = str(value)

            elif db_field == 'breadcrumb':
                if value:
                    if isinstance(value, str) and "[" in value:
                        try:
                            data_list = ast.literal_eval(value)
                            result = ' > '.join(data_list)
                            xl_dict['product_obj']['breadcrumb'] = result
                        except:
                            xl_dict['product_obj']['breadcrumb'] = str(value)
                    else:
                        xl_dict['product_obj']['breadcrumb'] = str(value)

            elif db_field == 'brand_name':
                if value:
                    brand_name_exist = True
                    xl_dict['brand_obj']['name'] = str(value)
                    xl_dict['product_obj']['brand_name'] = str(value)
                else:
                    if not brand_name_exist:
                        error_dict['error'].append("Brand Name should be present")

            elif db_field == 'brandlogo':
                if value:
                    xl_dict['brand_obj']['logo'] = str(value)

            elif db_field == 'vendorName':
                if value:
                    xl_dict['vendor_obj']['name'] = str(value)

            elif db_field == 'product_name':
                if value:
                    xl_dict['product_obj']['product_name'] = str(value).replace('"', "")
                else:
                    error_dict['error'].append("Product Name should be present")

            elif db_field == 'long_description':
                if value:
                    xl_dict['product_obj']['long_description'] = str(value)
                else:
                    error_dict['error'].append("Long Description should be present")

            elif db_field == 'short_description':
                if value:
                    xl_dict['product_obj']['short_description'] = str(value)

            elif db_field == 'tags':
                if value:
                    xl_dict['product_obj']['tags'] = str(value).split(",")

            elif db_field == 'msrp':
                if value:
                    try:
                        numbers = re.findall(r"\d+\.\d+|\d+", str(value))
                        result = ''.join(numbers)
                        xl_dict['product_obj']['msrp'] = float(result)
                    except:
                        xl_dict['product_obj']['msrp'] = 0.0
                else:
                    error_dict['error'].append("MSRP should be present")

            elif db_field == 'currency':
                if value:
                    xl_dict['product_obj']['currency'] = str(value)

            elif db_field == 'was_price':
                if value:
                    try:
                        numbers = re.findall(r"\d+\.\d+|\d+", str(value))
                        result = ''.join(numbers)
                        xl_dict['product_obj']['was_price'] = float(result)
                    except:
                        xl_dict['product_obj']['was_price'] = 0.0

            elif db_field == 'list_price':
                if value:
                    try:
                        numbers = re.findall(r"\d+\.\d+|\d+", str(value))
                        result = ''.join(numbers)
                        xl_dict['product_obj']['list_price'] = float(result)
                    except:
                        xl_dict['product_obj']['list_price'] = 0.0
                else:
                    error_dict['error'].append("List Price should be present")

            elif db_field == 'discount':
                if value:
                    try:
                        xl_dict['product_obj']['discount'] = float(str(value).replace("%", ""))
                    except:
                        xl_dict['product_obj']['discount'] = float(value)

            elif db_field == 'quantity':
                if value:
                    xl_dict['product_obj']['quantity'] = int(value)
                else:
                    error_dict['error'].append("Quantity should be present")

            elif db_field == 'availability':
                if value:
                    xl_dict['product_obj']['availability'] = str(value).lower() != "out of stock"
                else:
                    error_dict['error'].append("Availability should be present")

            elif db_field == 'return_applicable':
                if value:
                    xl_dict['product_obj']['return_applicable'] = str(value).lower() != "no"
                else:
                    error_dict['error'].append("Return Applicable should be present")

            # For other fields, add as needed

        # Handle features
        feature_fields = [field for field in df.columns if field.lower().startswith(("feature"))]
        for feature_field in feature_fields:
            value = row_dict.get(feature_field)
            if value and not (isinstance(value, float) and math.isnan(value)):
                xl_dict['product_obj']['features'].append(str(value))

        # Handle images
        image_fields = [field for field in df.columns if field.lower().startswith(("image"))]
        for image_field in image_fields:
            value = row_dict.get(image_field)
            if value and not (isinstance(value, float) and math.isnan(value)):
                xl_dict['product_obj']['images'].append(str(value))

        # Handle attributes (pairs of attribute names and values)
        attribute_fields = [field for field in df.columns if field.lower().startswith(("attr"))]
        for attr_field in attribute_fields:
            value = row_dict.get(attr_field)
            if pd.notnull(value) and (attr_field == 'attributes' or attr_field in attribute_fields):
                try:
                    if "{" in str(value):
                        try:
                            xl_dict['product_obj']['attributes'] = ast.literal_eval(value)
                        except:
                            pass
                    else:
                        found_empty_key = False
                        for key in xl_dict['product_obj']['attributes']:
                            if xl_dict['product_obj']['attributes'][key] == "":
                                xl_dict['product_obj']['attributes'][key] = value
                                found_empty_key = True
                                break
                        # If no empty key was found, create a new one
                        if not found_empty_key:
                            xl_dict['product_obj']['attributes'][str(value)] = ""
                except:
                    found_empty_key = False
                    for key in xl_dict['product_obj']['attributes']:
                        if xl_dict['product_obj']['attributes'][key] == "":
                            xl_dict['product_obj']['attributes'][key] = value
                            found_empty_key = True
                            break
                    # If no empty key was found, create a new one
                    if not found_empty_key:
                        xl_dict['product_obj']['attributes'][str(value)] = ""
        
        # Additional validation
        if len(xl_dict['category_obj']) < 2:
            error_dict['error'].append("At least two levels of categories should be present")
        if len(xl_dict['product_obj']['images']) == 0:
            error_dict['error'].append("At least one image should be present")
        if len(xl_dict['product_obj']['attributes']) < 2:
            error_dict['error'].append("At least two attributes should be present")

        # If errors exist, increment error count and add to validation_error list
        if len(error_dict['error']) > 0:
            xl_contains_error_count += 1
            validation_error.append(error_dict)
        else:
            xl_data.append(xl_dict)

    data['validation_error'] = validation_error
    data['xl_contains_error'] = False
    if xl_contains_error_count == 0:
        data['status'] = True
        # data['xl_data'] = xl_data

        # Proceed to save data to the database
        save_valid_data(xl_data, manufacture_unit_id, industry_id_str, allow_duplicate)
    else:
        data['xl_contains_error'] = True

    # Clean up the uploaded file
    if os.path.exists(file_path):
        os.remove(file_path)

    return JsonResponse(data)

def save_valid_data(xl_data, manufacture_unit_id, industry_id_str, allow_duplicate=False):
    duplicate_products = []
    
    for i in xl_data:
        # Process categories
        category_obj_dict = i['category_obj']
        previous_category_id = None
        for level_num in range(1, 7):
            level_key = f'level{level_num} category'
            category_name = category_obj_dict.get(level_key)
            if category_name:
                category_id = saveProductCategory(
                    manufacture_unit_id, category_name, level_num, previous_category_id, industry_id_str
                )
                previous_category_id = category_id

        if previous_category_id:
            DatabaseModel.update_documents(
                product_category.objects,
                {"id": previous_category_id},
                {"end_level": True}
            )
            category_id = previous_category_id
        else:
            category_id = None

        # Brand Mapping
        brand_obj = i['brand_obj']
        if brand_obj.get('name'):
            pipeline = [
                {"$match": {"name": brand_obj['name'],
                            "manufacture_unit_id_str": manufacture_unit_id,
                            "industry_id_str": industry_id_str}},
                {"$project": {"_id": 1}},
                {"$limit": 1}
            ]
            brand_db_obj = list(brand.objects.aggregate(*pipeline))
            if brand_db_obj:
                brand_id = brand_db_obj[0]['_id']
            else:
                brand_db_obj = DatabaseModel.save_documents(
                    brand, {
                        "name": brand_obj['name'],
                        "manufacture_unit_id_str": manufacture_unit_id,
                        "industry_id_str": industry_id_str
                    }
                )
                brand_id = brand_db_obj.id
            i['product_obj']['brand_id'] = brand_id
        else:
            brand_id = None

        # Vendor Mapping
        vendor_id = None
        vendor_obj = i['vendor_obj']
        if vendor_obj.get('name'):
            pipeline = [
                {"$match": {"name": vendor_obj['name'],
                            "manufacture_unit_id_str": manufacture_unit_id}},
                {"$project": {"_id": 1}},
                {"$limit": 1}
            ]
            vendor_db_obj = list(vendor.objects.aggregate(*pipeline))
            if vendor_db_obj:
                vendor_id = vendor_db_obj[0]['_id']
            else:
                vendor_db_obj = DatabaseModel.save_documents(
                    vendor, {
                        "name": vendor_obj['name'],
                        "manufacture_unit_id_str": manufacture_unit_id
                    }
                )
                vendor_id = vendor_db_obj.id
            i['product_obj']['vendor_id'] = vendor_id

        # Product Mapping
        product_obj = i['product_obj']
        pipeline = [
            {"$match": {"product_name": product_obj['product_name'],
                        "manufacture_unit_id": ObjectId(manufacture_unit_id),
                        "industry_id_str": industry_id_str}},
            {"$project": {"_id": 1}},
            {"$limit": 1}
        ]
        products_db_obj = list(product.objects.aggregate(*pipeline))

        # Prepare product object for saving
        product_obj['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
        product_obj['industry_id_str'] = industry_id_str
        if brand_id:
            product_obj['brand_id'] = brand_id
        if vendor_id:
            product_obj['vendor_id'] = vendor_id
        if category_id:
            product_obj['category_id'] = category_id

        # Sanitize keys to avoid dots in MongoDB field names
        def sanitize_keys(d):
            if isinstance(d, dict):
                return {k.replace('.', '_'): sanitize_keys(v) for k, v in d.items()}
            elif isinstance(d, list):
                return [sanitize_keys(item) for item in d]
            else:
                return d

        product_obj = sanitize_keys(product_obj)

        if not products_db_obj:
            # Save new product
            DatabaseModel.save_documents(product, product_obj)
        else:
            if allow_duplicate:
                products_id = products_db_obj[0]['_id']
                DatabaseModel.update_documents(
                    product.objects,
                    {"id": products_id},
                    product_obj
                )
            else:
                # Collect duplicate products
                duplicate_products.append(i)

    # Handle duplicates as needed
    if duplicate_products:
        # Implement logic to handle duplicates, e.g., log or notify
        pass



# def add_random_images_to_products():
#     image_urls = [
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_5_7d29b467-6fb0-4093-8718-06f2e9ccce5b.jpg?v=1739466536",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_11_bb991858-803d-4a58-b843-591f83fd23ba.jpg?v=1739513304",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_11_cbe38830-30d4-453b-98e1-129b0d8cc988.jpg?v=1739513217",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_5.jpg?v=1739441078",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_7_31f94fa0-c162-4775-9344-1ae7279afd3a.jpg?v=1739512966",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_4.jpg?v=1739440883",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_4.jpg?v=1739441016",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_13_4da36010-fd46-4c83-a76f-98a75ca2c0ad.jpg?v=1739466554",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_20.jpg?v=1739512798",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_8.jpg?v=1739512746",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_7_991c3145-66b3-4cae-993b-96b054bb165c.jpg?v=1739466454",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_9_a426922f-f7c3-4397-b856-af5bf4567735.jpg?v=1739512891",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_20_f57116a9-6659-4552-b6d8-7955b5097d60.jpg?v=1739512910",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_14.jpg?v=1739466415",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_8_8846a1dc-bd93-4109-b1a7-d598977a1ef3.jpg?v=1739466364",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_10_514340bf-a465-4b95-8fba-a7db38fb1ac4.jpg?v=1739466492",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_19_01e71f56-8bd7-413c-92cd-fe070017d847.jpg?v=1739512726",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_18_03829427-a996-4eb4-94e8-975208971484.jpg?v=1739512759",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_9_e3c6a375-c328-4648-aedd-29d4cafe3874.jpg?v=1739513177",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_15.jpg?v=1739512711",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_5_302b921b-9071-413e-9925-4ed62b9f89cf.jpg?v=1739466435",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_6_17f27aaa-8374-4367-91e5-5d0d228eae01.jpg?v=1739466511",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_6.jpg?v=1739441047",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_12.jpg?v=1739466383",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_7.jpg?v=1739513080",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_9.jpg?v=1739466333",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_17.jpg?v=1739512863",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_16.jpg?v=1739512834",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_15.jpg?v=1739512901",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_8.jpg?v=1739441060",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_7.jpg?v=1739441089",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/download_3.jpg?v=1739441102",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_4.jpg?v=1739441216",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_5.jpg?v=1739441235",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_6.jpg?v=1739441254",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_7.jpg?v=1739441273",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_8.jpg?v=1739441292",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_9.jpg?v=1739441311",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_10.jpg?v=1739441330",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_11.jpg?v=1739441349",
#         "https://cdn.shopify.com/s/files/1/0692/1696/0670/files/images_12.jpg?v=1739441368",
#     ]
#     print(len(image_urls))
#     products=DatabaseModel.list_documents(product.objects, {"industry_id_str" : "67b80d90ba414ab9b493b595"})
#     for i,product_ins in enumerate(products):
#         images = [image_urls[i]]
#         DatabaseModel.update_documents(product.objects, {"id": product_ins.id}, {"images": images})

# add_random_images_to_products()



# def updateindustryproject():
#     products=DatabaseModel.list_documents(product.objects, {"industry_id_str" : "67b80d90ba414ab9b493b595"})
#     for product_ins in products:
#         brand_name = product_ins.brand_id.name
#         long_description = ""
#         msrp = 0.0              
#         currency = "$"
#         was_price = 15         
#         list_price = 10      
#         discount = 1 
#         availability = True     
#         return_applicable = True 
#         visible = True
#         DatabaseModel.update_documents(product.objects, {"id": product_ins.id}, {
#             "brand_name": brand_name,
#             "long_description": long_description,
#             "msrp": msrp,
#             "currency": currency,
#             "was_price": was_price,
#             "list_price": list_price,
#             "discount": discount,
#             "availability": availability,
#             "return_applicable": return_applicable,
#             "visible": visible
#         })
# # updateindustryproject()
