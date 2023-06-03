from django import forms
from django.forms import ModelMultipleChoiceField, ModelForm
from slotter.models import Section, Student, Timeslot, Combination
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from datetime import date

def file_size(value):
	limit = 100 * 1024
	if value.size > limit:
		raise ValidationError('File is too large. Size should not exceed 100 kb,')

class TimeslotChoiceField(forms.ChoiceField):
	def to_python(self, value):
		return int(value)

class CombinationChoiceField(forms.ModelChoiceField):
	def label_from_instance(self, obj):
		timeslot_list = obj.timeslots.all()
		new_timeslot_list = []
		for time in timeslot_list:
			new = time.get_weekday_display()[0:3] + ' ' + time.start_time.strftime("%-I:%M %p").lower()
			new_timeslot_list.append(new)
		delimiter = ', '
		timeslot_string = delimiter.join(new_timeslot_list)
		return f'{timeslot_string}'

class SelectTimeslots(forms.Form):
	def __init__(self, *args, **kwargs):
		self.t = kwargs.pop("t")
		self.number = kwargs.pop("number")
		self.class_t = kwargs.pop("class_t")
		self.combos = kwargs.pop("combos")
		self.caps = kwargs.pop("caps")
		max_s = kwargs.pop("max_s")
		super(SelectTimeslots, self).__init__(*args, **kwargs)

		# check if the # of students in the class and the # of timeslots mean that the students can be divided evenly into groups

		class_division_quot = divmod(self.class_t, self.number)[0]
		class_division_remainder = divmod(self.class_t, self.number)[1]

		# making variable # of form fields

		n = 1
		while n <= self.number:
			self.fields["slot" + str(n)] = TimeslotChoiceField(choices=self.t, label="Slot " + str(n))
			if class_division_remainder == 0:
				self.fields["n_students" + str(n)] = forms.IntegerField(min_value=2, max_value=max_s, label="#:", initial=class_division_quot)
			else: 
				self.fields["n_students" + str(n)] = forms.IntegerField(min_value=2, max_value=max_s, label="#:")
			n = n + 1
		FIRST_TEN = [
			(True, 'Just give me the first 10'),
			(False, 'Show me all the options'),
		]
		self.fields["first_ten"] = forms.ChoiceField(choices=FIRST_TEN, widget=forms.RadioSelect, label="Number of options?")

	def clean(self):
		cleaned_data = super().clean()
		
		# checking that total # of students in the class == sum of all n_students fields

		total_student_n = []
		n = 1
		while n <= self.number:
			students = cleaned_data.get("n_students" + str(n))
			total_student_n.append(students)
			n = n + 1
		total_student_n = sum(total_student_n)
		if total_student_n != self.class_t:
			self.add_error(None, ValidationError('Total students (%(total)s) do not add up to the number of students in the class (%(class_n)s)', params={'class_n': self.class_t, 'total': total_student_n},))
		
		# checking that the # of students for each timeslot doesn't exceed the # of students available for that time

		n = 1
		n_students_by_timeslot = {}
		while n <= self.number:
			timeslot = cleaned_data.get("slot" + str(n))
			timeslot_obj = Timeslot.objects.get(pk=timeslot)
			day = timeslot_obj.weekday
			start_time = timeslot_obj.start_time
			timeslot = (day, start_time)
			n_students = cleaned_data.get("n_students" + str(n))
			n_students_by_timeslot[timeslot] = n_students
			n = n + 1
		for timeslot in n_students_by_timeslot:
			if n_students_by_timeslot[timeslot] > self.caps[timeslot]:
				self.add_error(None, ValidationError('Students assigned (%(x)s) to %(ts)s exceeds number of students available for this timeslot (%(y)s)', params={'ts': timeslot_obj, 'x': n_students_by_timeslot[timeslot], 'y': self.caps[timeslot],},))

		# checking that timeslot selections constitute a valid combination

		n = 1
		timeslot_choices = []
		while n <= self.number:
			timeslot = cleaned_data.get("slot" + str(n))
			timeslot = Timeslot.objects.get(pk=timeslot)
			day = timeslot.weekday
			start_time = timeslot.start_time
			timeslot = (day, start_time)
			timeslot_choices.append(timeslot)
			n = n + 1
		timeslot_choices.sort()
		timeslot_choices = tuple(timeslot_choices)
		if timeslot_choices not in self.combos:
			if len(timeslot_choices) != len(set(timeslot_choices)):
				self.add_error(None, ValidationError('Duplicate choices selected'))
			else:
				self.add_error(None, ValidationError('Selections do not constitute a valid combination of timeslots'))
		return cleaned_data

