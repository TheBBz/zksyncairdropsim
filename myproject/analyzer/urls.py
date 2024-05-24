from django.urls import path
from .views import analyze_wallet

urlpatterns = [
    path('analyze', analyze_wallet, name='analyze_wallet'),
]
