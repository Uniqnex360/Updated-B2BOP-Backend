from django.shortcuts import render
from user_management.models import *
from django.http import JsonResponse,HttpResponse
from b2bop_project.custom_mideleware import SIMPLE_JWT, createJsonResponse, createCookies,obtainManufactureIdFromToken, obtainUserIdFromToken, obtainUserRoleFromToken
from rest_framework.decorators import api_view
from django.middleware import csrf
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
import jwt
import pytz
from bson import ObjectId
import pandas as pd
from b2bop_project.crud import DatabaseModel
from datetime import datetime, timedelta
import threading


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
                "product_id" : json_request['product_id'],
                "status" : "Pending"
            }
        },
        {
           "$project" :{
                "_id":1,
                'price' :1,
                "quantity" : 1
           }
        }
    ]
    user_cart_item_obj = list(user_cart_item.objects.aggregate(*(pipeline)))
    if user_cart_item_obj != []:
        price = (user_cart_item_obj[0]['quantity'] + json_request['quantity']) * json_request['price']
        DatabaseModel.update_documents(user_cart_item.objects,{"id" : user_cart_item_obj[0]['_id']},{"inc__quantity" : json_request['quantity'],"price" : price,"unit_price" : json_request['price']})
        data['is_updated'] = True
    else:
        json_request['unit_price'] = json_request['price']
        json_request['price'] = json_request['price'] * json_request['quantity']
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
                "status" : "Pending"
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
           "$project" :{
                "_id": 0,
                "id" : {"$toString" : "$_id"},
                "product_id" : {"$toString" : "$products_ins._id"},
                "name" : "$products_ins.product_name",
                "description" : "$products_ins.long_description",
                "price" : {"$ifNull" : ["$unit_price",0.0]},
                "currency" : "$products_ins.currency",
                "primary_image" : {"$first":"$products_ins.images"},
                "sku_number" : "$products_ins.sku_number_product_code_item_number",
                "mpn_number" : "$products_ins.mpn",
                "brand_name" : "$products_ins.brand_name",
                # "colour" : "$products_ins.colour",
                "quantity" : 1,
                "total_price" : "$price"
           }
        }
    ]
    user_cart_item_list = list(user_cart_item.objects.aggregate(*(pipeline)))
    return user_cart_item_list



@csrf_exempt
def updateOrDeleteUserCartItem(request):
    data = dict()
    json_request = JSONParser().parse(request)
    if json_request['empty_cart'] == True:
        DatabaseModel.delete_documents(user_cart_item.objects,{"user_id" : ObjectId(json_request['user_id']),"status" : "Pending"})
        data['is_deleted'] = True
    elif json_request['is_delete'] == True:
        DatabaseModel.delete_documents(user_cart_item.objects,{"id" : ObjectId(json_request['id'])})
        data['is_deleted'] = True
    else:
        for cart_ins in json_request['cart_list']:
            cart_obj = DatabaseModel.get_document(user_cart_item.objects,{"id" : cart_ins['id']},['product_id','quantity'])
            unit_price = cart_obj.product_id.list_price
            updated_price = (unit_price) * cart_ins['quantity']
            DatabaseModel.update_documents(user_cart_item.objects,{"id" : cart_ins['id']},{"price" : updated_price,"quantity" : cart_ins['quantity'],"unit_price" : unit_price})

        data['is_updated'] = True
    return data


def totalCheckOutAmount(request):
    # user_id = obtainUserIdFromToken(request)
    user_id = request.GET.get('user_id')
    pipeline = [
    {
        "$match": {
            "user_id": ObjectId(user_id),
            "status": "Pending"
        }
    },
    {
        "$group": {
            "_id": None,
            'total_amount': {'$sum': '$price'},
            'cart_count': {'$sum': 1} 
        }
    },
    {
        "$project": {
            "_id": 0,
            'total_amount': {"$round":["$total_amount",2]},
            'cart_count': "$cart_count" 
        }
        }
    ]

    user_cart_item_list = list(user_cart_item.objects.aggregate(*(pipeline)))
    if len(user_cart_item_list) > 0:
        user_cart_item_list= user_cart_item_list[0]
    else:
        user_cart_item_list = {
            "total_amount" : 0.0,
            "cart_count" : 0
        }

    return user_cart_item_list

