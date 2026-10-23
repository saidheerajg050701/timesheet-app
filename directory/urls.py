from django.urls import path

from directory import views

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("profile/", views.profile, name="profile"),
]
