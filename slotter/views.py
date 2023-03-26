from django.shortcuts import render

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import loader

from django import forms

from .models import Student, Timeslot, Section, Combination
from .utils import get_students_from_time, get_availabilities, make_class_list, make_combinations, pull_students, will_combo_together, convert_to_timeslot_object, convert_timeslot_list_to_objects, convert_timeslots_in_dict_to_objects, in_minutes, in_hours_and_minutes, timetable_range, timetable, find_rowspans, determine_timeslot_duration, timetable_with_rowspans, write_out_n, availabilities_by_timeslot, student_availability, any_required_timeslots, least_available_students, reverse_keys_and_vals, recommended_pairings, define_week, define_quarter, find_date_by_week, fix_timeslots_by_week, convert_to_pyth_time, convert_list_to_pyth_time, find_week_in_quarter, any_timeslot_conflicts, quarter_table, multiple_section_timeslots_by_week, full_quarter_schedule, timeslots_for_quarter_by_date, conflicts_full_quarter, conflicts_integrated, get_chosen_combos, seminars_by_week, active_week_combos, find_first_active_week, make_combo_label, label_combos, basic_student_data, full_spreadsheet, get_time_headers, mine_timeslot, mine_timeslots, mine_student_availability, get_earliest_start, get_latest_end, get_timeslot_column, timeslot_durations, add_student, add_students, add_timeslot, add_timeslots, student_avail_starts, save_students, save_timeslots, add_timeslots_to_students, provisional_timetable, timeslot_pk_lookup_dict, all_combos_for_quarter, combination_lookup
from .forms import SelectTimeslots, InitialSetup, HandpickByTimeslot, HandpickStudents, RefineAssignments, ChooseSection, SaveTimeslotCombo, CalendarViews, JumpWeek, ChooseQuarter, ImportSectionCSV, ConfirmCSVImport, CreateSection, ClearImportedData, DummyForm

from datetime import time, date, datetime, timedelta

from random import choice

import csv

from json import dumps


# form elements within timeslots.html

def timeslot_options(n):
    option = "Option"
    option_list = []
    m = 1
    while m <= n:
        label = option + " " + str(m)
        option_list.append(label)
        m = m + 1
    return option_list

def narrow_down_selectable_options(options, lookup_dict_dj):
    """
    Will be used in form validation, I think? Also possibly in determining the options available in a given dropdown field.
    Options is a list, where the assumption is that all of the options selected in the list thus far (including previous rounds of selection) are a part of that list. Also, these options should be Timeslot objects, not regular Python times. If this is the first selection, there will be only one item in the list, and so, only the first part of the function will kick in. If there have been two or more selections, the rest will. There is no built-in limit on the number of Timeslots that can be added to this list. So, restricting the number of selections to the number of seminars there are supposed to be is a check that will have to happen elsewhere.
    """
    if len(options) == 1:
        option = options[0]
        return lookup_dict_dj[option]
    else:
        active_time1 = options[0]
        active_time2 = options[1]
        active_options1 = set(lookup_dict_dj[active_time1])
        active_options2 = set(lookup_dict_dj[active_time2])
        overlap = active_options1.intersection(active_options2)
        if len(options) == 2:
            overlap = list(overlap)
            return overlap
        else:
            options = options[2:]
            while len(options) >= 1:
                existing_options = overlap
                comparison_time = options[0]
                comp_options = set(lookup_dict_dj[comparison_time])
                overlap = existing_options.intersection(comp_options)
                if len(options) == 1:
                    overlap = list(overlap)
                    return overlap
                else:
                    options = options[1:]


def timeslot_choice_field(timeslots_dj, working_combos, timeslot_list):
    """
    Creates the list of tuples that make up the choices for all Timeslot choice fields
    T[0] is a str version with the form "(0, datetime.time(9, 30))"
    T[1] is the Timeslot object version of this -- so it will display the label associated with the object
    """
    timeslot_tups = []
    for time in timeslot_list:
        time_dj = convert_to_timeslot_object(time, timeslots_dj)
        tup = (time_dj.id, time_dj)
        timeslot_tups.append(tup)
    return timeslot_tups

def add_blank_field(choice_list):
    """
    Adds a blank field as the first option in a list of tuple choices meant to populate a select form field.
    """
    choice_list.insert(0, ('', '-----------'))
    return choice_list

def working_combos_form_validation(combos, timeslots_dj):
    """
    For form field validation -- converts working_combos to strings so that these can be matched up with the cleaned values the form fields spit out
    """
    new_combos = []
    new_combo = []
    for combo in combos:
        for timeslot in combo:
            new_timeslot = convert_to_timeslot_object(timeslot, timeslots_dj)
            new_combo.append(new_timeslot)
        new_combos.append(new_combo)
        new_combo = []
    return new_combos

def working_combos_pk(dj_combos):
    new_combos = []
    for combo in dj_combos:
        new_combo = []
        for timeslot in combo:
            new = timeslot.pk
            new_combo.append(new)
        new_combos.append(new_combo)
    return new_combos

def combo_lookup_dict_pk(pk_lookup_dict, pk_working_combos):
    combo_dict = {}
    for pk in pk_lookup_dict:
        combo_list = []
        for combo in pk_working_combos:
            if pk in combo:
                combo_list.append(combo)
        combo_dict[pk] = combo_list
    return combo_dict

def student_cap_by_timeslot(min_n, timeslots_dj, sec_name):
    """
    For form field validation, passed along to forms.py -- a dict indicating how many students are available for each timeslot
    """
    student_caps = {}
    avail = get_availabilities(min_n, timeslots_dj, sec_name)
    for timeslot in avail:
        students = avail[timeslot]
        cap = len(students)
        student_caps[timeslot] = cap
    return student_caps

def make_selected_timeslots_list(form_data):
    timeslots_list = []
    for selection in form_data:
        timeslot = Timeslot.objects.get(pk=selection[0])
        day = timeslot.weekday
        start_time = timeslot.start_time
        timeslot = (day, start_time)
        new_selection = (timeslot, selection[1])
        timeslots_list.append(new_selection)
    return timeslots_list

def get_just_selected_timeslots(timeslots_list):
    new_list = []
    for tup in timeslots_list:
        new_list.append(tup[0])
    return new_list

def make_selected_timeslots_list_dj(form_data):
    timeslots_list = []
    for selection in form_data:
        timeslot = Timeslot.objects.get(pk=selection[0])
        assign_n_students = selection[1]
        new_selection = (timeslot, assign_n_students)
        timeslots_list.append(new_selection)
    return timeslots_list

def selected_timeslots_for_json(form_data):
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",]
    lookup_dict = {}
    for selection in form_data:
        timeslot_pk = selection[0]
        timeslot = Timeslot.objects.filter(pk=timeslot_pk).values('weekday', 'start_time', 'end_time')
        lookup_dict[timeslot_pk] = timeslot[0]
    for timeslot in lookup_dict:
        lookup_dict[timeslot]['weekday'] = weekdays[lookup_dict[timeslot]['weekday']][0:3]
        lookup_dict[timeslot]['start_time'] = lookup_dict[timeslot]['start_time'].strftime("%-I:%M %p").lower()
        lookup_dict[timeslot]['end_time'] = lookup_dict[timeslot]['end_time'].strftime("%-I:%M %p").lower()
    return lookup_dict

def students_for_json(sec_name):
    lookup_dict = {}
    students = Student.objects.filter(section__name=sec_name)
    for student in students:
        lookup_dict[student.pk] = Student.objects.filter(pk=student.pk).values('cnetid', 'last_name', 'first_name', 'pronouns')[0]
    return lookup_dict

def students_cnet_to_pk(sec_name):
    lookup_dict = {}
    students = Student.objects.filter(section__name=sec_name)
    for student in students:
        lookup_dict[student.cnetid] = Student.objects.filter(pk=student.pk).values('pk', 'last_name', 'first_name', 'pronouns')[0]
    return lookup_dict

def selected_avail_dict(timeslot_list, avail_dict):
    selected_dict = {}
    for tup in timeslot_list:
        timeslot = tup[0]
        if timeslot in avail_dict:
            selected_dict[timeslot] = avail_dict[timeslot]
    return selected_dict

def convert_avail_dict(avail_dict, timeslots_dj, class_list_dj):
    avail_dict_dj = {}
    for timeslot in avail_dict:
        timeslot_dj = convert_to_timeslot_object(timeslot, timeslots_dj)
        students = avail_dict[timeslot]
        students_dj = []
        for student in students:
            student_dj = convert_to_student_object(student, class_list_dj)
            students_dj.append(student_dj)
        avail_dict_dj[timeslot_dj] = students_dj
    return avail_dict_dj

def student_choice_field(student_list):
    student_tups = []
    for student in student_list:
        tup = (student.cnetid, student)
        student_tups.append(tup)
    return student_tups

def student_choices_by_timeslot(selected_timeslots, avail_dict_dj):
    choice_tups = {}
    for selected in selected_timeslots:
        timeslot = Timeslot.objects.get(pk=int(selected))
        if timeslot in avail_dict_dj:
            students = avail_dict_dj[timeslot]
            student_choices = student_choice_field(students)
            choice_tups[timeslot] = student_choices
    return choice_tups

def handpicked_students_for_timeslots(form_data):
    avail_dict = {}
    for time in form_data:
        timeslot_dj= Timeslot.objects.get(pk=time)
        timeslot = (timeslot_dj.weekday, timeslot_dj.start_time)
        handpicked_students = form_data[time]
        avail_dict[timeslot] = handpicked_students
    return avail_dict

def replace_with_handpicked(avail_dict, handpicked):
    new_avail_dict = {}
    for timeslot in avail_dict:
        if timeslot in handpicked:
            new_avail_dict[timeslot] = handpicked[timeslot]
        else:
            new_avail_dict[timeslot] = avail_dict[timeslot]
    return new_avail_dict

def tally_student_availability(avail_dict):
    student_tally = {}
    only_availability = {}
    for timeslot in avail_dict:
        for student in avail_dict[timeslot]:
            if student not in student_tally:
                student_tally[student] = 1
            else:
                student_tally[student] += 1
    for student in student_tally:
        if student_tally[student] == 1:
            for timeslot in avail_dict:
                if student in avail_dict[timeslot]:
                    only_availability[student] = timeslot
    return only_availability

def make_pronoun_choices(class_list):
    choices_from_model = [
        ('NS', 'Not specified'),
        ('NB', 'they, them, theirs'),
        ('F', 'she, her, hers'),
        ('M', 'he, him, his'),
        ('PNS', 'Prefer not to specify'),
        ('O', 'Other'),
    ]
    pronouns_in_class = []
    for student in class_list:
        if student.pronouns not in pronouns_in_class:
            pronouns_in_class.append(student.pronouns)
    pronoun_choices = []
    for pronoun_tup in choices_from_model:
        if pronoun_tup[0] in pronouns_in_class:
            pronoun_choices.append(pronoun_tup)
    return pronoun_choices

