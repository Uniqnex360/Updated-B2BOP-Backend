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
from user_management.operations.user_operations import getAddressFormat
import pytz
from tzlocal import get_localzone
import requests
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.parsers import JSONParser
from bson import ObjectId
from user_management.models import user
from b2bop_project.crud import DatabaseModel
from bson import ObjectId
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.parsers import JSONParser
from bson import ObjectId
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from rest_framework.parsers import JSONParser

def getLocalTime(current_time):
    # Automatically detect the local timezone
    local_timezone = get_localzone()

    # Convert the UTC time to local time
    local_time = current_time.astimezone(local_timezone)

    # Format the datetime to only show the date and time (without microseconds)
    formatted_time = local_time.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


#create0r update user cart item

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
    start_date_str = json_request.get('start_date')
    end_date_str = json_request.get('end_date')
    sort_by_value = json_request['sort_by_value']
    dealer_list = json_request.get('dealer_list')
    delivery_status = json_request['delivery_status']
    fulfilled_status = json_request['fulfilled_status']
    payment_status = json_request['payment_status']
    industry_id_str = json_request.get('industry_id')
    is_reorder = json_request.get('is_reorder')

    status_match = {}
    status_match['manufacture_unit_id_str'] = manufacture_unit_id
    if delivery_status != "all":
        status_match['delivery_status'] = delivery_status
    if fulfilled_status != "all":
        status_match['fulfilled_status'] = fulfilled_status
    if payment_status != "all":
        status_match['payment_status'] = payment_status
    if industry_id_str is not None:
        status_match['industry_id_str'] = industry_id_str
    if is_reorder is not None and is_reorder != "" and is_reorder != "all":
        is_reorder = is_reorder.lower()
        if is_reorder == "yes":
            status_match['is_reorder'] = True
        elif is_reorder == "no":
            status_match['is_reorder'] = False

    pipeline = [
        {
            "$match": status_match
        },
        {
            "$lookup": {
                "from": "user",
                "localField": "customer_id",
                "foreignField": "_id",
                "as": "user_ins"
            }
        },
        {"$unwind": "$user_ins"}
    ]

    if dealer_list is not None and dealer_list != []:
        dealer_list = [ObjectId(ins) for ins in dealer_list]
        dealer_search_obj = {
            "$match": {
                "user_ins._id": {"$in": dealer_list}
            }
        }
        pipeline.append(dealer_search_obj)

    if start_date_str is not None and start_date_str != "":
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        local_timezone = datetime.now().astimezone().tzinfo

        start_of_day = start_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(local_timezone)
        if end_date_str is not None and end_date_str != "":
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_of_day = end_date.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(local_timezone)
        else:
            end_of_day = start_date.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(local_timezone)

        start_of_day_utc = start_of_day.astimezone(pytz.utc)
        end_of_day_utc = end_of_day.astimezone(pytz.utc)
        date_search_obj = {
            "$match": {
                "creation_date": {
                    "$gte": start_of_day_utc,
                    "$lte": end_of_day_utc
                }
            }
        }
        pipeline.append(date_search_obj)

    project_obj = [
        {
            "$lookup": {
                "from": "address",
                "localField": "shipping_address_id",
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
                "_id": {"$toString": "$_id"},
                "order_id": 1,
                "dealer_name": {
                    "$concat": [
                        "$user_ins.first_name",
                        {
                            "$cond": {
                                "if": {"$ne": ["$user_ins.last_name", None]},
                                "then": " ",
                                "else": ""
                            }
                        },
                        {"$ifNull": ["$user_ins.last_name", ""]}
                    ]
                },
                "total_items": 1,
                "amount": 1,
                "currency": 1,
                "shipping_service": "-",
                "tracking_code": "-",
                "creation_date": {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$creation_date",
                    }
                },
                "address": {
                    "street": "$address_ins.street",
                    "city": "$address_ins.city",
                    "state": "$address_ins.state",
                    "country": "$address_ins.country",
                    "zipCode": "$address_ins.zipCode"
                },
                "delivery_status": 1,
                "fulfilled_status": 1,
                "payment_status": 1,
                "is_reorder": 1
            }
        }
    ]
    pipeline.extend(project_obj)

    # 🔍 Updated search filter
    if search_query != "":
        search_obj = {
            "$match": {
                "$or": [
                    {"dealer_name": {"$regex": search_query, "$options": "i"}},
                    {"order_id": {"$regex": search_query, "$options": "i"}},
                    {"address.city": {"$regex": search_query, "$options": "i"}},
                    {"address.country": {"$regex": search_query, "$options": "i"}},
                    {"delivery_status": {"$regex": search_query, "$options": "i"}},
                    {"payment_status": {"$regex": search_query, "$options": "i"}}
                ]
            }
        }
        pipeline.append(search_obj)

    if sort_by != "":
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

    order_list = list(order.objects.aggregate(*pipeline))
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
                "#Order Id" : {"$toString" : "$_id"},
                "Dealer Name" : {
                    "$concat": [
                        "$user_ins.first_name",
                        { 
                        "$cond": {
                            "if": { "$ne": ["$user_ins.last_name", None] },  
                            "then": " ",                             
                            "else": ""                               
                        }
                        },
                        { "$ifNull": ["$user_ins.last_name", ""] }        
                    ]
                },
                "Order Value" : {"$concat": [{"$toString": "$amount"},"$currency"]},
                "Shipping Service" : "-",
                "Tracking Code" : "-",
                "Order Date": {
                    "$dateToString": {
                        "format": "%Y-%m-%dT%H:%M:%S.%LZ",
                        "date": "$creation_date",
                    }
                    },
                "Delivery Status" : "$delivery_status",
                "Fulfilled Status" : "$fulfilled_status",
                "Payment Status" : "$payment_status"
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
                    { 
                    "$cond": {
                        "if": { "$ne": ["$last_name", None] },  
                        "then": " ",                             
                        "else": ""                               
                    }
                    },
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
def editDealerDetails(request):
    if request.method != "PATCH":
        return JsonResponse({"status": False, "message": "Only PATCH allowed"}, status=405)

    try:
        json_request = JSONParser().parse(request)

        dealer_id = json_request.get("dealer_id")
        _id = json_request.get("_id")

        if not dealer_id and not _id:
            return JsonResponse({"status": False, "message": "Either dealer_id or _id is required"}, status=400)

        # Prepare fields to update
        update_fields = {}
        for field in ["email", "mobile_number", "company_name"]:
            if field in json_request:
                update_fields[field] = json_request[field]

        if "username" in json_request:
            name_parts = json_request["username"].strip().split(" ", 1)
            update_fields["first_name"] = name_parts[0]
            update_fields["last_name"] = name_parts[1] if len(name_parts) > 1 else ""

        if not update_fields:
            return JsonResponse({"status": False, "message": "No valid fields to update"}, status=400)

        # Correct filter condition for MongoEngine
        if _id:
            filter_query = {"id": ObjectId(_id)}
        else:
            # dealer_id is an integer, not ObjectId
            filter_query = {"dealer_id": int(dealer_id)}

        # Update
        updated = DatabaseModel.update_documents(user.objects, filter_query, update_fields)

        if updated:
            return JsonResponse({"status": True, "message": "Dealer updated successfully"})
        else:
            return JsonResponse({"status": False, "message": "Dealer not found"}, status=404)

    except Exception as e:
        return JsonResponse({"status": False, "message": str(e)}, status=500)

