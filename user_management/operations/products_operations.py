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
import math
import ast


def obtainProductCategoryList(request):
    # manufacture_unit_id = obtainManufactureIdFromToken(request)
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    product_category_id = request.GET.get('product_category_id')
    if product_category_id == None:
        match = {
                    "manufacture_unit_id_str" : manufacture_unit_id,
                    "level" : 1
                }
    else:
        match = {
                    "manufacture_unit_id_str" : manufacture_unit_id,
                    "parent_category_id" : ObjectId(product_category_id)
                }
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
    return product_category_list



def obtainbrandList(request):
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
            "id" : {"$toString" : "$_id"},
            "name" : 1
           }
        }
    ]
    product_list = list(brand.objects.aggregate(*(pipeline)))
    return product_list

@csrf_exempt
def obtainProductsList(request):
    json_request = JSONParser().parse(request)
    manufacture_unit_id = json_request['manufacture_unit_id']
    sort_by = json_request.get('sort_by')
    sort_by_value = json_request.get('sort_by_value')
    product_category_id = json_request.get('product_category_id')
    filters = json_request.get('filters')
    is_parent = json_request.get('is_parent')
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
            "$project" :{
                "_id":0,
                "id" : {"$toString" : "$_id"},
                "product_name" : "$product_name",
                "logo" : {"$first":"$images"},
                "sku_number_product_code_item_number" : "$sku_number_product_code_item_number",
                "mpn" : 1,
                "msrp" : 1,
                "was_price" :1,
                "brand_name" : 1,
                "visible" : 1,
                "end_level_category" : 1,
                "price" : "$list_price",
                "currency" : 1,
                "availability" : 1
            }
            }
        ]
        if sort_by != None and sort_by != "":
            pipeline2 = {
                    "$sort": {
                        sort_by: int(sort_by_value)
                    }
                }
            pipeline.append(pipeline2)
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
            "$project": {
                "_id": 0,
                "id": {"$toString": "$product_ins._id"},
                "product_name": "$product_ins.product_name",
                "logo": {"$first": "$product_ins.images"},
                "sku_number_product_code_item_number": "$product_ins.sku_number_product_code_item_number",
                "mpn": "$product_ins.mpn",
                "msrp": "$product_ins.msrp",
                "was_price": "$product_ins.was_price",
                "brand_name": "$product_ins.brand_name",
                "visible": "$product_ins.visible",
                "end_level_category": 1,
                "price": "$product_ins.list_price",
                "currency": "$product_ins.currency",
                "availability": "$product_ins.availability"
            }
        },
        # {"$skip": skip},
            # {"$limit": limit}
        ]
        if sort_by != None and sort_by != "":
            pipeline2 = {
                    "$sort": {
                        sort_by: int(sort_by_value)
                    }
                }
            pipeline.append(pipeline2)
        product_list = list(product_category.objects.aggregate(pipeline))

    return product_list

