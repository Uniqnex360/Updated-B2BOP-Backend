from django.shortcuts import render
from user_management.models import *
from django.http import JsonResponse,HttpResponse
from b2bop_project.custom_mideleware import SIMPLE_JWT, createJsonResponse, createCookies,obtainManufactureIdFromToken, obtainUserIdFromToken, obtainUserRoleFromToken
from rest_framework.decorators import api_view
from django.middleware import csrf
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
import jwt
from bson import ObjectId
import pandas as pd
from b2bop_project.crud import DatabaseModel


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
def obtainOrderList(request):
    json_request = JSONParser().parse(request)
    print("json_request",json_request,"\n\n\n")
    manufacture_unit_id = json_request['manufacture_unit_id']
    search_query = json_request['search_query']
    sort_by = json_request['sort_by']
    
    sort_by_value = json_request['sort_by_value']
    status = json_request['status']
    dealer_list = json_request.get('dealer_list')
    if status == "all":
        match = {
                "manufacture_unit_id_str" : manufacture_unit_id,
                # "status" : status
            }
    else:
        match = {
                "manufacture_unit_id_str" : manufacture_unit_id,
                "status" : status
            }
    pipeline = [
        {
            "$match" : match
        },
        {
            "$lookup" :{
                "from" : "user",
                "localField" : "customer_id",
                "foreignField" : "_id",
                "as" : "user_ins"
            }
        },
        {"$unwind" : "$user_ins"}]
    if search_query != "":
        search_obj = {
            "$match" : {
                "user_ins.username": {"$regex": search_query, "$options": "i"}
            }
        }
        pipeline.append(search_obj)
    if dealer_list != None and dealer_list != []:
        dealer_list = [ObjectId(ins) for ins in dealer_list]
        dealer_search_obj = {
            "$match" : {
                "user_ins._id": {"$in": dealer_list}
            }
        }
        pipeline.append(dealer_search_obj)
    project_obj ={
           "$project" :{
                "_id": 0,
                "_id" : {"$toString" : "$_id"},
                "dealer_name" : "$user_ins.username",
                "amount" : {"$concat": [{"$toString": "$amount"},"$currency"]},
                "shipping_service" : "-",
                "tracking_code" : "-",
                "creation_date": {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$creation_date",
                    }
                    },
                "status" : 1
           }
        }
    pipeline.append(project_obj)

    if sort_by != "":
        if sort_by == "amount":
            amount_sort = [{
                        "$addFields": {
                            "numeric_amount": {
                                "$toDouble": {
                                    "$arrayElemAt": [{"$split": ["$amount", "USD"]}, 0]
                                }
                            }
                        }
                    },
                    {
                        "$sort": {
                            "numeric_amount" : sort_by_value
                        }
                    }
                    ]
            pipeline.extend(amount_sort)
        else:
            pipeline2 = {
                "$sort": {
                    sort_by: sort_by_value
                }
            }
            pipeline.append(pipeline2)
    print("pipeline",pipeline,"\n\n\n\n")
    order_list = list(order.objects.aggregate(*(pipeline)))

    return order_list



@api_view(('GET', 'POST'))
def exportOrders(request):
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    status = request.GET.get('status')
    if status == "all":
        match = {
                "manufacture_unit_id_str" : manufacture_unit_id
            }
    else:
        match = {
                "manufacture_unit_id_str" : manufacture_unit_id,
                "status" : status
            }
    pipeline = [
        {
            "$match" : match
        },
        {
            "$lookup" :{
                "from" : "user",
                "localField" : "customer_id",
                "foreignField" : "_id",
                "as" : "user_ins"
            }
        },
        {"$unwind" : "$user_ins"},
        {
           "$project" :{
                "_id": 0,
                "order_id" : {"$toString" : "$_id"},
                "dealer_anme" : "$user_ins.username",
                "order_value" : {"$concat": [{"$toString": "$amount"},"$currency"]},
                "shipping_service" : "-",
                "tracking_code" : "-",
                "order_date": {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$creation_date",
                    }
                    },
                "status" : 1
           }
        }
    ]
    order_list = list(order.objects.aggregate(*(pipeline)))
    df = pd.DataFrame(order_list)
    # Create a HttpResponse object with Excel content type
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="data.xlsx"'

    # Save the DataFrame to the response as an Excel file
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')

    return response


def obtainDealerlist(request):
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    
    pipeline = [
        {
            "$match" : {
                "manufacture_unit_id" : ObjectId(manufacture_unit_id),
                "role_id" : ObjectId('670e3c616569d56ed4d4a75b'),
            }
        },
        {
           "$project" :{
                "_id": 0,
                'id': {"$toString" : "$_id"},
                "username" : 1
           }
        }
    ]
    dealer_list = list(user.objects.aggregate(*(pipeline)))
    return dealer_list