@csrf_exempt
def deleteDealerDetails(request):
    if request.method != "DELETE":
        return JsonResponse({"status": False, "message": "Only DELETE allowed"}, status=405)

    try:
        json_request = JSONParser().parse(request)
        dealer_id = json_request.get("dealer_id")
        _id = json_request.get("_id")

        if not dealer_id and not _id:
            return JsonResponse({"status": False, "message": "Either dealer_id or _id is required"}, status=400)

        # Build filter
        if _id:
            filter_query = {"id": ObjectId(_id)}
        else:
            filter_query = {"dealer_id": int(dealer_id)}

        deleted = DatabaseModel.delete_documents(user.objects, filter_query)

        if deleted:
            return JsonResponse({"status": True, "message": "Dealer deleted successfully"})
        else:
            return JsonResponse({"status": False, "message": "Dealer not found"}, status=404)

    except Exception as e:
        return JsonResponse({"status": False, "message": str(e)}, status=500)

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
    sendMailWhenOrderPlaced(customer_id,order_obj)
    data['is_created'] = True
    data['order_id'] = str(order_obj.id)  
        
    return data


def sendMailWhenOrderPlaced(user_id, order_obj):
    #*Items Ordered: {items_list}
    
    user_obj = DatabaseModel.get_document(user.objects,{"id" : user_id},['first_name',"last_name",'email','manufacture_unit_id'])

    manufacturer_admin_role_id = DatabaseModel.get_document(role.objects,{"name" : "manufacturer_admin"},['id']).id


    admin_obj = DatabaseModel.get_document(user.objects,{"manufacture_unit_id" : user_obj.manufacture_unit_id.id,"role_id" : manufacturer_admin_role_id},['email','first_name','last_name'])

    current_time = getLocalTime(datetime.now())

    new_order_placed_template_obj = DatabaseModel.get_document(mail_template.objects,{"code" : "new_order_placed","manufacture_unit_id_str" : str(user_obj.manufacture_unit_id.id)})

    subject = new_order_placed_template_obj.subject.format(order_id=order_obj.order_id)

    body = new_order_placed_template_obj.default_template.format(seller_name=f"{admin_obj.first_name} {admin_obj.last_name or ''}".strip(), order_id=order_obj.order_id, buyer_name=f"{user_obj.first_name} {user_obj.last_name or ''}".strip(),total_amount=order_obj.amount,order_date=current_time,currency=order_obj.currency)
    
    send_email(admin_obj.email, subject, body)




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
                    { 
                    "$cond": {
                        "if": { "$ne": ["$last_name", None] },  
                        "then": " ",                             
                        "else": ""                               
                    }
                    },
                    { "$ifNull": ["$last_name", ""] }        
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
    is_reorder = json_request.get('is_reorder')
    start_date_str = json_request.get('start_date')
    end_date_str = json_request.get('end_date')

    status_match = {}
    status_match['customer_id'] = ObjectId(user_id)
    if delivery_status != "all":
        status_match['delivery_status'] = delivery_status
    if fulfilled_status != "all":
        status_match['fulfilled_status'] = fulfilled_status
    if payment_status != "all":
        status_match['payment_status'] = payment_status
    if is_reorder != None and is_reorder != "" and is_reorder != "all":
        is_reorder = is_reorder.lower()
        if is_reorder == "yes":
            status_match['is_reorder'] = True
        elif is_reorder == "no":
            status_match['is_reorder'] = False
    if start_date_str != None and start_date_str != "":
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

        # Get the system's local timezone dynamically
        local_timezone = datetime.now().astimezone().tzinfo

        # Localize start and end of the day to the local timezone
        start_of_day = start_date.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(local_timezone)
        if end_date_str != None and end_date_str != "":
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_of_day = end_date.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(local_timezone)
        else:
            end_of_day = start_date.replace(hour=23, minute=59, second=59, microsecond=999999).astimezone(local_timezone)

        # Convert to UTC for MongoDB query
        start_of_day_utc = start_of_day.astimezone(pytz.utc)
        end_of_day_utc = end_of_day.astimezone(pytz.utc)
        status_match["creation_date"] =  {
                                "$gte": start_of_day_utc,
                                "$lte": end_of_day_utc 
                                 }

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
            "currency" :1,
            "is_reorder" : 1
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

    body = payment_under_review_template_obj.default_template.format(name=f"{user_obj.first_name} {user_obj.last_name or ''}".strip(), order_id=order_obj.order_id)
    
    send_email(user_obj.email, subject, body)

    manufacturer_admin_role_id = DatabaseModel.get_document(role.objects,{"name" : "manufacturer_admin"},['id']).id


    admin_obj = DatabaseModel.get_document(user.objects,{"manufacture_unit_id" : user_obj.manufacture_unit_id.id,"role_id" : manufacturer_admin_role_id},['email','first_name','last_name'])





    current_time = getLocalTime(datetime.now())

    payment_confirmation_obj = DatabaseModel.get_document(mail_template.objects,{"code" : "payment_notification","manufacture_unit_id_str" : str(user_obj.manufacture_unit_id.id)})

    subject = payment_confirmation_obj.subject.format(order_id=order_obj.order_id)

    body = payment_confirmation_obj.default_template.format(name=f"{admin_obj.first_name} {admin_obj.last_name or ''}".strip(),order_id=order_obj.order_id, first_name=user_obj.first_name, transaction_id = transaction_id, total_amount= total_amount, current_time = current_time)
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
                { 
                "$cond": {
                    "if": { "$ne": ["$user_ins.last_name", None] },  
                    "then": " ",                             
                    "else": ""                               
                }
                },
                { "$ifNull": ["$user_ins.last_name", ""] }
            ]
            },
            "email": "$user_ins.email",
            "mobile_number": {"$ifNull": ["$user_ins.mobile_number",""]},
            "profile_image" : {"$ifNull" : ['$user_ins.profile_image',""]}
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
                "id" : {"$toString" : "$_id"},
                "product_id" : {"$toString" : "$product_id"},
                "product_name" : "$products_ins.product_name",
                "primary_image" : {"$first":"$products_ins.images"},
                "sku_number" : "$products_ins.sku_number_product_code_item_number",
                "mpn_number" : "$products_ins.mpn",
                "brand_name" : "$products_ins.brand_name",
                "price" : {"$ifNull" : ["$unit_price",0.0]},
                "currency" : "$products_ins.currency",
                "quantity" : 1,
                "total_price" : "$price",
                "product_status" : 1
        }
        }
    ]
    user_cart_item_list = list(user_cart_item.objects.aggregate(*(pipeline)))
    order_obj[0]['product_list'] = user_cart_item_list
    transaction_list = list()
    if order_obj[0]['payment_status'] != "Pending":
        pipeline =[
        {
            "$match" : {
                "order_id" : ObjectId(order_id)
            }
        },
        {
        "$project" :{
                "_id": 0,
                "id" : {"$toString" : "$_id"},
                "status" : 1,
                "payment_proof" : 1,
                "transaction_date" : 1,
                "updated_date" : 1,
                "message" : {"$ifNull" : ["$message",""]},
                "transaction_id" : 1
        }
        },
        {
            "$sort" : {
                "id" : -1
            }
        }
        ]
        transaction_list = list(transaction.objects.aggregate(*(pipeline)))

    order_obj[0]['transaction_list'] = transaction_list
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
                    { 
                    "$cond": {
                        "if": { "$ne": ["$last_name", None] },  
                        "then": " ",                             
                        "else": ""                               
                    }
                    },
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
                "creation_date" : "$creation_date",
                "name" : {
                "$concat": [
                    "$user_ins.first_name",
                    { 
                    "$cond": {
                        "if": { "$ne": ["$user_ins.last_name", None] },  
                        "then": " ",                             
                        "else": ""                               
                    }
                    },
                    { "$ifNull": ["$user_ins.last_name", ""] }        
                ]
                },
                "email" : "$user_ins.email",
                "amount" : {"$concat":[{"$toString":"$amount"},"$currency"]}
        }
        }
    ]
    order_user_obj = list(order.objects.aggregate(*(pipeline)))
    transaction_pipeline =[
        {
            "$match" : {
                "order_id" : ObjectId(order_id)
            }
        },
        {
        "$project" :{
                "_id": 1,
        }
        },
        {
            "$sort" : {
                "_id" : -1
            }
        }
    ]
    transaction_obj = list(transaction.objects.aggregate(*(transaction_pipeline)))
    if status == "accept":
        
        # Start a new thread to call createOrUpdateTopSellings
        threading.Thread(target=createOrUpdateTopSellings, args=(order_id,)).start()

        payment_status = "Completed"

        payment_confirmation_obj = DatabaseModel.get_document(mail_template.objects,{"code" : "payment_confirmation","manufacture_unit_id_str" : admin_user_obj[0]['manufacture_unit_id']})

        subject = payment_confirmation_obj.subject.format(order_id=order_user_obj[0]['order_id'])

        body = payment_confirmation_obj.default_template.format(order_id=order_user_obj[0]['order_id'],dealer_name=order_user_obj[0]['name'],amount=order_user_obj[0]['amount'],date=getLocalTime(datetime.now()),your_company_name=admin_user_obj[0]['company_name'],your_mobile_number=admin_user_obj[0]['mobile_number'],your_name=admin_user_obj[0]['name'],your_mail=admin_user_obj[0]['email'])
        
        DatabaseModel.update_documents(order.objects,{"id" : order_id},{"payment_status" : payment_status,"updated_date" : datetime.now()})

        DatabaseModel.update_documents(transaction.objects,{"id" : transaction_obj[0]['_id']},{"status" : payment_status,"updated_date" : datetime.now()})
        
    elif status == "reject":
        payment_status = "Failed"

        payment_rejection_obj = DatabaseModel.get_document(mail_template.objects,{"code" : "payment_rejection","manufacture_unit_id_str" : admin_user_obj[0]['manufacture_unit_id']})

        subject = payment_rejection_obj.subject.format(order_id=order_user_obj[0]['order_id'])

        body = payment_rejection_obj.default_template.format(order_id=order_user_obj[0]['order_id'],dealer_name=order_user_obj[0]['name'],your_company_name=admin_user_obj[0]['company_name'],your_mobile_number=admin_user_obj[0]['mobile_number'],your_name=admin_user_obj[0]['name'],your_mail=admin_user_obj[0]['email'])

        DatabaseModel.update_documents(order.objects,{"id" : order_id},{"payment_status" : payment_status,"updated_date" : datetime.now()})
        DatabaseModel.update_documents(transaction.objects,{"id" : transaction_obj[0]['_id']},{"status" : payment_status,"updated_date" : datetime.now()})

    elif status == "fulfilled" or status == "unfulfilled" or status == "partially fulfilled":
        if status == "fulfilled":
            fulfilled_status = "Fulfilled"
            status_message_obj = DatabaseModel.get_document(status_message.objects,{"code" : "fulfilled"},['message']).message
        elif status == "fulfilled":
            fulfilled_status = "Unfulfilled"
            status_message_obj = DatabaseModel.get_document(status_message.objects,{"code" : "unfulfilled"},['message']).message
        elif status == "fulfilled":
            fulfilled_status = "Partially Fulfilled"
            status_message_obj = DatabaseModel.get_document(status_message.objects,{"code" : "partially_fulfilled"},['message']).message   

        fullfillment_status_obj = DatabaseModel.get_document(mail_template.objects,{"code" : "fulfillment_status"})

        subject = fullfillment_status_obj.subject.format(order_id=order_user_obj[0]['order_id'])

        body = fullfillment_status_obj.default_template.format(order_id=order_user_obj[0]['order_id'],dealer_name=order_user_obj[0]['name'],order_date=getLocalTime(order_user_obj[0]['creation_date']),fulfillment_status = fulfilled_status,status_message = status_message_obj, your_company_name=admin_user_obj[0]['company_name'],your_mobile_number=admin_user_obj[0]['mobile_number'],your_name=admin_user_obj[0]['name'],your_mail=admin_user_obj[0]['email'])

        DatabaseModel.update_documents(order.objects,{"id" : order_id},{"fulfilled_status" : fulfilled_status,"updated_date" : datetime.now()})

    send_email(order_user_obj[0]['email'], subject, body)


    
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
def createWishList(request):
    data = dict()
    try:
        json_request = JSONParser().parse(request)
        user_id = json_request.get('user_id')
        product_id = json_request.get('product_id')

        if not user_id or not product_id:
            return JsonResponse({"message": "user_id and product_id are required", "status": False, "data": []})

        # Convert to ObjectId
        user_obj_id = ObjectId(user_id)
        product_obj_id = ObjectId(product_id)

        # Check if wishlist entry exists
        wishlist_obj = wishlist.objects(user_id=user_obj_id, product_id=product_obj_id).first()

        if not wishlist_obj:
            # Create wishlist entry
            wishlist_obj = wishlist(user_id=user_obj_id, product_id=product_obj_id)
            wishlist_obj.save()
            data['is_created'] = True
        else:
            # Update timestamp if already exists
            wishlist_obj.update(set__updated_at=datetime.utcnow())
            data['is_updated'] = True

        data['wishlist_id'] = str(wishlist_obj.id)
        data['message'] = "Wishlist updated successfully"
        data['status'] = True
        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({"message": str(e), "status": False, "data": []})


