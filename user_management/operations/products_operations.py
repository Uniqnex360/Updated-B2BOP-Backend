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


def obtainProductsList(request):
    product_category_id = request.GET.get('product_category_id')
    # brand_id = request.GET.get('brand_id')
    # manufacture_unit_id = obtainManufactureIdFromToken(request)
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    if product_category_id != None:
        match = {
                "manufacture_unit_id" : ObjectId(manufacture_unit_id),
                "category_id" : ObjectId(product_category_id)
            }
    else:
        match = {
                "manufacture_unit_id" : ObjectId(manufacture_unit_id),
            }
    pipeline =[
        {
            "$match" : match
        },
        {
           "$project" :{
            "_id":0,
            "id" : {"$toString" : "$_id"},
            "name" : "$product_name",
            "logo" : {"$first":"$images"},
            "description" : "$long_description"
           }
        }
    ]
    product_list = list(product.objects.aggregate(*(pipeline)))
    return product_list

def obtainProductDetails(request):
    project_id = request.GET.get('project_id')
    pipeline =[
        {
            "$match" : {
                "_id" : ObjectId(project_id),
            }
        },
        {
           "$project" :{
            "_id":0,
            "id" : {"$toString" : "$_id"},
            "name" : "$product_name",
            "sku_number_product_code_item_number" : 1,
            "model" : 1,
            "mpn" : 1,
            "upc_ean" : 1,
            "logo" : {"$first":"$images"},
            "description" : "$long_description",
            "short_description" : 1,
            "price" : "$list_price",
            "discount" : {"$concat" : [{"$toString" : "$discount"},"%"]},
            "currency" : 1,
            "quantity" : 1,
            "availability" : 1,
            "product_image_list" : "$images",
            "attributes" : 1,
            "features" : 1
           
           }
        }
    ]
    product_list = list(product.objects.aggregate(*(pipeline)))
    return product_list[0]