class ImportSectionCSV(forms.Form):
	def __init__(self, *args, **kwargs):
		self.section_choices = kwargs.pop("section_choices")
		super(ImportSectionCSV, self).__init__(*args, **kwargs)
		self.fields["section"] = forms.ChoiceField(choices=self.section_choices, label='Section')
		self.fields["spreadsheet"] = forms.FileField(label='Spreadsheet', widget=forms.FileInput(), validators=[FileExtensionValidator(allowed_extensions=['csv']), file_size])

class ConfirmCSVImport(forms.Form):
	def __init__(self, *args, **kwargs):
		self.json_data = kwargs.pop("json_data")
		self.assoc_students = kwargs.pop("assoc_students")
		super(ConfirmCSVImport, self).__init__(*args, **kwargs)
		self.fields["spreadsheet_data"] = forms.CharField(widget=forms.HiddenInput, initial=self.json_data)
		if self.assoc_students > 0:
			self.fields["confirm_delete"] = forms.BooleanField(label='Clear existing data and proceed with import?')

class ChooseSection(forms.Form):
	def __init__(self, *args, **kwargs):
		self.section_choices = kwargs.pop("section_choices")
		super(ChooseSection, self).__init__(*args, **kwargs)
		self.fields["section"] = forms.ChoiceField(choices=self.section_choices, label='Section')

class ChooseQuarter(forms.Form):
	
	YEAR_CHOICES = []
	for r in range(2020, (date.today().year+1)):
		YEAR_CHOICES.append((r, r))
	
	QUARTER_CHOICES = [
    	(0, 'Summer'),
        (1, 'Autumn'),
        (2, 'Winter'),
        (3, 'Spring'),
        ]
	current_month = date.today().month
	if current_month <= 3:
		current_quarter = 2
	elif current_month <= 8:
		current_quarter = 3
	elif current_month >= 9:
		current_quarter = 1
	year = forms.ChoiceField(label='Year', choices=YEAR_CHOICES, initial=date.today().year)
	quarter = forms.ChoiceField(label='Quarter', choices=QUARTER_CHOICES, initial = current_quarter)
	def clean(self):
		cleaned_data = super().clean()
		chosen_year = int(cleaned_data.get("year"))
		chosen_quarter = int(cleaned_data.get("quarter"))
		sections = Section.objects.filter(quarter=chosen_quarter, year=chosen_year)
		if len(sections) == 0:
			self.add_error(None, ValidationError('No saved timeslot combinations for this quarter.'))
		else:
			for section in sections:
				if len(Combination.objects.filter(section=section)) > 1:
					return None
			self.add_error(None, ValidationError('No saved timeslot combinations for this quarter.'))


class CalendarViews(forms.Form):
	def __init__(self, *args, **kwargs):
		self.year = kwargs.pop('year')
		self.quarter = kwargs.pop('quarter')
		super(CalendarViews, self).__init__(*args, **kwargs)

		if self.quarter == None:
			current_month = date.today().month
			if current_month <= 3:
				current_quarter = 2
			elif current_month <= 8:
				current_quarter = 3
			elif current_month >= 9:
				current_quarter = 1
			current_sections = Section.objects.filter(year=date.today().year, quarter=current_quarter)
		else:
			current_sections = Section.objects.filter(year=self.year, quarter=self.quarter)

		options = [('WEEK', 'Week'), ('QUARTER', 'Quarter')]
		
		for section in current_sections:
			combos = len(Combination.objects.filter(section=section))
			if combos > 0:
				self.fields['timeslot_combinations_' + str(section.pk)] = CombinationChoiceField(label=section.name, queryset=Combination.objects.filter(section__pk=section.pk), widget=forms.CheckboxSelectMultiple)

