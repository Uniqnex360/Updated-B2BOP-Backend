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
                "status" : "pending"
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
        DatabaseModel.update_documents(user_cart_item.objects,{"id" : user_cart_item_obj[0]['_id']},{"inc__quantity" : json_request['quantity'],"price" : price})
        user_cart_item.objects(id = user_cart_item_obj[0]['_id']).update(quantity = json_request['quantity'])
        data['is_updated'] = True
    else:
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
                "status" : "pending"
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
                "price" : "$products_ins.list_price",
                "currency" : "$products_ins.currency",
                "primary_image" : {"$first":"$products_ins.images"},
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
        DatabaseModel.delete_documents(user_cart_item.objects,{"user_id" : ObjectId(json_request['user_id'])})
        data['is_deleted'] = True
    elif json_request['is_delete'] == True:
        DatabaseModel.delete_documents(user_cart_item.objects,{"id" : ObjectId(json_request['id'])})
        data['is_deleted'] = True
    else:
        for cart_ins in json_request['cart_list']:
            cart_obj = DatabaseModel.get_document(user_cart_item.objects,{"id" : cart_ins['id']},['product_id','quantity'])
            print("price",cart_obj.product_id.list_price,type(cart_obj.product_id.list_price))
            print("quantity",cart_ins['quantity'], type(cart_ins['quantity']))
            updated_price = (cart_obj.product_id.list_price) * cart_ins['quantity']
            DatabaseModel.update_documents(user_cart_item.objects,{"id" : cart_ins['id']},{"price" : updated_price,"quantity" : cart_ins['quantity']})

        data['is_updated'] = True
    return data


