from django.db import models
from mongoengine import fields,Document
from datetime import datetime
import re
from mongoengine.errors import ValidationError


def validateEmail(value):
    mail_re = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if(not re.fullmatch(mail_re, value)):
        raise ValidationError("Email format is invalid")
    
class address(Document):
    street = fields.StringField(required=True)
    city = fields.StringField(required=True)
    state = fields.StringField(required=True)
    zipCode = fields.StringField(required=True)
    country = fields.StringField(required=True)


class bank_details(Document):
    #Indian bank
    ifsc_code = fields.StringField()
    #International Bank Account Number
    iban = fields.StringField()
    swift_code = fields.StringField() #SWIFT code or BIC (Bank Identifier Code) of the recipient's bank

    bank_name = fields.StringField()
    account_number = fields.StringField()
    branch = fields.StringField()
    currency = fields.StringField()
    creation_date = fields.DateTimeField(default=datetime.now())
    updated_date = fields.DateTimeField(default=datetime.now())
    address_id = fields.ReferenceField(address)

class role(Document):
    name = fields.StringField()
    description = fields.StringField()
    priority = fields.IntField()

class manufacture_unit(Document):
    name = fields.StringField()
    description = fields.StringField()
    location = fields.StringField()
    logo = fields.StringField()

class user(Document):
    first_name = fields.StringField()
    last_name = fields.StringField()
    username = fields.StringField(required=True)
    email = fields.StringField(validation=validateEmail,required=True)
    password = fields.StringField(required=True)
    age = fields.IntField()
    date_of_birth = fields.StringField()
    mobile_number = fields.StringField(required=True)
    active = fields.BooleanField(default=True)
    profile_image = fields.StringField()
    role_id = fields.ReferenceField(role)
    manufacture_unit_id = fields.ReferenceField(manufacture_unit)
    address_id = fields.ListField(fields.ReferenceField(address))
    bank_details_id = fields.ReferenceField(bank_details)


class product_category(Document):
    name = fields.StringField(required=True)
    description = fields.StringField()
    code = fields.StringField()
    creation_date = fields.DateTimeField(default=datetime.now)
    manufacture_unit_id_str = fields.StringField()

class product_sub_category(Document):
    name = fields.StringField(required=True)
    description = fields.StringField()
    code = fields.StringField()
    product_category_id = fields.ReferenceField(product_category)
    manufacture_unit_id_str = fields.StringField()


class brand(Document):
    name = fields.StringField(required=True)
    code = fields.StringField()
    product_sub_category_id_str = fields.StringField()
    logo = fields.StringField()
    manufacture_unit_id_str = fields.StringField()

class products(Document):
    name = fields.StringField(required=True)
    description = fields.StringField()
    price = fields.FloatField(required=True)
    discount_price = fields.FloatField()
    is_available = fields.BooleanField(default=True)
    currency = fields.StringField(required=True)
    stock_quantity = fields.IntField(required=True)
    primary_image = fields.StringField()
    product_image_list = fields.ListField()
    product_video_list = fields.ListField()
    colour = fields.StringField()
    creation_date = fields.DateTimeField(default=datetime.now())
    updated_date = fields.DateTimeField(default=datetime.now())
    height = fields.FloatField()
    weight = fields.FloatField()
    sku = fields.StringField() 
    mpin = fields.StringField()
    dimensions = fields.StringField()
    rating = fields.FloatField()
    review_count = fields.IntField(default=0)
    warranty_period = fields.StringField()
    tags = fields.ListField(fields.StringField())
    product_sub_category_id = fields.ReferenceField(product_sub_category)
    manufacture_unit_id = fields.ReferenceField(manufacture_unit)
    brand_id = fields.ReferenceField(brand)
    



class user_cart_item(Document):
    user_id = fields.ReferenceField(user)
    product_id = fields.ReferenceField(products)
    quantity = fields.IntField(required=True)
    price = fields.FloatField(required=True)    
    creation_date = fields.DateTimeField(default=datetime.now())
    updated_date = fields.DateTimeField(default=datetime.now())
    status = fields.StringField(default="pending")


class order(Document):
    customer_id = fields.ReferenceField(user, required=True)
    order_items = fields.ListField(fields.ReferenceField(user_cart_item))
    order_date = fields.DateTimeField(default=datetime.now)
    status = fields.StringField(choices=["pending", "shipped", "completed", "canceled"], default="pending")
    shipping_address_id = fields.ReferenceField(address, required=True)
    amount = fields.FloatField(required=True),             
    currency = fields.StringField(required=True)             
    creation_date = fields.DateTimeField(default=datetime.now())
    updated_date = fields.DateTimeField(default=datetime.now())



class transaction(Document):
    order_id = fields.ReferenceField(order, required=True)       
    total_amount = fields.FloatField(required=True) 
    currency = fields.StringField(required=True) 
    transaction_date = fields.DateTimeField(default=datetime.now)
    payment_method = fields.StringField(choices=["credit_card", "bank_transfer", "paypal"], required=True)
    status = fields.StringField(choices=["successful", "failed", "pending"], default="pending") 
    creation_date = fields.DateTimeField(default=datetime.now())
    updated_date = fields.DateTimeField(default=datetime.now())
    bank_details_id = fields.ReferenceField(bank_details)