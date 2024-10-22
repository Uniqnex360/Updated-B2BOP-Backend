from django.urls import path
from .views import loginUser, obtainProductCategoryList, obtainProductSubCategoryList, obtainProductsList, obtainbrandList, createOrUpdateUserCartItem, updateOrDeleteUserCartItem, obtainUserCartItemList, totalCheckOutAmount, obtainRolesForCreatingUser, checkEmailExistOrNot, createORUpdateUser, createORUpdateManufactureUnit, obtainManufactureUnitList, obtainManufactureUnitDetails


urlpatterns = [

    path('loginUser/',loginUser,name="loginUser"),


    #Manufacture Unit creation
    path('createORUpdateManufactureUnit/',createORUpdateManufactureUnit,name="createORUpdateManufactureUnit"),
    path('obtainManufactureUnitList/',obtainManufactureUnitList,name="obtainManufactureUnitList"),
    path('obtainManufactureUnitDetails/',obtainManufactureUnitDetails,name="obtainManufactureUnitDetails"),

    #User creation
    path('obtainRolesForCreatingUser/',obtainRolesForCreatingUser,name="obtainRolesForCreatingUser"),
    path('checkEmailExistOrNot/',checkEmailExistOrNot,name="checkEmailExistOrNot"),
    path('createORUpdateUser/',createORUpdateUser,name="createORUpdateUser"),


    #Products Show Page
    path('obtainProductCategoryList/',obtainProductCategoryList,name="obtainProductCategoryList"),
    path('obtainProductSubCategoryList/',obtainProductSubCategoryList,name="obtainProductSubCategoryList"),
    path('obtainProductsList/',obtainProductsList,name="obtainProductsList"),
    path('obtainbrandList/',obtainbrandList,name="obtainbrandList"),
    path('createOrUpdateUserCartItem/',createOrUpdateUserCartItem,name="createOrUpdateUserCartItem"),
    path('updateOrDeleteUserCartItem/',updateOrDeleteUserCartItem,name="updateOrDeleteUserCartItem"),
    path('obtainUserCartItemList/',obtainUserCartItemList,name="obtainUserCartItemList"),
    path('totalCheckOutAmount/',totalCheckOutAmount,name="totalCheckOutAmount"),

    #Upload File
    # path('upload_file/',upload_file,name="upload_file"),

]
