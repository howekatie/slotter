from django import forms
from django.core.exceptions import ValidationError

class SelectTimeslots(forms.Form):
	def __init__(self, *args, **kwargs):
		t = kwargs.pop("t")
		self.number = kwargs.pop("number")
		self.class_t = kwargs.pop("class_t")
		self.combos = kwargs.pop("combos")
		self.caps = kwargs.pop("caps")
		max_s = kwargs.pop("max_s")
		super(SelectTimeslots, self).__init__(*args, **kwargs)

		# making variable # of form fields

		n = 1
		while n <= self.number:
			self.fields["slot" + str(n)] = forms.ChoiceField(choices=t, label="Slot " + str(n),)
			self.fields["n_students" + str(n)] = forms.IntegerField(min_value=2, max_value=max_s, label="#:")
			n = n + 1

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
			n_students = cleaned_data.get("n_students" + str(n))
			n_students_by_timeslot[timeslot] = n_students
			n = n + 1
		for timeslot in n_students_by_timeslot:
			if n_students_by_timeslot[timeslot] > self.caps[timeslot]:
				self.add_error(None, ValidationError('Students assigned (%(x)s) to %(ts)s exceeds number of students available for this timeslot (%(y)s)', params={'ts': timeslot, 'x': n_students_by_timeslot[timeslot], 'y': self.caps[timeslot],},))

		# checking that timeslot selections constitute a valid combination

		n = 1
		timeslot_choices = []
		while n <= self.number:
			timeslot = cleaned_data.get("slot" + str(n))
			timeslot_choices.append(timeslot)
			n = n + 1
		timeslot_choices.sort()
		if timeslot_choices not in self.combos:
			if len(timeslot_choices) != len(set(timeslot_choices)):
				self.add_error(None, ValidationError('Duplicate choices selected'))
			else:
				self.add_error(None, ValidationError('Selections do not constitute a valid combination of timeslots'))
		return cleaned_data

class InitialSetup(forms.Form):
	min_students = forms.IntegerField(label='Min number of students per seminar group', min_value=2, max_value=10)
	n_seminars = forms.IntegerField(label='Number of seminar groups', min_value=2, max_value=10)