def obtainProductsListForDealer(request):
    product_category_id = request.GET.get('product_category_id')
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    skip = int(request.GET.get("skip")) -1
    limit = int(request.GET.get("limit"))

    filters = request.GET.get('filters')
    sort_by = request.GET.get('sort_by')
    sort_by_value = request.GET.get('sort_by_value')

    match = {}
    match['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
    match['visible'] = True

    if product_category_id != None:
        match['category_id'] = ObjectId(product_category_id)
    if filters != None and filters != "all" and filters != "":
        match['availability'] = True if filters == "true" else False

    if product_category_id == None:
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
            "$project" :{
                "_id":0,
                "id" : {"$toString" : "$_id"},
                "name" : "$product_name",
                "logo" : {"$first":"$images"},
                "sku_number" : "$sku_number_product_code_item_number",
                "mpn" : 1,
                "msrp" : 1,
                "was_price" :1,
                "brand_name" : 1,
                "visible" : 1,
                "end_level_category" : "$product_category_ins.name",
                "brand_logo" : {"$ifNull" : ["$brand_ins.logo",""]},
                "price" : "$list_price",
                "currency" : 1,
                "availability" : 1,
                "discount" : 1,
                "quantity" : 1,
            }
            },
            {
                "$skip": skip
            },
            {
                "$limit": limit
            }
        ]
        if sort_by != None and sort_by != "":
            # if sort_by == "price":
            #     sort_by = "list_price"
            # elif sort_by == "end_level_category":
            #     sort_by = "product_category_ins.name"
            pipeline2 = {
                    "$sort": {
                        sort_by: int(sort_by_value)
                    }
                }
            pipeline.append(pipeline2)
        product_list = list(product.objects.aggregate(*(pipeline)))

    elif product_category_id != None:
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
                "$match" : match
        },
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
        {"$unwind": "$brand_ins"},
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
                "end_level_category": 1,
                "brand_logo" : {"$ifNull" : ["$brand_ins.logo",""]},
                "price": "$product_ins.list_price",
                "currency": "$product_ins.currency",
                "availability": "$product_ins.availability",
                "discount" : "$product_ins.discount",
                "quantity" : "$product_ins.quantity",
            }
        },
         {
                "$skip": skip
            },
            {
                "$limit": limit
            }
        ]
        if sort_by != None and sort_by != "":
            pipeline2 = {
                    "$sort": {
                        sort_by: int(sort_by_value)
                    }
                }
            pipeline.append(pipeline2)
        product_list = list(product_category.objects.aggregate(pipeline))

    return product_list

def productCountForDealer(request):
    product_category_id = request.GET.get('product_category_id')
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    filters = request.GET.get('filters')

    match = {}
    match['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
    match['visible'] = True

    if product_category_id != None:
        match['category_id'] = ObjectId(product_category_id)
    if filters != None and filters != "all":
        match['availability'] = True if filters == "true" else False
    
    if product_category_id == None:

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
    elif product_category_id != None:
        match = {}
        match['product_ins.manufacture_unit_id'] = ObjectId(manufacture_unit_id)
        match['product_ins.visible'] = True
        if filters is not None and filters != "all" and filters != "":
            match['product_ins.availability'] = True if filters == "true" else False

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
                "$match": match
            },
            {
                "$count": "total_products"
            }
        ]
        total_count_result = list(product_category.objects.aggregate(*(pipeline)))
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
            "logo" : {"$first":"$images"},
            "long_description" : 1,
            "short_description" : 1,
            "list_price" : 1,
            "discount" : {"$concat" : [{"$toString" : "$discount"},"%"]},
            "brand_name" : 1,
            "brand_logo" : {"$ifNull" : ["$brand_ins.logo",""]},
            "currency" : 1,
            "quantity" : 1,
            "availability" : 1,
            "images" : 1,
            "attributes" : 1,
            "features" : 1,
            "from_the_manufacture" : 1
           }
        }
    ]
    product_list = list(product.objects.aggregate(*(pipeline)))
    if len(product_list) > 0:
        product_list = product_list[0]
    return product_list