@csrf_exempt
def upload_file(request):
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
            if len(df.iloc[0]) != 47:
                data['error'] = "File having Missing columns"
                return data 
        elif file.name.endswith('.csv') or file.name.endswith('.txt'):
            df = pd.read_csv(file)
        else:
            data['error'] = "Unsupported file format."
            return data
    except Exception as e:
        data['error'] = f"Error reading file: {str(e)}"
        return data
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
        xl_dict['category_obj'] = dict()
        xl_dict['vendor_obj'] = dict()
        xl_dict['brand_obj'] = dict()

        if str(type(row_dict[0])) == "<class 'float'>":
            error_dict['error'].append(f"SKU number/Product Code/Item number Should be present")
        else:
            xl_dict['product_obj']['sku_number_product_code_item_number'] = str(row_dict[0])

        if str(type(row_dict[1])) != "<class 'float'>":
            xl_dict['product_obj']['model'] = str(row_dict[1])

        if str(type(row_dict[2])) == "<class 'float'>":
            error_dict['error'].append(f"MPN Should be present")
        else:
            xl_dict['product_obj']['mpn'] = str(row_dict[2])

        if str(type(row_dict[3])) != "<class 'float'>":
            xl_dict['product_obj']['upc_ean'] = str(row_dict[3])


        if str(type(row_dict[4])) == "<class 'float'>" or str(type(row_dict[5])) == "<class 'float'>":
            error_dict['error'].append(f"At least a two-level of categorys should be present")
        else:
            xl_dict['category_obj']['level 1'] = str(row_dict[4])
            xl_dict['category_obj']['level 2'] = str(row_dict[5])
        
        if str(type(row_dict[6])) != "<class 'float'>":
            xl_dict['category_obj']['level 3'] = str(row_dict[6])
        
        if str(type(row_dict[7])) != "<class 'float'>":
            xl_dict['category_obj']['level 4'] = str(row_dict[7])

        if str(type(row_dict[8])) != "<class 'float'>":
            xl_dict['category_obj']['level 5'] = str(row_dict[8])

        if str(type(row_dict[9])) != "<class 'float'>":
            xl_dict['category_obj']['level 6'] = str(row_dict[9])

        if str(type(row_dict[10])) != "<class 'float'>":
            xl_dict['product_obj']['breadcrumb'] = str(row_dict[10]) 

        
        if str(type(row_dict[11])) == "<class 'float'>":
            error_dict['error'].append(f"Brand Name Should be present")
        else:
            xl_dict['brand_obj']['name'] = str(row_dict[11])
            xl_dict['product_obj']['brand_name'] = str(row_dict[11])

        if str(type(row_dict[12])) != "<class 'float'>":
            xl_dict['vendor_obj']['name'] = str(row_dict[12])


        if str(type(row_dict[13])) == "<class 'float'>":
            error_dict['error'].append(f"Product Name Should be present")
        else:
            xl_dict['product_obj']['product_name'] = str(row_dict[13])

        if str(type(row_dict[14])) == "<class 'float'>":
            error_dict['error'].append(f"Long Description Should be present")
        else:
            xl_dict['product_obj']['long_description'] = str(row_dict[14])


        if str(type(row_dict[15])) != "<class 'float'>":
            xl_dict['product_obj']['short_description'] = str(row_dict[15])

        if str(type(row_dict[16])) != "<class 'float'>":
            xl_dict['product_obj']['features'] = str(row_dict[16]).split(",")

        if str(type(row_dict[17])) == "<class 'float'>":
            error_dict['error'].append(f"Images Link list Should be present")
        else:
            xl_dict['product_obj']['images'] = str(row_dict[17]).split(",")


        if str(type(row_dict[18])) == "<class 'float'>" or str(type(row_dict[19])) == "<class 'float'>" or str(type(row_dict[20])) == "<class 'float'>" or str(type(row_dict[21])) == "<class 'float'>":
            error_dict['error'].append(f"At least a two-level of Attributes should be present")
        else:
            xl_dict['product_obj']['attributes'] = {}

            for j in range(18, 38, 2):  # Step by 2 to access "Attribute name" and "Attribute value" pairs
                attribute_name = row_dict[j]          # Attribute name
                attribute_value = row_dict[j + 1]     # Attribute value
                
                # Check if both attribute name and value are not null
                if pd.notnull(attribute_name) and pd.notnull(attribute_value):
                    xl_dict['product_obj']['attributes'][attribute_name] = attribute_value


        if str(type(row_dict[38])) == "<class 'float'>":
            error_dict['error'].append(f"MSRP Should be present")
        else:
            xl_dict['product_obj']['msrp'] = float(row_dict[38][1:])
            xl_dict['product_obj']['currency'] = row_dict[38][0]

        if str(type(row_dict[39])) != "<class 'float'>":
            xl_dict['product_obj']['was_price'] = float(row_dict[39][1:])

        if str(type(row_dict[40])) == "<class 'float'>":
            error_dict['error'].append(f"List Price Should be present")
        else:
            xl_dict['product_obj']['list_price'] = float(row_dict[40][1:])

        if str(type(row_dict[41])) != "<class 'float'>":
            xl_dict['product_obj']['discount'] = float(row_dict[41].replace("%", ""))

        if str(type(row_dict[42])) != "<class 'float'>":
            xl_dict['product_obj']['quantity_price'] = float(row_dict[42][1:])

        if str(type(row_dict[43])) == "<class 'float'>":
            error_dict['error'].append(f"Quantity Should be present")
        else:
            xl_dict['product_obj']['quantity'] = int(row_dict[43]) 

        if str(type(row_dict[44])) == "<class 'float'>":
            error_dict['error'].append(f"Availability Should be present")
        else:
            if str(row_dict[44]).lower() == "out of stock":
                xl_dict['product_obj']['availability'] = False
            else:
                xl_dict['product_obj']['availability'] = True

        if str(type(row_dict[45])) == "<class 'float'>":
            error_dict['error'].append(f"Return Applicable or not Should be present")
        else:
            if str(row_dict[45]).lower() == "no":
                xl_dict['product_obj']['return_applicable'] = False
            else:
                xl_dict['product_obj']['return_applicable'] = True
        
        if str(type(row_dict[46])) != "<class 'float'>":
            xl_dict['product_obj']['tags'] = str(row_dict[46]).split(",")
        
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
        DatabaseModel.update_documents(product_category.objects,{"id" : parent_id},{"push__child_categories" : product_category_obj.id})

    return product_category_obj.id