@csrf_exempt
def obtainOrderList(request):
    json_request = JSONParser().parse(request)
    manufacture_unit_id = json_request['manufacture_unit_id']
    search_query = json_request['search_query']
    sort_by = json_request['sort_by']
    search_by_date = json_request.get('search_by_date')
    
    sort_by_value = json_request['sort_by_value']
    # status = json_request['status']
    dealer_list = json_request.get('dealer_list')
    delivery_status = json_request['delivery_status']
    fulfilled_status = json_request['fulfilled_status']
    payment_status = json_request['payment_status']
    industry_id_str = json_request.get('industry_id')

    
    status_match = {}
    status_match['manufacture_unit_id_str'] = manufacture_unit_id
    if delivery_status != "all":
        status_match['delivery_status'] = delivery_status
    if fulfilled_status != "all":
        status_match['fulfilled_status'] = fulfilled_status
    if payment_status != "all":
        status_match['payment_status'] = payment_status
    if industry_id_str != None:
        status_match['industry_id_str'] = industry_id_str


    # print("status_match",status_match,"\n\n\n\n")
   
    pipeline = [
        {
            "$match" : status_match
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
    
    if dealer_list != None and dealer_list != []:
        dealer_list = [ObjectId(ins) for ins in dealer_list]
        dealer_search_obj = {
            "$match" : {
                "user_ins._id": {"$in": dealer_list}
            }
        }
        pipeline.append(dealer_search_obj)

    if search_by_date != None and search_by_date != "":
        search_date = datetime.strptime(search_by_date, "%Y-%m-%d")
        # print("search_date",search_date,type(search_date),"\n\n")

        # Get the system's local timezone dynamically
        local_timezone = datetime.now().astimezone().tzinfo

        # Localize start and end of the day to the local timezone
        start_of_day = search_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(local_timezone)
        end_of_day = search_date.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(local_timezone)

        # Convert to UTC for MongoDB query
        start_of_day_utc = start_of_day.astimezone(pytz.utc)
        end_of_day_utc = end_of_day.astimezone(pytz.utc)
        date_search_obj = {
            "$match" : {
                "creation_date":  {
                                "$gte": start_of_day_utc,
                                "$lte": end_of_day_utc 
                                 }
            }
        }
        pipeline.append(date_search_obj)
    project_obj =[
        {
            "$lookup" :{
                "from" : "address",
                "localField" : "shipping_address_id",
                "foreignField" : "_id",
                "as" : "address_ins"
            }
        },
        {
        "$unwind": {
            "path": "$address_ins",
            "preserveNullAndEmptyArrays": True
        }
        },
        {
           "$project" :{
                "_id": 0,
                "_id" : {"$toString" : "$_id"},
                "order_id" : 1,
                "dealer_name" : {"$concat":["$user_ins.first_name",{"$ifNull" : ["$user_ins.last_name",""]}]},
                "total_items" : 1,
                "amount" : {"$concat": [{"$toString": "$amount"},"$currency"]},
                "shipping_service" : "-",
                "tracking_code" : "-",
                "creation_date": {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$creation_date",
                    }
                    },
                "address" : {
                    "street" : "$address_ins.street",
                    "city" : "$address_ins.city",
                    "state" : "$address_ins.state",
                    "country" : "$address_ins.country",
                    "zipCode" : "$address_ins.zipCode"
                },
                "delivery_status" : 1,
                "fulfilled_status" : 1,
                "payment_status" : 1
           }
        }]
    pipeline.extend(project_obj)
    if search_query != "":
        search_obj = {
            "$match" : { "$or" : [
                                {"dealer_name": {"$regex": search_query, "$options": "i"}},
                                {"order_id" : {"$regex": search_query, "$options": "i"}}
                                ]
            }
        }
        pipeline.append(search_obj)

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
    else:
        pipeline2 = {
                "$sort": {
                    "_id": -1
                }
            }
        pipeline.append(pipeline2)

    order_list = list(order.objects.aggregate(*(pipeline)))
    # print("order_list",len(order_list))
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
    sort_by = request.GET.get('sort_by')
    sort_by_value = request.GET.get('sort_by_value')
    dealer_admin_role_id = DatabaseModel.get_document(role.objects,{"name" : "dealer_admin"},['id']).id

    
    pipeline = [
        {
            "$match" : {
                "manufacture_unit_id" : ObjectId(manufacture_unit_id),
                "role_id" : dealer_admin_role_id,
            }
        },
        {
            "$lookup" :{
                "from" : "address",
                "localField" : "default_address_id",
                "foreignField" : "_id",
                "as" : "address_ins"
            }
        },
        {
        "$unwind": {
            "path": "$address_ins",
            "preserveNullAndEmptyArrays": True
        }
        },
        {
           "$project" :{
                "_id": 0,
                'id': {"$toString" : "$_id"},
                "dealer_id" : 1,
                "username" :  {
                "$concat": [
                    "$first_name",
                    { "$ifNull": ["$last_name", ""] } 
                ]
                },
                "email" : {"$ifNull":["$email",""]},
                "mobile_number" : {"$ifNull":["$mobile_number",""]},
                "company_name" : {"$ifNull":["$company_name",""]},
                "address" : {
                    "street" : "$address_ins.street",
                    "city" : "$address_ins.city",
                    "state" : "$address_ins.state",
                    "country" : "$address_ins.country",
                    "zipCode" : "$address_ins.zipCode"
                },
                "website" : {"$ifNull":["$website",""]},
                "no_of_orders" : "5"
           }
        }
    ]
    if sort_by != None and sort_by != "":
        if sort_by != "no_of_orders":
            pipeline2 = {
                    "$sort": {
                        sort_by: int(sort_by_value)
                    }
                }
            pipeline.append(pipeline2)
            
    else:
        pipeline2 = {
                    "$sort": {
                        "id" : -1
                    }
                }
        pipeline.append(pipeline2)

    dealer_list = list(user.objects.aggregate(*(pipeline)))
    for ins in dealer_list:
        pipeline = [
        {
            "$match": {
                "customer_id": ObjectId(ins['id'])
            }
        },
        {
            "$count": "total_count"
        }
        ]

        no_of_orders_obj = list(order.objects.aggregate(*(pipeline)))
        ins['no_of_orders'] = no_of_orders_obj[0]['total_count'] if no_of_orders_obj else 0
    if dealer_list != [] and sort_by != None and sort_by != "":
        if sort_by == "no_of_orders" and int(sort_by_value) == 1:
            dealer_list = sorted(dealer_list, key=lambda x: x["no_of_orders"])
        elif sort_by == "no_of_orders" and int(sort_by_value) == -1:
            dealer_list = sorted(dealer_list, key=lambda x: x["no_of_orders"], reverse=True)

        
    return dealer_list


@csrf_exempt
def createOrder(request):
    data = dict()
    json_request = JSONParser().parse(request)

    manufacture_unit_id_str = json_request['manufacture_unit_id']
    customer_id = json_request['user_id']
    order_items = json_request['order_items']
    amount = json_request['amount']
    currency = json_request['currency']
    shipping_address_id = json_request['shipping_address_id']
    industry_id_str = json_request.get('industry_id')

    pipeline = [
        {
            "$match" : {
                "_id" : ObjectId(shipping_address_id),
            }
        }, 
        {
           "$project" :{
                "_id": 0,
                "street" : 1,
                "city" : 1,
                "state" : 1,
                "zipCode" : 1,
                "country" : 1
           }
        }
    ]
    address_obj = list(address.objects.aggregate(*(pipeline)))
    shipping_address_obj = DatabaseModel.save_documents(address,address_obj[0])

    pipeline = [
        {
            "$match" : {
                "manufacture_unit_id_str" : manufacture_unit_id_str,
            }
        },
        { "$sort" : { "_id": -1 } },
        { "$limit": 1 }, 
        {
           "$project" :{
                "_id": 0,
                "order_id" : 1
           }
        }
    ]
    orders = list(order.objects.aggregate(*(pipeline)))
    if orders != []:
        order_id = int(orders[0]['order_id']) + 1
    else:
        order_id = 1

    formatted_order_id = f"{order_id:04d}"
    order_items = [ObjectId(ins) for ins in order_items]
    if industry_id_str == None:
        order_obj = DatabaseModel.save_documents(order,{"order_id" : formatted_order_id,"customer_id" : ObjectId(customer_id),"manufacture_unit_id_str" : manufacture_unit_id_str, "amount" : amount, "currency" : currency,"order_items" : order_items,"total_items" : len(order_items), "shipping_address_id" : shipping_address_obj.id})
    else:
        order_obj = DatabaseModel.save_documents(order,{"order_id" : formatted_order_id,"customer_id" : ObjectId(customer_id),"manufacture_unit_id_str" : manufacture_unit_id_str, "amount" : amount, "currency" : currency,"order_items" : order_items,"total_items" : len(order_items), "shipping_address_id" : shipping_address_obj.id,"industry_id_str" : industry_id_str})

    DatabaseModel.update_documents(user_cart_item.objects,{"id__in" : order_items},{"status" : "completed","updated_date" : datetime.now()})
    pipeline = [
        {
            "$match" : {
                "_id" : {"$in" : order_items},
            }
        },
        {
        "$lookup": {
            "from": "product",  
            "localField": "product_id",  
            "foreignField": "_id",  
            "as": "product_ins"  
        }
        },
        {
            "$unwind": {
                "path": "$product_ins",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
           "$project" :{
                "_id": 0,
                "product_id" : 1,
                "quantity" : 1,
                "product_quantity" : "$product_ins.quantity"
           }
        }
    ]
    cart_list = list(user_cart_item.objects.aggregate(*(pipeline)))
    for cart_ins in cart_list:
        balance_quantity = cart_ins['product_quantity'] - cart_ins['quantity']
        availability = True if balance_quantity > 0 else False
        DatabaseModel.update_documents(product.objects,{"id" : cart_ins['product_id']},{"quantity" : balance_quantity,"availability" : availability})

    data['is_created'] = True
    data['order_id'] = str(order_obj.id)  
        
    return data
from user_management.operations.user_operations import getAddressFormat

def obtainUserDetails(request):
    data = dict()
    user_id = request.GET.get('user_id')
    pipeline = [
    {"$match": {"_id": ObjectId(user_id)}},  
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
            "preserveNullAndEmptyArrays": True
        }
    },
    {
        "$project": {
            "_id": 0,
            "id": {"$toString": "$_id"},
            "username": {
                "$concat": [
                    "$first_name",  
                    {"$ifNull": ["$last_name", ""]}  
                ]
            },
            "email": 1, 
            "mobile_number": 1,
            "manufacture_unit_id" : {"$toString" : "$manufacture_unit_id"},
            "address": {
                "address_id" : {"$toString" : "$address_ins._id"},
                "street": "$address_ins.street",
                "city": "$address_ins.city",
                "state": "$address_ins.state",
                "country": "$address_ins.country",
                "zipCode": "$address_ins.zipCode"
            },
            "address_id_list" : {"$ifNull" : ["$address_id_list",[]]}
        }
    }
    ]
    user_obj = list(user.objects.aggregate(*pipeline))
    address_obj_list = []
    if user_obj != []:
        if user_obj[0]['address_id_list'] != []:
            for i in user_obj[0]['address_id_list']:
               address_obj_list.append(getAddressFormat(i))
        del user_obj[0]['address_id_list']
        user_obj[0]['address_obj_list'] = address_obj_list
        data['user_obj'] = user_obj[0]
    else:
        data['user_obj'] = {}
    return data

