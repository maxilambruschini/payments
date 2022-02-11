from django.urls import path

from .apiviews import AccountView, UserCreate, LoginView, FundCreation, FundDestruction, TransferFunds


urlpatterns = [
    path('users/', UserCreate.as_view(), name="user_create"),
    path("login/", LoginView.as_view(), name="login"),
    path("accounts/", AccountView.as_view(), name="accounts"),
    path("createfunds/", FundCreation.as_view(), name="fund_creation"),
    path('burnfunds/<int:account_pk>/', FundDestruction.as_view(), name="burn_funds"),
    path('transferfunds/<int:destination_account_pk>/', TransferFunds.as_view(), name="transfer_funds")
]