class JumpWeek(forms.Form):
	def __init__(self, *args, **kwargs):
		self.quarter = kwargs.pop('quarter')
		super(JumpWeek, self).__init__(*args, **kwargs)
		
		options = [(1,1),
			(2, 2),
			(3, 3),
			(4, 4),
			(5, 5),
			(6, 6),
			(7, 7),
			(8, 8),
			(9, 9),]
		if self.quarter == 1:
			ten = (10, 9)
			options = options[:8]
			options.append(ten)
		self.fields['jump_to_week'] = forms.ChoiceField(choices=options, label="Jump to Week")

class InitialSetup(forms.Form):
	def __init__(self, *args, **kwargs):
		self.section = kwargs.pop("section")
		super(InitialSetup, self).__init__(*args, **kwargs)

		self.fields['min_students'] = forms.IntegerField(label='Min number of students per seminar group', min_value=2, max_value=10)
		self.fields['n_seminars'] = forms.IntegerField(label='Number of seminar groups', min_value=2, max_value=10)

	def clean(self):
		cleaned_data = super().clean()

		# ensures that the number of seminars * the min number of students per seminar is not > the number of students actually in the selected section

		sec_pk = self.section
		seminar_n = int(cleaned_data.get("n_seminars"))
		min_student_n = int(cleaned_data.get("min_students"))
		student_list = Student.objects.filter(section__pk=sec_pk)
		cap = len(student_list)
		projected_students = seminar_n*min_student_n
		if projected_students > cap:
			self.add_error(None, ValidationError('Seminars × students per seminar exceeds total # of students enrolled'))

		# ensures that the number of seminars specified will actually yield at least one possible combination of timeslots (having too few groups -- like dividing the class in two -- makes it likely that there just won't be any two timeslots that will cover the whole class) --> the current validation below is insufficient, since as long as there are at least as many viable timeslots as there are seminars to be scheduled, the form validation will go through, but if there are no combinations of timeslots that cover the entire class, the timeslots view will still error out. Checking for this before the form goes through would require using some fancy functions like make_combinations and pull_students, and so, it seems like it might make more sense to just funnel all of the validation for this form into an AJAX request? Will have to do some more reading first.

		
		timeslots = Timeslot.objects.filter(section__pk=sec_pk)
		viable_timeslots = []
		for timeslot in timeslots:
			students = timeslot.student_set.filter(section__pk=sec_pk)
			if len(students) >= min_student_n:
				viable_timeslots.append(timeslot)
		if len(viable_timeslots) <= seminar_n:
			self.add_error (None, ValidationError('Too few seminars'))
		

class SaveTimeslotCombo(forms.Form):
	save_ts_combo = forms.BooleanField(label='Save this timeslot combination?', required=False)

class RefineAssignments(forms.Form):
	options = [
		('PRONOUNS', 'Grouping students together by the pronouns they use'),
		('GROUP/AVOID', 'Grouping together/keeping apart specific students'),
		('HANDPICK', 'Handpicking students for some of the selected timeslots'),
	]
	refine_options = forms.MultipleChoiceField(choices=options, label="Refine these assignments by:", widget=forms.CheckboxSelectMultiple)