@csrf_exempt
def upload_file(request):
    
    general_fields = ['skuNumber code itemNumber', 'model', 'mpn', 'upc ean', 'level1 category', 'level2 category', 'level3 category', 'level4 category', 'level5 category', 'level6 category', 'breadcrumb', 'brandName', "brandlogo", "vendorName", 'productName', 'long description', 'short description', 'features', 'images', 'attributes', 'tags', 'msrp', 'currency', 'was price', 'list price', 'discount', 'quantity', 'quantityPrice', 'availability', 'return applicable']
    
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
                fields_list.append(f"NA {ins}")
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

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'upc ean':
                xl_dict['product_obj']['upc_ean'] = str(row_dict[j])


            elif pd.notnull(row_dict[j]) and fields_list[j] == 'level1 category':
                xl_dict['category_obj']['level 1'] = str(row_dict[j])

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'level2 category':
                xl_dict['category_obj']['level 2'] = str(row_dict[j])
            
            elif pd.notnull(row_dict[j]) and fields_list[j] == 'level3 category':
                xl_dict['category_obj']['level 3'] = str(row_dict[j])

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'level4 category':
                xl_dict['category_obj']['level 4'] = str(row_dict[j])

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'level5 category':
                xl_dict['category_obj']['level 5'] = str(row_dict[j])

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'level6 category':
                xl_dict['category_obj']['level 6'] = str(row_dict[j])


            elif pd.notnull(row_dict[j]) and fields_list[j] == 'breadcrumb':
                if "[" in row_dict[j]:
                    try:
                        data_list = ast.literal_eval(row_dict[j])
                        result = ' > '.join(data_list)
                        xl_dict['product_obj']['breadcrumb'] = result
                    except:
                        xl_dict['product_obj']['breadcrumb'] = ""
                else:
                    xl_dict['product_obj']['breadcrumb'] = str(row_dict[10]) 

            
            elif fields_list[j] == 'brandName':
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
                    xl_dict['product_obj']['product_name'] = str(row_dict[j])
                else:
                    error_dict['error'].append(f"Product Name Should be present") 

            elif fields_list[j] == 'long description':
                if pd.notnull(row_dict[j]):
                    xl_dict['product_obj']['long_description'] = str(row_dict[j])
                else:
                    error_dict['error'].append(f"Long Description Should be present")


            elif pd.notnull(row_dict[j]) and fields_list[j] == 'shortdescription':
                try:
                    data_list = ast.literal_eval(row_dict[j])
                    result = ', '.join(data_list)
                    xl_dict['product_obj']['short_description'] = result
                except:
                    xl_dict['product_obj']['short_description'] = str(row_dict[j])
                # else:
                #     xl_dict['product_obj']['short_description'] = str(row_dict[j])
                
            elif pd.notnull(row_dict[j]) and fields_list[j] == 'features':
                try:
                    try:
                        xl_dict['product_obj']['features'].extend(ast.literal_eval(row_dict[j]))
                    except:
                        xl_dict['product_obj']['features'].append(row_dict[j])
                except:
                    xl_dict['product_obj']['features'] = str(row_dict[16]).split(",")

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'images':
                try:
                    try:
                        xl_dict['product_obj']['images'].extend(ast.literal_eval(row_dict[j]))
                    except:
                        xl_dict['product_obj']['images'].extend(str(row_dict[j]).split(","))
                except:
                    xl_dict['product_obj']['images'].append(row_dict[j])
            
            elif pd.notnull(row_dict[j]) and fields_list[j] == 'attributes':
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
                    

            elif fields_list[j] == 'msrp':
                if pd.notnull(row_dict[j]):
                    try:
                        numbers = re.findall(r"\d+\.\d+|\d+", row_dict[j])
                        result = ''.join(numbers)
                        xl_dict['product_obj']['msrp'] = float(result)
                    except:
                        xl_dict['product_obj']['msrp'] = 0.0
                else:
                    error_dict['error'].append(f"MSRP Should be present")

            elif pd.notnull(row_dict[j]) and fields_list[j] == 'was price':
                try:
                    numbers = re.findall(r"\d+\.\d+|\d+", row_dict[j])
                    result = ''.join(numbers)
                    xl_dict['product_obj']['was_price'] = float(result)
                except:
                    xl_dict['product_obj']['was_price'] = 0.0
                

            elif fields_list[j] == 'list price':
                if pd.notnull(row_dict[j]):
                    try:
                        numbers = re.findall(r"\d+\.\d+|\d+", row_dict[j])
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