@csrf_exempt
def obtainOrderListForDealer(request):
    json_request = JSONParser().parse(request)

    user_id = json_request.get('user_id')
    sort_by = json_request.get('sort_by')
    sort_by_value = json_request.get('sort_by_value')

    delivery_status = json_request['delivery_status']
    fulfilled_status = json_request['fulfilled_status']
    payment_status = json_request['payment_status']

    status_match = {}
    status_match['customer_id'] = ObjectId(user_id)
    if delivery_status != "all":
        status_match['delivery_status'] = delivery_status
    if fulfilled_status != "all":
        status_match['fulfilled_status'] = fulfilled_status
    if payment_status != "all":
        status_match['payment_status'] = payment_status

    pipeline = [
    {"$match": status_match},  
    {
        "$project": {
            "_id": 0,
            "id": {"$toString": "$_id"},
            "order_id" : 1,
            "total_items" : 1,
            "order_date" : 1,
            "delivery_status" : 1,
            "fulfilled_status" : 1,
            "payment_status" : 1,
            "amount" : 1,
            "currency" :1
        }
    }
    ]
    if sort_by != None and sort_by != "":
        pipeline2 = {
                "$sort": {
                    sort_by: int(sort_by_value)
                }
            }
    else:
        pipeline2 = {
                "$sort": {
                    "id" : -1
                }
            }
    pipeline.append(pipeline2)   

    order_list = list(order.objects.aggregate(*pipeline))
    return order_list



