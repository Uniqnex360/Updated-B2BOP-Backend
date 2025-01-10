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


def obtainProductCategoryList(request):
    # manufacture_unit_id = obtainManufactureIdFromToken(request)
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    product_category_id = request.GET.get('product_category_id')
    
    match = dict()
    match['manufacture_unit_id_str'] = manufacture_unit_id
    parent_category_obj = None
    if product_category_id == None:
        match['level'] = 1
    else:
        match['parent_category_id'] = ObjectId(product_category_id)
        pipeline =[
        {
            "$match" : {"_id" : ObjectId(product_category_id)}
        },
        {
           "$project" :{
            "_id":0,
            "id":{"$toString" : "$_id"},
            "name" : 1,
            "parent_category" : True,
            "is_parent": { 
                "$cond": { 
                    "if": { "$ne": ["$child_categories", []] }, 
                    "then": True, 
                    "else": False 
                } 
            }
           }
        }
        ]
        parent_category_obj = (list(product_category.objects.aggregate(*(pipeline))))[0]


    pipeline =[
        {
            "$match" : match
        },
        {
           "$project" :{
            "_id":0,
            "id":{"$toString" : "$_id"},
            "name" : 1,
            "is_parent": { 
                "$cond": { 
                    "if": { "$ne": ["$child_categories", []] }, 
                    "then": True, 
                    "else": False 
                } 
            }
           }
        }
    ]
    product_category_list = list(product_category.objects.aggregate(*(pipeline)))
    if product_category_list != [] and parent_category_obj != None:
        product_category_list.append(parent_category_obj)

    return product_category_list

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