def saveProductCategory(manufacture_unit_id,name,level,parent_id):
    product_category_obj = DatabaseModel.get_document(
            product_category.objects, {"name": name,"manufacture_unit_id_str" : manufacture_unit_id}
    )
    if product_category_obj is None:
        product_category_obj = DatabaseModel.save_documents(
            product_category, {
                "name": name,
                "level": level,
                "manufacture_unit_id_str" : manufacture_unit_id
            }
        )
    if parent_id != None:
        DatabaseModel.update_documents(product_category.objects,{"id" : product_category_obj.id},{"parent_category_id" : ObjectId(parent_id)})

        DatabaseModel.update_documents(product_category.objects,{"id" : parent_id},{"add_to_set__child_categories" : product_category_obj.id})

    return product_category_obj.id


@csrf_exempt
def save_file(request):
    data = dict()
    json_request = JSONParser().parse(request)
    manufacture_unit_id = json_request['manufacture_unit_id']
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
                level1_obj = saveProductCategory(manufacture_unit_id,value,1,None)
            elif key == "level 2" and value != "nan":
                level2_obj = saveProductCategory(manufacture_unit_id,value,2,level1_obj)
            elif key == "level 3" and value != "nan":
                level3_obj = saveProductCategory(manufacture_unit_id,value,3,level2_obj)
            elif key == "level 4" and value != "nan":
                level4_obj = saveProductCategory(manufacture_unit_id,value,4,level3_obj)
            elif key == "level 5" and value != "nan":
                level5_obj = saveProductCategory(manufacture_unit_id,value,5,level4_obj)
            elif key == "level 6" and value != "nan":
                level6_obj = saveProductCategory(manufacture_unit_id,value,6,level5_obj)

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
        brand_obj = DatabaseModel.get_document(
            brand.objects, {"name": i['brand_obj']['name'],"manufacture_unit_id_str" : manufacture_unit_id}
        )
        if brand_obj is None:
            brand_obj = DatabaseModel.save_documents(
                brand, {
                    "name": i['brand_obj']['name'],
                    "manufacture_unit_id_str" : manufacture_unit_id
                }
            )

        # Vendor Mapping
        vendor_obj = None
        if i['vendor_obj'].get('name'):
            vendor_obj = DatabaseModel.get_document(
                vendor.objects, {"name": i['vendor_obj']['name'],"manufacture_unit_id_str" : manufacture_unit_id}
            )
            if vendor_obj is None:
                vendor_obj = DatabaseModel.save_documents(
                    vendor, {
                        "name": i['vendor_obj']['name'],
                        "manufacture_unit_id_str" : manufacture_unit_id
                    }
                )

        # Product Mapping
        products_obj = DatabaseModel.get_document(
            product.objects, {"product_name": i['product_obj']['product_name'], "manufacture_unit_id": ObjectId(manufacture_unit_id)}
        )
        try:
            del i['product_obj']['quantity_price']
        except:
            pass
        if products_obj is None:
            
            i['product_obj']['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
            i['product_obj']['brand_id'] = brand_obj.id
            if vendor_obj != None:
                i['product_obj']['vendor_id'] = vendor_obj.id  
            i['product_obj']['category_id'] = category_id
            products_obj = DatabaseModel.save_documents(product, i['product_obj'])
        else:
            if allow_duplicate != None and allow_duplicate == True:
                i['product_obj']['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
                i['product_obj']['brand_id'] = brand_obj.id
                if vendor_obj != None:
                    i['product_obj']['vendor_id'] = vendor_obj.id  
                i['product_obj']['category_id'] = category_id
                DatabaseModel.update_documents(product.objects,{"id" : products_obj.id},i['product_obj'])
            else:
                duplicate_products.append(i)
    
    data['status'] = True
    data['duplicate_products'] = duplicate_products
    return data



@csrf_exempt
def productSearch(request):
    json_request = JSONParser().parse(request)
    search_query = json_request['search_query']
    manufacture_unit_id = json_request['manufacture_unit_id']
    
    pipeline = [
        {
            "$match": {
                "manufacture_unit_id": ObjectId(manufacture_unit_id)
            }
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
                    {"sku_number_product_code_item_number": {"$regex": search_query, "$options": "i"}},
                    {"mpn": {"$regex": search_query, "$options": "i"}},
                    {"product_name": {"$regex": search_query, "$options": "i"}},
                    {"long_description": {"$regex": search_query, "$options": "i"}},
                    {"short_description": {"$regex": search_query, "$options": "i"}},
                    {"features": {"$regex": search_query, "$options": "i"}},
                    {"tags": {"$regex": search_query, "$options": "i"}},
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
                    {"brand_info.name": {"$regex": search_query, "$options": "i"}},
                    {"vendor_info.name": {"$regex": search_query, "$options": "i"}},
                    {"breadcrumbs.name": {"$regex": search_query, "$options": "i"}}
                ]
            }
        },
        {
            "$project": {
                "_id": {"$toString": "$_id"},
                "sku_number_product_code_item_number": {"$ifNull": ["$sku_number_product_code_item_number", ""]},
                "product_name": {"$ifNull": ["$product_name", ""]},
                "brand_name": {"$ifNull": ["$brand_name", ""]},
                "price": {"$ifNull": ["$list_price", ""]},
                "was_price": {"$ifNull": ["$was_price", ""]},
                "discount": {"$ifNull": ["$discount", ""]},
                "currency": {"$ifNull": ["$currency", ""]},
                "quantity": {"$ifNull": ["$quantity", ""]},
                "availability": {"$ifNull": ["$availability", ""]},
                "return_applicable": {"$ifNull": ["$return_applicable", ""]},
                "images": {"$ifNull": ["$images", []]},
                "features": {"$ifNull": ["$features", []]},
                "tags": {"$ifNull": ["$tags", []]},
                "attributes" : "$attributes",
                # "brand_info": {
                #     "name": {"$arrayElemAt": [{"$ifNull": ["$brand_info.name", ["N/A"]]}, 0]},
                #     "logo": {"$arrayElemAt": [{"$ifNull": ["$brand_info.logo", ["N/A"]]}, 0]}
                # },
                # "vendor_info": {
                #     "name": {"$arrayElemAt": [{"$ifNull": ["$vendor_info.name", ["N/A"]]}, 0]}
                # },
                "breadcrumbs": {
                    "$map": {
                        "input": "$breadcrumbs",
                        "as": "breadcrumb",
                        "in": "$$breadcrumb.name"
                    }
                }
            }
        },
        # {"$skip": 0},
        # {"$limit": 10}
    ]
    
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
    for i in product_list:
        product_obj = {}
        if 'list_price' in i:
            product_obj['list_price'] = i['list_price']
            if discount_percentage != None and discount_percentage != "":
                product_obj['list_price'] = round(i['list_price'] + (i['list_price'] * (discount_percentage / 100)),2)
                product_obj['was_price'] = i['list_price']
        if 'visible' in i:
            product_obj['visible'] = i['visible']
        if 'msrp' in i:
            product_obj['msrp'] = i['msrp']
        if 'was_price' in i:
            product_obj['was_price'] = i['was_price']
            if discount_percentage != None and discount_percentage != "":
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


