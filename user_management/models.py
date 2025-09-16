from django.db import models
from mongoengine import fields,Document,EmbeddedDocument, EmbeddedDocumentField
from datetime import datetime
import re
import random
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
    is_default = fields.BooleanField(default=False) 


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
    images = fields.ListField(fields.StringField(),default=[])
    creation_date = fields.DateTimeField(default=datetime.now())
    updated_date = fields.DateTimeField(default=datetime.now())
    address_id = fields.ReferenceField(address)
    is_default = fields.BooleanField(default=False)

class role(Document):
    name = fields.StringField()
    description = fields.StringField()
    priority = fields.IntField()

class manufacture_unit(Document):
    name = fields.StringField()
    description = fields.StringField()
    location = fields.StringField()
    logo = fields.StringField()
    industry = fields.StringField()
    is_active = fields.BooleanField(default=True)

class user(Document):
    dealer_id = fields.IntField(default=None)
    first_name = fields.StringField()
    last_name = fields.StringField()
    username = fields.StringField(required=True)
    email = fields.StringField(validation=validateEmail,required=True)
    password = fields.StringField(required=True)
    age = fields.IntField()
    date_of_birth = fields.StringField()
    mobile_number = fields.StringField()
    active = fields.BooleanField(default=True)
    profile_image = fields.StringField()
    company_name = fields.StringField()
    role_id = fields.ReferenceField(role)
    manufacture_unit_id = fields.ReferenceField(manufacture_unit)
    default_address_id = fields.ReferenceField(address)
    address_id_list = fields.ListField(fields.ReferenceField(address),default=[])
    bank_details_id_list = fields.ListField(fields.ReferenceField(bank_details),default=[])
    ware_house_id_list = fields.ListField(fields.ReferenceField(address),default=[])
    website = fields.StringField()
    creation_date = fields.DateTimeField(default=datetime.now())
    updated_date = fields.DateTimeField(default=datetime.now())
    otp = fields.IntField()
    otp_generated_time = fields.DateTimeField(default=datetime.now())
    last_login = fields.DateTimeField(default=datetime.now())

    def clean(self):
        # Ensure unique dealer_id
        if not self.dealer_id:
            while True:
                candidate_id = random.randint(100000, 999999)
                if not user.objects(dealer_id=candidate_id):
                    self.dealer_id = candidate_id
                    break
        super().clean()


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
    industry_id_str = fields.StringField()


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
    end_level = fields.BooleanField(default=False)
    industry_id_str = fields.StringField()

class vendor(Document):
    name = fields.StringField(required=True)
    manufacture_unit_id_str = fields.StringField()



class product(Document):
    sku_number_product_code_item_number = fields.StringField(default="")
    # product_code = fields.StringField(default="")
    # item_number = fields.StringField(default="")
    model = fields.StringField()
    mpn = fields.StringField(default="")
    upc_ean = fields.StringField()
    
    breadcrumb = fields.StringField()

    brand_name = fields.StringField(default="")
    product_name = fields.StringField(default="")
    long_description = fields.StringField(default="")
    short_description = fields.StringField()
    features = fields.ListField(fields.StringField())
    images = fields.ListField(fields.StringField())
    attributes = fields.DictField(default={})
    tags = fields.ListField(fields.StringField())
    msrp = fields.FloatField(default=0.0)              # Manufacturer's Suggested Retail Price
    currency = fields.StringField(default="")
    was_price = fields.FloatField(default=0.0)          # Previous price before discount
    list_price = fields.FloatField(default=0.0)         # List price of the product
    discount = fields.FloatField(default=0.0)          #Discount percentage or amount
    quantity_prices = fields.FloatField(default=0.0)     # Price per unit for a specified quantity
    quantity = fields.FloatField()          #Quantity available or minimum purchase quantity
    availability = fields.BooleanField(default=True)      # "in stock", "out of stock", "pre-order"
    return_applicable = fields.BooleanField(default=False)   # Whether returns are allowed or not
    return_in_days = fields.StringField()
    visible = fields.BooleanField(default=True)
    manufacture_unit_id = fields.ReferenceField(manufacture_unit)
    brand_id = fields.ReferenceField(brand)
    vendor_id = fields.ReferenceField(vendor)
    # Reference to the lowest category level (Level 6 in this example)
    category_id = fields.ReferenceField(product_category)
    quantity_price = fields.DictField(default={"1-100" : 1,"100-1000" : 2,"1000-10000" : 3})
    rating_count = fields.IntField(default=0)
    rating_average = fields.FloatField(default=0.0)
    from_the_manufacture = fields.StringField()
    industry_id_str = fields.StringField()
    tax = fields.FloatField(default=0.0)


