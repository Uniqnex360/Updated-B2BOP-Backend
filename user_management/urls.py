from django.urls import path
from user_management.operations.order_and_purchase_operations import createOrUpdateUserCartItem, updateOrDeleteUserCartItem, obtainUserCartItemList, totalCheckOutAmount, obtainOrderList, obtainDealerlist, exportOrders, obtainUserDetails, createOrder,obtainOrderListForDealer, getManufactureBankDetails, conformPayment, getorderDetails, acceptOrRejectOrder, createWishList,deleteWishlist, obtainWishlistForBuyer, getAvaliableCarrierList, createReorder, notifyBuyerForAvailableProductsInOrder



from user_management.operations.user_operations import createORUpdateManufactureUnit, obtainManufactureUnitList, obtainManufactureUnitDetails, obtainRolesForCreatingUser, checkEmailExistOrNot, createORUpdateUser, loginUser,createUser, generateUserName, validateEmail, obtainUserListForManufactureUnit, obtainUserDetailsForProfile, updateUserProfile, obtainAllMailTemplateForManufactureUnit, updateMailTemplate, obtainDealerDetails, obtainDashboardDetailsForManufactureAdmin, manufactureDashboardEachDealerOrderValue, deleteAddress, deleteBankDetails, obtainDashboardDetailsForDealer, obtainIndustryList, updateIndustryForManufactureUnit, obtainIndustryForManufactureUnit, createIndustry, forgotPassword, changePassword


from user_management.operations.products_operations import obtainProductCategoryList, obtainProductsList, obtainbrandList, productSearch, upload_file, obtainProductDetails, save_file, getProductsByTopLevelCategory, updateProduct, getColumnFormExcel, updateBulkProduct, obtainProductsListForDealer, productCountForDealer, obtainProductCategoryListForDealer, get_related_products, get_highest_priced_product


urlpatterns = [
    path('loginUser/',loginUser,name="loginUser"),
    path('createUser/',createUser,name="createUser"),
    path('forgotPassword/',forgotPassword,name="forgotPassword"),
    path('changePassword/',changePassword,name="changePassword"),
    path('generateUserName/',generateUserName,name="generateUserName"),
    path('validateEmail/',validateEmail,name="validateEmail"),
    path('obtainUserDetailsForProfile/',obtainUserDetailsForProfile,name="obtainUserDetailsForProfile"),
    path('updateUserProfile/',updateUserProfile,name="updateUserProfile"),
    path('obtainAllMailTemplateForManufactureUnit/',obtainAllMailTemplateForManufactureUnit,name="obtainAllMailTemplateForManufactureUnit"),
    path('updateMailTemplate/',updateMailTemplate,name="updateMailTemplate"),
    path('deleteAddress/',deleteAddress,name="deleteAddress"),
    path('deleteBankDetails/',deleteBankDetails,name="deleteBankDetails"),


    #Manufacture Unit creation
    path('createORUpdateManufactureUnit/',createORUpdateManufactureUnit,name="createORUpdateManufactureUnit"),
    path('obtainManufactureUnitList/',obtainManufactureUnitList,name="obtainManufactureUnitList"),
    path('obtainManufactureUnitDetails/',obtainManufactureUnitDetails,name="obtainManufactureUnitDetails"),
    path('obtainUserListForManufactureUnit/',obtainUserListForManufactureUnit,name="obtainUserListForManufactureUnit"),
    path('obtainIndustryList/',obtainIndustryList,name="obtainIndustryList"),
    path('updateIndustryForManufactureUnit/',updateIndustryForManufactureUnit,name="updateIndustryForManufactureUnit"),
    path('obtainIndustryForManufactureUnit/',obtainIndustryForManufactureUnit,name="obtainIndustryForManufactureUnit"),
    path('createIndustry/',createIndustry,name="createIndustry"),

    #Order Details
    path('obtainOrderList/',obtainOrderList,name="obtainOrderList"), 
    path('obtainDealerlist/',obtainDealerlist,name="obtainDealerlist"),
    path('exportOrders/',exportOrders,name="exportOrders"),
    path('createOrder/',createOrder,name="createOrder"),
    path('obtainOrderListForDealer/',obtainOrderListForDealer,name="obtainOrderListForDealer"),
    path('getManufactureBankDetails/',getManufactureBankDetails,name="getManufactureBankDetails"),
    path('conformPayment/',conformPayment,name="conformPayment"),
    path('getorderDetails/',getorderDetails,name="getorderDetails"),
    path('acceptOrRejectOrder/',acceptOrRejectOrder,name="acceptOrRejectOrder"),
    path('notifyBuyerForAvailableProductsInOrder/',notifyBuyerForAvailableProductsInOrder,name="notifyBuyerForAvailableProductsInOrder"),

    #Reorder  
    path('createReorder/',createReorder,name="createReorder"),


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
    path('get_related_products/',get_related_products,name="get_related_products"),
    path('getProductsByTopLevelCategory/',getProductsByTopLevelCategory,name="getProductsByTopLevelCategory"),
    path('updateProduct/',updateProduct,name="updateProduct"),   
    path('updateBulkProduct/',updateBulkProduct,name="updateBulkProduct"),
    path('productCountForDealer/',productCountForDealer,name="productCountForDealer"), 
    path('obtainProductCategoryListForDealer/',obtainProductCategoryListForDealer,name="obtainProductCategoryListForDealer"),
    path('get_highest_priced_product/',get_highest_priced_product,name="get_highest_priced_product"),

    #Upload File
    path('upload_file/',upload_file,name="upload_file"),
    path('save_file/',save_file,name="save_file"),
    path('getColumnFormExcel/',getColumnFormExcel,name="getColumnFormExcel"),


    #Dealer actions
    path('obtainProductsListForDealer/',obtainProductsListForDealer,name="obtainProductsListForDealer"),
    path('obtainDealerDetails/',obtainDealerDetails,name="obtainDealerDetails"), 
    path('obtainDashboardDetailsForDealer/',obtainDashboardDetailsForDealer,name="obtainDashboardDetailsForDealer"),

    # Manufacture Admin Dashboard  
    path('obtainDashboardDetailsForManufactureAdmin/',obtainDashboardDetailsForManufactureAdmin,name="obtainDashboardDetailsForManufactureAdmin"),
    path('manufactureDashboardEachDealerOrderValue/',manufactureDashboardEachDealerOrderValue,name="manufactureDashboardEachDealerOrderValue"),

    #Wishlist actions
    path('createWishList/',createWishList,name="createWishList"),
    path('deleteWishlist/',deleteWishlist,name="deleteWishlist"), 
    path('obtainWishlistForBuyer/',obtainWishlistForBuyer,name="obtainWishlistForBuyer"),

    #Shipping Actions
    path('getAvaliableCarrierList/',getAvaliableCarrierList,name="getAvaliableCarrierList"),

   
]