def display_students(class_list_dj):
    class_total = len(class_list_dj)
    if class_total < 9:
        increments = divmod(class_total, 2)
        first_column_end = increments[0] + increments[1]
        first_column = class_list_dj[:first_column_end]
        second_column_start = first_column_end
        second_column_end = second_column_start + increments[0]
        second_column = class_list_dj[second_column_start:second_column_end]
        two_columns = [first_column, second_column]
        return two_columns
    else:
        increments = divmod(class_total, 3)
        first_column_end = increments[0] + increments[1]
        first_column = class_list_dj[:first_column_end]
        second_column_start = first_column_end
        second_column_end = second_column_start + increments[0]
        second_column = class_list_dj[second_column_start:second_column_end]
        third_column_start = second_column_end
        third_column = class_list_dj[third_column_start:]
        three_columns = [first_column, second_column, third_column]
        return three_columns


# for assign_students

def make_student_combinations(n, timeslot, avail_dict):
    """
    Takes a timeslot and runs through all the combinations of n students available at that time.
    The resulting dict has keys in the form of tuples, (timeslot, id number), and each value is one possible combination of students.
    """
    listy = avail_dict[timeslot]
    start = n - 1
    start_token = n-2
    right_most = listy[start:]
    combos_so_far = []
    list_wrapper = []
    for item in right_most:
        list_wrapper.append(item)
        combos_so_far.append(list_wrapper)
        list_wrapper = []
    start = start - 1
    upperbound = len(listy) - 2
    new_combo = []
    new_combos = []
    while start >= 0:
        while start <= upperbound:
            for combo in combos_so_far:
                index = 0
                # could replace this with the list.index() method...
                while index <= len(listy) - 1:
                    if listy[index] == combo[0]:
                        bingo = index
                        index = len(listy)
                    else:
                        index = index + 1
                if start < bingo:
                    new_combo.append(listy[start])
                    new_combo.extend(combo)
                    new_combos.append(new_combo)
                    new_combo = []
            start = start + 1
        start_token = start_token - 1
        start = start_token
        upperbound = upperbound - 1
        if start == -1:
            new_dict = {}
            x = 0
            for combo in new_combos:
                key = (timeslot, x)
                new_dict[key] = combo
                x = x + 1
            return new_dict
        combos_so_far = new_combos
        new_combos = []

def student_combos_for_selected_timeslots(timeslots, avail_dict):
    """
    This assumes that when the user selects timeslots and assigns the # of students to each slot, these choices will eventually be fed into this function as a list of tuples in form of (Timeslot, # of students).
    For each such tuple/choice, it runs make_student_combinations, and at the end, it returns a dict containing each of the dicts produced by make_student_combinations.
    So, the top-level dict keys will be timeslot, and the values associated with each of these keys will be the make_student_combinations dict corresponding to that timeslot.
    """
    all_combos = {}
    for tup in timeslots:
        timeslot = tup[0]
        n = tup[1]
        combos = make_student_combinations(n, timeslot, avail_dict)
        all_combos[timeslot] = combos
    return all_combos

def sort_timeslots_by_length(timeslots, avail_dict):
    """
    Orders timeslots by the # of possible ways of assigning students to these timeslots and returns a list. This will be used in the next phase, where we're determining whether the combo of timeslots can actually produce usable student assignments.
    Right now, the ordering is done by determining the # of possible student combinations, but since this is just determined by the # of students who have signed up for that timeslot, using len() on that list might be simpler. (But then again, the # of combinations also depends on how many students will be assigned to a timeslot, so if that # varies between timeslots, the current way of ordering does actually provide a more accurate picture of things.)
    """
    timeslot_dict = student_combos_for_selected_timeslots(timeslots, avail_dict)
    timeslot_list = list(timeslot_dict.keys())
    x = 0
    y = 1
    last = len(timeslot_list) - 1
    sorted_timeslots = []
    while y <= last:
        if len(timeslot_dict[timeslot_list[x]]) <= len(timeslot_dict[timeslot_list[y]]) and y != last:
            y = y + 1
        elif len(timeslot_dict[timeslot_list[x]]) <= len(timeslot_dict[timeslot_list[y]]) and y == last:
            sorted_timeslots.append(timeslot_list[x])
            timeslot_list.pop(x)
            last = len(timeslot_list) - 1
            x = 0
            y = 1
        elif len(timeslot_dict[timeslot_list[x]]) > len(timeslot_dict[timeslot_list[y]]) and y != last:
            x = y
            y = y + 1
        elif len(timeslot_dict[timeslot_list[x]]) > len(timeslot_dict[timeslot_list[y]]) and y == last:
            sorted_timeslots.append(timeslot_list[y])
            timeslot_list.pop(y)
            last = len(timeslot_list) - 1
            x = 0
            y = 1
    sorted_timeslots.append(timeslot_list[0])
    return sorted_timeslots

def no_overlap(list1, list2):
    """
    Takes two lists of students, returns true only if there is no overlap between lists.
    Used with gut_options().
    """
    for x in list1:
        for y in list2:
            if x == y:
                return False
    return True

def gut_options(student_list, combo_dict):
    """
    Takes a list of students (who can meet at a given time)
    Takes a dict with all of the combinations of students that can meet at another time
    Returns a new dict that only has those combinations of students that do not overlap with the provided list
    """
    gutted_combo_dict = {}
    for combo in combo_dict:
        if no_overlap(student_list, combo_dict[combo]):
            gutted_combo_dict[combo] = combo_dict[combo]
    return gutted_combo_dict

def gut_options_final(student_list, combo_dict):
    """
    Performs the same operation as gut_options, only that it is intended for use with the final dict that needs gutting to determine whether or not there is a combo that will work with the given combination set thus far. So, the only difference is what it returns -- the tuple that is the dict key (timeslot, id#) for the combination of students that will in fact work (assuming that there is one).
    """
    for combo in combo_dict:
        if no_overlap(student_list, combo_dict[combo]):
            return combo

def gut_for_all_times(timelist, master_dict, active_list):
    """
    Generates a dict of dicts of gutted student combos for each timeslot by comparing these combos to one given list.
    timelist is the list of timeslots (this list helps the function navigate to the relevant dict of student combos). This should start off as the result of sort_timeslots_by_length but will change as the gutting progresses.
    mastter_dict should be a dict of dicts -- the top-level keys are timeslots, each set of keys in the next dict down is a (timeslot, id#) tuple whose value is a combination of students who can make that time. The actual dict that is used for master_dict changes depending on what stage of the gutting we're at. It starts out with the product of student_combos_for_selected_timeslots() but will change as the relevant megafunction produces gutted results.
    active_list is the list of students that all of the other combos of students are being compared to. This value is determined by the megafuction.
    There are two return options -- the first assumes that we're on the last stage of gutting (since the timelist is down to one time) and so just returns the (timeslot, id#) tuple of the combo that will work with the rest, assuming that there is one. The second is for all of the preceding operations, where what's being returned is actually a new version of the master_dict (now gutted) that will be fed back into this function via the megafunction.
    """
    new_master = {}
    if len(timelist) == 1:
        gutted = gut_options_final(active_list, master_dict[timelist[0]])
        return gutted
    for time in timelist:
        gutted = gut_options(active_list, master_dict[time])
        if len(gutted) == 0:
            return None
        elif len(gutted) > 0:
            new_master[time] = gutted
    return new_master

def working_student_combos(timelist, master_dict, first_ten):
    """
    This is the megafunction that draws on all of the gut-fuctions from above. The timelist should be a list of tuples (to be generated by user selection), each of these tuples should specify a timeslot and the number of students to be assigned to that slot. The master_dict is generated by student_combos_for_selected_timeslots() and contains all of the possible combinations of students for each timeslot, organized of course by timeslot.
    There are 3 stages to the function. The first stage takes the master_dict and selects the first time in the timelist as active time whose student combos will be used to gut the other times' student combo dicts. The resulting dict from this stage is gutted_master, which will then take the place of the master_dict for subsequent guttings.
    The middle stage of the function repeats this process on gutted_master, producing new_gutted_master. Each time this part of the function runs, it takes the first item in the timelist to be the new active time and also redefines the timelist so that this first time is gone from this list. So, the list shrinks by one each time, and when the list only has one item left, the function exits the while loop and moves to the last stage of the function. Also, gutted_master gets redefined as new_gutted master, and new_gutted_master is reset with each loop too, so that the function is always further gutting the number of combos from the remaining dicts.
    In the last stage, the function does something pretty similar to what it's been doing previously, except that what it returns is a list instead of a dict. So, each item in the list is a list, and each such list contains keys for the student combos that will work together and together form a way of assigning all of the students to this combo of times.
    Added 3-6-2023: if first_ten is True, then the function will return the list with the first 10 options. (There to save the user time if desired. Cuts load time to 1/4 or 1/3, depending on the total number of options ot churn through.)
    """
    # first stage
    gutted_master = {}
    active_time = timelist[0]
    active_dict = master_dict[active_time]
    remaining_list = timelist[1:]
    # for combos of 2 only
    if len(remaining_list) == 1:
        combo_list = []
        for student_list in active_dict:
            gutted_combos = gut_for_all_times(remaining_list, master_dict, active_dict[student_list])
            if gutted_combos != None:
                sublist = [student_list, gutted_combos]
                combo_list.append(sublist)
        return combo_list
    for student_list in active_dict:
        gutted_combos = gut_for_all_times(remaining_list, master_dict, active_dict[student_list])
        if gutted_combos != None:
            gutted_master[student_list] = gutted_combos
    active_time = remaining_list[0]
    remaining_list = remaining_list[1:]
    new_gutted_master = {}
    # middle stage
    while len(remaining_list) > 1:
        for x in gutted_master:
            active_dict = gutted_master[x][active_time]
            for y in active_dict:
                gutted_combos = gut_for_all_times(remaining_list, gutted_master[x], active_dict[y])
                if gutted_combos != None:
                    if isinstance(x[0][0], int):
                        key = []
                        key.append(x)
                        key.append(y)
                    else:
                        key = list(x)
                        key.append(y)
                    new_key = tuple(key)
                    new_gutted_master[new_key] = gutted_combos
        active_time = remaining_list[0]
        remaining_list = remaining_list[1:]
        gutted_master = new_gutted_master
        new_gutted_master = {}
    # last stage
    combo_list = []
    for x in gutted_master:
        active_dict = gutted_master[x][active_time]
        for y in active_dict:
            gutted_combos = gut_for_all_times(remaining_list, gutted_master[x], active_dict[y])
            if gutted_combos != None:
                if isinstance(x[0][0], int):
                    keys = []
                    keys.append(x)
                else:
                    keys = list(x)
                keys.append(y)
                keys.append(gutted_combos)
                combo_list.append(keys)
                if first_ten == True and len(combo_list) >= 10:
                    return combo_list
    return combo_list