def totalCheckOutAmount(request):
    # user_id = obtainUserIdFromToken(request)
    user_id = request.GET.get('user_id')
    pipeline = [
    {
        "$match": {
            "user_id": ObjectId(user_id),
            "status": "pending"
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
            'total_amount': "$total_amount",
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
    print("json_request",json_request,"\n\n\n")
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

    
    status_match = {}
    status_match['manufacture_unit_id_str'] = manufacture_unit_id
    if delivery_status != "all":
        status_match['delivery_status'] = delivery_status
    if fulfilled_status != "all":
        status_match['fulfilled_status'] = fulfilled_status
    if payment_status != "all":
        status_match['payment_status'] = payment_status

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
                "dealer_name" : "$user_ins.username",
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
    
    pipeline = [
        {
            "$match" : {
                "manufacture_unit_id" : ObjectId(manufacture_unit_id),
                "role_id" : ObjectId('670e3c616569d56ed4d4a75b'),
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
                "email" : 1,
                "mobile_number" : 1,
                "company_name" : 1,
                "address" : {
                    "street" : "$address_ins.street",
                    "city" : "$address_ins.city",
                    "state" : "$address_ins.state",
                    "country" : "$address_ins.country",
                    "zipCode" : "$address_ins.zipCode"
                },
                "website" : "www.google.com",
                "no_of_orders" : "5"
           }
        }
    ]
    dealer_list = list(user.objects.aggregate(*(pipeline)))
    return dealer_list


@csrf_exempt
def createOrder(request):
    data = dict()
    json_request = JSONParser().parse(request)

    # print("json_request-------------",json_request,"\n\n\n")
    manufacture_unit_id_str = json_request['manufacture_unit_id']
    customer_id = json_request['user_id']
    order_items = json_request['order_items']
    amount = json_request['amount']
    currency = json_request['currency']
    shipping_address_id = json_request['shipping_address_id']
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
    order_obj = DatabaseModel.save_documents(order,{"order_id" : formatted_order_id,"customer_id" : ObjectId(customer_id),"manufacture_unit_id_str" : manufacture_unit_id_str, "amount" : amount, "currency" : currency,"order_items" : order_items,"total_items" : len(order_items), "shipping_address_id" : ObjectId(shipping_address_id)})

    DatabaseModel.update_documents(user_cart_item.objects,{"id__in" : order_items},{"status" : "completed"})
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
        "$lookup": {
            "from": "address",  
            "localField": "address_id_list",
            "foreignField": "_id", 
            "as": "other_address_ins" 
        }
    },
    {
        "$unwind": {
            "path": "$other_address_ins", 
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
            "other_address": {
                "$cond": {
                    "if": {
                        "$gt": [
                            {"$size": {"$ifNull": ["$other_address_ins", []]}},
                            0
                        ]
                    },
                    "then": {
                        "address_id" : {"$toString" : "$other_address_ins._id"},
                        "street": "$other_address_ins.street",
                        "city": "$other_address_ins.city",
                        "state": "$other_address_ins.state",
                        "country": "$other_address_ins.country",
                        "zipCode": "$other_address_ins.zipCode"
                    },
                    "else": [] 
                }
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


def obtainOrderListForDealer(request):
    user_id = request.GET.get('user_id')
    pipeline = [
    {"$match": {"customer_id": ObjectId(user_id)}},  
    # {
    #     "$lookup": {
    #         "from": "address",  
    #         "localField": "default_address_id",  
    #         "foreignField": "_id",  
    #         "as": "address_ins"  
    #     }
    # },
    # {
    #     "$unwind": {
    #         "path": "$address_ins",
    #         "preserveNullAndEmptyArrays": True
    #     }
    # },
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
            # "email": 1, 
            # "mobile_number": 1,
            # "manufacture_unit_id" : {"$toString" : "$manufacture_unit_id"},
            # "address": {
            #     "address_id" : {"$toString" : "$address_ins._id"},
            #     "street": "$address_ins.street",
            #     "city": "$address_ins.city",
            #     "state": "$address_ins.state",
            #     "country": "$address_ins.country",
            #     "zipCode": "$address_ins.zipCode"
            # },
            # "other_address": {
            #     "$cond": {
            #         "if": {
            #             "$gt": [
            #                 {"$size": {"$ifNull": ["$other_address_ins", []]}},
            #                 0
            #             ]
            #         },
            #         "then": {
            #             "address_id" : {"$toString" : "$other_address_ins._id"},
            #             "street": "$other_address_ins.street",
            #             "city": "$other_address_ins.city",
            #             "state": "$other_address_ins.state",
            #             "country": "$other_address_ins.country",
            #             "zipCode": "$other_address_ins.zipCode"
            #         },
            #         "else": [] 
            #     }
            # }
        }
    }
    ]
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
            "localField": "bank_details_id",
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
    DatabaseModel.update_documents(order.objects,{"id" : order_id},{"payment_status" : "paid"})

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

    # Send a welcome email
    subject = "Payment Received - Under Review"
    body = f"""
    Dear {user_obj.first_name},

    Thank you for submitting your payment for order #{order_obj.order_id}. Your payment is currently under review, and we are working to verify it as quickly as possible.

    What to Expect Next:

    Once the payment is successfully verified, you will receive a confirmation email from us with your order summary, payment confirmation, and shipping information.
    We aim to complete this verification process within [estimated time frame, e.g., 1-2 business days].
    Thank you for your patience and trust in us. If you have any questions or need further assistance, please feel free to reply to this email.

    Best regards,
    Service Team
    """
    
    send_email(user_obj.email, subject, body)

    admin_obj = DatabaseModel.get_document(user.objects,{"manufacture_unit_id" : user_obj.manufacture_unit_id.id,"role_id" : ObjectId('670e3b206569d56ed4d4a759')},['email','first_name'])

    current_time = getLocalTime(datetime.now())

    subject = f"New Payment Confirmation Submitted for Order #{order_obj.order_id}"

    body = f"""
    Hello {admin_obj.first_name},

    A new payment confirmation has been submitted by a customer for review.

    Order Details:

    Order Number: #{order_obj.order_id}
    Customer Name: {user_obj.first_name}
    Transaction ID: {transaction_id}
    Payment Amount: {total_amount}
    Submission Date: {current_time} UTC
    Next Steps: Please review the payment confirmation and verify its authenticity. Once confirmed, notify the customer by sending a payment confirmation and order summary.

    If any issues arise during verification, please contact the customer promptly to resolve.

    Thank you for your attention to this order.

    Best regards,
    Service Team
    """
    
    send_email(admin_obj.email, subject, body)

    
    data['is_saved'] = "Transaction saved SucessFully"
    return data