def deleteWishlist(request):
    data = dict()
    wish_list_id = request.GET.get('wish_list_id')
    DatabaseModel.delete_documents(wishlist.objects,{"id" : wish_list_id})
    data['is_deleted'] = True
    return data



def obtainWishlistForBuyer(request):
    try:
        user_id = request.GET.get('user_id')
        search_query = request.GET.get('search', '').strip()

        if not user_id:
            return JsonResponse({"data": [], "message": "user_id is required", "status": False})

        try:
            user_obj_id = ObjectId(user_id)
        except:
            user_obj_id = None

        # Base match stage
        match_stage = {
            "$match": {
                "$expr": {
                    "$or": [
                        {"$eq": ["$user_id", user_obj_id]} if user_obj_id else {"$eq": ["$user_id", ""]},
                        {"$eq": ["$user_id", user_id]}
                    ]
                }
            }
        }

        # Base pipeline (all wishlist)
        base_pipeline = [
            match_stage,
            {"$lookup": {
                "from": "product",
                "let": {"pid": "$product_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$or": [
                                    {"$eq": ["$_id", "$$pid"]},
                                    {"$eq": [{"$toString": "$_id"}, "$$pid"]}
                                ]
                            }
                        }
                    }
                ],
                "as": "product_ins"
            }},
            {"$unwind": "$product_ins"},
            {
                "$project": {
                    "_id": 0,
                    "id": {"$toString": "$_id"},
                    "product_id": {"$toString": "$product_ins._id"},
                    "name": "$product_ins.product_name",
                    "price": {"$ifNull": ["$product_ins.list_price", 0.0]},
                    "currency": "$product_ins.currency",
                    "primary_image": {"$first": "$product_ins.images"},
                    "sku_number": "$product_ins.sku_number_product_code_item_number",
                    "mpn_number": "$product_ins.mpn",
                    "brand_name": "$product_ins.brand_name",
                    "availability": "$product_ins.availability",
                    "was_price": "$product_ins.was_price",
                    "discount": "$product_ins.discount",
                    "msrp": "$product_ins.msrp"
                }
            }
        ]

        # If search query exists, build search pipeline
        if search_query:
            search_pipeline = base_pipeline[:-1] + [  # keep all stages except projection for now
                {
                    "$match": {
                        "$or": [
                            {"product_ins.product_name": {"$regex": search_query, "$options": "i"}},
                            {"product_ins.brand_name": {"$regex": search_query, "$options": "i"}}
                        ]
                    }
                },
                base_pipeline[-1]  # add projection
            ]
            wish_list = list(wishlist.objects.aggregate(*search_pipeline))

            # If search returns empty, fallback to base pipeline (all products)
            if not wish_list:
                wish_list = list(wishlist.objects.aggregate(*base_pipeline))
        else:
            wish_list = list(wishlist.objects.aggregate(*base_pipeline))

        # Fetch cart items
        cart_items_cursor = user_cart_item.objects(
            user_id=user_obj_id if user_obj_id else user_id,
            status="Pending"
        ).only('product_id')
        cart_product_ids = set(str(item.product_id) for item in cart_items_cursor)

        # Mark in_cart
        for item in wish_list:
            item['in_cart'] = item['product_id'] in cart_product_ids

        return JsonResponse({"data": wish_list, "message": "success", "status": True})

    except Exception as e:
        return JsonResponse({"data": [], "message": str(e), "status": False})