def getManufactureBankDetails(request):
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
            "role_ins.name" : "manufacturer_admin"
        }
    },
    {
        "$lookup": {
            "from": "bank_details",  
            "localField": "bank_details_id_list",
            "foreignField": "_id", 
            "as": "bank_details_ins" 
        }
    },
    {
        "$unwind": {
            "path": "$bank_details_ins", 
            "preserveNullAndEmptyArrays": True
        }
    },
    {
        "$match": {
            "$or": [
                {"bank_details_ins.is_default": True},
                {"bank_details_ins": {"$eq": None}}
            ]
        }
    },
    {
        "$project": {
            "_id": 0,
            "first_name" : {"$ifNull": ["$first_name", ""]},
            "last_name" : {"$ifNull": ["$last_name", ""]},
            "bank_details": {
                "ifsc_code": {"$ifNull": ["$bank_details_ins.ifsc_code", ""]},
                "iban": {"$ifNull": ["$bank_details_ins.iban", ""]},
                "swift_code": {"$ifNull": ["$bank_details_ins.swift_code", ""]},
                "bank_name": {"$ifNull": ["$bank_details_ins.bank_name", ""]},
                "account_number": {"$ifNull": ["$bank_details_ins.account_number", ""]},
                "branch": {"$ifNull": ["$bank_details_ins.branch", ""]},
                "currency": {"$ifNull": ["$bank_details_ins.currency", ""]},
                "images": {"$ifNull": ["$bank_details_ins.images", []]}
            }
        }
        }
    
    ]
    user_obj = list(user.objects.aggregate(*pipeline))

    if user_obj != []:
        data['user_obj'] = user_obj[0]
    else:
        data['user_obj'] = {}

    return data    


