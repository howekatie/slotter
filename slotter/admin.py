from django.contrib import admin

from .models import Student, Timeslot, Section, Combination

admin.site.register(Student)
admin.site.register(Timeslot)
admin.site.register(Section)
admin.site.register(Combination)