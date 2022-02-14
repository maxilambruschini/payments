from django.urls import path

from rest_framework.routers import DefaultRouter
from .apiviews import AccountViewSet, UserCreate, LoginView, FundCreation, FundDestruction, TransferFunds,\
    TransactionView


router = DefaultRouter()
router.register('accounts', AccountViewSet, basename='accounts')

urlpatterns = [
    path('users/', UserCreate.as_view(), name="user_create"),
    path("login/", LoginView.as_view(), name="login"),
    path("createfunds/", FundCreation.as_view(), name="fund_creation"),
    path('burnfunds/<int:account_pk>/', FundDestruction.as_view(), name="burn_funds"),
    path('transferfunds/<int:destination_account_pk>/', TransferFunds.as_view(), name="transfer_funds"),
    path('transactions/', TransactionView.as_view(), name="transactions")
]

urlpatterns += router.urls