class HandpickByTimeslot(forms.Form):
	def __init__(self, *args, **kwargs):
		self.selected_timeslots = kwargs.pop("selected_timeslots")
		self.pronouns = kwargs.pop("pronouns")
		self.refining = kwargs.pop("refining")
		self.students = kwargs.pop("students")
		self.timeslot_list = kwargs.pop("timeslot_list")
		super(HandpickByTimeslot, self).__init__(*args, **kwargs)

		GROUP_OR_NOT = [
			('GROUP', 'Group together'),
			('APART', 'Keep apart'),
		]

		if 'HANDPICK' in self.refining and 'PRONOUNS' in self.refining and 'GROUP/AVOID' in self.refining:
			self.fields["balance_by_pronouns"] = forms.MultipleChoiceField(choices=self.pronouns, label="Group students together if they use these pronouns", widget=forms.CheckboxSelectMultiple, required=False)
			self.fields["group_or_avoid"] = forms.ChoiceField(choices=GROUP_OR_NOT, widget=forms.RadioSelect, label="Together or apart:")
			self.fields["students_selected"] = forms.MultipleChoiceField(choices=self.students, label="Choose students:", widget=forms.CheckboxSelectMultiple, required=False)
			self.fields["timeslots_to_handpick"] = forms.MultipleChoiceField(choices=self.selected_timeslots, label="Handpick students for these timeslots:", widget=forms.CheckboxSelectMultiple, required=False)
		elif 'HANDPICK' in self.refining and 'PRONOUNS' in self.refining:
			self.fields["balance_by_pronouns"] = forms.MultipleChoiceField(choices=self.pronouns, label="Group students together if they use these pronouns", widget=forms.CheckboxSelectMultiple, required=False)
			self.fields["timeslots_to_handpick"] = forms.MultipleChoiceField(choices=self.selected_timeslots, label="Handpick for these timeslots:", widget=forms.CheckboxSelectMultiple, required=False)
		elif 'PRONOUNS' in self.refining and 'GROUP/AVOID' in self.refining:
			self.fields["balance_by_pronouns"] = forms.MultipleChoiceField(choices=self.pronouns, label="Group students together if they use these pronouns", widget=forms.CheckboxSelectMultiple, required=False)
			self.fields["group_or_avoid"] = forms.ChoiceField(choices=GROUP_OR_NOT, widget=forms.RadioSelect, label="Together or apart:")
			self.fields["students_selected"] = forms.MultipleChoiceField(choices=self.students, label="Choose students:", widget=forms.CheckboxSelectMultiple, required=False)
		elif 'HANDPICK' in self.refining and 'GROUP/AVOID' in self.refining:
			self.fields["group_or_avoid"] = forms.ChoiceField(choices=GROUP_OR_NOT, widget=forms.RadioSelect, label="Together or apart:")
			self.fields["students_selected"] = forms.MultipleChoiceField(choices=self.students, label="Choose students:", widget=forms.CheckboxSelectMultiple, required=False)
			self.fields["timeslots_to_handpick"] = forms.MultipleChoiceField(choices=self.selected_timeslots, label="Handpick for these timeslots:", widget=forms.CheckboxSelectMultiple, required=False)
		elif 'PRONOUNS' in self.refining:
			self.fields["balance_by_pronouns"] = forms.MultipleChoiceField(choices=self.pronouns, label="Group students together if they use these pronouns", widget=forms.CheckboxSelectMultiple, required=False)
		elif 'HANDPICK' in self.refining and 'PRONOUNS' not in self.refining:
			self.fields["timeslots_to_handpick"] = forms.MultipleChoiceField(choices=self.selected_timeslots, label="Handpick for these timeslots:", widget=forms.CheckboxSelectMultiple, required=False)
		elif 'GROUP/AVOID' in self.refining:
			self.fields["group_or_avoid"] = forms.ChoiceField(choices=GROUP_OR_NOT, widget=forms.RadioSelect, label="Together or apart:")
			self.fields["students_selected"] = forms.MultipleChoiceField(choices=self.students, label="Choose students:", widget=forms.CheckboxSelectMultiple)

	def clean(self):
		cleaned_data = super().clean()
		n_timeslots = len(self.selected_timeslots)
		picked_timeslots = cleaned_data.get("timeslots_to_handpick")
		pronouns = cleaned_data.get("balance_by_pronouns")
		to_group_or_avoid = cleaned_data.get("students_selected")

		if picked_timeslots:
			n_picked = len(picked_timeslots)
			picked_cap = n_timeslots / 2
			
			# checks the number of selections made -- # of selections should be fewer than half the # of total timeslots
			if n_picked > picked_cap:
				self.add_error(None, ValidationError('Too many timeslots selected. Pick no more than %(cap)s.', params={'cap': int(picked_cap),}))

		if pronouns:
			n_pronouns_picked = len(pronouns)
			n_pronoun_options = len(self.pronouns)
			if n_pronouns_picked == n_pronoun_options:
				self.add_error(None, ValidationError('Selecting all pronouns will not refine your assignment options'))

		if to_group_or_avoid:
			if len(to_group_or_avoid) < 2:
				self.add_error(None, ValidationError('You must select more than 1 student to group together or keep apart'))
			seminar_ns = []
			for tup in self.timeslot_list:
				seminar_ns.append(tup[1])
			seminar_ns.sort()
			max_students = seminar_ns[0]
			if len(to_group_or_avoid) > max_students:
				self.add_error(None, ValidationError('You can only select %(cap)s students or fewer to group together or keep apart', params={'cap': max_students,}))
	
