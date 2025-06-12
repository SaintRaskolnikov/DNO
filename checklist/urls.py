from django.urls import path
from . import views

urlpatterns = [
    path('checklist/<str:dno>', views.checklist_view, name='checklist'),
    path('', views.landing, name='landing'),
]