def working_student_combos_test(timelist, master_dict):
    """
    This is the megafunction that draws on all of the gut-fuctions from above. The timelist should be a list of tuples (to be generated by user selection), each of these tuples should specify a timeslot and the number of students to be assigned to that slot. The master_dict is generated by student_combos_for_selected_timeslots() and contains all of the possible combinations of students for each timeslot, organized of course by timeslot.
    There are 3 stages to the function. The first stage takes the master_dict and selects the first time in the timelist as active time whose student combos will be used to gut the other times' student combo dicts. The resulting dict from this stage is gutted_master, which will then take the place of the master_dict for subsequent guttings.
    The middle stage of the function repeats this process on gutted_master, producing new_gutted_master. Each time this part of the function runs, it takes the first item in the timelist to be the new active time and also redefines the timelist so that this first time is gone from this list. So, the list shrinks by one each time, and when the list only has one item left, the function exits the while loop and moves to the last stage of the function. Also, gutted_master gets redefined as new_gutted master, and new_gutted_master is reset with each loop too, so that the function is always further gutting the number of combos from the remaining dicts.
    In the last stage, the function does something pretty similar to what it's been doing previously, except that what it returns is a list instead of a dict. So, each item in the list is a list, and each such list contains keys for the student combos that will work together and together form a way of assigning all of the students to this combo of times.
    """
    # first stage
    gutted_master = {}
    active_time = timelist[0]
    active_dict = master_dict[active_time]
    remaining_list = timelist[1:]
    # for combos of 2 only
    if len(remaining_list) == 1:
        combo_list = []
        for student_list in active_dict:
            gutted_combos = gut_for_all_times(remaining_list, master_dict, active_dict[student_list])
            if gutted_combos != None:
                sublist = [student_list, gutted_combos]
                combo_list.append(sublist)
        return combo_list
    for student_list in active_dict:
        gutted_combos = gut_for_all_times(remaining_list, master_dict, active_dict[student_list])
        if gutted_combos != None:
            gutted_master[student_list] = gutted_combos
    active_time = remaining_list[0]
    remaining_list = remaining_list[1:]
    new_gutted_master = {}
    # middle stage
    while len(remaining_list) > 1:
        for x in gutted_master:
            active_dict = gutted_master[x][active_time]
            for y in active_dict:
                gutted_combos = gut_for_all_times(remaining_list, gutted_master[x], active_dict[y])
                if gutted_combos != None:
                    if isinstance(x[0], Timeslot):
                        key = []
                        key.append(x)
                        key.append(y)
                    else:
                        key = list(x)
                        key.append(y)
                    new_key = tuple(key)
                    new_gutted_master[new_key] = gutted_combos
        active_time = remaining_list[0]
        remaining_list = remaining_list[1:]
        gutted_master = new_gutted_master
        new_gutted_master = {}
    # last stage
    combo_list = []
    for x in gutted_master:
        active_dict = gutted_master[x][active_time]
        for y in active_dict:
            gutted_combos = gut_for_all_times(remaining_list, gutted_master[x], active_dict[y])
            if gutted_combos != None:
                if isinstance(x[0], Timeslot):
                    keys = []
                    keys.append(x)
                else:
                    keys = list(x)
                keys.append(y)
                keys.append(gutted_combos)
                combo_list.append(keys)
    return combo_list

def make_assignments(combo_list, master_dict):
    """
    Takes the list of lists from working_student_combos() and uses the master_dict (from student_combos_for_selected_timeslots) to pull each student combo and generate the assignments that will work. Returns a dict of dicts. The top-level keys are just id numbers starting from 0, and the next-level keys are the (timeslot, id#) tuples that identify each combo of students. The value for each of these keys is this student combo.
    """
    n = 1
    assignment_dict = {}
    combo_dict = {}
    for key_list in combo_list:
        key_list.sort()
        for key in key_list:
            timeslot_dict = master_dict[key[0]]
            student_list = timeslot_dict[key]
            combo_dict[key] = student_list
        assignment_dict[n] = combo_dict
        n = n + 1
        combo_dict = {}
    return assignment_dict

def convert_to_student_object(student, class_list_dj):
    """
    Takes a cnetid identifying a student and returns the corresponding Student object
    """
    for s in class_list_dj:
        if s.cnetid == student:
            return s

def convert_assgs(assg, class_list_dj, timeslots_dj):
    """
    Takes the assignment dict and returns an equivalent dict with Timeslot objects (as the second-level dict keys) and lists of Student objects
    """
    readable_dict = {}
    subdict = {}
    for key in assg:
        for time_key in assg[key]:
            timeslot = convert_to_timeslot_object(time_key[0], timeslots_dj)
            student_list = assg[key][time_key]
            new_student_list = []
            for student in student_list:
                s = convert_to_student_object(student, class_list_dj)
                new_student_list.append(s)
            subdict[timeslot] = new_student_list
        readable_dict[key] = subdict
        subdict = {}
    return readable_dict

def pronoun_tally(student_list, pronoun_list):
    n = 0
    for student in student_list:
        if student.pronouns in pronoun_list:
            n = n + 1
    return n

def any_singleton_assignments(combo, pronoun_list):
    for timeslot in combo:
        student_list = combo[timeslot]
        count = pronoun_tally(student_list, pronoun_list)
        if count == 1:
            return False
    return True

def gut_singleton_assignments(assg, pronoun_list):
    new_assignments = {}
    for key in assg:
        if any_singleton_assignments(assg[key], pronoun_list):
            new_assignments[key] = assg[key]
    return new_assignments

def without_these_students(students, combo):
    """
    Takes a list of students that should not be put into the same Timeslot assignment and compares them with a combination of students
    """
    verdicts = []
    for s in students:
        if s in combo:
            verdicts.append(True)
        else:
            verdicts.append(False)
    if all(verdicts):
        return False
    else:
        return True

def group_these_students(students, combo):
    """
    Takes a list of students that should be put together into the same Timeslot assignment and compares them with a combination of students
    """
    verdicts = []
    for s in students:
        if s in combo:
            verdicts.append(True)
        else:
            verdicts.append(False)
    if all(verdicts):
        return True
    else:
        return False

def group_or_avoid_combos(students, assg, grouping_action, class_list_dj):
    """
    Uses without_these_students()/group_these_students to return a new dict with only those assignments that do/don't contain the relevant students together
    """
    new_student_list = []
    for student in students:
        student_dj = convert_to_student_object(student, class_list_dj)
        new_student_list.append(student_dj)
    filtered_assg = {}
    if grouping_action == 'APART':
        for key in assg:
            verdicts = []
            for timeslot in assg[key]:
                combo = assg[key][timeslot]
                verdict = without_these_students(new_student_list, combo)
                verdicts.append(verdict)
            if all(verdicts):
                filtered_assg[key] = assg[key]
        return filtered_assg
    elif grouping_action == 'GROUP':
        for key in assg:
            verdicts = []
            for timeslot in assg[key]:
                combo = assg[key][timeslot]
                verdict = group_these_students(new_student_list, combo)
                verdicts.append(verdict)
            if True in verdicts:
                filtered_assg[key] = assg[key]
        return filtered_assg

def display_assgs(assg):
    """
    Returns the actual dict that gets unpacked in the HTML template. Takes the assignment dict (or the filtered assignment dict -- still need to wire that in properly at some point) and returns the full assignment dict if there are less than 15 possible combos. If there are 15+, then it uses random.choice() to pick 10 possibilities to display instead.
    """
    if len(assg) <= 15:
        newly_numbered = {}
        n = 1
        for combo in assg:
            newly_numbered[n] = assg[combo]
            n =n + 1
        return newly_numbered
    else:
        pick_list = list(assg.keys())
        samples = []
        while len(samples) < 10:
            number = choice(pick_list)
            if number not in samples:
                samples.append(number)
        samples.sort()
        sample_dict = {}
        for number in samples:
            sample_dict[number] = assg[number]
        newly_numbered = {}
        n = 1
        for combo in sample_dict:
            newly_numbered[n] = sample_dict[combo]
            n = n + 1
        return newly_numbered

# note to self -- it would be good to write a function that records the combos that don't actually produce any results so that this can be saved (maybe to the db?) as a result that shouldn't be tried again



# was just using these temporarily to import some test data

def add_availabilities_to_students(dicty, class_list_dj, timeslots_dj):
    new_dict = {}
    new_list = []
    for student in dicty:
        student_dj = convert_to_student_object(student, class_list_dj)
        for ts in dicty[student]:
            day = ts[0]
            tup = ts[1]
            ts_dj = convert_to_timeslot_object((day,time(tup[0], tup[1])), timeslots_dj)
            new_list.append(ts_dj)
        new_dict[student_dj] = new_list
        new_list = []
    return new_dict

def actually_add_avails(avail_dict):
    for x in avail_dict:
        for timeslot in avail_dict[x]:
            x.timeslots.add(timeslot)

"""

def add_student(listy):
    sec = listy[3]
    sections = Section.objects.all()
    for s in sections:
        if s.name == sec:
            sec_obj = s
    new_student = Student(cnetid=listy[0], last_name=listy[1], first_name=listy[2], section=sec_obj)   
    new_student.save()

def add_new_students(dicty):
    for x in dicty:
        add_student(dicty[x])

def add_timeslot_entry(listy):
    sec = listy[3]
    sections = Section.objects.all()
    for s in sections:
        if s.name == sec:
            sec_obj = s
    existing = Timeslot.objects.all()
    new_start_time = datetime.strptime(listy[1], '%H:%M').time()
    new_end_time = datetime.strptime(listy[2], '%H:%M').time()
    for time in existing:
        if time.weekday == listy[0] and time.start_time == new_start_time and time.end_time == new_end_time:
            time.section.add(sec_obj)
            return None
    new_timeslot = Timeslot(weekday=listy[0], start_time=listy[1], end_time=listy[2])
    new_timeslot.save()
    new_timeslot.section.add(sec_obj)

def add_timeslot_entries(dicty):
    for entry in dicty:
        add_timeslot_entry(dicty[entry])

"""

