from django.db import models

class Section(models.Model):
    name = models.CharField(max_length=30)

    def __str__(self):
        return self.name

class Timeslot(models.Model):
    class Weekday(models.IntegerChoices):
        MON = 0, 'Monday'
        TUE = 1, 'Tuesday'
        WED = 2, 'Wednesday'
        THUR = 3, 'Thursday'
        FRI = 4, 'Friday'

    class Meta:
        ordering = ['weekday', 'start_time']

    weekday = models.IntegerField(choices=Weekday.choices, default=Weekday.MON)
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration = models.IntegerField(default=2)
    viable = models.BooleanField(default=False)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, default=1)

    def __str__(self):
        return '(%s, %s)' % (self.get_weekday_display(), self.start_time)

class Student(models.Model):
    cnetid = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    first_name = models.CharField(max_length=30)
    timeslots = models.ManyToManyField(Timeslot)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, default=1)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)
