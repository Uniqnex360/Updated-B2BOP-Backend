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

def obtainOrderList(request):
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    pipeline = [
        {
            "$match" : {
                "manufacture_unit_id_str" : manufacture_unit_id
            }
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
    return order_list