def add_timeslot_combo(timeslot_list_dj, sec_name):
    sections = Section.objects.all()
    for s in sections:
        if s.name == sec_name:
            sec_obj = s
    new_combo = Combination(section=sec_obj)
    new_combo.save()
    for timeslot in timeslot_list_dj:
        new_combo.timeslots.add(timeslot)
    new_combo.save()

# test

def convert_assgs_pk(assg, class_list_dj, timeslots_dj):
    """
    Takes the assignment dict and returns an equivalent dict with Timeslot objects (as the second-level dict keys) and lists of Student objects
    """
    readable_dict = {}
    subdict = {}
    for key in assg:
        for time_key in assg[key]:
            timeslot = convert_to_timeslot_object(time_key[0], timeslots_dj).pk
            student_list = assg[key][time_key]
            new_student_list = []
            for student in student_list:
                s = convert_to_student_object(student, class_list_dj).pk
                new_student_list.append(s)
            subdict[timeslot] = new_student_list
        readable_dict[key] = subdict
        subdict = {}
    return readable_dict

def checkbox_count(timeslot_list_dj, selected_avail, tally_student_avail):
    checkbox_count_by_field = {}
    n = 0
    for timeslot_tup in timeslot_list_dj:
        timeslot = timeslot_tup[0]
        timeslot_data = {}
        timeslot_data['n_checkboxes'] = len(selected_avail[timeslot])
        timeslot_data['n_selections'] = timeslot_tup[1]
        timeslot_data['pk'] = timeslot.pk
        required_students = []
        for student in tally_student_avail:
            if tally_student_avail[student] == timeslot:
                required_students.append(student.cnetid)
        timeslot_data['req_students'] = required_students
        checkbox_count_by_field[n] = timeslot_data
        n = n + 1
    return checkbox_count_by_field


def matches_existing_combo(combo, timeslots):
    for timeslot in timeslots:
        if timeslot not in combo.timeslots.all():
            return False
    return True

def unique_timeslot_combo(combos, timeslots):
    verdicts = []
    for combo in combos:
        verdict = matches_existing_combo(combo, timeslots)
        verdicts.append(verdict)
    if True in verdicts:
        return False
    else:
        return True

# the actual views    

def index(request):
    return HttpResponse("Hello, world. This is where the scheduling magic happens.")

def start(request):
    form1 = ChooseSection()
    active_section = request.session.get('active_section')
    if request.method == 'POST':
        if request.POST.get('section'):
            form1 = ChooseSection(request.POST or None)
            request.session['section'] = request.POST['section']
            chosen_section = request.POST['section']
            class_list = Student.objects.filter(section__name=chosen_section)
            class_size = len(class_list)
            timeslots = Timeslot.objects.filter(section__name=chosen_section)
            n_possible_timeslots = len(timeslots)
            section_dj = Section.objects.get(name=chosen_section)
            instructor = section_dj.instructor
            class_days = section_dj.class_days
            class_start_time = section_dj.class_start_time
            class_end_time = section_dj.class_end_time
            class_list_columns = display_students(class_list)
            form2 = InitialSetup(section=chosen_section)
            return render(request, 'slotter/start.html', {
                'form1': form1,
                'form2': form2,
                'class_list': class_list,
                'class_size': class_size,
                'instructor': instructor,
                'class_days': class_days,
                'class_start_time': class_start_time,
                'class_end_time': class_end_time,
                'n_possible_timeslots': n_possible_timeslots,
                'class_list_columns': class_list_columns,
                })
        elif request.POST.get('min_students'):
            chosen_section = request.session.get('section')
            form2 = InitialSetup(request.POST or None, section=chosen_section)
            if form2.is_valid():
                request.session['min_students'] = form2.cleaned_data['min_students']
                request.session['n_seminars'] = form2.cleaned_data['n_seminars']
                return HttpResponseRedirect('/slotter/timeslots/')
            else:
                chosen_section = request.session.get('section')
                class_list = Student.objects.filter(section__name=chosen_section)
                class_size = len(class_list)
                timeslots = Timeslot.objects.filter(section__name=chosen_section)
                n_possible_timeslots = len(timeslots)
                section_dj = Section.objects.get(name=chosen_section)
                instructor = section_dj.instructor
                class_days = section_dj.class_days
                class_start_time = section_dj.class_start_time
                class_end_time = section_dj.class_end_time
                class_list_columns = display_students(class_list)
                return render(request, 'slotter/start.html', {
                'form1': form1,
                'form2': form2,
                'class_list': class_list,
                'class_size': class_size,
                'instructor': instructor,
                'class_days': class_days,
                'class_start_time': class_start_time,
                'class_end_time': class_end_time,
                'n_possible_timeslots': n_possible_timeslots,
                'class_list_columns': class_list_columns,
                })
    template = loader.get_template('slotter/start.html')
    context = {
        'form1': form1,
        'active_section': active_section,
        }
    return HttpResponse(template.render(context, request))

