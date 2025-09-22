from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, activate_view, news_list, ArticleView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('activate/', activate_view, name='activate'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('news/', news_list, name='news_list'),
    path('articles/', ArticleView.as_view(), name='articles'),
]