# def normalize_header(header):
#     """
#     Normalize headers by:
#     - Converting to lowercase
#     - Removing special characters and extra spaces
#     """
#     return re.sub(r'[^a-z0-9]+', ' ', header.lower()).strip()


# @csrf_exempt
# def upload_file(request):
#     attribute_field_prefix="attribute"
#     # Example user header mapping
#     user_header_mapping = {
#     'product_obj.sku_number_product_code_item_number': 'SKU/Code/Item Number',
#     'product_obj.model': 'Model',
#     'product_obj.mpn': 'MPN',
#     'product_obj.upc_ean': 'UPC/EAN',
#     'category_obj.level 1': 'Category Level 1',
#     'category_obj.level 2': 'Category Level 2',
#     'brand_obj.name': 'Brand Name',
#     'vendor_obj.name': 'Vendor Name',
#     'product_obj.product_name': 'Product Name',
#     'product_obj.long_description': 'Long Description',
#     'product_obj.images': 'Image Links',
#     'product_obj.quantity': 'Quantity',
#     'product_obj.availability': 'Availability',
#     }
#     data = dict()
#     data['status'] = False
#     data['error'] = ""
#     if 'file' not in request.FILES:
#         data['error'] = "No file uploaded."
#         return data

#     file = request.FILES['file']
#     try:
#         if file.name.endswith('.xlsx'):
#             df = pd.read_excel(file, header=0)
#         elif file.name.endswith('.csv') or file.name.endswith('.txt'):
#             df = pd.read_csv(file)
#         else:
#             data['error'] = "Unsupported file format."
#             return data
#     except Exception as e:
#         data['error'] = f"Error reading file: {str(e)}"
#         return data