def create_section(request):
    if request.method == 'POST':
        form = CreateSection(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            newest = Section.objects.order_by('-pk')[0].pk
            request.session['active_section'] = newest
            return HttpResponseRedirect('/slotter/section_created/')
    else:
        form = CreateSection()
    template = loader.get_template('slotter/create_section.html')
    context = {
        'form': form,
    }
    return HttpResponse(template.render(context, request))

def edit_section(request):
    form0 = ChooseSection()
    active_section_pk = request.session.get('active_section')
    if request.method == 'POST':
        if request.POST.get('section'):
            form0 = ChooseSection(request.POST)
            section_name = request.POST['section']
            active_section = Section.objects.get(name=section_name)
            request.session['active_section'] = active_section.pk
            form = CreateSection(instance=active_section)
            return render(request, 'slotter/edit_section.html', {
                'form0': form0,
                'form': form,
                'active_section': active_section,
            })
        else:
            active_section_pk = request.session.get('active_section')
            active_section = Section.objects.get(pk=active_section_pk)
            form = CreateSection(request.POST, request.FILES, instance=active_section)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect('/slotter/section_edited/')
            else:
                template = loader.get_template('slotter/edit_section.html')
                context = {
                    'form': form,
                    'form0': form0,
                }
                return HttpResponse(template.render(context, request))
    if active_section_pk != None:
        active_section = Section.objects.get(pk=active_section_pk)
        form = CreateSection(instance=active_section)
    else:
        form = None
        active_section = None
    template = loader.get_template('slotter/edit_section.html')
    context = {
        'form': form,
        'form0': form0,
        'active_section': active_section,
    }
    return HttpResponse(template.render(context, request))

def section_created(request):
    active_section_pk = request.session.get('active_section')
    active_section = Section.objects.get(pk=active_section_pk)
    template = loader.get_template('slotter/section_created.html')
    context = {
        'active_section': active_section,
    }
    return HttpResponse(template.render(context, request))

def section_edited(request):
    active_section_pk = request.session.get('active_section')
    active_section = Section.objects.get(pk=active_section_pk)
    template = loader.get_template('slotter/section_edited.html')
    context = {
        'active_section': active_section,
    }
    return HttpResponse(template.render(context, request))

def section_deleted(request):
    active_section_pk = request.session.get('active_section')
    active_section = Section.objects.get(pk=active_section_pk)
    deleted_section_name = active_section.name
    active_section.delete()
    request.session['active_section'] = None
    template = loader.get_template('slotter/section_deleted.html')
    context = {
        'deleted_section_name': deleted_section_name,
    }
    return HttpResponse(template.render(context, request))

def data_imported(request):
    active_section_pk = request.session.get('active_section')
    active_section = Section.objects.get(pk=active_section_pk)
    possible_timeslots_n = len(Timeslot.objects.filter(section__pk=active_section_pk))
    class_list = Student.objects.filter(section__pk=active_section_pk)
    class_size = len(class_list)
    class_list_columns = display_students(class_list)
    template = loader.get_template('slotter/schedules_imported.html')
    context = {
        'active_section': active_section,
        'class_list': class_list,
        'class_size': class_size,
        'class_list_columns': class_list_columns,
        'possible_timeslots_n': possible_timeslots_n,
    }
    return HttpResponse(template.render(context, request))

def find_thanksgiving(year):
    nov_first = date(year, 11, 1).weekday()
    difference = 3 - nov_first
    if nov_first < 4:
        thanksgiving = 22 + difference
    elif nov_first >= 4:
        thanksgiving = 29 + difference
    return date(year, 11, thanksgiving)

def fall_first_monday(year):
    nov_first = date(year,11,1).weekday()
    if nov_first < 4:
        difference = 3 - nov_first
        thanksgiving = 22 + difference
    elif nov_first >= 4:
        difference = 3 - nov_first
        thanksgiving = difference + 29
    first_thur = date(year,11,thanksgiving) - timedelta(days=(8*7))
    first_mon = first_thur - timedelta(days=3)
    return first_mon

def winter_first_monday(year):
    jan_first = date(year,1,1).weekday()
    if jan_first == 0:
        first_mon = date(year,1,1)
    elif jan_first == 6:
        first_mon = date(year,1,1) + timedelta(days=1)
    elif jan_first > 0:
        weekday_difference = 0 - jan_first
        difference = weekday_difference + 7
        first_mon = date(year,1,1) + timedelta(difference)
    return first_mon

def spring_first_monday(year):
    winter_first_mon = winter_first_monday(year)
    first_mon = winter_first_mon + timedelta(11*7)
    return first_mon

def set_first_monday(year, quarter):
    if quarter == 1:
        return fall_first_monday(year)
    elif quarter == 2:
        return winter_first_monday(year)
    elif quarter == 3:
        return spring_first_monday(year)

def json_time(time):
    if isinstance(time, (datetime, date)):
        return str(time.year) + "-" + str(time.month) + '-' + str(time.day)

def json_time_dict(time_dict):
    json_dict = {}
    for key in time_dict:
        for time in time_dict[key]:
            new_time = json_time(time)
            empty_list = []
            json_dict[new_time] = empty_list
    return json_dict

def json_week_by_week_cal(quarter_cal):
    json_dict = {}
    for week in quarter_cal:
        json_week = []
        for time in quarter_cal[week]:
            json_week.append(json_time(time))
        json_dict[week] = json_week
    return json_dict

def combo_count_by_section(sections):
    section_list = []
    for section in sections:
        if section.combination_set.all().count() > 0:
            section_dict = {}
            section_dict['pk'] = section.pk
            section_dict['count'] = section.combination_set.all().count()
            section_dict['name'] = section.name
            section_list.append(section_dict)
    return section_list

def calendar(request):
    chosen_year = None
    chosen_quarter = None
    form0 = ChooseQuarter()
    form = CalendarViews(year=chosen_year, quarter=chosen_quarter)
    if request.method == 'POST':
        if request.POST.get('year'):
            form0 = ChooseQuarter(request.POST or None)
            if form0.is_valid():
                request.session['year'] = request.POST.get('year')
                request.session['quarter'] = request.POST.get('quarter')
                form2 = JumpWeek(quarter=chosen_quarter)
                chosen_year = int(request.session.get('year'))
                chosen_quarter = int(request.session.get('quarter'))
                chosen_quarter_names = ['Summer', 'Autumn', 'Winter', 'Spring']
                chosen_quarter_name = chosen_quarter_names[chosen_quarter]
                form = CalendarViews(year=chosen_year, quarter=chosen_quarter)
                first_monday = set_first_monday(chosen_year, chosen_quarter)
                if chosen_quarter == 1:
                    quarter_by_week = define_quarter(first_monday, 10)
                else:
                    quarter_by_week = define_quarter(first_monday, 9)
                quarter_calendar = quarter_table(quarter_by_week)
                serializable_quarter_cal = json_time_dict(quarter_calendar)
                json_date_dict = dumps(serializable_quarter_cal)
                all_combos = all_combos_for_quarter(chosen_year, chosen_quarter)
                combos_by_week = seminars_by_week(all_combos)
                filled_quarter_cal = full_quarter_schedule(combos_by_week, quarter_by_week)
                combo_lookup = combination_lookup(combos_by_week, quarter_by_week)
                json_combo_lookup = dumps(combo_lookup)
                mon_to_fri = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",]
                thanksgiving = find_thanksgiving(chosen_year)
                sections = Section.objects.filter(year=chosen_year, quarter=chosen_quarter)
                combo_count = combo_count_by_section(sections)
                json_combo_count = dumps(combo_count)
                json_week_by_week = dumps(json_week_by_week_cal(quarter_calendar))
                form2 = JumpWeek(quarter=chosen_quarter)
                return render(request, 'slotter/calendar.html', {
                    'form2': form2,
                    'form0': form0,
                    'form': form,
                    'chosen_year': chosen_year,
                    'chosen_quarter_name': chosen_quarter_name,
                    'quarter_calendar': quarter_calendar,
                    'serializable_quarter_cal': serializable_quarter_cal,
                    'all_combos': all_combos,
                    'combos_by_week': combos_by_week,
                    'combo_lookup': combo_lookup,
                    'mon_to_fri': mon_to_fri,
                    'thanksgiving': thanksgiving,
                    'chosen_quarter': chosen_quarter,
                    'json_date_dict': json_date_dict,
                    'json_combo_lookup': json_combo_lookup,
                    'json_combo_count': json_combo_count,
                    'json_week_by_week': json_week_by_week,
                    })
    template = loader.get_template('slotter/calendar.html')
    context = {
        'form': form,
        'form0': form0,
        }
    return HttpResponse(template.render(context, request))

def timeslots(request):
    min_students = request.session.get('min_students')
    n_seminars = request.session.get('n_seminars')
    sec_name = request.session.get('section')
    n = n_seminars
    min_n = min_students
    timeslots_dj = Timeslot.objects.filter(section__name=sec_name)
    timeslots_pyth = list(get_availabilities(min_n, timeslots_dj, sec_name).keys())
    class_list_dj = Student.objects.filter(section__name=sec_name)
    class_list = make_class_list(class_list_dj)
    all_time_combos = make_combinations(n, timeslots_pyth)
    avail = get_availabilities(min_n, timeslots_dj, sec_name)
    working_combos = pull_students(avail, all_time_combos, class_list)
    lookup_dict = will_combo_together(timeslots_pyth, working_combos)
    working_timeslots = list(lookup_dict.keys())
    working_timeslots_dj = convert_timeslot_list_to_objects(working_timeslots, timeslots_dj)
    column_times = timetable_range(working_timeslots)
    basic_timetable = timetable(column_times, working_timeslots, timeslots_dj)
    rowspans = find_rowspans(working_timeslots_dj)
    n_written_out = write_out_n(n)
    n_possibilities = len(working_combos)
    table = timetable_with_rowspans(basic_timetable, rowspans)
    weekdays = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu", "Friday": "Fri",}
    durations = determine_timeslot_duration(working_timeslots_dj)
    lookup = convert_timeslots_in_dict_to_objects(lookup_dict, timeslots_dj)    
    availability_numbers = availabilities_by_timeslot(working_timeslots, avail, timeslots_dj)
    required = any_required_timeslots(class_list_dj, working_timeslots_dj)
    least_avail = least_available_students(class_list_dj, working_timeslots_dj, timeslots_dj)
    overlapping = reverse_keys_and_vals(least_avail)
    recommended = recommended_pairings(class_list_dj, working_timeslots_dj, timeslots_dj)
    max_students = len(class_list) - (n-1)*2
    class_total = len(class_list)
    working_combos_dj = working_combos_form_validation(working_combos, timeslots_dj)
    student_caps = student_cap_by_timeslot(min_n, timeslots_dj, sec_name)
    timeslot_choices_no_blank = timeslot_choice_field(timeslots_dj, working_combos_dj, lookup_dict)
    timeslot_choices = add_blank_field(timeslot_choices_no_blank)
    pk_lookup_dict = timeslot_pk_lookup_dict(lookup, timeslots_dj)
    working_combos_by_pk = working_combos_pk(working_combos_dj)
    pk_combo_lookup = combo_lookup_dict_pk(pk_lookup_dict, working_combos_by_pk)
    json_dump = dumps(pk_lookup_dict)
    json_dump2 = dumps(pk_combo_lookup)
    form = SelectTimeslots(request.POST or None, t=timeslot_choices, number=n, max_s=max_students, class_t=class_total, combos=working_combos, caps=student_caps,)
    m = 1
    if request.method == 'POST':
        if form.is_valid():
            while m <= n:
                request.session['slot' + str(m)] = form.cleaned_data['slot' + str(m)]
                request.session['n_students' + str(m)] = form.cleaned_data['n_students' + str(m)]
                m = m + 1
            request.session['first_ten'] = form.cleaned_data['first_ten']
            return HttpResponseRedirect('/slotter/assign_students/')
    else:
        form = SelectTimeslots(t=timeslot_choices, number=n, max_s=max_students, class_t=class_total, combos=working_combos, caps=student_caps,)
    template = loader.get_template('slotter/timeslots.html')
    context = {
        'table': table, 
        'weekdays': weekdays,
        'durations': durations, 
        'lookup': lookup, 
        'n': n, 
        'n_written_out': n_written_out, 
        'min_students': min_students, 
        'n_seminars': n_seminars, 
        'n_possibilities': n_possibilities, 
        'max_students': max_students, 
        'availability_numbers': availability_numbers, 
        'required': required, 
        'recommended': recommended, 
        'form': form, 
        'sec_name': sec_name, 
        'class_total': class_total, 
        'pk_lookup_dict': pk_lookup_dict,
        'json_dump': json_dump,
        'working_combos_by_pk': working_combos_by_pk,
        'pk_combo_lookup': pk_combo_lookup,
        'json_dump2': json_dump2,
    }
    return HttpResponse(template.render(context, request))

"""
OLD ASSIGNED STUDENTS VIEW -- NO AJAX, JS
Also, accidentally broke the handpick option -- suspect something in the validation isn't working; what gets rendered is not the right version of the view

def assign_students(request):
    passed_section = request.session.get('section')
    passed_min_students = request.session.get('min_students')
    passed_n_seminars = request.session.get('n_seminars')
    min_n = passed_min_students
    sec_name = passed_section
    n_timeslots = passed_n_seminars
    m = 1
    form_data = []
    while m <= n_timeslots:
        selection = request.session.get('slot' + str(m))
        n_assigned = request.session.get('n_students' + str(m))
        tup = (selection, n_assigned)
        form_data.append(tup)
        m = m + 1
    timeslot_list = make_selected_timeslots_list(form_data)
    timeslot_list_dj = make_selected_timeslots_list_dj(form_data)
    just_selected_timeslots = get_just_selected_timeslots(timeslot_list_dj)
    timeslots_dj = Timeslot.objects.filter(section__name=sec_name)
    class_list_dj = Student.objects.filter(section__name=sec_name)
    class_list = make_class_list(class_list_dj)
    avail = get_availabilities(min_n, timeslots_dj, sec_name)
    timeslots_pyth = list(avail.keys())
    all_time_combos = make_combinations(n_timeslots, timeslots_pyth)
    working_combos = pull_students(avail, all_time_combos, class_list)

    combos = student_combos_for_selected_timeslots(timeslot_list, avail)
    sorted_timeslot_list = sort_timeslots_by_length(timeslot_list, avail)
    working = working_student_combos(sorted_timeslot_list, combos)
    assignments = make_assignments(working, combos)
    dj_assignments = convert_assgs(assignments, class_list_dj, timeslots_dj)
    n_assignments = len(assignments)
    table = display_assgs(dj_assignments)

    all_students_choices = student_choice_field(class_list_dj)
    student_pronouns = make_pronoun_choices(class_list_dj)
    selected_avail_pyth = selected_avail_dict(timeslot_list, avail)
    selected_avail = convert_avail_dict(selected_avail_pyth, timeslots_dj, class_list_dj)
    tally_student_avail = tally_student_availability(selected_avail)
    selected_timeslots = list(selected_avail_pyth.keys())
    timeslots_for_handpicking = timeslot_choice_field(timeslots_dj, working_combos, selected_timeslots)
    form00 = SaveTimeslotCombo
    form0 = RefineAssignments
    refining_methods_selected = []
    form1 = HandpickByTimeslot(selected_timeslots=timeslots_for_handpicking, pronouns=student_pronouns, refining=refining_methods_selected, students=all_students_choices, timeslot_list=timeslot_list_dj)
    handpick_selections = None
    refined = None
    if request.method == 'POST':
        if request.POST.get('refine_options'):
            form0 = RefineAssignments(request.POST or None)
            refining_methods_selected = request.POST.getlist('refine_options')
            request.session['refine_options'] = request.POST.getlist('refine_options')
            form1 = HandpickByTimeslot(selected_timeslots=timeslots_for_handpicking, pronouns=student_pronouns, refining=refining_methods_selected, students=all_students_choices, timeslot_list=timeslot_list_dj)
            return render(request, 'slotter/assign_students.html', {
            'assignments': assignments, 
            'n_assignments': n_assignments, 
            'table': table, 
            'form_data': form_data, 
            'timeslot_list': timeslot_list, 
            'passed_section': passed_section, 
            'passed_min_students': passed_min_students, 
            'passed_n_seminars': passed_n_seminars,
            'selected_avail': selected_avail,
            'form1': form1,
            'handpick_selections': handpick_selections,
            'tally_student_avail': tally_student_avail,
            'form0': form0,
            'refining_methods_selected': refining_methods_selected,
                    })
        elif request.POST.get('timeslots_to_handpick'):
            refining_methods_selected = request.session.get('refine_options')
            form1 = HandpickByTimeslot(request.POST or None, selected_timeslots=timeslots_for_handpicking, pronouns=student_pronouns, refining=refining_methods_selected, students=all_students_choices, timeslot_list=timeslot_list_dj)
            if form1.is_valid():
                handpick_selections = request.POST.getlist('timeslots_to_handpick')
                first_timeslot_pk = handpick_selections[0]
                student_options = student_choices_by_timeslot(handpick_selections, selected_avail)
                request.session['handpick_selections'] = request.POST.getlist('timeslots_to_handpick')
                request.session['pronoun_list'] = request.POST.getlist('balance_by_pronouns')
                request.session['grouping_action'] = request.POST.get('group_or_avoid')
                request.session['grouped_students'] = request.POST.getlist('students_selected')
                form2 = HandpickStudents(choices_dict=student_options, timeslot_list=timeslot_list_dj, only_avail=tally_student_avail)
                return render(request, 'slotter/assign_students.html', {
                    'assignments': assignments, 
                    'n_assignments': n_assignments, 
                    'table': table, 
                    'form_data': form_data, 
                    'timeslot_list': timeslot_list, 
                    'passed_section': passed_section, 
                    'passed_min_students': passed_min_students, 
                    'passed_n_seminars': passed_n_seminars,
                    'selected_avail': selected_avail,
                    'form1': form1,
                    'handpick_selections': handpick_selections,
                    'student_options': student_options,
                    'form2': form2,
                    'tally_student_avail': tally_student_avail,
                    'form0': form0,
                    'student_options': student_options,
                            })
            else:
                handpick_selections = request.POST.getlist('timeslots_to_handpick')
                student_options = student_choices_by_timeslot(handpick_selections, selected_avail)
                return render(request, 'slotter/assign_students.html', {
                'assignments': assignments, 
                'n_assignments': n_assignments, 
                'table': table, 
                'form_data': form_data, 
                'timeslot_list': timeslot_list, 
                'passed_section': passed_section, 
                'passed_min_students': passed_min_students, 
                'passed_n_seminars': passed_n_seminars,
                'selected_avail': selected_avail,
                'form1': form1,
                'handpick_selections': handpick_selections,
                'student_options': student_options,
                'tally_student_avail': tally_student_avail,
                'form0': form0,
                        })         
        elif request.POST.get('balance_by_pronouns'):
            refining_methods_selected = request.session.get('refine_options')
            form1 = HandpickByTimeslot(request.POST or None, selected_timeslots=timeslots_for_handpicking, pronouns=student_pronouns, refining=refining_methods_selected, students=all_students_choices, timeslot_list=timeslot_list_dj)
            if form1.is_valid():
                balance_by_pronouns = request.POST.getlist('balance_by_pronouns')
                handpick_selections = request.POST.getlist('timeslots_to_handpick')
                grouping_action = request.POST.get('group_or_avoid')
                grouped_students = request.POST.getlist('students_selected')
                student_options = student_choices_by_timeslot(handpick_selections, selected_avail)
                if grouping_action == None:
                    n_assignments = len(gut_singleton_assignments(dj_assignments, balance_by_pronouns))
                    refined = True
                    table = display_assgs(gut_singleton_assignments(dj_assignments, balance_by_pronouns))
                else:
                    pronoun_gutting = gut_singleton_assignments(dj_assignments, balance_by_pronouns)
                    group_gutting = group_or_avoid_combos(grouped_students, pronoun_gutting, grouping_action, class_list_dj)
                    n_assignments = len(group_gutting)
                    refined = True
                    table = display_assgs(group_gutting)
                    return render(request, 'slotter/assign_students.html', {
                        'assignments': assignments, 
                        'n_assignments': n_assignments, 
                        'table': table, 
                        'form_data': form_data, 
                        'timeslot_list': timeslot_list, 
                        'passed_section': passed_section, 
                        'passed_min_students': passed_min_students, 
                        'passed_n_seminars': passed_n_seminars,
                        'selected_avail': selected_avail,
                        'handpick_selections': handpick_selections,
                        'student_options': student_options,
                        'tally_student_avail': tally_student_avail,
                        'form0': form0,
                        'refined': refined,
                                })
            else:
                handpick_selections = request.POST.getlist('timeslots_to_handpick')
                student_options = student_choices_by_timeslot(handpick_selections, selected_avail)
                return render(request, 'slotter/assign_students.html', {
                'assignments': assignments, 
                'n_assignments': n_assignments, 
                'table': table, 
                'form_data': form_data, 
                'timeslot_list': timeslot_list, 
                'passed_section': passed_section, 
                'passed_min_students': passed_min_students, 
                'passed_n_seminars': passed_n_seminars,
                'selected_avail': selected_avail,
                'form1': form1,
                'handpick_selections': handpick_selections,
                'student_options': student_options,
                'tally_student_avail': tally_student_avail,
                'form0': form0,
                        })  
        elif request.POST.get('group_or_avoid'):
            refining_methods_selected = request.session.get('refine_options')
            form1 = HandpickByTimeslot(request.POST or None, selected_timeslots=timeslots_for_handpicking, pronouns=student_pronouns, refining=refining_methods_selected, students=all_students_choices, timeslot_list=timeslot_list_dj)
            if form1.is_valid():
                grouping_action = request.POST.get('group_or_avoid')
                grouped_students = request.POST.getlist('students_selected')
                n_assignments = len(group_or_avoid_combos(grouped_students, dj_assignments, grouping_action, class_list_dj))
                refined = True
                table = display_assgs(group_or_avoid_combos(grouped_students, dj_assignments, grouping_action, class_list_dj))
                return render(request, 'slotter/assign_students.html', {
                        'assignments': assignments, 
                        'n_assignments': n_assignments, 
                        'table': table, 
                        'form_data': form_data, 
                        'timeslot_list': timeslot_list, 
                        'passed_section': passed_section, 
                        'passed_min_students': passed_min_students, 
                        'passed_n_seminars': passed_n_seminars,
                        'selected_avail': selected_avail,
                        'form0': form0,
                        'grouping_action': grouping_action,
                        'grouped_students': grouped_students,
                        'refined': refined,
                                })
            else:
                handpick_selections = request.POST.getlist('timeslots_to_handpick')
                student_options = student_choices_by_timeslot(handpick_selections, selected_avail)
                return render(request, 'slotter/assign_students.html', {
                'assignments': assignments, 
                'n_assignments': n_assignments, 
                'table': table, 
                'form_data': form_data, 
                'timeslot_list': timeslot_list, 
                'passed_section': passed_section, 
                'passed_min_students': passed_min_students, 
                'passed_n_seminars': passed_n_seminars,
                'selected_avail': selected_avail,
                'form1': form1,
                'handpick_selections': handpick_selections,
                'student_options': student_options,
                'tally_student_avail': tally_student_avail,
                'form0': form0,
                        }) 
        elif request.POST.get('handpicked_students'+'1'):
            handpick_selections = request.session.get('handpick_selections')
            balance_by_pronouns = request.session.get('pronoun_list')
            grouping_action = request.session.get('grouping_action')
            grouped_students = request.session.get('grouped_students')
            student_options = student_choices_by_timeslot(handpick_selections, selected_avail)
            form2 = HandpickStudents(request.POST or None, choices_dict=student_options, timeslot_list=timeslot_list_dj, only_avail=tally_student_avail)
            if form2.is_valid():
                n_timeslots = int(request.POST.get('timeslot_number'))
                n = 1
                handpicked_avail = {}
                while n <= n_timeslots:
                    timeslot = int(request.POST.get('selected_timeslot'+str(n)))
                    students = request.POST.getlist('handpicked_students'+str(n))
                    handpicked_avail[timeslot] = students
                    n = n + 1
                handpicked = handpicked_students_for_timeslots(handpicked_avail)
                replacement_avail = replace_with_handpicked(avail, handpicked)
                combos = student_combos_for_selected_timeslots(timeslot_list, replacement_avail)
                sorted_timeslot_list = sort_timeslots_by_length(timeslot_list, replacement_avail)
                working = working_student_combos(sorted_timeslot_list, combos)
                assignments = make_assignments(working, combos)
                dj_assignments = convert_assgs(assignments, class_list_dj, timeslots_dj)
                if len(balance_by_pronouns) > 0 and len(grouped_students) == 0:
                    n_assignments = len(gut_singleton_assignments(dj_assignments, balance_by_pronouns))
                    refined = True
                    table = display_assgs(gut_singleton_assignments(dj_assignments, balance_by_pronouns))
                elif len(grouped_students) > 0 and len(balance_by_pronouns) == 0:
                    n_assignments = len(group_or_avoid_combos(grouped_students, dj_assignments, grouping_action, class_list_dj))
                    refined = True
                    table = display_assgs(group_or_avoid_combos(grouped_students, dj_assignments, grouping_action, class_list_dj))
                elif len(grouped_students) > 0 and len(balance_by_pronouns) > 0:
                    pronoun_gutting = gut_singleton_assignments(dj_assignments, balance_by_pronouns)
                    group_gutting = group_or_avoid_combos(grouped_students, pronoun_gutting, grouping_action, class_list_dj)
                    n_assignments = len(group_gutting)
                    refined = True
                    table = display_assgs(group_gutting)
                else:
                    n_assignments = len(assignments)
                    refined = True
                    table = display_assgs(dj_assignments)
                return render(request, 'slotter/assign_students.html', {
                    'assignments': assignments, 
                    'n_assignments': n_assignments, 
                    'table': table, 
                    'form_data': form_data, 
                    'timeslot_list': timeslot_list, 
                    'passed_section': passed_section, 
                    'passed_min_students': passed_min_students, 
                    'passed_n_seminars': passed_n_seminars,
                    'selected_avail': selected_avail,
                    'n_timeslots': n_timeslots,
                    'handpicked': handpicked,
                    'replacement_avail': replacement_avail,
                    'tally_student_avail': tally_student_avail,
                    'form0': form0,
                    'refined': refined,
                                })
            else:
                handpick_selections = request.session.get('handpick_selections')
                return render(request, 'slotter/assign_students.html', {
                                    'assignments': assignments, 
                                    'n_assignments': n_assignments, 
                                    'table': table, 
                                    'form_data': form_data, 
                                    'timeslot_list': timeslot_list, 
                                    'passed_section': passed_section, 
                                    'passed_min_students': passed_min_students, 
                                    'passed_n_seminars': passed_n_seminars,
                                    'selected_avail': selected_avail,
                                    'handpick_selections': handpick_selections,
                                    'student_options': student_options,
                                    'form2': form2,
                                    'tally_student_avail': tally_student_avail,
                                    'form0': form0,
                                                })
        elif request.POST.get('save_ts_combo'):
            add_combo = add_timeslot_combo(just_selected_timeslots, sec_name)
            save_message = 'Great! These timeslots have been saved.'
            return render(request, 'slotter/assign_students.html', {
                'assignments': assignments, 
                'n_assignments': n_assignments, 
                'table': table, 
                'form_data': form_data, 
                'timeslot_list': timeslot_list,
                'just_selected_timeslots': just_selected_timeslots, 
                'passed_section': passed_section, 
                'passed_min_students': passed_min_students, 
                'passed_n_seminars': passed_n_seminars,
                'selected_avail': selected_avail,
                'handpick_selections': handpick_selections,
                'tally_student_avail': tally_student_avail,
                'form0': form0,
                'save_message': save_message,
                'add_combo': add_combo,
                })
    template = loader.get_template('slotter/assign_students.html')
    context = {
        'assignments': assignments, 
        'n_assignments': n_assignments, 
        'table': table, 
        'form_data': form_data, 
        'timeslot_list': timeslot_list,
        'just_selected_timeslots': just_selected_timeslots, 
        'passed_section': passed_section, 
        'passed_min_students': passed_min_students, 
        'passed_n_seminars': passed_n_seminars,
        'selected_avail': selected_avail,
        'handpick_selections': handpick_selections,
        'tally_student_avail': tally_student_avail,
        'form0': form0,
        'form00': form00,
        'refined': refined,
    }
    return HttpResponse(template.render(context, request))

"""

def assign_students(request):
    save_combo_form = SaveTimeslotCombo
    passed_section = request.session.get('section')
    passed_min_students = request.session.get('min_students')
    passed_n_seminars = request.session.get('n_seminars')
    min_n = passed_min_students
    sec_name = passed_section
    n_timeslots = passed_n_seminars
    m = 1
    form_data = []
    while m <= n_timeslots:
        selection = request.session.get('slot' + str(m))
        n_assigned = request.session.get('n_students' + str(m))
        tup = (selection, n_assigned)
        form_data.append(tup)
        m = m + 1
    selected_timeslots_to_json = selected_timeslots_for_json(form_data)
    json_selected_timeslots = dumps(selected_timeslots_to_json)
    students = students_for_json(sec_name)
    students_cnet_lookup = dumps(students_cnet_to_pk(sec_name))
    json_students = dumps(students)

    # form stuff

    timeslot_list = make_selected_timeslots_list(form_data)
    timeslot_list_dj = make_selected_timeslots_list_dj(form_data)
    just_selected_timeslots = get_just_selected_timeslots(timeslot_list_dj)
    timeslots_dj = Timeslot.objects.filter(section__name=sec_name)
    class_list_dj = Student.objects.filter(section__name=sec_name)
    class_list = make_class_list(class_list_dj)
    avail = get_availabilities(min_n, timeslots_dj, sec_name)
    timeslots_pyth = list(avail.keys())
    all_time_combos = make_combinations(n_timeslots, timeslots_pyth)
    working_combos = pull_students(avail, all_time_combos, class_list)

    class_list_dj = Student.objects.filter(section__name=sec_name)
    all_students_choices = student_choice_field(class_list_dj)
    student_pronouns = make_pronoun_choices(class_list_dj)
    selected_avail_pyth = selected_avail_dict(timeslot_list, avail)
    selected_avail = convert_avail_dict(selected_avail_pyth, timeslots_dj, class_list_dj)
    tally_student_avail = tally_student_availability(selected_avail)
    selected_timeslots = list(selected_avail_pyth.keys())
    timeslots_for_handpicking = timeslot_choice_field(timeslots_dj, working_combos, selected_timeslots)
    refine_results_form = RefineAssignments
    refining_methods_selected = ['PRONOUNS', 'GROUP/AVOID', 'HANDPICK']
    refine_results_form2 = HandpickByTimeslot(selected_timeslots=timeslots_for_handpicking, pronouns=student_pronouns, refining=refining_methods_selected, students=all_students_choices, timeslot_list=timeslot_list_dj)

    # final stage form stuff
    handpick_selections = []
    for timeslot in  just_selected_timeslots:
        handpick_selections.append(timeslot.pk)
    student_options = student_choices_by_timeslot(handpick_selections, selected_avail)
    refine_results_form3 = HandpickStudents(choices_dict=student_options, timeslot_list=timeslot_list_dj, only_avail=tally_student_avail)

    # form validation data
    n_pronoun_choices = len(student_pronouns)
    student_total = len(class_list)
    n_students_for_timeslots = []
    for time in timeslot_list:
        n_students_for_timeslots.append(time[1])
    n_students_for_timeslots.sort()
    max_n_students_group_avoid = n_students_for_timeslots[0]
    n_timeslots = len(selected_timeslots)
    max_timeslot_selection = int(n_timeslots / 2)
    checkbox_ns = dumps(checkbox_count(timeslot_list_dj, selected_avail, tally_student_avail))

    # check to display save combo box
    section = Section.objects.get(name=passed_section)
    existing_combos = Combination.objects.filter(section=section)
    unique_combo = dumps(unique_timeslot_combo(existing_combos, just_selected_timeslots))

    template = loader.get_template('slotter/assign_students.html')
    context = {
        'selected_timeslots_to_json': selected_timeslots_to_json,
        'json_selected_timeslots': json_selected_timeslots,
        'json_students': json_students,
        'refine_results_form': refine_results_form,
        'refine_results_form2': refine_results_form2,
        'refine_results_form3': refine_results_form3,
        'n_pronoun_choices': n_pronoun_choices,
        'max_n_students_group_avoid': max_n_students_group_avoid,
        'student_total': student_total,
        'n_timeslots': n_timeslots,
        'max_timeslot_selection': max_timeslot_selection,
        'checkbox_ns': checkbox_ns,
        'student_options': student_options,
        'students_cnet_lookup': students_cnet_lookup,
        'save_combo_form': save_combo_form,
        'unique_combo': unique_combo,
    }
    return HttpResponse(template.render(context, request))

def testing_page(request):
    passed_section = request.session.get('section')
    passed_min_students = request.session.get('min_students')
    passed_n_seminars = request.session.get('n_seminars')
    min_n = passed_min_students
    sec_name = passed_section
    n_timeslots = passed_n_seminars
    m = 1
    form_data = []
    while m <= n_timeslots:
        selection = request.session.get('slot' + str(m))
        n_assigned = request.session.get('n_students' + str(m))
        tup = (selection, n_assigned)
        form_data.append(tup)
        m = m + 1
    selected_timeslots_to_json = selected_timeslots_for_json(form_data)
    json_selected_timeslots = dumps(selected_timeslots_to_json)
    students = students_for_json(sec_name)
    students_cnet_lookup = dumps(students_cnet_to_pk(sec_name))
    json_students = dumps(students)

    # form stuff

    timeslot_list = make_selected_timeslots_list(form_data)
    timeslot_list_dj = make_selected_timeslots_list_dj(form_data)
    just_selected_timeslots = get_just_selected_timeslots(timeslot_list_dj)
    timeslots_dj = Timeslot.objects.filter(section__name=sec_name)
    class_list_dj = Student.objects.filter(section__name=sec_name)
    class_list = make_class_list(class_list_dj)
    avail = get_availabilities(min_n, timeslots_dj, sec_name)
    timeslots_pyth = list(avail.keys())
    all_time_combos = make_combinations(n_timeslots, timeslots_pyth)
    working_combos = pull_students(avail, all_time_combos, class_list)

    class_list_dj = Student.objects.filter(section__name=sec_name)
    all_students_choices = student_choice_field(class_list_dj)
    student_pronouns = make_pronoun_choices(class_list_dj)
    selected_avail_pyth = selected_avail_dict(timeslot_list, avail)
    selected_avail = convert_avail_dict(selected_avail_pyth, timeslots_dj, class_list_dj)
    tally_student_avail = tally_student_availability(selected_avail)
    selected_timeslots = list(selected_avail_pyth.keys())
    timeslots_for_handpicking = timeslot_choice_field(timeslots_dj, working_combos, selected_timeslots)
    refine_results_form = RefineAssignments
    refining_methods_selected = ['PRONOUNS', 'GROUP/AVOID', 'HANDPICK']
    refine_results_form2 = HandpickByTimeslot(selected_timeslots=timeslots_for_handpicking, pronouns=student_pronouns, refining=refining_methods_selected, students=all_students_choices, timeslot_list=timeslot_list_dj)

    # final stage form stuff
    handpick_selections = []
    for timeslot in  just_selected_timeslots:
        handpick_selections.append(timeslot.pk)
    student_options = student_choices_by_timeslot(handpick_selections, selected_avail)
    refine_results_form3 = HandpickStudents(choices_dict=student_options, timeslot_list=timeslot_list_dj, only_avail=tally_student_avail)

    # form validation data
    n_pronoun_choices = len(student_pronouns)
    student_total = len(class_list)
    n_students_for_timeslots = []
    for time in timeslot_list:
        n_students_for_timeslots.append(time[1])
    n_students_for_timeslots.sort()
    max_n_students_group_avoid = n_students_for_timeslots[0]
    n_timeslots = len(selected_timeslots)
    max_timeslot_selection = int(n_timeslots / 2)
    checkbox_ns = dumps(checkbox_count(timeslot_list_dj, selected_avail, tally_student_avail))
    template = loader.get_template('slotter/testing.html')
    context = {
        'selected_timeslots_to_json': selected_timeslots_to_json,
        'json_selected_timeslots': json_selected_timeslots,
        'json_students': json_students,
        'refine_results_form': refine_results_form,
        'refine_results_form2': refine_results_form2,
        'refine_results_form3': refine_results_form3,
        'n_pronoun_choices': n_pronoun_choices,
        'max_n_students_group_avoid': max_n_students_group_avoid,
        'student_total': student_total,
        'n_timeslots': n_timeslots,
        'max_timeslot_selection': max_timeslot_selection,
        'checkbox_ns': checkbox_ns,
        'student_options': student_options,
        'students_cnet_lookup': students_cnet_lookup,
    }
    return HttpResponse(template.render(context, request))

def save_timeslots_combo(request):
    passed_section = request.session.get('section')
    passed_n_seminars = request.session.get('n_seminars')
    section = Section.objects.get(name=passed_section)
    n = 1
    timeslot_list = []
    while n <= passed_n_seminars:
        selection = request.session.get('slot' + str(n))
        timeslot_list.append(selection)
        n = n + 1
    timeslot_objs_list = []
    for pk in timeslot_list:
        if Timeslot.objects.get(pk=pk):
            ts = Timeslot.objects.get(pk=pk)
            timeslot_objs_list.append(ts)
    existing_combos = Combination.objects.filter(section=section)
    unique_combo = unique_timeslot_combo(existing_combos, timeslot_objs_list)
    dict_response = {}
    # only creates a new Timeslot Combo for this section if there isn't already one with the exact same timeslots saved
    if unique_combo == True:
        new_combo = Combination(section=section)
        new_combo.save()
        for ts in  timeslot_objs_list:
            new_combo.timeslots.add(ts)
        new_combo.save()
        dict_response[new_combo.pk] = 'saved'
    else:
        dict_response['not_unique'] = 'not_saved'
    response = JsonResponse(dict_response)
    return response

def assignment_churn(request):
    passed_section = request.session.get('section')
    passed_min_students = request.session.get('min_students')
    passed_n_seminars = request.session.get('n_seminars')
    passed_ten = request.session.get('first_ten')
    if passed_ten == 'False':
        passed_ten = False
    else:
        passed_ten = True
    min_n = passed_min_students
    sec_name = passed_section
    n_timeslots = passed_n_seminars
    m = 1
    form_data = []
    while m <= n_timeslots:
        selection = request.session.get('slot' + str(m))
        n_assigned = request.session.get('n_students' + str(m))
        tup = (selection, n_assigned)
        form_data.append(tup)
        m = m + 1
    timeslot_list = make_selected_timeslots_list(form_data)
    timeslot_list_dj = make_selected_timeslots_list_dj(form_data)
    just_selected_timeslots = get_just_selected_timeslots(timeslot_list_dj)
    timeslots_dj = Timeslot.objects.filter(section__name=sec_name)
    class_list_dj = Student.objects.filter(section__name=sec_name)
    class_list = make_class_list(class_list_dj)
    avail = get_availabilities(min_n, timeslots_dj, sec_name)
    timeslots_pyth = list(avail.keys())
    all_time_combos = make_combinations(n_timeslots, timeslots_pyth)
    working_combos = pull_students(avail, all_time_combos, class_list)
    """
    this is actually noticeably slower than churning going the Python route and then converting
    combos = student_combos_for_selected_timeslots(timeslot_list_dj, avail_dj)
    sorted_timeslot_list = sort_timeslots_by_length(timeslot_list_dj, avail_dj)
    working_test = working_student_combos_test(sorted_timeslot_list, combos)
    assignments_test = make_assignments_test(working_test, combos)
    """
    combos = student_combos_for_selected_timeslots(timeslot_list, avail)
    sorted_timeslot_list = sort_timeslots_by_length(timeslot_list, avail)
    test_ten = True
    working = working_student_combos(sorted_timeslot_list, combos, passed_ten)
    assignments = make_assignments(working, combos)
    dj_assignments_test = convert_assgs_pk(assignments, class_list_dj, timeslots_dj)

    response = JsonResponse(dj_assignments_test)
    return response



"""

def assign_students(request):
    min_n = 4
    n_students = 4
    n_timeslots = 2
    timeslot1 = list(will_combo_together(n_timeslots, min_n).keys())[0]
    timeslot2 = list(will_combo_together(n_timeslots, min_n).keys())[2]
    timeslot_list = [(timeslot1, 4), (timeslot2, 4)]
    combos = student_combos_for_selected_timeslots(min_n, timeslot_list)
    sorted_timeslot_list = sort_timeslots_by_length(min_n, timeslot_list)
    working = working_student_combos(sorted_timeslot_list, combos)
    assignments = make_assignments(working, combos)
    new_list = []
    for x in assignments:
        new_list.append(x)
        new_list.append(assignments[x])
    return HttpResponse(new_list)

"""


def choose_timeslots(request):
    n = 2
    min_n = 4
    sec_name = "Disco Elysium"
    class_list_dj = Student.objects.filter(section__name=sec_name)
    class_list = make_class_list(class_list_dj)
    max_students = len(class_list) - (n-1)*2
    class_total = len(class_list)
    timeslots_dj = Timeslot.objects.filter(section__name=sec_name)
    avail = get_availabilities(min_n, timeslots_dj, sec_name)
    timeslots_pyth = list(get_availabilities(min_n, timeslots_dj, sec_name).keys())
    all_time_combos = make_combinations(n, timeslots_pyth)
    working_combos_pyth = pull_students(avail, all_time_combos, class_list)
    lookup_dict = will_combo_together(timeslots_pyth, working_combos_pyth)
    working_combos = working_combos_form_validation(working_combos_pyth, timeslots_dj)
    student_caps = student_cap_by_timeslot(min_n, timeslots_dj, sec_name)
    timeslots = timeslot_choice_field(timeslots_dj, working_combos, lookup_dict)
    form = SelectTimeslots(request.POST or None, t=timeslots, number=n, max_s=max_students, class_t=class_total, combos=working_combos, caps=student_caps,)
    m = 1
    if request.method == 'POST':
        if form.is_valid():
            while m <= n:
                request.session['slot' + str(m)] = request.POST['slot' + str(m)]
                request.session['n_students' + str(m)] = request.POST['n_students' + str(m)]
                m = m + 1
            return HttpResponseRedirect('/slotter/assign_students/')
    else:
        form = SelectTimeslots(t=timeslots, number=n, max_s=max_students, class_t=class_total, combos=working_combos, caps=student_caps,)
    template = loader.get_template('slotter/choose_timeslots.html')
    context = {'form': form, 'timeslots': timeslots,}
    return HttpResponse(template.render(context, request))

def import_schedules(request):
    if request.method == 'POST':
        if request.POST.get('section'):
            form = ImportSectionCSV(request.POST or None)
            form2 = ConfirmCSVImport()
            form1point5 = ClearImportedData()
            request.session['sec'] = request.POST['section']
            chosen_section = request.session['sec']
            section = Section.objects.get(name=chosen_section)
            associated_students = len(Student.objects.filter(section__pk=section.pk))
            request.session['active_section'] = section.pk
            sheet = open(section.spreadsheet.path)
            open_sheet = csv.reader(sheet)
            full_sheet = full_spreadsheet(open_sheet)
            header = get_time_headers(full_sheet)
            student_data = basic_student_data(full_sheet)
            header_timeslots = mine_timeslots(header)
            student_avail = mine_student_availability(full_sheet, header)
            earliest_start = get_earliest_start(header_timeslots)
            latest_end = get_latest_end(header_timeslots)
            column_times = get_timeslot_column(header_timeslots)
            student_starts = student_avail_starts(student_avail)
            prov_timetable = provisional_timetable(header_timeslots)
            durations = timeslot_durations(header_timeslots)
            weekdays = {"Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu", "Friday": "Fri",}
            student_objs = add_students(student_data, section)
            timeslot_objs = add_timeslots(header_timeslots)
            return render(request, 'slotter/import_schedules.html', {
                'chosen_section': chosen_section,
                'section': section,
                'header_timeslots': header_timeslots,
                'durations': durations,
                'weekdays': weekdays,
                'student_data': student_data,
                'form': form,
                'student_objs': student_objs,
                'timeslot_objs': timeslot_objs,
                'student_avail': student_avail,
                'form2': form2,
                'prov_timetable': prov_timetable,
                'associated_students': associated_students,
                'form1point5': form1point5,
                })
        elif request.POST.get('clear_data_confirmation'):
            form1point5 = ClearImportedData(request.POST or None)
            if form1point5.is_valid():
                confirmation_to_clear = form1point5.cleaned_data['clear_data_confirmation']
                if confirmation_to_clear == True:
                    active_section_pk = request.session.get('active_section')
                    active_section = Section.objects.get(pk=active_section_pk)
                    active_section_timeslots = Timeslot.objects.filter(section__pk=active_section_pk)
                    active_section_students = Student.objects.filter(section__pk=active_section_pk)
                    for timeslot in active_section_timeslots:
                        timeslot.section.remove(active_section)
                    for student in active_section_students:
                        student.delete()
                    active_section_timeslots = active_section.timeslot_set.all()
                    active_section_students = Student.objects.filter(section__pk=active_section_pk)
                    confirmation_message = 'Scheduling data cleared.'
                    form = ImportSectionCSV(initial={'section': Section.objects.get(pk=active_section_pk)})
                    return render(request, 'slotter/import_schedules.html', {
                        'form': form,
                        'confirmation_to_clear': confirmation_to_clear,
                        'active_section_students': active_section_students,
                        'active_section_timeslots': active_section_timeslots,
                        'confirmation_message': confirmation_message,
                    })
        elif request.POST.get('confirmation'):
            form2 = ConfirmCSVImport(request.POST or None)
            if form2.is_valid():
                request.session['confirmation'] = form2.cleaned_data['confirmation']
                confirmation = request.session['confirmation']
                if confirmation == True:
                    chosen_section = request.session['sec']
                    section = Section.objects.get(name=chosen_section)
                    sheet = open(section.spreadsheet.path)
                    open_sheet = csv.reader(sheet)
                    full_sheet = full_spreadsheet(open_sheet)
                    header = get_time_headers(full_sheet)
                    student_data = basic_student_data(full_sheet)
                    header_timeslots = mine_timeslots(header)
                    student_avail = mine_student_availability(full_sheet, header)
                    student_objs = add_students(student_data, section)
                    timeslot_objs = add_timeslots(header_timeslots)
                    save_students(student_objs)
                    save_timeslots(timeslot_objs, section)
                    add_timeslots_to_students(student_avail)
                    return HttpResponseRedirect('/slotter/data_imported/')
    else:
        if request.session.get('active_section') != None:
            active_section_pk = request.session.get('active_section')
            form = ImportSectionCSV(initial={'section': Section.objects.get(pk=active_section_pk)})
        else:
            form = ImportSectionCSV()
    template = loader.get_template('slotter/import_schedules.html')
    context = {
        'form': form,
    }
    return HttpResponse(template.render(context, request))


"""
            request.session['section'] = request.POST['section']
            request.session['min_students'] = request.POST['min_students']
"""



"""

def timeslots(request):
    n = 2
    output = get_availabilities()
    new_list = []
    output8 = determine_timeslot_duration(n)
    output9 = make_combinations(2)
    output10 = convert_timeslots_in_dict_to_objects(n)
    for x in output10:
        new_list.append(x)
        new_list.append(output10[x])
    return HttpResponse(new_list)

"""