import pytz
from tzlocal import get_localzone

def getLocalTime(current_time):
    # Automatically detect the local timezone
    local_timezone = get_localzone()

    # Convert the UTC time to local time
    local_time = current_time.astimezone(local_timezone)

    # Format the datetime to only show the date and time (without microseconds)
    formatted_time = local_time.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time

from .user_operations import send_email
@csrf_exempt
def conformPayment(request):
    data = dict()
    json_request = JSONParser().parse(request)
    user_id = json_request['user_id']
    order_id = json_request['order_id']
    payment_proof = json_request['payment_proof']
    message = json_request['message']
    transaction_id = json_request['transaction_id']


    order_obj = DatabaseModel.get_document(order.objects,{"id" : order_id},["id",'amount', 'currency','order_id'])
    DatabaseModel.update_documents(order.objects,{"id" : order_id},{"payment_status" : "Paid","updated_date" : datetime.now()})

    total_amount = order_obj.amount
    currency = order_obj.currency
    transaction_obj = {
        "order_id" : order_obj.id,
        "total_amount" : total_amount,
        "currency" : currency,
        "payment_proof" : payment_proof,
        "message" : message,
        "transaction_id" : transaction_id 
    }

    DatabaseModel.save_documents(transaction,transaction_obj)

    user_obj = DatabaseModel.get_document(user.objects,{"id" : user_id},['first_name',"last_name",'email','manufacture_unit_id'])

    payment_under_review_template_obj = DatabaseModel.get_document(mail_template.objects,{"code" : "payment_under_review_template","manufacture_unit_id_str" : str(user_obj.manufacture_unit_id.id)})

    subject = payment_under_review_template_obj.subject

    body = payment_under_review_template_obj.default_template.format(name=user_obj.first_name, order_id=order_obj.order_id)
    
    send_email(user_obj.email, subject, body)

    admin_obj = DatabaseModel.get_document(user.objects,{"manufacture_unit_id" : user_obj.manufacture_unit_id.id,"role_id" : ObjectId('670e3b206569d56ed4d4a759')},['email','first_name'])

    current_time = getLocalTime(datetime.now())

    payment_confirmation_obj = DatabaseModel.get_document(mail_template.objects,{"code" : "payment_notification","manufacture_unit_id_str" : str(user_obj.manufacture_unit_id.id)})

    subject = payment_confirmation_obj.subject.format(order_id=order_obj.order_id)

    body = payment_confirmation_obj.default_template.format(name=admin_obj.first_name,order_id=order_obj.order_id, first_name=user_obj.first_name, transaction_id = transaction_id, total_amount= total_amount, current_time = current_time)
    send_email(admin_obj.email, subject, body)

    
    data['is_saved'] = "Transaction saved SucessFully"
    return data