def obtainbrandList(request):
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    industry_id = request.GET.get('industry_id')

    match = {"manufacture_unit_id_str": manufacture_unit_id}
    if industry_id:
        match["industry_id_str"] = industry_id

    pipeline = [
        {"$match": match},
        {
            "$lookup": {
                "from": "product",
                "let": {"brand_id": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$brand_id", "$$brand_id"]}}},
                    {"$count": "total_count"},
                ],
                "as": "products_count",
            }
        },
        {
            "$addFields": {
                "products_count": {
                    "$arrayElemAt": ["$products_count.total_count", 0],
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "id": {"$toString": "$_id"},
                "name": 1,
                "products_count": {"$ifNull": ["$products_count", 0]},
            }
        },
    ]

    brand_list = list(brand.objects.aggregate(*pipeline))
    return brand_list


@csrf_exempt
def obtainProductsList(request):
    json_request = JSONParser().parse(request)
    manufacture_unit_id = json_request['manufacture_unit_id']
    sort_by = json_request.get('sort_by')
    sort_by_value = json_request.get('sort_by_value')
    product_category_id = json_request.get('product_category_id')
    filters = json_request.get('filters')
    is_parent = json_request.get('is_parent')
    brand_id = json_request.get('brand_id')
    price_from = json_request.get('price_from')
    price_to = json_request.get('price_to')
    product_list = []

    match = {}
    match['manufacture_unit_id'] = ObjectId(manufacture_unit_id)

    if product_category_id != None and product_category_id != "":
        match['category_id'] = ObjectId(product_category_id)
    if filters != None and filters != "all" and filters != "":
        match['availability'] = True if filters == "In-stock" else False

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
        if brand_id != None and brand_id != "":
            price_match['brand_ins._id'] = ObjectId(brand_id)
        if (price_from != None and price_from != "") and (price_to != None and price_to != ""):
            price_match['list_price'] = {
                "$gte": int(price_from),
                "$lte": int(price_to)
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
                "availability" : 1
            }
            }
        pipeline.append(project_stage)
        if sort_by != None and sort_by != "":
            sorting_pipeline = {
                    "$sort": {
                        sort_by: int(sort_by_value)
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
        if brand_id != None and brand_id != "":
            price_match['brand_ins._id'] = ObjectId(brand_id)
        if (price_from != None and price_from != "") and (price_to != None and price_to != ""):
            price_match['product_ins.list_price'] = {
                "$gte": int(price_from),
                "$lte": int(price_to)
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
                "availability": "$product_ins.availability"
            }
        }
        pipeline.append(project_stage)
        
        if sort_by != None and sort_by != "":
            sorting_pipeline = {
                    "$sort": {
                        sort_by: int(sort_by_value)
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
            price_match['list_price'] = {
                "$gte": int(price_from),
                "$lte": int(price_to)
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
            price_match['product_ins.list_price'] = {
                "$gte": int(price_from),
                "$lte": int(price_to)
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
    
    
    if product_category_id == "":

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
    elif product_category_id != None and product_category_id != "":
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
        pipeline = [
            {
                "$match": match
            },
            
            {
                "$count": "total_products"
            }
        ]
        total_count_result = list(product.objects.aggregate(*(pipeline)))
        total_count = total_count_result[0]['total_products'] if total_count_result else 0

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
            "visible" : 1,
            "end_level_category" : "$product_category_ins.name",
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
    json_request = JSONParser().parse(request)
    search_query = re.escape(json_request['search_query'])
    # search_query = json_request['search_query']
    manufacture_unit_id = json_request['manufacture_unit_id']
    role_name = json_request.get('role_name')
    sort_by = json_request.get("sort_by")
    sort_by_value = json_request.get("sort_by_value")
    skip = json_request.get("skip")
    limit = json_request.get("limit")
    product_category_id = request.GET.get('product_category_id')
    search_query = search_query.strip()
    spell = SpellChecker()
    search_query = ' '.join([spell.correction(word) for word in search_query.split()])
    match = dict()
    match['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
    if role_name != None:
        match['visible'] = True

    
    pipeline = [
        {
            "$match": match
        },
        {
            "$graphLookup": {
                "from": "product_category",
                "startWith": "$category_id",
                "connectFromField": "parent_category_id",
                "connectToField": "_id",
                "as": "breadcrumbs",
                "maxDepth": 5,
                "depthField": "level"
            }
        },
        {
            "$lookup": {
                "from": "brand",
                "localField": "brand_id",
                "foreignField": "_id",
                "as": "brand_info"
            }
        },
        {
            "$lookup": {
                "from": "vendor",
                "localField": "vendor_id",
                "foreignField": "_id",
                "as": "vendor_info"
            }
        },
        {
            "$match": {
                "$or": [
                    {"brand_info.name": {"$regex": search_query, "$options": "i"}},
                    {"breadcrumbs.name": {"$regex": search_query, "$options": "i"}},
                    {"sku_number_product_code_item_number": {"$regex": search_query, "$options": "i"}},
                    {"mpn": {"$regex": search_query, "$options": "i"}},
                    {"model": {"$regex": search_query, "$options": "i"}},
                    {"upc_ean": {"$regex": search_query, "$options": "i"}},
                    {"product_name": {"$regex": f'^{search_query}$', "$options": "i"}},
                    # {"brand_info.name": {"$regex": search_query, "$options": "i"}},
                    {"vendor_info.name": {"$regex": search_query, "$options": "i"}},
                    {
                        "$expr": {
                            "$gt": [
                                {
                                    "$size": {
                                        "$filter": {
                                            "input": { "$objectToArray": "$attributes" },
                                            "cond": {
                                                "$or": [
                                                    # Check if key matches the search query
                                                    {
                                                        "$and": [
                                                            { "$eq": [{ "$type": "$$this.k" }, "string"] },
                                                            { "$regexMatch": { "input": "$$this.k", "regex": search_query, "options": "i" } }
                                                        ]
                                                    },
                                                    # Check if string values match the search query
                                                    {
                                                        "$and": [
                                                            { "$eq": [{ "$type": "$$this.v" }, "string"] },
                                                            { "$regexMatch": { "input": "$$this.v", "regex": search_query, "options": "i" } }
                                                        ]
                                                    },
                                                    # Check if numeric values match the search query (by converting to string)
                                                    {
                                                        "$and": [
                                                            { "$in": [{ "$type": "$$this.v" }, ["int", "long", "double", "decimal"]] },
                                                            { "$regexMatch": { "input": { "$toString": "$$this.v" }, "regex": search_query, "options": "i" } }
                                                        ]
                                                    }
                                                ]
                                            }
                                        }
                                    }
                                },
                                0
                            ]
                        }
                    },
                    {"long_description": {"$regex": search_query, "$options": "i"}},
                    {"short_description": {"$regex": search_query, "$options": "i"}},
                    {"features": {"$regex": search_query, "$options": "i"}},
                    {"tags": {"$regex": search_query, "$options": "i"}},
                    
                ]
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
    if product_category_id != None and product_category_id != "":
        match = {"$match" : {
            "product_category_ins._id" : ObjectId(product_category_id)
        }}
        pipeline.append(match)
    pipeline3 = [{"$unwind" : "$product_category_ins"},
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
        },
        {
            "$project": {
                "_id": 0,
                "id" : {"$toString" : "$_id"},
                "name" : "$product_name",
                "product_name" : "$product_name",
                "logo" : {"$ifNull" : [{"$first": "$images"},"http://example.com/"]},
                "sku_number_product_code_item_number" : "$sku_number_product_code_item_number",
                "sku_number" : "$sku_number_product_code_item_number",
                "mpn" : 1,
                "msrp" : 1,
                "was_price" :1,
                "brand_name" : 1,
                "visible" : 1,
                "end_level_category" : 1,
                "price" : "$list_price",
                "currency" : 1,
                "availability" : 1,
                "quantity" : 1,
                "discount" : {"$round" : ["$discount",2]},
                "brand_logo" : {"$ifNull" : ["$brand_ins.logo",""]},
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
        },
        # {"$skip": 0},
        # {"$limit": 10}
    ]
    if sort_by != None and sort_by != "":
        pipeline2 = [{
                "$sort": {
                    sort_by: int(sort_by_value)
                }
            },
            {
                "$skip": skip-1
            },
            {
                "$limit": limit
            }]
        pipeline3.extend(pipeline2)
    pipeline.extend(pipeline3)
    
    results = list(product.objects.aggregate(pipeline))
    return results



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



# def get_related_products(request):
#     # Get the product_id and manufacture_unit_id from the request
#     product_id = request.GET.get('product_id')
#     manufacture_unit_id = request.GET.get('manufacture_unit_id')
#     product_object_id = ObjectId(product_id)

#     # Fetch the current product's details from the database
#     current_product = DatabaseModel.get_document(
#         product.objects,
#         {"id": product_object_id},  # Using '_id' for MongoDB queries
#         ['brand_id', 'category_id', 'attributes']
#     )

#     # Extract plain values for use in the pipeline
#     current_brand_id = str(current_product.brand_id.id) if current_product.brand_id else None
#     current_category_id = str(current_product.category_id.id) if current_product.category_id else None
#     # If you plan to use attributes, ensure it's extracted like below
#     # current_attributes = current_product.attributes or []

#     # MongoDB aggregation pipeline
#     pipeline = [
#     {
#         "$match": {
#             "_id": {"$ne": product_object_id},  # Exclude the current product
#             "visible": True,
#             "availability": True,
#             "manufacture_unit_id": ObjectId(manufacture_unit_id)
#         }
#     },
#     {
#         "$addFields": {
#             "relevance": {
#                 "$sum": [
#                     {"$cond": [{"$eq": ["$brand_id", current_brand_id]}, 3, 0]},
#                     {"$cond": [{"$eq": ["$category_id", current_category_id]}, 2, 0]},
#                     # Uncomment and adjust if you want to include attribute matching
#                     # {"$cond": [{"$gt": [{"$size": {"$setIntersection": ["$attributes", current_attributes]}}, 0]}, 1, 0]}
#                 ]
#             }
#         }
#     },
#     {
#         "$sort": {
#             "relevance": -1,  # Sort by relevance score
#             "rating_average": -1  # If relevance is the same, sort by rating
#         }
#     },
#     {"$limit": 10},
#     {
#         "$project": {
#             "_id": 0,
#             "id": {"$toString": "$_id"},
#             "name": "$product_name",
#             "logo": {"$ifNull": [{"$first": "$images"}, "http://example.com/"]},
#             "sku_number": "$sku_number_product_code_item_number",
#             "mpn": 1,
#             "msrp": {"$round": ["$msrp", 2]},
#             "was_price": {"$round": ["$was_price", 2]},
#             "brand_name": 1,
#             "visible": 1,
#             "end_level_category": "$product_category_ins.name",
#             "brand_logo": {"$ifNull": ["$brand_ins.logo", ""]},
#             "price": {"$round": ["$list_price", 2]},
#             "currency": 1,
#             "availability": 1,
#             "discount": 1,
#             "quantity": 1,
#             "upc_ean": 1,
#         }
#     }
#     ]

#     # Execute the pipeline and return the result
#     related_products = list(product.objects.aggregate(*pipeline))
    
#     # You can format the response as needed, for example, using Django's JsonResponse
#     return related_products


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
