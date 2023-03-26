from django.db import models
from datetime import date
from django.core.validators import FileExtensionValidator

class Section(models.Model):
    DAYS_CHOICES = [
        ('MW', 'Monday/Wednesday'),
        ('TR', 'Tuesday/Thursday'),
    ]

    YEAR_CHOICES = []
    for r in range(2020, (date.today().year+1)):
        YEAR_CHOICES.append((r, r))

    QUARTER_CHOICES = [
        (0, 'Summer'),
        (1, 'Autumn'),
        (2, 'Winter'),
        (3, 'Spring'),
    ]

    name = models.CharField(max_length=30)
    year = models.IntegerField(choices=YEAR_CHOICES, default=date.today().year)
    quarter = models.IntegerField(choices=QUARTER_CHOICES, default=1)
    instructor = models.CharField(max_length=50)
    seminar_weeks = models.CharField(max_length=7, default='1, 2, 3')
    class_days = models.CharField(choices=DAYS_CHOICES, default='MW', max_length=3)
    class_start_time = models.TimeField()
    class_end_time = models.TimeField()
    spreadsheet = models.FileField(blank=True, null=True, upload_to='uploads/', validators=[FileExtensionValidator(allowed_extensions=['csv'])])

    class Meta:
        ordering = ['name',]

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
    section = models.ManyToManyField(Section)

    def __str__(self):
        return '%s, %s' % (self.get_weekday_display()[0:3], self.start_time.strftime("%-I:%M %p").lower())

class Student(models.Model):
    PRONOUN_CHOICES = [
        ('NS', 'Not specified'),
        ('NB', 'they, them, theirs'),
        ('F', 'she, her, hers'),
        ('M', 'he, him, his'),
        ('PNS', 'Prefer not to specify'),
        ('O', 'Other'),
    ]
    cnetid = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    first_name = models.CharField(max_length=30)
    pronouns = models.CharField(max_length=3, choices=PRONOUN_CHOICES, default='NS')
    timeslots = models.ManyToManyField(Timeslot)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, default=1)

    class Meta:
        ordering = ['section', 'last_name', 'first_name']

    def __str__(self):
        return '%s %s' % (self.first_name, self.last_name)

class Combination(models.Model):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, default=1)
    timeslots = models.ManyToManyField(Timeslot)

    class Meta:
        ordering = ['section',]

    def __str__(self):
        timeslot_list = list(self.timeslots.all())
        return '%s - %s' % (self.section, self.pk)
