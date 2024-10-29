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
    default_address_id = fields.ListField(fields.ReferenceField(address))
    address_id = fields.ListField(fields.ReferenceField(address))
    bank_details_id = fields.ReferenceField(bank_details)


# class product_category(Document):
#     name = fields.StringField(required=True)
#     description = fields.StringField()
#     code = fields.StringField()
#     creation_date = fields.DateTimeField(default=datetime.now)
#     manufacture_unit_id_str = fields.StringField()

# class product_sub_category(Document):
#     name = fields.StringField(required=True)
#     description = fields.StringField()
#     code = fields.StringField()
#     product_category_id = fields.ReferenceField(product_category)
#     manufacture_unit_id_str = fields.StringField()


class brand(Document):
    name = fields.StringField(required=True)
    code = fields.StringField()
    product_sub_category_id_str = fields.StringField()
    logo = fields.StringField()
    manufacture_unit_id_str = fields.StringField()

# class product(Document):
#     name = fields.StringField(required=True)
#     description = fields.StringField()
#     price = fields.FloatField(required=True)
#     discount_price = fields.FloatField()
#     is_available = fields.BooleanField(default=True)
#     currency = fields.StringField(required=True)
#     stock_quantity = fields.IntField(required=True)
#     primary_image = fields.StringField()
#     product_image_list = fields.ListField()
#     product_video_list = fields.ListField()
#     colour = fields.StringField()
#     creation_date = fields.DateTimeField(default=datetime.now())
#     updated_date = fields.DateTimeField(default=datetime.now())
#     height = fields.FloatField()
#     weight = fields.FloatField()
#     sku = fields.StringField() 
#     mpin = fields.StringField()
#     dimensions = fields.StringField()
#     rating = fields.FloatField()
#     review_count = fields.IntField(default=0)
#     warranty_period = fields.StringField()
#     tags = fields.ListField(fields.StringField())
#     manufacture_unit_id = fields.ReferenceField(manufacture_unit)
#     brand_id = fields.ReferenceField(brand)

class product_category(Document):
    name = fields.StringField(required=True)
    level = fields.IntField(default=0)
    parent_category_id = fields.ReferenceField('self', null=True)
    child_categories = fields.ListField(fields.ReferenceField('self'))
    breadcrumb = fields.StringField()
    manufacture_unit_id_str = fields.StringField()
    creation_date = fields.DateTimeField(default=datetime.now())
    description = fields.StringField()
    code = fields.StringField()

class vendor(Document):
    name = fields.StringField(required=True)
    manufacture_unit_id_str = fields.StringField()

class product(Document):
    sku_number_product_code_item_number = fields.StringField(required=True)
    # product_code = fields.StringField(required=True)
    # item_number = fields.StringField(required=True)
    model = fields.StringField()
    mpn = fields.StringField(required=True)
    upc_ean = fields.StringField()
    
    breadcrumb = fields.StringField()

    brand_name = fields.StringField(required=True)
    product_name = fields.StringField(required=True)
    long_description = fields.StringField(required=True)
    short_description = fields.StringField()
    features = fields.ListField(fields.StringField())
    images = fields.ListField(fields.StringField())
    attributes = fields.DictField(default={})
    tags = fields.ListField(fields.StringField())
    msrp = fields.FloatField(default=0.0)              # Manufacturer's Suggested Retail Price
    currency = fields.StringField(required=True)
    was_price = fields.FloatField(default=0.0)          # Previous price before discount
    list_price = fields.FloatField(default=0.0)         # List price of the product
    discount = fields.FloatField(default=0.0)          #Discount percentage or amount
    quantity_price = fields.FloatField(default=0.0)     # Price per unit for a specified quantity
    quantity = fields.FloatField()          #Quantity available or minimum purchase quantity
    availability = fields.BooleanField(default=True)      # "in stock", "out of stock", "pre-order"
    return_applicable = fields.BooleanField(default=False)   # Whether returns are allowed or not
    manufacture_unit_id = fields.ReferenceField(manufacture_unit)
    brand_id = fields.ReferenceField(brand)
    vendor_id = fields.ReferenceField(vendor)
    # Reference to the lowest category level (Level 6 in this example)
    category_id = fields.ReferenceField(product_category)
    



class user_cart_item(Document):
    user_id = fields.ReferenceField(user)
    product_id = fields.ReferenceField(product)
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
    manufacture_unit_id_str = fields.StringField()



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