@csrf_exempt
def save_file(request):
    data = dict()
    json_request = JSONParser().parse(request)
    manufacture_unit_id = json_request['manufacture_unit_id']
    xl_data = json_request['xl_data']
    
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
        if products_obj is None:
            
            i['product_obj']['manufacture_unit_id'] = ObjectId(manufacture_unit_id)
            i['product_obj']['brand_id'] = brand_obj.id
            if vendor_obj != None:
                i['product_obj']['vendor_id'] = vendor_obj.id  
            i['product_obj']['category_id'] = category_id
            products_obj = DatabaseModel.save_documents(product, i['product_obj'])
    
    data['status'] = True
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
        # Recursively lookup categories up to 6 levels to generate breadcrumbs
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
        # Lookup brand information
        {
            "$lookup": {
                "from": "brand",
                "localField": "brand_id",
                "foreignField": "_id",
                "as": "brand_info"
            }
        },
        # Lookup vendor information
        {
            "$lookup": {
                "from": "vendor",
                "localField": "vendor_id",
                "foreignField": "_id",
                "as": "vendor_info"
            }
        },
        # Match against search query in various fields
        {
            "$match": {
                "$or": [
                    {"product_name": {"$regex": search_query, "$options": "i"}},
                    {"long_description": {"$regex": search_query, "$options": "i"}},
                    {"short_description": {"$regex": search_query, "$options": "i"}},
                    {"features": {"$regex": search_query, "$options": "i"}},
                    {"tags": {"$regex": search_query, "$options": "i"}},
                    {"attributes": {"$regex": search_query, "$options": "i"}},
                    {"brand_info.name": {"$regex": search_query, "$options": "i"}},
                    {"vendor_info.name": {"$regex": search_query, "$options": "i"}},
                    {"breadcrumbs.name": {"$regex": search_query, "$options": "i"}}
                ]
            }
        },
        # Project fields to include in the result
        {
            "$project": {
                "_id": {"$toString": "$_id"},  # Convert product _id to string
                "sku_number_product_code_item_number": {"$ifNull": ["$sku_number_product_code_item_number", None]},
                "product_name": {"$ifNull": ["$product_name", None]},
                "brand_name": {"$ifNull": ["$brand_name", None]},
                "price": {"$ifNull": ["$list_price", None]},
                "was_price": {"$ifNull": ["$was_price", None]},
                "discount": {"$ifNull": ["$discount", None]},
                "currency": {"$ifNull": ["$currency", None]},
                "quantity": {"$ifNull": ["$quantity", None]},
                "availability": {"$ifNull": ["$availability", None]},
                "return_applicable": {"$ifNull": ["$return_applicable", None]},
                "images": {"$ifNull": ["$images", []]},
                "features": {"$ifNull": ["$features", []]},
                "tags": {"$ifNull": ["$tags", []]},
                "brand_info": {
                    "name": {"$arrayElemAt": [{"$ifNull": ["$brand_info.name", ["N/A"]]}, 0]},
                    "logo": {"$arrayElemAt": [{"$ifNull": ["$brand_info.logo", ["N/A"]]}, 0]}
                },
                "vendor_info": {
                    "name": {"$arrayElemAt": [{"$ifNull": ["$vendor_info.name", ["N/A"]]}, 0]}
                },
                # Breadcrumbs, ordering from root to leaf based on category levels
                "breadcrumbs": {
                    "$map": {
                        "input": "$breadcrumbs",
                        "as": "breadcrumb",
                        "in": "$$breadcrumb.name"
                    }
                }
            }
        },
        # Pagination
        {"$skip": 0},
        {"$limit": 10}
    ]
    
    results = list(product.objects.aggregate(pipeline))
    return results