@csrf_exempt
def moveCartItemsToWishlist(request):
    data = dict()
    try:
        json_request = JSONParser().parse(request)
        user_id = json_request.get("user_id")
        product_id = json_request.get("product_id")

        if not user_id or not product_id:
            return JsonResponse({"message": "user_id and product_id are required", "status": False, "data": []})

        user_obj_id = ObjectId(user_id)
        product_obj_id = ObjectId(product_id)

        # Check pending cart item
        cart_item = user_cart_item.objects(
            user_id=user_obj_id,
            product_id=product_obj_id,
            status="Pending"
        ).first()

        if not cart_item:
            return JsonResponse({"message": "No pending cart item found", "status": True, "data": []})

        # Check if already in wishlist
        wishlist_obj = wishlist.objects(user_id=user_obj_id, product_id=product_obj_id).first()
        if not wishlist_obj:
            wishlist_obj = wishlist(user_id=user_obj_id, product_id=product_obj_id)
            wishlist_obj.save()
            message = "Cart item moved to wishlist successfully"
        else:
            wishlist_obj.update(set__updated_at=datetime.utcnow())
            message = "Cart item already in wishlist; timestamp updated"

        # Remove cart item
        cart_item.delete()

        data["message"] = message
        data["status"] = True
        data["data"] = []
        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({"message": str(e), "status": False, "data": []})



