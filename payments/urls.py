from django.urls import path

from rest_framework.routers import DefaultRouter
from .apiviews import AccountViewSet, UserCreate, LoginView, FundCreation, FundDestruction, TransferFunds, \
    TransferLogView, CreateLoan, PayLoan, GetLoanStatus

router = DefaultRouter()
router.register('accounts', AccountViewSet, basename='accounts')

urlpatterns = [
    path('users/', UserCreate.as_view(), name="user_create"),
    path("login/", LoginView.as_view(), name="login"),
    path("createfunds/", FundCreation.as_view(), name="fund_creation"),
    path('burnfunds/<int:account_pk>/', FundDestruction.as_view(), name="burn_funds"),
    path('transferfunds/<int:destination_account_pk>/', TransferFunds.as_view(), name="transfer_funds"),
    path('transferlogs/', TransferLogView.as_view(), name="transfer_logs"),
    path('createloan/', CreateLoan.as_view(), name="create_loan"),
    path('payloan/', PayLoan.as_view(), name="pay_loan"),
    path('loanstatus/<int:loan_pk>/', GetLoanStatus.as_view(), name="get_loan_status")
]

urlpatterns += router.urls
