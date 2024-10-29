from django.urls import path
from user_management.operations.order_and_purchase_operations import createOrUpdateUserCartItem, updateOrDeleteUserCartItem, obtainUserCartItemList, totalCheckOutAmount, obtainOrderList


from user_management.operations.user_operations import createORUpdateManufactureUnit, obtainManufactureUnitList, obtainManufactureUnitDetails, obtainRolesForCreatingUser, checkEmailExistOrNot, createORUpdateUser, loginUser


from user_management.operations.products_operations import obtainProductCategoryList, obtainProductsList, obtainbrandList, productSearch, upload_file, obtainProductDetails, save_file


urlpatterns = [

    path('loginUser/',loginUser,name="loginUser"),


    #Manufacture Unit creation
    path('createORUpdateManufactureUnit/',createORUpdateManufactureUnit,name="createORUpdateManufactureUnit"),
    path('obtainManufactureUnitList/',obtainManufactureUnitList,name="obtainManufactureUnitList"),
    path('obtainManufactureUnitDetails/',obtainManufactureUnitDetails,name="obtainManufactureUnitDetails"),

    #Order Details
    path('obtainOrderList/',obtainOrderList,name="obtainOrderList"),

    #User creation
    path('obtainRolesForCreatingUser/',obtainRolesForCreatingUser,name="obtainRolesForCreatingUser"),
    path('checkEmailExistOrNot/',checkEmailExistOrNot,name="checkEmailExistOrNot"),
    path('createORUpdateUser/',createORUpdateUser,name="createORUpdateUser"),


    #Products Show Page
    path('obtainProductCategoryList/',obtainProductCategoryList,name="obtainProductCategoryList"),
    path('obtainProductsList/',obtainProductsList,name="obtainProductsList"),
    path('obtainbrandList/',obtainbrandList,name="obtainbrandList"),
    path('createOrUpdateUserCartItem/',createOrUpdateUserCartItem,name="createOrUpdateUserCartItem"),
    path('updateOrDeleteUserCartItem/',updateOrDeleteUserCartItem,name="updateOrDeleteUserCartItem"),
    path('obtainUserCartItemList/',obtainUserCartItemList,name="obtainUserCartItemList"),
    path('totalCheckOutAmount/',totalCheckOutAmount,name="totalCheckOutAmount"),

    path('productSearch/',productSearch,name="productSearch"),
    path('obtainProductDetails/',obtainProductDetails,name="obtainProductDetails"),

    #Upload File
    path('upload_file/',upload_file,name="upload_file"),
    path('save_file/',save_file,name="save_file"),

]
