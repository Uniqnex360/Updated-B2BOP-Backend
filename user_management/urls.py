from django.urls import path
from user_management.operations.order_and_purchase_operations import createOrUpdateUserCartItem, updateOrDeleteUserCartItem, obtainUserCartItemList, totalCheckOutAmount, obtainOrderList, obtainDealerlist, exportOrders, obtainUserDetails, createOrder,obtainOrderListForDealer, getManufactureBankDetails, conformPayment, getorderDetails, AcceptOrRejectOrder



from user_management.operations.user_operations import createORUpdateManufactureUnit, obtainManufactureUnitList, obtainManufactureUnitDetails, obtainRolesForCreatingUser, checkEmailExistOrNot, createORUpdateUser, loginUser,createUser, generateUserName, validateEmail, obtainUserListForManufactureUnit, obtainUserDetailsForProfile, updateUserProfile, obtainAllMailTemplateForManufactureUnit, updateMailTemplate


from user_management.operations.products_operations import obtainProductCategoryList, obtainProductsList, obtainbrandList, productSearch, upload_file, obtainProductDetails, save_file, getProductsByTopLevelCategory, updateProduct, getColumnFormExcel, updateBulkProduct, obtainProductsListForDealer, productCountForDealer


urlpatterns = [

    path('loginUser/',loginUser,name="loginUser"),
    path('createUser/',createUser,name="createUser"),
    path('generateUserName/',generateUserName,name="generateUserName"),
    path('validateEmail/',validateEmail,name="validateEmail"),
    path('obtainUserDetailsForProfile/',obtainUserDetailsForProfile,name="obtainUserDetailsForProfile"),
    path('updateUserProfile/',updateUserProfile,name="updateUserProfile"),
    path('obtainAllMailTemplateForManufactureUnit/',obtainAllMailTemplateForManufactureUnit,name="obtainAllMailTemplateForManufactureUnit"),
    path('updateMailTemplate/',updateMailTemplate,name="updateMailTemplate"),


    #Manufacture Unit creation
    path('createORUpdateManufactureUnit/',createORUpdateManufactureUnit,name="createORUpdateManufactureUnit"),
    path('obtainManufactureUnitList/',obtainManufactureUnitList,name="obtainManufactureUnitList"),
    path('obtainManufactureUnitDetails/',obtainManufactureUnitDetails,name="obtainManufactureUnitDetails"),
    path('obtainUserListForManufactureUnit/',obtainUserListForManufactureUnit,name="obtainUserListForManufactureUnit"),

    #Order Details
    path('obtainOrderList/',obtainOrderList,name="obtainOrderList"), 
    path('obtainDealerlist/',obtainDealerlist,name="obtainDealerlist"),
    path('exportOrders/',exportOrders,name="exportOrders"),
    path('createOrder/',createOrder,name="createOrder"),
    path('obtainOrderListForDealer/',obtainOrderListForDealer,name="obtainOrderListForDealer"),
    path('getManufactureBankDetails/',getManufactureBankDetails,name="getManufactureBankDetails"),
    path('conformPayment/',conformPayment,name="conformPayment"),
    path('getorderDetails/',getorderDetails,name="getorderDetails"),
    path('AcceptOrRejectOrder/',AcceptOrRejectOrder,name="AcceptOrRejectOrder"),



    #User creation
    path('obtainRolesForCreatingUser/',obtainRolesForCreatingUser,name="obtainRolesForCreatingUser"),
    path('checkEmailExistOrNot/',checkEmailExistOrNot,name="checkEmailExistOrNot"),
    path('createORUpdateUser/',createORUpdateUser,name="createORUpdateUser"),
    path('obtainUserDetails/',obtainUserDetails,name="obtainUserDetails"),


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
    path('getProductsByTopLevelCategory/',getProductsByTopLevelCategory,name="getProductsByTopLevelCategory"),
    path('updateProduct/',updateProduct,name="updateProduct"),
    path('updateBulkProduct/',updateBulkProduct,name="updateBulkProduct"),
    path('productCountForDealer/',productCountForDealer,name="productCountForDealer"),


    #Upload File
    path('upload_file/',upload_file,name="upload_file"),
    path('save_file/',save_file,name="save_file"),
    path('getColumnFormExcel/',getColumnFormExcel,name="getColumnFormExcel"),


    #Dealer actions
    path('obtainProductsListForDealer/',obtainProductsListForDealer,name="obtainProductsListForDealer"),
]