@csrf_exempt
def createReorder(request):
    data = dict()
    json_request = JSONParser().parse(request)

    shipping_address_id = json_request.get('shipping_address_id')
    order_id = json_request['order_id']

    pipeline = [
        {
            "$match" : {
                "_id" : ObjectId(order_id),
            }
        }, 
        {
           "$project" :{
                "_id": 0,
                "manufacture_unit_id_str" : 1,
                "customer_id" : 1,
                "order_items" : 1,
                "currency" : 1,
                "industry_id_str" : {"$ifNull":['industry_id_str',""]}
           }
        }
    ]
    old_order_obj = list(order.objects.aggregate(*(pipeline)))
    old_order_obj = old_order_obj[0]

    manufacture_unit_id_str = old_order_obj['manufacture_unit_id_str']
    customer_id = old_order_obj['customer_id']
    currency = old_order_obj['currency']
    industry_id_str = old_order_obj['industry_id_str']
    order_items = old_order_obj['order_items']

    new_order_items = list()
    amount = 0

    for old_cart_ins in order_items:
        pipeline = [
        {
            "$match" : {
                "_id" : old_cart_ins,
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
                "price" : "$product_ins.list_price"
                
           }
        }
        ]
        cart_list = list(user_cart_item.objects.aggregate(*(pipeline)))

        cart_save_obj = dict()
        cart_save_obj['unit_price'] = cart_list[0]['price']
        cart_save_obj['price'] = cart_list[0]['price'] * cart_list[0]['quantity']
        cart_save_obj['status'] = "Completed"
        cart_save_obj['quantity'] = cart_list[0]['quantity']
        cart_save_obj['product_id'] = cart_list[0]['product_id']
        cart_save_obj['user_id'] = customer_id

        new_cart_obj = DatabaseModel.save_documents(user_cart_item,cart_save_obj)
        new_order_items.append(new_cart_obj.id)
        
        amount += cart_save_obj['price']


    pipeline = [
        {
            "$match" : {
                "_id" : customer_id
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
        {"$unwind" : "$address_ins"}, 
        {
           "$project" :{
                "_id": 0,
                "street" : "$address_ins.street",
                "city" : "$address_ins.city",
                "state" : "$address_ins.state",
                "zipCode" : "$address_ins.zipCode",
                "country" : "$address_ins.country"
           }
        }
    ]
    address_obj = list(user.objects.aggregate(*(pipeline)))
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
    
    if industry_id_str == "":
        order_obj = DatabaseModel.save_documents(order,{"order_id" : formatted_order_id,"customer_id" : ObjectId(customer_id),"manufacture_unit_id_str" : manufacture_unit_id_str, "amount" : amount, "currency" : currency,"order_items" : new_order_items,"total_items" : len(new_order_items), "shipping_address_id" : shipping_address_obj.id,"is_reorder" : True})
    else:
        order_obj = DatabaseModel.save_documents(order,{"order_id" : formatted_order_id,"customer_id" : ObjectId(customer_id),"manufacture_unit_id_str" : manufacture_unit_id_str, "amount" : amount, "currency" : currency,"order_items" : new_order_items,"total_items" : len(new_order_items), "shipping_address_id" : shipping_address_obj.id,"industry_id_str" : industry_id_str, "is_reorder" : True})

    pipeline = [
        {
            "$match" : {
                "_id" : {"$in" : new_order_items},
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
    sendMailWhenOrderPlaced(customer_id,order_obj)
    data['is_created'] = True
    data['order_id'] = str(order_obj.id)  
        
    return data







# settings.py
SHIPENGINE_API_KEY = "TEST_NEwEXewJdqQ91auh8NyGHI6KpP9zolbLJUNi4JFsNJ0"
SHIPENGINE_BASE_URL = "https://api.shipengine.com/v1"

def get_carriers():
    url = f"{SHIPENGINE_BASE_URL}/carriers"
    headers = {
        "API-Key": SHIPENGINE_API_KEY,
    }
    response = requests.get(url, headers=headers)
    return response.json()


import json

def get_shipping_rates(ship_from, ship_to, packages, carrier_ids):
    url = f"{SHIPENGINE_BASE_URL}/rates/estimate"
    headers = {
        "Content-Type": "application/json",
        "API-Key": SHIPENGINE_API_KEY,
    }

    # package_list = []
    
    # for package in packages:
    #     package_details = {
    #         "weight": {
    #             "value": package["weight"]["value"],  # Total weight (including quantity)
    #             "unit": package["weight"]["unit"]
    #         },
    #     }
        
    #     package_list.append(package_details)
    
    # Final data to send
    data = {
        "carrier_ids": carrier_ids,
        "from_country_code": ship_from["country_code"],
        "from_postal_code": ship_from["postal_code"],
        "to_country_code": ship_to["country_code"],
        "to_postal_code": ship_to["postal_code"],
        "weight": packages # Ensure packages are structured correctly
    }
    
    # Debugging: Print out the request before sending
    print("Sending Request to ShipEngine:")
    print(json.dumps(data, indent=4))
    
    # Send the request to ShipEngine API
    response = requests.post(url, json=data, headers=headers)
    
    # Return the response to check the result
    return response.json()






def create_shipping_label(ship_from, ship_to, package):
    url = f"{SHIPENGINE_BASE_URL}/labels"
    headers = {

        "Content-Type": "application/json",
        "API-Key": SHIPENGINE_API_KEY,
    }
    data = {
        "shipment": {
            "service_code": "usps_priority_mail",  # Replace with actual service code
            "ship_from": {
                "name": ship_from["name"],
                "address_line1": ship_from["address_line1"],
                "city_locality": ship_from["city_locality"],
                "state_province": ship_from["state_province"],  # Ensure state_province is passed
                "country_code": ship_from["country_code"],
                "postal_code": ship_from["postal_code"],
                "phone": ship_from["phone"]
            },
            "ship_to": {
                "name": ship_to["name"],
                "address_line1": ship_to["address_line1"],
                "city_locality": ship_to["city_locality"],
                "state_province": ship_to["state_province"],  # Ensure state_province is passed
                "country_code": ship_to["country_code"],
                "postal_code": ship_to["postal_code"],
                "phone": ship_to["phone"]
            },
            "packages": [
                {
                    "weight": {
                        "value": package["weight"]['value'],
                        "unit": "pound"
                    },
                    "dimensions": {
                        "length": package["dimensions"]["length"],
                        "width": package["dimensions"]["width"],
                        "height": package["dimensions"]["height"],
                        "unit": "inch"
                    }
                }
            ]
        }
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()



ship_from = {
    "name": "John Doe",
    "address_line1": "123 Main Street",
    "city_locality": "Los Angeles",
    "state_province": "CA",  # Added state code
    "country_code": "US",
    "postal_code": "90001",
    "phone": "1234567890"
}

# ship_from = {
#     "name": "John Doe",
#     "address_line1": "123 Main Street",
#     "city_locality": "Los Angeles",
#     "state_province": "TN",  # Added state code
#     "country_code": "IN",
#     "postal_code": "643006",
#     "phone": "1234567890"
# }

# ship_to = {
#     "name": "Jane Smith",
#     "address_line1": "456 Market Street",
#     "city_locality": "San Francisco",
#     "state_province": "CA",  # Added state code
#     "country_code": "US",
#     "postal_code": "94103",
#     "phone": "0987654321"
# }
ship_to = {
    "name": "Rajesh Kumar",
    "address_line1": "123 Mount Road",
    "city_locality": "Chennai",
    "state_province": "TN",  # Tamil Nadu state code
    "country_code": "IN",
    "postal_code": "600002",
    "phone": "9876543210"
}

package = {
      "weight": {
        "value": 50,  
        "unit": "pound"
      },
      "dimensions": {
        "length": 24,  
        "width": 20,
        "height": 16,
        "unit": "inch"
      },
      "quantity": 1  
    }

# [{
#       "weight": {
#         "value": 50,  
#         "unit": "pound"
#       },
#       "dimensions": {
#         "length": 24,  
#         "width": 20,
#         "height": 16,
#         "unit": "inch"
#       },
#       "quantity": 1  
#     },
#     {
#       "weight": {
#         "value": 50,  
#         "unit": "pound"
#       },
#       "dimensions": {
#         "length": 20,  
#         "width": 22,
#         "height": 18,
#         "unit": "inch"
#       },
#       "quantity": 1  
#     },
#     {
#       "weight": {
#         "value": 50,
#         "unit": "pound"
#       },
#       "dimensions": {
#         "length": 26,  
#         "width": 18,
#         "height": 15,
#         "unit": "inch"
#       },
#       "quantity": 1  
#     }]
  
weight = {
          "value": 6,
          "unit": "ounce"
        }
   
# # Fetch carrier IDs (once)
# carriers = get_carriers()
# carrier_ids = [carrier['carrier_id'] for carrier in carriers['carriers']]

# # Get shipping rates
# rates = get_shipping_rates(ship_from, ship_to, weight, carrier_ids)
# print("Rates:", rates)

# # Create a shipping label
# label = create_shipping_label(ship_from, ship_to, package)
# print("Label:", label)


####Get Shipping Rates


# def get_shipping_rates(ship_from, ship_to, package):
#     url = "https://api.shipengine.com/v1/rates"
#     headers = {
#         "API-Key": SHIPENGINE_API_KEY,
#         "Content-Type": "application/json"
#     }

#     data = {
#         "ship_from": ship_from,
#         "ship_to": ship_to,
#         "packages": [package]
#     }

#     response = requests.post(url, json=data, headers=headers)
#     rates = response.json()

#     # Sort rates in ascending order
#     sorted_rates = sorted(rates['rate'], key=lambda x: x['rate'])
#     return sorted_rates

####Confirm Shipment

def confirm_shipment(ship_from, ship_to, package, carrier_id, rate):
    url = "https://api.shipengine.com/v1/labels"
    headers = {
        "API-Key": SHIPENGINE_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "shipment": {
            "service_code": carrier_id,  # Carrier service code (e.g., "usps_priority_mail")
            "ship_from": ship_from,
            "ship_to": ship_to,
            "packages": [package],
            "rates": rate
        }
    }

    response = requests.post(url, json=data, headers=headers)
    shipment = response.json()
    return shipment

####Track Shipment

def track_shipment(tracking_number):
    url = f"https://api.shipengine.com/v1/tracking?tracking_number={tracking_number}"
    headers = {
        "API-Key": SHIPENGINE_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    tracking_info = response.json()

    # Save tracking info in the database
    TrackingInfo.objects.create(
        shipment_id=tracking_info['shipment_id'],
        tracking_number=tracking_info['tracking_number'],
        events=tracking_info['events'],
        last_updated=tracking_info['last_updated']
    )

    return tracking_info


######Live Tracking Updates


def update_tracking_info(tracking_number):
    tracking_info = track_shipment(tracking_number)

    # Update the tracking status in the database
    tracking_obj = TrackingInfo.objects(tracking_number=tracking_number).first()
    tracking_obj.events = tracking_info['events']
    tracking_obj.last_updated = datetime.now()
    tracking_obj.save()

    return tracking_info


#########Return the Response to the User

def get_order_tracking_status(order_id):
    shipment = Shipment.objects(order_id=order_id).first()
    tracking_info = TrackingInfo.objects(shipment_id=shipment.id).first()

    return {
        "tracking_number": shipment.tracking_number,
        "status": shipment.status,
        "events": tracking_info.events if tracking_info else [],
        "expected_delivery": shipment.expected_delivery
    }

def getAvaliableCarrierList(request):
    data = dict()
    carrier_list = list()
    error = ""
    try:
        url = f"{SHIPENGINE_BASE_URL}/carriers"
        headers = {
            "API-Key": SHIPENGINE_API_KEY,
        }
        response = requests.get(url, headers=headers)
        for carrier in response.json():
            result_data = {
                "carrier_id" : carrier['carrier_id'],
                "carrier_code" : carrier['carrier_code']
            }
            carrier_list.append(result_data)
    except Exception as e:
        error = e
    data = {
            "carrier_list" : carrier_list,
            "error" : error
            }
    return data



@csrf_exempt
def notifyBuyerForAvailableProductsInOrder(request):
    # Fetch order details
    json_request = JSONParser().parse(request)

    order_id = json_request.get('order_id')
    user_cart_item_ids = json_request.get('user_cart_item_ids')

    user_cart_item_ids = [ObjectId(pid) for pid in user_cart_item_ids]

    order_obj = DatabaseModel.get_document(order.objects, {"id": order_id}, ["customer_id", "order_items", "order_id"])
    user_obj = DatabaseModel.get_document(user.objects, {"id": order_obj.customer_id.id}, ["first_name", "last_name", "email"])
    user_name = f"{user_obj.first_name} {user_obj.last_name or ''}".strip()

    # Fetch product details
    pipeline = [
        {
            "$match": {
                "_id": {"$in": user_cart_item_ids}
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
                "path": "$product_ins"            }
        },
        {
            "$project": {
                "_id": 0,
                "product_name": "$product_ins.product_name",
            }
        }
    ]
    product_list = list(user_cart_item.objects.aggregate(pipeline))
   

    # Prepare email content
    product_names = "\n".join([f"{i+1}. {product_ins['product_name']}" for i, product_ins in enumerate(product_list)])
    subject = f"Order #{order_obj.order_id} - Product Fulfillment Notification"
    body = f"""
    Dear {user_name},

    We are pleased to inform you that the following products from your order #{order_obj.order_id} are now available and will be transported shortly:

    {product_names}

    Thank you for shopping with us!

    Best regards,
    B2Bop Team
    """

    # Send email
    send_email(user_obj.email, subject, body)

    DatabaseModel.update_documents(user_cart_item.objects,{"id__in" : user_cart_item_ids},{"product_status" : "Shipped"})
    updateOrderFulfillmentStatus(order_id)

    return {"status": "Email sent successfully"}



# DatabaseModel.update_documents(user_cart_item.objects,{},{"product_status" : "Pending"})
def updateOrderFulfillmentStatus(order_id):
    # Fetch the order details
    order_obj = DatabaseModel.get_document(order.objects, {"id": order_id}, ["order_items"])

    # Check the status of each product in the order
    pipeline = [
        {
            "$match": {
                "_id": {"$in": [ins.id for ins in order_obj.order_items]}
            }
        },
        {
            "$project": {
                "_id": 0,
                "product_status": 1
            }
        }
    ]
    user_cart_item_list = list(user_cart_item.objects.aggregate(pipeline))

    # Determine the fulfillment status
    all_shipped = all(item['product_status'] == "Shipped" for item in user_cart_item_list)
    if all_shipped:
        fulfillment_status = "Fulfilled"
    else:
        fulfillment_status = "Partially Fulfilled"

    # Update the order's fulfillment status
    DatabaseModel.update_documents(order.objects, {"id": order_id}, {"fulfilled_status": fulfillment_status, "updated_date": datetime.now()})

    return {"status": "Order fulfillment status updated successfully"}