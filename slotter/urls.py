from django.urls import path

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('create/', views.create_section, name='create_section'),
    path('section_created/', views.section_created, name='section_created'),
    path('edit_section/', views.edit_section, name='edit_section'),
    path('section_edited/', views.section_edited, name='section_edited'),
    path('section_deleted/', views.section_deleted, name='section_deleted'),
    path('timeslots/', views.timeslots, name='timeslots'),
    path('choose_timeslots/', views.choose_timeslots, name='choose_timeslots'),
    path('start/', views.start, name='start'),
    path('assign_students/', views.assign_students, name='assign_students'),
    path('calendar/', views.calendar, name='calendar'),
    path('import/', views.import_schedules, name='import_schedules'),
    path('data_imported/', views.data_imported, name='data_imported'),
    path('testing/', views.testing_page, name='testing_page'),
    path('assignment_churn/', views.assignment_churn, name='assignment_churn'),
     path('save_timeslots/', views.save_timeslots_combo, name='save_timeslots_combo'),
    ]

urlpatterns += staticfiles_urlpatterns()