class unit_wise_field_mapping(Document):
    manufacture_unit_id = fields.ReferenceField(manufacture_unit)
    attributes = fields.DictField(default={})


class rating(Document):
    user_id = fields.ReferenceField(user)
    product_id = fields.ReferenceField(product)    
    feedback = fields.StringField(default="")
    rating_count = fields.FloatField()



class user_cart_item(Document):
    user_id = fields.ReferenceField(user)
    product_id = fields.ReferenceField(product)
    quantity = fields.IntField(required=True)
    price = fields.FloatField(required=True)    
    creation_date = fields.DateTimeField(default=datetime.now())
    updated_date = fields.DateTimeField(default=datetime.now())
    status = fields.StringField(choices=["Pending", "Completed"], default="Pending")
    unit_price = fields.FloatField(required=True) 
    product_status = fields.StringField(choices=["Shipped", "Pending"], default="Pending")

    # 🔹 Add these new fields for discount support:
    seller_discount = fields.FloatField(default=0.0)  # percentage
    discounted_price = fields.FloatField(default=0.0) # total price after discount   # total price after discount

class order(Document):
    order_id = fields.StringField()
    customer_id = fields.ReferenceField(user, required=True)
    order_items = fields.ListField(fields.ReferenceField(user_cart_item))
    total_items = fields.IntField()
    order_date = fields.DateTimeField(default=datetime.now)
    delivery_status = fields.StringField(choices=["Pending", "Shipped", "Completed", "Canceled"], default="Pending")
    fulfilled_status = fields.StringField(choices=["Fulfilled", "Unfulfilled", "Partially Fulfilled" ], default="Unfulfilled")
    payment_status = fields.StringField(choices=["Completed","Pending", "Paid", "Failed" ], default="Pending")
    shipping_address_id = fields.ReferenceField(address)
    amount = fields.FloatField(required=True)
    currency = fields.StringField(required=True)             
    creation_date = fields.DateTimeField(default=datetime.now())
    updated_date = fields.DateTimeField(default=datetime.now())
    manufacture_unit_id_str = fields.StringField()
    is_reorder = fields.BooleanField(default=False)
    industry_id_str = fields.StringField()
    shipping_from = fields.ReferenceField(address)
    shipping_fee = fields.FloatField(default=0.0)



class transaction(Document):
    order_id = fields.ReferenceField(order, required=True)       
    total_amount = fields.FloatField(required=True) 
    currency = fields.StringField(required=True) 
    transaction_date = fields.DateTimeField(default=datetime.now)
    payment_method = fields.StringField(choices=["credit_card", "bank_transfer", "paypal"], default="bank_transfer")
    status = fields.StringField(choices=["Completed","Paid", "Failed"], default="Paid") 
    payment_proof = fields.StringField()
    creation_date = fields.DateTimeField(default=datetime.now())
    updated_date = fields.DateTimeField(default=datetime.now())
    bank_details_id = fields.ReferenceField(bank_details)
    message = fields.StringField()
    transaction_id = fields.StringField()


class mail_template(Document):
    code = fields.StringField()
    subject = fields.StringField()
    default_template = fields.StringField()
    cutomize_template = fields.StringField()
    manufacture_unit_id_str = fields.StringField()
    is_default = fields.BooleanField(default=False)



######     MANUFACUTURE ADMIN DASHBOARD COLLECTIONS    ######


class top_selling_product(Document):
    product_id = fields.ReferenceField(product)
    product_name = fields.StringField()
    category_name = fields.StringField()
    brand_name = fields.StringField()
    total_sales = fields.FloatField()
    units_sold = fields.IntField()
    last_updated = fields.DateTimeField(default=datetime.now())
    manufacture_unit_id_str = fields.StringField()