class HandpickStudents(forms.Form):
	def __init__(self, *args, **kwargs):
		self.choices_dict = kwargs.pop("choices_dict")
		self.timeslot_list = kwargs.pop("timeslot_list")
		self.only_avail = kwargs.pop("only_avail")
		super(HandpickStudents, self).__init__(*args, **kwargs)

		# generating student options for each selected timeslot
		n = 0
		for timeslot in self.choices_dict:
			student_choices = self.choices_dict[timeslot]
			required_students = []
			for tup in student_choices:
				if tup[1] in self.only_avail:
					required_students.append(tup[0])
			# if there is a student (or students) who must be assigned to the chosen timeslot, they are selected by default
			if len(required_students) > 0:
				field_label = timeslot.get_weekday_display() + ", " + str(timeslot.start_time.strftime("%-I:%M %p").lower())
				self.fields["handpicked_students" + str(n)] = forms.MultipleChoiceField(choices=student_choices, label=field_label, widget=forms.CheckboxSelectMultiple, initial=required_students)
				# passes the pk of the selected timeslot back to views
				self.fields["selected_timeslot" + str(n)] = forms.IntegerField(widget=forms.HiddenInput, initial=timeslot.pk)
				# counts the number of timeslots selected for handpicking - important for form data retrieval in views
				self.fields["timeslot_number"] = forms.IntegerField(widget=forms.HiddenInput, initial=n)
				n = n + 1
			else:
				field_label = timeslot.get_weekday_display() + ", " + str(timeslot.start_time.strftime("%-I:%M %p").lower())
				self.fields["handpicked_students" + str(n)] = forms.MultipleChoiceField(choices=student_choices, label=field_label, widget=forms.CheckboxSelectMultiple)
				# passes the pk of the selected timeslot back to views
				self.fields["selected_timeslot" + str(n)] = forms.IntegerField(widget=forms.HiddenInput, initial=timeslot.pk)
				# counts the number of timeslots selected for handpicking - important for form data retrieval in views
				self.fields["timeslot_number"] = forms.IntegerField(widget=forms.HiddenInput, initial=n)
				n = n + 1

	def clean(self):
		cleaned_data = super().clean()

		# ensures that the # of students selected matches the # of students that are supposed to be selected for that timeslot

		n_timeslots = len(self.choices_dict)
		n = 1
		while n <= n_timeslots:
			student_list = cleaned_data.get("handpicked_students" + str(n))
			n_students_selected = len(student_list)
			timeslot = Timeslot.objects.get(pk=cleaned_data.get("selected_timeslot" + str(n)))
			for tup in self.timeslot_list:
				if tup[0] == timeslot:
					if tup[1] != n_students_selected:
						self.add_error(None, ValidationError('# of students selected (%(n_selected)s) is not equal to # students to be assigned (%(n)s) to %(ts)s', params={'n': tup[1], 'n_selected': n_students_selected, 'ts': timeslot,}))
			n = n + 1

		# ensures that students who can only make one of the selected timeslots are included in handpicked st udents for that timeslot

		n_timeslots = len(self.choices_dict)
		n = 1
		selections_dict = {}
		while n <= n_timeslots:
			student_list = cleaned_data.get("handpicked_students" + str(n))
			new_student_list = []
			for student in student_list:
				student_dj = Student.objects.get(cnetid=student)
				new_student_list.append(student_dj)
			timeslot = Timeslot.objects.get(pk=cleaned_data.get("selected_timeslot" + str(n)))
			selections_dict[timeslot] = new_student_list
			n = n + 1
		for student in self.only_avail:
			timeslot = self.only_avail[student]
			if timeslot in selections_dict:
				if student not in selections_dict[timeslot]:
					self.add_error(None, ValidationError('%(student_x)s must be included in %(ts)s to generate valid assignments', params={'student_x': student, 'ts': timeslot,}))

		# ensures that the same student has not been picked twice

		all_students_selected = []
		for timeslot in selections_dict:
			all_students_selected.extend(selections_dict[timeslot])
		student_count = {}
		for student in all_students_selected:
			if student in student_count:
				student_count[student] += 1
				self.add_error(None, ValidationError('%(student_x)s has been selected for multiple timeslots', params={'student_x': student,}))
			else:
				student_count[student] = 1


	# need to add some custom validations here
	# should at the very least check that the # of students selected is equal to the # of students to be assigned
	# maybe in a future version of this part of the form, it could be open-ended -- that is, if the # of students selected == the # of students assigned, these students just replace the relevant entry in the avail_dict (as is already the case), but if the # of students is < the # of students assigned, then instead, something else in views should kick in to just gut the already generated assignments to look for student combos that include the selecgted students
	# a fancier validation would involve making sure that the user selects students that must be in that timeslot, given the other timeslot selections, so if 

