from django.urls import path 
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

router.register("properties-crud",views.PropertyViewSet)

urlpatterns = [
    path("" , views.home , name="home"),
    path('properties/', views.property_list, name='property_list'),
    path('properties/add/',           views.property_add,    name='property_add'),
    path('properties/<int:pk>/',      views.property_detail, name='property_detail'),
    path('properties/<int:pk>/edit/', views.property_edit,   name='property_edit'),
    path('properties/<int:pk>/delete/', views.property_delete, name='property_delete'),
]

urlpatterns+=router.urls