class top_selling_brand(Document):
    brand_id = fields.ReferenceField(brand)
    brand_name = fields.StringField()
    category_name = fields.StringField()
    total_sales = fields.IntField()
    units_sold = fields.IntField()
    products_sold = fields.ListField(fields.ReferenceField(top_selling_product),default=[])
    last_updated = fields.DateTimeField(default=datetime.now())
    manufacture_unit_id_str = fields.StringField()


class top_selling_category(Document):
    category_id = fields.ReferenceField(product_category)
    category_name = fields.StringField()
    total_sales = fields.IntField()
    units_sold = fields.IntField()
    top_products = fields.ListField(fields.ReferenceField(top_selling_product),default=[])
    top_brands = fields.ListField(fields.ReferenceField(top_selling_brand),default=[])
    last_updated = fields.DateTimeField(default=datetime.now())
    manufacture_unit_id_str = fields.StringField()


class industry(Document):
    name = fields.StringField()

class manufacture_unit_industry_config(Document):
    manufacture_unit_id_str = fields.StringField()
    industry_list = fields.ListField(fields.ReferenceField(industry),default=[])

class user_industry_config(Document):
    user_id_str = fields.StringField()
    allowed_industry_list = fields.ListField(fields.ReferenceField(industry),default=[])


class ignore_calls(Document):
    name = fields.StringField()

class status_message(Document):
    code = fields.StringField()
    message = fields.StringField()


class wishlist(Document):
    user_id = fields.ReferenceField(user)
    product_id = fields.ReferenceField(product)
    added_at = fields.DateTimeField(default=datetime.now())
    updated_at = fields.DateTimeField(default=datetime.now())


class ScheduledTask(models.Model):
    task_name = fields.StringField()
    trigger_time = fields.DateTimeField()
    status = fields.StringField(default="pending")
    payload = fields.DictField()
    created_at = fields.DateTimeField(default=datetime.now())
    updated_at = fields.DateTimeField(default=datetime.now())

    def __str__(self):
        return f"{self.task_name} - {self.trigger_time}"
    

#####SHIPPING SCHEMAS######

class Shipment(Document):
    order_id = fields.StringField(required=True)  # Associated Order ID
    carrier_id = fields.StringField(required=True)  # The carrier used for shipment
    carrier_name = fields.StringField(required=True)  # Carrier name (e.g., USPS, FedEx, etc.)
    tracking_number = fields.StringField(required=True)  # Tracking number provided by carrier
    status = fields.StringField(default="pending")  # Shipment status (e.g., pending, shipped, delivered)
    expected_delivery = fields.DateTimeField()  # Expected delivery date
    ship_from = fields.DictField()  # Address from where the item is shipped
    ship_to = fields.DictField()  # Address where the item is going
    weight = fields.FloatField()  # Package weight
    dimensions = fields.DictField()  # Package dimensions (length, width, height)
    shipping_rate = fields.FloatField()  # Rate charged for shipping
    created_at = fields.DateTimeField()
    updated_at = fields.DateTimeField()

class ShippingRate(Document):
    carrier_id = fields.StringField(required=True)  # Carrier ID (e.g., USPS, FedEx)
    carrier_name = fields.StringField(required=True)  # Carrier name
    shipping_method = fields.StringField(required=True)  # Method (e.g., Ground, Express)
    origin = fields.DictField()  # Origin address
    destination = fields.DictField()  # Destination address
    weight = fields.FloatField(required=True)  # Weight of the package
    rate = fields.FloatField()  # Cost of the shipping method
    dimensions = fields.DictField()  # Dimensions of the package
    created_at = fields.DateTimeField()

class TrackingInfo(Document):
    shipment_id = fields.StringField(required=True)  # Associated shipment ID
    tracking_number = fields.StringField(required=True)  # Carrier tracking number
    events = fields.ListField(fields.DictField())  # List of tracking events (e.g., "In Transit", "Delivered")
    last_updated = fields.DateTimeField()  # Timestamp for the last update