from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('timeslots/', views.timeslots, name='timeslots'),
    path('choose_timeslots/', views.choose_timeslots, name='choose_timeslots'),
    path('start/', views.start, name='start'),
    path('assign_students/', views.assign_students, name='assign_students'),
    ]