class CreateSection(ModelForm):
	WEEK_CHOICES = []
	for i in range(10):
		WEEK_CHOICES.append((i, i))
	WEEK_CHOICES = WEEK_CHOICES[1:]
	seminar_weeks = forms.MultipleChoiceField(choices=WEEK_CHOICES, widget=forms.CheckboxSelectMultiple)

	def __init__(self, *args, **kwargs):
		if 'instance' in kwargs:
			if kwargs['instance'] is not None:
				kwargs['initial'] = {}
				seminar_weeks_split = kwargs['instance'].seminar_weeks.split(', ')
				kwargs['initial']['seminar_weeks'] = seminar_weeks_split
		super().__init__(*args, **kwargs)

	
	def clean_seminar_weeks(self):
		sem_weeks = self.cleaned_data['seminar_weeks']
		self.cleaned_data['seminar_weeks'] = ', '.join(sem_weeks)
		return self.cleaned_data['seminar_weeks']

	def save(self, *args, **kwargs):
		instance = super(CreateSection, self).save(*args, **kwargs)
		instance.seminar_weeks = self.cleaned_data['seminar_weeks']
		instance.save()
		return instance

	class Meta:
		model = Section
		fields = ['name', 'year', 'quarter', 'instructor', 'class_days', 'class_start_time', 'class_end_time', 'seminar_weeks']

		widgets = {
			'class_start_time': forms.TimeInput(attrs={'type': 'time'}),
			'class_end_time': forms.TimeInput(attrs={'type': 'time'}),
		}

class ShowSavedCombos(forms.Form):
	def __init__(self, *args, **kwargs):
		self.section_list = kwargs.pop('section_list')
		super(ShowSavedCombos, self).__init__(*args, *kwargs)

		for section in self.section_list:
			label = section.name + ' (Weeks ' + section.seminar_weeks + ')'
			self.label_suffix = ""
			self.fields['combos_for_sec_' + str(section.pk)] = CombinationChoiceField(label=label, queryset=Combination.objects.filter(section=section), widget=forms.CheckboxSelectMultiple)
