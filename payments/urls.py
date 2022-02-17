from django.urls import path

from rest_framework.routers import DefaultRouter
from payments.apiviews import UserAPIViews, TransactionsAPIViews, LoanAPIViews

router = DefaultRouter()
router.register('accounts', UserAPIViews.AccountViewSet, basename='accounts')

urlpatterns = [
    path('users/', UserAPIViews.UserCreate.as_view(), name="user_create"),
    path("login/", UserAPIViews.LoginView.as_view(), name="login"),
    path("createfunds/", TransactionsAPIViews.FundCreation.as_view(), name="fund_creation"),
    path('burnfunds/<int:account_pk>/', TransactionsAPIViews.FundDestruction.as_view(), name="burn_funds"),
    path('transferfunds/<int:destination_account_pk>/', TransactionsAPIViews.TransferFunds.as_view(),
         name="transfer_funds"),
    path('transferlogs/', TransactionsAPIViews.TransferLogView.as_view(), name="transfer_logs"),
    path('createloan/', LoanAPIViews.CreateLoan.as_view(), name="create_loan"),
    path('payloan/', LoanAPIViews.PayLoan.as_view(), name="pay_loan"),
    path('loanstatus/<int:loan_pk>/', LoanAPIViews.GetLoanStatus.as_view(), name="get_loan_status")
]

urlpatterns += router.urls