#     # Normalize the headers in the DataFrame
#     original_headers = df.columns
#     normalized_headers = {normalize_header(header): header for header in original_headers}
#     df.rename(columns=normalized_headers, inplace=True)

#     # Debugging: Print normalized and original headers
#     print("Original Headers:", original_headers)
#     print("Normalized Headers:", list(normalized_headers.keys()))

#     validation_error = []
#     xl_data = []
#     xl_contains_error_count = 0

#     for i in range(len(df)):
#         row_dict = df.iloc[i]
#         error_dict = dict()
#         xl_dict = dict()
        
#         error_dict['row'] = i + 1
#         error_dict['error'] = []

#         xl_dict['product_obj'] = {}
#         xl_dict['category_obj'] = {}
#         xl_dict['vendor_obj'] = {}
#         xl_dict['brand_obj'] = {}
#         xl_dict['product_obj']['attributes'] = {}

#         # Match headers with normalization
#         for key, column_name in user_header_mapping.items():
#             normalized_column_name = normalize_header(column_name)
#             matched_column = normalized_headers.get(normalized_column_name)

#             if matched_column:
#                 value = row_dict[matched_column]
#                 if pd.notnull(value):
#                     keys = key.split('.')
#                     obj = xl_dict
#                     for k in keys[:-1]:
#                         obj = obj[k]
#                     obj[keys[-1]] = value
#                 else:
#                     error_dict['error'].append(f"{key.replace('_', ' ').title()} is missing.")
#             else:
#                 error_dict['error'].append(f"Expected header '{column_name}' not found in file.")

#         # Process attribute fields dynamically
#         for j in range(1, 21):  # Assuming up to 20 attributes   
#             attr_name_col = f"{attribute_field_prefix} name {j}".lower()
#             attr_value_col = f"{attribute_field_prefix} value {j}".lower()
#             if attr_name_col in df.columns and attr_value_col in df.columns:
#                 attr_name = row_dict[attr_name_col]
#                 attr_value = row_dict[attr_value_col]
#                 if pd.notnull(attr_name) and pd.notnull(attr_value):
#                     xl_dict['product_obj']['attributes'][attr_name] = attr_value
#                 elif pd.notnull(attr_name) or pd.notnull(attr_value):
#                     error_dict['error'].append(f"Incomplete attribute pair at {attr_name_col} and {attr_value_col}.")
#             elif attr_name_col in df.columns or attr_value_col in df.columns:
#                 error_dict['error'].append(f"Missing one of the attribute columns: {attr_name_col}, {attr_value_col}.")

#         if len(error_dict['error']) > 0:
#             xl_contains_error_count += 1

#         validation_error.append(error_dict)
#         xl_data.append(xl_dict)

#     # data['validation_error'] = validation_error
#     # data['xl_contains_error'] = xl_contains_error_count > 0
#     # if xl_contains_error_count == 0:
#     #     data['status'] = True
#     data['xl_data'] = xl_data
#     return data