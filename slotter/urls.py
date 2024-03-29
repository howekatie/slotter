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
    path('start/', views.start, name='start'),
    path('assign_students/', views.assign_students, name='assign_students'),
    path('calendar/', views.calendar, name='calendar'),
    path('import/', views.import_schedules, name='import_schedules'),
    path('data_imported/', views.data_imported, name='data_imported'),
    path('assignment_churn/', views.assignment_churn, name='assignment_churn'),
    path('save_timeslots/', views.save_timeslots_combo, name='save_timeslots_combo'),
    path('set_timeslot_session_data/', views.set_timeslot_session_data, name='set_timeslot_session_data'),
    path('delete_timeslot_combo/', views.delete_timeslot_combo, name='delete_timeslot_combo'),
    path('csv_guidelines/', views.csv_guidelines, name='csv_guidelines'),
    path('write_assignments_csv/', views.write_assignments_csv, name='write_assignments_csv'),
    path('set_csv_session_data/', views.set_csv_session_data, name='set_csv_session_data'),
    ]

urlpatterns += staticfiles_urlpatterns()