def getorderDetails(request):
    data = dict()
    order_id = request.GET.get('order_id')
    manufacture_unit_id = request.GET.get('manufacture_unit_id')
    pipeline = [
    {"$match": {"_id": ObjectId(order_id)}},  
    {
        "$lookup": {
            "from": "user",  
            "localField": "customer_id",  
            "foreignField": "_id",  
            "as": "user_ins"  
        }
    },
    {
        "$unwind": {
            "path": "$user_ins",
        }
    },
    {
        "$lookup": {
            "from": "address",  
            "localField": "shipping_address_id",
            "foreignField": "_id", 
            "as": "shipping_address_ins" 
        }
    },
    {
        "$unwind": {
            "path": "$shipping_address_ins", 
            "preserveNullAndEmptyArrays": True
        }
    },
    {
        "$lookup": {
            "from": "transaction",  
            "localField": "_id",
            "foreignField": "order_id", 
            "as": "transaction_ins" 
        }
    },
    {
        "$unwind": {
            "path": "$transaction_ins", 
            "preserveNullAndEmptyArrays": True
        }
    },
    {
        "$project": {
            "_id": 0,
            "id" : {"$toString" : "$_id"},
            "order_id" : 1,
            "payment_status" : 1,
            "delivery_status" : 1,
            "fulfilled_status" : 1,
            "placed_on": {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$creation_date",
                    }
                    },
            "updated": {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$updated_date",
                    }
                    },
            "paid_on": {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$transaction_ins.transaction_date",
                    }
                    },
            "total_amount" : "$amount",
            "currency" : 1,
            "order_items" : 1,
            "total_items" : 1,

            "billing_address": {
                "_id" : {"$toString" : "$shipping_address_ins._id"},
                "street": "$shipping_address_ins.street",
                "city": "$shipping_address_ins.city",
                "state": "$shipping_address_ins.state",
                "country": "$shipping_address_ins.country",
                "zipCode": "$shipping_address_ins.zipCode"
            },
            "name": {
                "$concat": [
                    "$user_ins.first_name",  
                    {"$ifNull": ["$user_ins.last_name", ""]}  
                ]
            },
            "email": "$user_ins.email",
            "mobile_number": {"$ifNull": ["$user_ins.mobile_number",""]},
        }
        }
    
    ]
    order_obj = list(order.objects.aggregate(*pipeline))

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
            "role_ins.name" : "manufacturer_admin"
        }
    },
    {
        "$lookup": {
            "from": "address",  
            "localField": "default_address_id",
            "foreignField": "_id", 
            "as": "shipping_address_ins" 
        }
    },
    {
        "$unwind": {
            "path": "$shipping_address_ins", 
            "preserveNullAndEmptyArrays": True
        }
    },
    {
        "$project": {
            "_id": 0,
            "shipping_address": {
                "_id" : {"$toString" : "$shipping_address_ins._id"},
                "street": "$shipping_address_ins.street",
                "city": "$shipping_address_ins.city",
                "state": "$shipping_address_ins.state",
                "country": "$shipping_address_ins.country",
                "zipCode": "$shipping_address_ins.zipCode"
            },
        }
        }
    
    ]
    billing_address_obj = list(user.objects.aggregate(*pipeline))
    if billing_address_obj != []:
        order_obj[0]['shipping_address'] = billing_address_obj[0]
    else:
        order_obj[0]['shipping_address'] = {}
    pipeline =[
        {
            "$match" : {
                "_id" : {"$in" : order_obj[0]['order_items']}
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
        "$project" :{
                "_id": 0,
                "product_name" : "$products_ins.product_name",
                "primary_image" : {"$first":"$products_ins.images"},
                "sku_number" : "$products_ins.sku_number_product_code_item_number",
                "mpn_number" : "$products_ins.mpn",
                "brand_name" : "$products_ins.brand_name",
                "price" : {"$ifNull" : ["$unit_price",0.0]},
                "currency" : "$products_ins.currency",
                "quantity" : 1,
                "total_price" : "$price"
        }
        }
    ]
    user_cart_item_list = list(user_cart_item.objects.aggregate(*(pipeline)))
    order_obj[0]['product_list'] = user_cart_item_list

    del order_obj[0]['order_items']

    data['order_obj'] = order_obj[0]
    return data



def acceptOrRejectOrder(request):
    data = dict()
    order_id = request.GET.get('order_id')
    user_id = request.GET.get('user_id')
    status = request.GET.get('status').lower()


    pipeline =[
        {
            "$match" : {
                "_id" : ObjectId(user_id)
            }
        },
        {
        "$project" :{
                "_id": 0,
                "name" : {
                "$concat": [
                    "$first_name",
                    { "$ifNull": ["$last_name", ""] } 
                ]
                },
                "email" : "$email",
                "company_name" : {"$ifNull" : ['$company_name',""]},
                "mobile_number" : {"$ifNull" : ['$mobile_number',""]},
                "manufacture_unit_id" : {"$toString" : "$manufacture_unit_id"}
                

        }
        }
    ]
    admin_user_obj = list(user.objects.aggregate(*(pipeline)))

    pipeline =[
        {
            "$match" : {
                "_id" : ObjectId(order_id)
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
                "order_id" : "$order_id",
                "name" : {
                "$concat": [
                    "$user_ins.first_name",
                    { "$ifNull": ["$user_ins.last_name", ""] } 
                ]
                },
                "email" : "$user_ins.email",
                "amount" : {"$concat":[{"$toString":"$amount"},"$currency"]}
        }
        }
    ]
    order_user_obj = list(order.objects.aggregate(*(pipeline)))
    if status == "accept":
        
        # Start a new thread to call createOrUpdateTopSellings
        threading.Thread(target=createOrUpdateTopSellings, args=(order_id,)).start()

        payment_status = "Completed"

        payment_confirmation_obj = DatabaseModel.get_document(mail_template.objects,{"code" : "payment_confirmation","manufacture_unit_id_str" : admin_user_obj[0]['manufacture_unit_id']})

        subject = payment_confirmation_obj.subject.format(order_id=order_user_obj[0]['order_id'])

        body = payment_confirmation_obj.default_template.format(order_id=order_user_obj[0]['order_id'],dealer_name=order_user_obj[0]['name'],amount=order_user_obj[0]['amount'],date=getLocalTime(datetime.now()),your_company_name=admin_user_obj[0]['company_name'],your_mobile_number=admin_user_obj[0]['mobile_number'],your_name=admin_user_obj[0]['name'],your_mail=admin_user_obj[0]['email'])
        
    else:
        payment_status = "Failed"

        payment_rejection_obj = DatabaseModel.get_document(mail_template.objects,{"code" : "payment_rejection","manufacture_unit_id_str" : admin_user_obj[0]['manufacture_unit_id']})

        subject = payment_rejection_obj.subject.format(order_id=order_user_obj[0]['order_id'])

        body = payment_rejection_obj.default_template.format(order_id=order_user_obj[0]['order_id'],dealer_name=order_user_obj[0]['name'],your_company_name=admin_user_obj[0]['company_name'],your_mobile_number=admin_user_obj[0]['mobile_number'],your_name=admin_user_obj[0]['name'],your_mail=admin_user_obj[0]['email'])

    send_email(order_user_obj[0]['email'], subject, body)


    
    DatabaseModel.update_documents(order.objects,{"id" : order_id},{"payment_status" : payment_status,"updated_date" : datetime.now()})
    data['is_action'] = "Mail sended SuccessFully"
    return data


def createOrUpdateTopSellingProduct(product_id, product_name, brand_name, category_name, quantity, total_price, manufacture_unit_id):
    top_selling_product_obj = DatabaseModel.get_document(top_selling_product.objects,{"product_name" : product_name},['id'])

    if top_selling_product_obj != None:
        top_selling_product_id = top_selling_product_obj.id
        DatabaseModel.update_documents(top_selling_product.objects,{"id" : top_selling_product_id},{"inc__total_sales" : total_price,"inc__units_sold" : quantity, "last_updated" : datetime.now()})
    else:
        new_top_selling_product_obj = DatabaseModel.save_documents(top_selling_product,{"product_id" : product_id, "product_name" : product_name, "category_name" : category_name, "brand_name" :brand_name, "total_sales" : total_price, "units_sold" :quantity, "manufacture_unit_id_str" : str(manufacture_unit_id)})
        top_selling_product_id = new_top_selling_product_obj.id
    return top_selling_product_id


def createOrUpdateTopSellingBrand(top_selling_product_id, brand_id, brand_name, category_name, quantity, total_price, manufacture_unit_id):
    top_selling_brand_obj = DatabaseModel.get_document(top_selling_brand.objects,{"brand_name" : brand_name},['id'])

    if top_selling_brand_obj != None:
        top_selling_brand_id = top_selling_brand_obj.id
        DatabaseModel.update_documents(top_selling_brand.objects,{"id" : top_selling_brand_id},{"inc__total_sales" : total_price,"inc__units_sold" : quantity, "last_updated" : datetime.now(),"add_to_set__products_sold" : top_selling_brand_id})
    else:
        new_top_selling_brand_obj = DatabaseModel.save_documents(top_selling_brand,{"brand_id" : brand_id, "products_sold" : [top_selling_product_id], "category_name" : category_name, "brand_name" :brand_name, "total_sales" : total_price, "units_sold" :quantity, "manufacture_unit_id_str" : str(manufacture_unit_id)})
        top_selling_brand_id = new_top_selling_brand_obj.id
    return top_selling_brand_id


def createOrUpdateTopSellingCategory(top_selling_product_id, top_selling_brand_id, category_id, category_name, quantity, total_price, manufacture_unit_id):
    top_selling_category_obj = DatabaseModel.get_document(top_selling_category.objects,{"category_name" : category_name},['id'])

    if top_selling_category_obj != None:
        top_selling_category_id = top_selling_category_obj.id
        DatabaseModel.update_documents(top_selling_category.objects,{"id" : top_selling_category_id},{"inc__total_sales" : total_price,"inc__units_sold" : quantity, "last_updated" : datetime.now(),"add_to_set__top_products" : top_selling_product_id, "add_to_set__top_brands" : top_selling_brand_id})
    else:
        new_top_selling_category_obj = DatabaseModel.save_documents(top_selling_category,{"category_id" : category_id, "category_name" : category_name, "top_products" : [top_selling_product_id], "top_brands" :[top_selling_brand_id], "total_sales" : total_price, "units_sold" :quantity, "manufacture_unit_id_str" : str(manufacture_unit_id)})
        top_selling_category_id = new_top_selling_category_obj.id
    return top_selling_category_id



def createOrUpdateTopSellings(order_id):
    pipeline =[
        {
            "$match" : {
                "_id" : ObjectId(order_id)
            }
        },
        {
            "$lookup" :{
                "from" : "user_cart_item",
                "localField" : "order_items",
                "foreignField" : "_id",
                "as" : "user_cart_item_ins"
            }
        },
        {"$unwind" : "$user_cart_item_ins"},
        {
            "$lookup" :{
                "from" : "product",
                "localField" : "user_cart_item_ins.product_id",
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
        {
            "$lookup" :{
                "from" : "product_category",
                "localField" : "products_ins.category_id",
                "foreignField" : "_id",
                "as" : "category_ins"
            }
        },
        {"$unwind" : "$category_ins"},
        {
        "$project" :{
                "_id": 0,
                "product_id" : "$products_ins._id",
                "product_name" : "$products_ins.product_name",

                "brand_id" : "$brand_ins._id",
                "brand_name" : "$brand_ins.name",

                "category_id" : "$category_ins._id",
                "category_name" : "$category_ins.name",

                "currency" : "$products_ins.currency",
                "quantity" : "$user_cart_item_ins.quantity",
                "total_price" : "$user_cart_item_ins.price",

                "manufacture_unit_id" : "$products_ins.manufacture_unit_id"
        }
        }
    ]
    user_cart_item_list = list(order.objects.aggregate(*(pipeline)))
    
    for ins in user_cart_item_list:
        
        top_selling_product_id = createOrUpdateTopSellingProduct(ins['product_id'], ins['product_name'], ins['brand_name'], ins['category_name'], ins['quantity'], ins['total_price'],ins['manufacture_unit_id'])

        top_selling_brand_id = createOrUpdateTopSellingBrand(top_selling_product_id, ins['brand_id'], ins['brand_name'], ins['category_name'], ins['quantity'], ins['total_price'],ins['manufacture_unit_id'])

        top_selling_category_id = createOrUpdateTopSellingCategory(top_selling_product_id, top_selling_brand_id, ins['category_id'], ins['category_name'], ins['quantity'], ins['total_price'],ins['manufacture_unit_id'])

    return True


@csrf_exempt
def updateOrder(request):
    json_request = JSONParser().parse(request)
    data = dict()
    data['is_updated'] = False
    order_obj = DatabaseModel.get_document(order.objects,{"id" : json_request['update_onj']['id']},['id'])
    if order_obj != None:
        del json_request['update_onj']['id']
        data['is_updated'] = DatabaseModel.update_documents(order.objects,{"id" : order_obj.id},json_request['update_onj'])
    return data
