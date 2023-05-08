from datetime import time
from datetime import date
from datetime import datetime
from datetime import timedelta

from django.db.models import Q

import re

from .models import Combination, Student, Timeslot, Section, Combination

# CHOOSING TIMESLOTS

# core data-crunching

def get_students_from_time(timeslot, sec_name):
    """
    Takes a Timeslot object and retrieves all the Student objects available at that time for the specified section. Makes a list of these students, subbing in each student's cnetid for the Student object. 
    """
    student_list = []
    students = timeslot.student_set.filter(section__name=sec_name)
    for x in students:
        cnetid = x.cnetid
        student_list.append(cnetid)
    return student_list

def get_availabilities(min_n, timeslots, sec_name):
    """
    Takes all Timeslot objects (for a given section) and turns them into (weekday, start_time) tuples. min_n is the minimum # of students acceptable for a timeslot (if there are fewer than n students, the timeslot gets filtered out). Returns a dict where the key is a timeslot tuple and the values are the students available at that time.
    """
    avail_dict = {}
    for x in timeslots:
        time = x.weekday, x.start_time
        avail_students = get_students_from_time(x, sec_name)
        if len(avail_students) >= min_n:
            avail_dict[time] = avail_students
    return avail_dict

def make_class_list(class_list_dj):
    """
    Retrieves all Student objects and returns a list of students (identified by cnetid)
    Used in pull_students to check available students (for a combo of timeslots) against the class list
    """
    class_list = []
    for x in class_list_dj:
        class_list.append(x.cnetid)
    class_list.sort()
    return class_list

def make_combinations(n, timeslots):
    """
    Takes the list of timeslots and runs through all the possible combinations of n timeslots
    n specifies the number of timeslots that should make up one combination
    """
    listy = timeslots
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
            return new_combos
        combos_so_far = new_combos
        new_combos = []

def pull_students(avail, combined_timeslots, students):
    """
    Takes all of the combinations of timeslots and determines which students are available for each combination of timeslots (by using get_availabilities). Compares the students available for each combo of timeslots to the class list and filters out combos that don't include all the students in the class list. Returns these combos as a list. (The name of this function is kinda misleading, since it now does more than the OG function did!)
    """
    students_by_time_combo = {}
    students_in_combo = []
    for combo in combined_timeslots:
        for time in combo:
            if time in avail:
                for student in avail[time]:
                    if student not in students_in_combo:
                        students_in_combo.append(student)
        students_in_combo.sort()
        tuple_combo = tuple(combo)
        students_by_time_combo[tuple_combo] = students_in_combo
        students_in_combo = []
    working_combos = []
    for combo in students_by_time_combo:
        if students_by_time_combo[combo] == students:
            working_combos.append(combo)
    return working_combos

def will_combo_together(timeslots, working_combos):
    """
    Takes all of the combos from pull_students. Makes a new dict where each key is a timeslot and its corresponding value is a list of the timeslots that are compatible with it (according to the combos from pull_students).
    """
    lookup_dict = {}
    combo_times = []
    for timeslot in timeslots:
        for combo in working_combos:
            if timeslot in combo:
                for time in combo:
                    if timeslot != time:
                        if time not in combo_times:
                            combo_times.append(time)
        combo_times.sort()
        if len(combo_times) > 0:
            lookup_dict[timeslot] = combo_times
        combo_times = []
    return lookup_dict

# conversions from Django data structures to Python and back

def convert_to_pyth_time(timeslot_dj):
    day = timeslot_dj.weekday
    time = timeslot_dj.start_time
    pyth_time = day, time
    return pyth_time

def convert_list_to_pyth_time(timeslot_list_dj):
    pyth_times = []
    for time in timeslot_list_dj:
        pyth_time = convert_to_pyth_time(time)
        pyth_times.append(pyth_time)
    return pyth_times

def convert_to_timeslot_object(pyth_time, timeslots_dj):
    """
    Takes a tuple representing a time and returns the existing corresponding Timeslot object
    """
    for timeslot in timeslots_dj:
        dj_tuple = (timeslot.weekday, timeslot.start_time)
        if dj_tuple == pyth_time:
            return timeslot

def convert_to_student_object(student, class_list_dj):
    """
    Takes a cnetid identifying a student and returns the corresponding Student object
    """
    for s in class_list_dj:
        if s.cnetid == student:
            return s

def convert_timeslots_in_dict_to_objects(lookup_dict, timeslots_dj):
    """
    Converts the dict generated by will_combo_together into a dict with the same content, just with the corresponding Timeslot objects as the keys and values instead
    """
    object_dict = {}
    for time in lookup_dict:
        new_list = []
        new_key = convert_to_timeslot_object(time, timeslots_dj)
        for timeslot in lookup_dict[time]:
            new_list.append(convert_to_timeslot_object(timeslot, timeslots_dj))
        object_dict[new_key] = new_list
    return object_dict

def convert_timeslot_list_to_objects(timeslots, timeslots_dj):
    """
    Converts the list of workable timeslots in tuple form to Timeslot objects
    """
    dj_timeslots = []
    for timeslot in timeslots:
        timeslot = convert_to_timeslot_object(timeslot, timeslots_dj)
        dj_timeslots.append(timeslot)
    return dj_timeslots

# extra crunching to help with timeslot selection

def availabilities_by_timeslot(working_times, avail_dict, timeslots_dj):
    """
    Generates a dict where each key is a Django Timeslot object and the value is the # of students available for that time. Currently being used in the table in the HTML template to help inform Timeslot selection decisions.
    """
    availability_numbers_dict = {}
    for time in working_times:
        if time in avail_dict:
            number = len(avail_dict[time])
            time_dj = convert_to_timeslot_object(time, timeslots_dj)
            availability_numbers_dict[time_dj] = number
    return availability_numbers_dict

def student_availability(class_list_dj, working_timeslots_dj):
    """
    Generates a dict where each key is a student and the corresponding value is the list of times at which the student is available.
    """
    student_avail = {}
    for student in class_list_dj:
        timeslots = student.timeslots.all()
        working = []
        for time in timeslots:
            if time in working_timeslots_dj:
                working.append(time)
        avail = working
        student_avail[student] = avail
        working = []
    return student_avail

def any_required_timeslots(class_list_dj, working_timeslots_dj):
    """
    Determines whether any Timeslots are required because there are students that can only make one time.
    """
    student_avail = student_availability(class_list_dj, working_timeslots_dj)
    required = []
    for student in student_avail:
        if len(student_avail[student]) == 1:
            time = student_avail[student][0]
            required.append(time)
    return required

def least_available_students(class_list_dj, working_timeslots_dj, timeslots_dj):
    """
    Generates a dict where each key is a student and the corresponding value is a list of the times they can make. Students are included in this dict if they can make fewer than 1/3 of the available times (or 5 or fewer times in cases where there are more than 15 times available).
    """
    student_avail = student_availability(class_list_dj, working_timeslots_dj)
    least_available = {}
    total = len(timeslots_dj)
    threshold = int(total/3)
    if threshold > 5:
        threshold = 5
    for student in student_avail:
        if len(student_avail[student]) <= threshold:
            least_available[student] = student_avail[student]
    return least_available

def reverse_keys_and_vals(dicty):
    """
    Takes each unique value in a dict (assuming that these values were stored in lists) and turns it into the key of a new dict. The new values are the keys from the old dict. Used in recommended_pairings to figure out which times are ones that multiple students in the *least available* category can make.
    """
    new_dict = {}
    for key in dicty:
        for i in dicty[key]:
            if i not in new_dict:
                new_dict[i] = [key]
            else:
                new_dict[i].append(key)
    return new_dict

def recommended_pairings(class_list_dj, working_timeslots_dj, timeslots_dj):
    least_avail_students = list(least_available_students(class_list_dj, working_timeslots_dj, timeslots_dj).keys())
    overlapping_times = {}
    overlapping = reverse_keys_and_vals(least_available_students(class_list_dj, working_timeslots_dj, timeslots_dj))
    for time in overlapping:
        if len(overlapping[time]) > 1:
            overlapping_times[time] = overlapping[time]
    overlapping_list = list(overlapping_times.keys())
    # checks if any of the times by themselves cover all the least available students
    full_coverage = []
    for time in overlapping_times:
        if len(overlapping_times[time]) == len(least_avail_students):
            full_coverage.append([time])
    if len(full_coverage) > 0:
        return full_coverage
    # if none, checks for pairs of times that will cover all the least available students
    pair_overlap = {}
    combined_students = []
    pairs = make_combinations(2, overlapping_list)
    for pair in pairs:
        for time in pair:
            combined_students.extend(overlapping_times[time])
        pared_pair = set(combined_students)
        combined_students = list(pared_pair)
        pair = tuple(pair)
        pair_overlap[pair] = combined_students
        combined_students = []
    n = len(least_avail_students)
    while n > int(len(least_avail_students)/2):    
        for pair in pair_overlap:
            if len(pair_overlap[pair]) == n:
                full_coverage.append(list(pair))
        if len(full_coverage) > 0:
            return full_coverage
        else:
            n = n - 1
    return full_coverage

# prepping data for timetable display

def in_minutes(time):
    """
    Takes a Python Datetime Time tuple, e.g., (9,00) and converts it to minutes (where 0 minutes == midnight)
    """
    return time.hour*60 + time.minute

def in_hours_and_minutes(time):
    """
    Converts a time represented in minutes (where 0 min == midnight) back to a tuple, e.g., (9,00)
    """
    return divmod(time, 60)

def timetable_range(working_timeslots):
    """
    Takes the list of working timeslots from will_combo_together and strips away the day tuple (t[0]). Determines what the earliest and latest times are from among these. Returns a list of the range of times starting from the earliest and ending in the latest in 30 min increments. This list of times is what determines what the left-most column in the HTML scheduling table will look like.

    # in reviewing this, it seems like this works on the assumption that seminars are only an hour long, but that might not always be the case, so it seems to me that this needs to be updated using Django objects intead of pyth times
    """
    just_times = []
    for t in working_timeslots:
        just_times.append(t[1])
    just_times.sort()
    earliest = in_minutes(just_times[0])
    last = len(just_times) - 1
    latest = in_minutes(just_times[last])
    times_in_minutes= [earliest,]
    n = earliest
    while n <= latest:
        n = n + 30
        times_in_minutes.append(n)
    times_in_hours = []
    for t in times_in_minutes:
        t = in_hours_and_minutes(t)
        times_in_hours.append(t)
    table_times = []
    for t in times_in_hours:
        new_time = time(t[0], t[1])
        table_times.append(new_time)
    return table_times

def timetable(column_times, timeslots, timeslots_dj):
    """
    Creates the content for each HTML table cell, not including the header row. Each key is just a time derived from timetable_range and the values (formatted as a list) represent subsequent cells in the same table row. If the day/time represented by a cell corresponds with a timeslot, the value just is the Timeslot object. If there is no corresponding timeslot for that day/time cell, the value is None
    """
    weekdays = [0, 1, 2, 3, 4]
    timetable_dict = {}
    mon_to_fri = []
    for t in column_times:
        for day in weekdays:
            slot = (day, t)
            if slot in timeslots:
                mon_to_fri.append(convert_to_timeslot_object(slot, timeslots_dj))
            else:
                mon_to_fri.append(None)
        timetable_dict[t] = mon_to_fri
        mon_to_fri = []
    return timetable_dict

def find_rowspans(timeslots_dj):
    """
    Returns a list of tuples that represent the day, start time, and end time of each Timeslot that will be represented in the HTML table
    This is used in conjunction with timetable_with_rowspans to mark out where no new table cell should be made, since there will be a rowspan starting somewhere in the same column above
    """
    rowspans = []
    for timeslot in timeslots_dj:
        day = timeslot.weekday
        start = timeslot.start_time
        end = timeslot.end_time
        extent = (day, start, end)
        rowspans.append(extent)
    return rowspans

def determine_timeslot_duration(working_timeslots_dj):
    """
    Assigns a Timeslot.duration to each Timeslot in the list. This ensures that in the HTML table that gets generated, the rowspan n is correct for each timeslot. Duration is expressed in terms of 30 min increments, so if a Timeslot's start time and end time are 30 minutes apart, the duration of this timeslot is 1.

    # Maybe something like this function should end up being part of a different view (before the table content is determined), since durations are technically independent of any of the computing being done for the timeslot table view.
    """
    for timeslot in working_timeslots_dj:
        start = in_minutes(timeslot.start_time)
        end = in_minutes(timeslot.end_time)
        duration_in_min = end - start
        duration_half_hour_incr = divmod(duration_in_min, 30)
        if duration_half_hour_incr[0] == 0:
            duration = 1
        elif duration_half_hour_incr[0] > 0:
            if duration_half_hour_incr[1] == 0:
                duration = duration_half_hour_incr[0]
            elif duration_half_hour_incr[1] > 0:
                duration = duration_half_hour_incr[0] + 1
        timeslot.duration = duration
        timeslot.save()

def timetable_with_rowspans(basic_timetable, rowspans):
    """
    Uses the dict from timetable and the list of timeslot tuples with beginning and end times to make a new dict that will actually be used to in the template to generate the HTML scheduling table.
    Values that were None in the timetable() version of the table but that should actually not represent a new, empty cell in the table (because the cell from above continues as a part of a rowspan) are replaced by "continuation," which will tell the template not to created a new <td></td>.
    """
    for x in rowspans:
        for t in basic_timetable:
            if x[1] < t and x[2] > t:
                day = x[0]
                basic_timetable[t][day] = "continuation"
    new_timetable = {}
    for t in basic_timetable:
        new_timetable[t.strftime("%-I:%M %p")] = basic_timetable[t]
    return new_timetable

def write_out_n(n):
    """
    Takes an integer and returns the written version if it is between 0 and 9, otherwise just returns the int itself. Right now, this is just being used in the template to write out the number of timeslots that need to be selected (totally for aesthetic purposes).
    """
    written_numbers = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",}
    if n in written_numbers:
        return written_numbers[n]
    else:
        return n

# other elements for the timeslots view -- form elements, lookup dicts, etc. to be passed to the front end

def timeslot_choice_field(timeslots_dj, working_combos, timeslot_list):
    """
    Creates the list of tuples that make up the choices for all Timeslot choice fields (obviously, this list can't be determined by a simple queryset)
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
    Adds a blank field as the first option in a list of tuple choices meant to populate a select form field. (Currently used with timeslot_choice_field but could have other uses.)
    """
    choice_list.insert(0, ('', '-----------'))
    return choice_list

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

def working_combos_django(combos, timeslots_dj):
    """
    Converts the datetime.times of working_combos to Timeslot objects
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
    """
    Converts the Timeslot objects in each working combo so that each timeslot is identified by its pk instead.
    """
    new_combos = []
    for combo in dj_combos:
        new_combo = []
        for timeslot in combo:
            new = timeslot.pk
            new_combo.append(new)
        new_combos.append(new_combo)
    return new_combos

def timeslot_pk_lookup_dict(obj_lookup_dict, timeslots_dj):
    """
    Converts the dict originally generated by will_combo_together into a dict with the same structure/content, just with Timeslot pks as the keys and values instead
    """
    pk_dict = {}
    for timeslot_key in obj_lookup_dict:
        ts_list = []
        for timeslot in obj_lookup_dict[timeslot_key]:
            ts_list.append(timeslot.pk)
        pk_dict[timeslot_key.pk] = ts_list
    return pk_dict

def combo_lookup_dict_pk(pk_lookup_dict, pk_working_combos):
    """
    Makes a *different* lookup dict (timeslots identified by pk of course), where each key is one of the selectable timeslots, and each value is a list of the combos that contain that timeslot. Gets converted into a JSON object for front-end use (narrowing down which timeslots are still selectable).
    """
    combo_dict = {}
    for pk in pk_lookup_dict:
        combo_list = []
        for combo in pk_working_combos:
            if pk in combo:
                combo_list.append(combo)
        combo_dict[pk] = combo_list
    return combo_dict

# ASSIGNING STUDENTS

# pulling and processing form data submitted from the timeslots view

def make_selected_timeslots_list(form_data):
    """
    Form data is a list of tuples, where the first tuple is the pk of a Timeslot object, and the second is the number of students who are to be assigned to that timeslot (corresponds to the pair of form fields in the timeslots form). This function returns the same list just with a (day, datetime.time) instead of the pk for the first of each tuple value.
    """
    timeslots_list = []
    for selection in form_data:
        timeslot = Timeslot.objects.get(pk=selection[0])
        day = timeslot.weekday
        start_time = timeslot.start_time
        timeslot = (day, start_time)
        new_selection = (timeslot, selection[1])
        timeslots_list.append(new_selection)
    return timeslots_list

def make_selected_timeslots_list_dj(form_data):
    """
    Same list containing form data from the timeslots view, only the first tuple value is now a Timeslot object instead of the regular Python datetime.time.
    """
    timeslots_list = []
    for selection in form_data:
        timeslot = Timeslot.objects.get(pk=selection[0])
        assign_n_students = selection[1]
        new_selection = (timeslot, assign_n_students)
        timeslots_list.append(new_selection)
    return timeslots_list

def get_just_selected_timeslots(timeslots_list):
    """
    Makes a list of the Timeslot objects selected in the timeslots view -- no extra data about how many students should be assigned to each time.
    """
    new_list = []
    for tup in timeslots_list:
        new_list.append(tup[0])
    return new_list

# packaging data to pass to the front end

def selected_timeslots_for_json(form_data):
    """
    Makes a lookup dict to be turned into a JSON object, where each key is the pk for one of the selected timeslots and each value is a dict with values for each timeslot's weekday, start time, and end time.
    """
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
    """
    Look-up dict of students for a given section -- keys are students' pks.
    """
    lookup_dict = {}
    students = Student.objects.filter(section__name=sec_name)
    for student in students:
        lookup_dict[student.pk] = Student.objects.filter(pk=student.pk).values('cnetid', 'last_name', 'first_name', 'pronouns')[0]
    return lookup_dict

def students_cnet_to_pk(sec_name):
    """
    Same student look-up dict, basically, but with students' cnetid as the keys (the code that depends on this, e.g. some stuff in forms.py primarily, should really be updated so that it doesn't depend on students' cnets. Obv, the related js would also have to be updated. But this way, you could make distinct model instances for the same student across quarters (instead of deleting the previous quarter's data) without crazy things happening).
    """
    lookup_dict = {}
    students = Student.objects.filter(section__name=sec_name)
    for student in students:
        lookup_dict[student.cnetid] = Student.objects.filter(pk=student.pk).values('pk', 'last_name', 'first_name', 'pronouns')[0]
    return lookup_dict

def selected_avail_dict(timeslot_list, avail_dict):
    """
    A truncated version of the original avail_dict -- just includes the times (datetime.times) selected by the user
    """
    selected_dict = {}
    for tup in timeslot_list:
        timeslot = tup[0]
        if timeslot in avail_dict:
            selected_dict[timeslot] = avail_dict[timeslot]
    return selected_dict

def convert_avail_dict(avail_dict, timeslots_dj, class_list_dj):
    """
    Converts any avail_dict, where the keys are python day/time tuples and the values are lists of cnetids, to Timeslot objects and Student objects.
    """
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

# data to pass to the various forms in the assign_students view

def student_choice_field(student_list):
    """
    Creates a list of tuples to populate a choicefield, where the choices are students. Used, for example, to populate the choices when handpicking students for a timeslot. *** This is one of the functions that should be updated at some point so that the value that gets used and passed is not a cnetid but the Student object's pk.
    """
    student_tups = []
    for student in student_list:
        tup = (student.cnetid, student)
        student_tups.append(tup)
    return student_tups

def student_choices_by_timeslot(selected_timeslots, avail_dict_dj):
    """
    Creates a dict to populate the handpick students by timeslot fields, where each key is a timeslot and each value is a list of the students available at that time.
    """
    choice_tups = {}
    for selected in selected_timeslots:
        timeslot = Timeslot.objects.get(pk=int(selected))
        if timeslot in avail_dict_dj:
            students = avail_dict_dj[timeslot]
            student_choices = student_choice_field(students)
            choice_tups[timeslot] = student_choices
    return choice_tups

def tally_student_availability(avail_dict):
    """
    Uses the avail dict (with selected timeslots only) to identify students who are only available for one timeslot (and therefore must be selected for that timeslot). Makes a dict where the keys are students and the value is the timeslot that they must be in. Used in the handpick students form.
    """
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
    """
    Makes a list of the pronoun choices relevant for students in a class. Used to determine which pronouns should be a part of the group by pronouns form.
    """
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

# core data crunching -- figuring out what all of the combinations of n students are for a given timeslot and putting those together into valid assignments for the whole class

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
    master_dict should be a dict of dicts -- the top-level keys are timeslots, each set of keys in the next dict down is a (timeslot, id#) tuple whose value is a combination of students who can make that time. The actual dict that is used for master_dict changes depending on what stage of the gutting we're at. It starts out with the product of student_combos_for_selected_timeslots() but will change as the relevant megafunction produces gutted results.
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

# more data to pass to the front end -- all the results of the core data crunching

def convert_assgs_pk(assg, class_list_dj, timeslots_dj):
    """
    Takes the assignment dict and returns an equivalent dict with Timeslot pks (as the second-level dict keys) and lists of Student pks. This is main dict that gets converted into a JSON object and then drawn on by the js.
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
    """
    Data for setting up and validating the handpick by timeslot fields. Returns a dict where each key is an int (corresponds with how checkbox ids are named in the html) and each value is another dict containing data about each timeslot -- how many students/checkboxes there will be for the timeslot, how many students/checkboxes must be selected for the timeslot, and the timeslot's pk.
    """
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

# SAVING TIMESLOT COMBINATIONS (connected to the assign_students view but also the start view)

def matches_existing_combo(combo, timeslots):
    """
    Checks if the timeslots selected to be saved as a new timeslot combo match an existing saved combo.
    """
    for timeslot in timeslots:
        if timeslot not in combo.timeslots.all():
            return False
    return True

def unique_timeslot_combo(combos, timeslots):
    """
    Uses matches_existing_combo to check the selected timeslots against all existing combos -- if the selected timeslots are unique, returns true.
    """
    verdicts = []
    for combo in combos:
        verdict = matches_existing_combo(combo, timeslots)
        verdicts.append(verdict)
    if True in verdicts:
        return False
    else:
        return True

def stringify_assigned_student_numbers(tuple_list):
    """
    Takes a list of tuples, where each tuple has the form (timeslot.pk, n), and converts the list into a string to be saved as the value for 'assigned_students_breakdown' for a given Combination object. In the string, commas separate each timeslot, and a hyphen separates the timeslot pk from the number of students to be assigned to that timeslot.
    """
    new_list = []
    for tup in tuple_list:
        new_string = str(tup[0]) + '-' + str(tup[1])
        new_list.append(new_string)
    return ','.join(new_list)

def destring_student_breakdown(string):
    """
    Reinterprets the string saved as 'assigned_students_breakdown' for a given Combination as a list of tuples of the form (Timeslot, n).
    """
    breakdown_list = string.split(',')
    new_list = []
    for pair in breakdown_list:
        destringified = pair.split('-')
        timeslot = Timeslot.objects.get(pk=int(destringified[0]))
        n = int(destringified[1])
        tup = (timeslot, n)
        new_list.append(tup)
    return new_list

def combination_timeslot_assgned_students_lookup(section):
    """
    Lookup dict to be passed to the front end of the start view. Each key is the pk of a saved timeslot combo, and each corresponding value is the combo's assigned_students_breakdown, which is a string that contains the pk of each timeslot in the combo and the number of students to be assigned to that timeslot. Used to pre-fill the timeslots form in the timeslots view if the user chooses to skip the normal start view process and jump to an already saved timeslot combo.
    """
    lookup_dict = {}
    combos = section.combination_set.all()
    for combo in combos:
        lookup_dict[combo.pk] = combo.assigned_students_breakdown
    return lookup_dict

def timeslot_in_minutes(timeslot):
    """
    Converts a Timeslot object into minutes, assuming that Monday at midnight == 0 minutes. Used to sort Timeslot objects that aren't just being called through a query.
    """
    return timeslot.weekday * 24 * 60 + in_minutes(timeslot.start_time)

def sort_timeslots(timeslot_list):
    """
    Returns a list of Timeslot objects sorted by weekday, time. Current use is ensuring that saved timeslot combinations are listed in the right order instead of in the order the timeslots were selected.
    """
    timeslot_minute_list = []
    for timeslot in timeslot_list:
        timeslot_int = timeslot_in_minutes(timeslot)
        timeslot_minute_list.append(timeslot_int)
    timeslot_minute_list.sort()
    sorted_timeslots = []
    for time in timeslot_minute_list:
        for timeslot in timeslot_list:
            if time == timeslot_in_minutes(timeslot):
                sorted_timeslots.append(timeslot)
    return sorted_timeslots

def label_combo_by_timeslots(combo):
    """
    Returns a string that lists each timeslot in a combo in a readable format -- the way in which combos are labeled for display.
    """
    weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    timeslots = combo.timeslots.all()
    timeslot_label_list = []
    for timeslot in timeslots:
        weekday = weekdays[timeslot.weekday]
        time = timeslot.start_time.strftime("%-I:%M %p").lower()
        label = weekday + ', ' + time
        timeslot_label_list.append(label)
    timeslot_labels = ', '.join(timeslot_label_list)
    return timeslot_labels

def combo_dicts_for_display(combo_list):
    """
    Returns a list of dicts, where each dict contains a combo's pk and the readable label that will be used for it. Used in the start view to identify saved combos for a section.
    """
    dict_list = []
    for combo in combo_list:
        combo_dict = {}
        labels = label_combo_by_timeslots(combo)
        combo_dict['pk'] = combo.pk
        combo_dict['label'] = labels
        dict_list.append(combo_dict)
    return dict_list

# CHOOSING A SECTION

def display_students(class_list_dj):
    """
    Organizes students from a section into two or three lists for display in the start view once a section has been picked
    """
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

# CSV READING

def full_spreadsheet(raw_data):
    """
    Takes a CSV file from csv.reader and makes a line-by-line dict
    Replaced by check_csv -- no longer in use
    """
    sheet_dict = {}
    n = 0
    for line in raw_data:
        sheet_dict[n] = line
        n = n + 1
    return sheet_dict

def a1_notation(tup):
    alphabet = ['', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    if tup[0] <= 26:
        return (alphabet[tup[0]], tup[1])
    else:
        multiplier = int(tup[0] / 26)
        converted = tup[0] - multiplier * 26
        return (alphabet[converted] * multiplier, tup[1])

def check_csv(raw_data):
    row = 1
    col = 1
    n = 0
    error_list = []
    other_allowed = ['[', ']', '-', ':']
    avail_options = ['Available', 'Not available']
    sheet_dict = {}
    for line in raw_data:
        for cell in line:
            # headers
            if row == 1 and col > 4:
                if all(char.isalnum() or char.isspace() or char in other_allowed for char in cell) == False:
                    error_list.append((col, row))
            elif row == 1 and col <= 4:
                if all(char.isalpha() or char.isspace() or char == '?' for char in cell) == False:
                    error_list.append((col, row))
            # entries for cnetid
            elif row > 1 and col == 1:
                if cell.isalnum() == False or len(cell) > 30:
                    error_list.append((col, row))
            # entries for pronouns
            elif row > 1 and col == 4 and len(cell) <= 15:
                regex_pronouns = re.compile('^[a-z]{2,4}/[a-z]{2,4}/[a-z]{3,6}$|[a-z]{2,4}/^[a-z]{2,4}$|^[a-z ]{2,25}$', re.IGNORECASE)
                if bool(regex_pronouns.match(cell)) == False:
                    error_list.append((col, row))
            # entries for first and last names
            elif row > 1 and col < 4:
                if all(char.isalpha() or char.isspace() or char == '-' for char in cell) == False or len(cell) > 30:
                    error_list.append((col, row))
            # entries for availability
            elif row > 1 and col > 4:
                if cell not in avail_options:
                    error_list.append((col, row))
            col = col + 1
        if any(error[0] == row for error in error_list) == False:
            sheet_dict[n] = line
            n = n + 1
        row = row + 1
        col = 1
    if len(error_list) == 0:
        return sheet_dict
    a1_error_list = []
    for error in error_list:
        a1_error_list.append(a1_notation(error))
    a1_error_list.sort()
    return a1_error_list

def get_time_headers(spreadsheet):
    """
    Isolates the header columns in the spreadsheet that contain times and returns them as a list
    """
    header = spreadsheet[0]
    time_cols = header[4:]
    return time_cols

def mine_timeslot(string):
    """
    Parses a time string (assumes certain formatting idiosyncrasies from how I've laid things out in my Google Forms) and returns it as a tuple of the form (weekday int, datetime.time start, datetime.time end)
    """
    error_log = []
    times =[]
    weekdays = ['mon', 'tue', 'wed', 'thu', 'fri']
    regex_time_format = re.compile('^([1][0-2]|[1-9]):[0-5][0-9] (am|pm)$', re.IGNORECASE)
    regex_start_time_capture = '([0-9]|[0-9][0-9a-zA-Z: ]{0,9}[0-9a-zA-Z])(?: {0,3}-)'
    regex_end_time_capture = '(?:- {0,3})([0-9][0-9a-zA-Z: ]{0,9}[0-9a-zA-Z]|[0-9])'
    regex_weekday_capture = '[mtwfMTWF][dehinours]{2}[a-z]{0,6}'
    captured_start_time = re.search(regex_start_time_capture, string)
    captured_end_time = re.search(regex_end_time_capture, string)
    captured_weekday = re.search(regex_weekday_capture, string)
    if string[0].isalpha() == False:
        error_log.append('header must start with an alpha char')
    if len(string) > 60:
        error_log.append('header must be less than 60 char')
    if captured_weekday == None:
        error_log.append('cannot find weekday')
    else:
        day = re.search(regex_weekday_capture, string)[0]
        day = day[0:3].lower()
        if day not in weekdays:
            error_log.append('no such weekday')
        else:
            day_int = weekdays.index(day)
    if captured_start_time == None:
        error_log.append('cannot find start time')
    else:
        start_time = re.search(regex_start_time_capture, string).groups()[0]
        if bool(regex_time_format.match(start_time)) == False:
            error_log.append('start time formatting')
        else:
            times.append(start_time)
            start_time = datetime.strptime(start_time, '%I:%M %p').time()
    if captured_end_time == None:
        error_log.append('cannot find end time')
    else:
        end_time = re.search(regex_end_time_capture, string).groups()[0]
        if bool(regex_time_format.match(end_time)) == False:
            error_log.append('end time formatting')
        else:
            times.append(end_time)
            end_time = datetime.strptime(end_time, '%I:%M %p').time()
    if len(times) == 2:
        start_time_minutes = in_minutes(start_time)
        end_time_minutes = in_minutes(end_time)
        if start_time_minutes >= end_time_minutes:
            error_log.append('start time is not earlier than end time')
    if len(error_log) > 0:
        return error_log
    return (day_int, start_time, end_time)

def mine_timeslots(header):
    """
    Uses the header strings from get_time_headers to return a list of tuples representing all of the timeslots in the csv
    """
    timeslot_list = []
    error_list = []
    n = 5
    for string in header:
        timeslot = mine_timeslot(string)
        if isinstance(timeslot, list):
            error_dict = {}
            error_dict['error_coords'] = a1_notation((n, 1))
            error_dict['errors'] = timeslot
            error_list.append(error_dict)
        else:
            timeslot_list.append(timeslot)
        n = n + 1
    if len(error_list) > 0:
        return error_list
    return timeslot_list

def convert_avail_to_times(avail_list, header):
    """
    Used in mine_student_availability to match students' responses to the correct time column from the header
    """
    times = mine_timeslots(header)
    student_avail = []
    l = len(avail_list)
    n = 0
    while n < l:
        if avail_list[n] == 'Available':
            timeslot = times[n]
            student_avail.append(timeslot)
            n = n + 1
        else:
            n = n + 1
    return student_avail

def mine_student_availability(spreadsheet, header):
    """
    Creates a dict where each key is a student's cnet id and the corresponding value is a list of the times at which they're available
    """
    student_avail = {}
    for line in spreadsheet:
        if line != 0:
            avail_list = spreadsheet[line][4:]
            student_times = convert_avail_to_times(avail_list, header)
            student_avail[spreadsheet[line][0]] = student_times
    return student_avail

def student_avail_starts(student_avail):
    """
    Creates a truncated version of the dict returned by mine_student_availability -- the timeslot tuples only contain start times, not end times. Used with make_provisional_timetable to populate the HTML table with a couple of students' availabilities across the week.
    """
    abbrev_avails = {}
    for student in student_avail:
        timeslot_starts = []
        for time in student_avail[student]:
            abbrev_time = (time[0], time[1])
            timeslot_starts.append(abbrev_time)
        abbrev_avails[student] = timeslot_starts
    return abbrev_avails

def convert_pronoun_response(string):
    """
    Converts responses from the Google Form to match the way they're represented as options in the Student Model
    """
    if 'hers' in string:
        return 'F'
    elif 'him' in string:
        return 'M'
    elif 'they' in string:
        return 'NB'
    elif 'prefer not to specify' in string:
        return 'PNS'
    else:
        return 'O'

def basic_student_data(spreadsheet):
    """
    Takes the full spreadsheet and makes a dict for each student containing their basic biographical data. Returns a list of these dicts. Used to create new Student objects.
    """
    student_data = []
    student_dict = {}
    for line in spreadsheet:
        if line != 0:
            student_dict['cnet'] = spreadsheet[line][0]
            student_dict['last_name'] = spreadsheet[line][1]
            student_dict['first_name'] = spreadsheet[line][2]
            student_dict['pronouns'] = convert_pronoun_response(spreadsheet[line][3])
            student_data.append(student_dict)
            student_dict = {}
    return student_data

def get_earliest_start(timeslots):
    start_times = []
    for slot in timeslots:
        start_times.append(slot[1])
    start_times.sort()
    earliest = start_times[0]
    return earliest

def get_latest_end(timeslots):
    end_times = []
    for slot in timeslots:
        end_times.append(slot[2])
    end_times.sort(reverse=True)
    latest = end_times[0]
    return latest

def get_timeslot_column(timeslots):
    earliest = get_earliest_start(timeslots)
    latest = get_latest_end(timeslots)
    column_list = []
    n = earliest
    while n < latest:
        column_list.append(n)
        minutes = in_minutes(n)
        advance_time = minutes + 30
        new_time_tup = in_hours_and_minutes(advance_time)
        new_time = time(new_time_tup[0], new_time_tup[1])
        n = new_time
    return column_list

def provisional_timetable(timeslots):
    days = [0, 1, 2, 3, 4]
    column_times = get_timeslot_column(timeslots)
    timeslot_starts = []
    for slot in timeslots:
        weekday = slot[0]
        start_time = slot[1]
        end_time = slot[2]
        start = (weekday, start_time)
        timeslot_starts.append(start)
    timetable_dict = {}
    for time in column_times:
        row_list = []
        for day in days:
            if (day, time) in timeslot_starts:
                row_list.append(True)
            else:
                row_list.append(False)
        timetable_dict[time] = row_list
    for slot in timeslots:
        for row in timetable_dict:
            if slot[1] < row and slot[2] > row:
                timetable_dict[row][slot[0]] = 'continuation'
    final_timetable_dict = {}
    for time in timetable_dict:
        final_timetable_dict[time.strftime("%-I:%M %p").lower()] = timetable_dict[time]
    return final_timetable_dict

def timeslot_durations(timeslots):
    time = timeslots[0]
    start_min = in_minutes(time[1])
    end_min = in_minutes(time[2])
    duration_min = end_min - start_min
    duration_in_half_hour_incr = divmod(duration_min, 30)
    if duration_in_half_hour_incr[0] == 0:
        duration = 1
    elif duration_in_half_hour_incr[0] > 0:
        if duration_in_half_hour_incr[1] == 0:
            duration = duration_in_half_hour_incr[0]
        elif duration_in_half_hour_incr[1] > 0:
            duration = duration_in_half_hour_incr[0] + 1
    return duration

def add_student(student, sec):
    # add pronouns
    new_student = Student(cnetid=student['cnet'], last_name=student['last_name'], first_name=student['first_name'], section=sec, pronouns=student['pronouns'])
    return new_student

def add_students(student_list, sec):
    students = []
    for student in student_list:
        new_student = add_student(student, sec)
        students.append(new_student)
    return students

def add_timeslot(time_tup):
    existing = Timeslot.objects.all()
    for time in existing:
        if time.weekday == time_tup[0] and time.start_time == time_tup[1] and time.end_time == time_tup[2]:
            return time
    new_timeslot = Timeslot(weekday=time_tup[0], start_time=time_tup[1], end_time=time_tup[2])
    return new_timeslot

def add_timeslots(timeslots):
    section_timeslots = []
    for time_tup in timeslots:
        new_time = add_timeslot(time_tup)
        section_timeslots.append(new_time)
    return section_timeslots

def save_students(student_objs):
    for student in student_objs:
        student.save()

def save_timeslots(timeslot_objs, sec):
    existing = Timeslot.objects.all()
    for timeslot in timeslot_objs:
        if timeslot in existing:
            timeslot.section.add(sec)
        else:
            timeslot.save()
            timeslot.section.add(sec)

def add_timeslots_to_students(student_avail):
    for student in student_avail:
        student_obj = Student.objects.get(cnetid=student)
        for time in student_avail[student]:
            timeslot_obj = Timeslot.objects.filter(weekday=time[0], start_time=time[1], end_time=time[2])[0]
            student_obj.timeslots.add(timeslot_obj)

# TESTS

def define_week(start):
    """
    Takes a datetime.date and defines it as the first day of the week. Returns the first and last day of this seven-day week as a tuple. Used in define_quarter.
    """
    end = start + timedelta(days=6)
    return (start, end)

def define_quarter(first_day, n_weeks):
    """
    first_day should be a datetime.date -- defines the first day (should be a Monday) of the academic quarter. n_weeks sets the number of weeks in the quarter. Returns a dict where each key is an int (the nth week) and the value is a tuple of start/end dates for each week.
    """
    quarter = {}
    n = 1
    while n <= n_weeks:
        quarter[n] = define_week(first_day)
        first_day = first_day + timedelta(days=7)
        n = n + 1
    return quarter

def find_date_by_week(timeslot, week, quarter):
    """
    Takes a Django Timeslot object and returns a datetime.datetime for a defined week of the quarter.
    """
    selected_week = quarter[week]
    # translates week 9 in fall quarter to week 10 in the backend to account for thanksgiving
    if week == 9 and selected_week[0].month == 11:
        selected_week = quarter[10]
    actual_date = selected_week[0] + timedelta(days=timeslot.weekday)
    dated_timeslot = datetime.combine(actual_date, timeslot.start_time)
    return dated_timeslot

def find_week_in_quarter(week, quarter):
    """
    Used in the one-week calendar and for each row in the quarter-long calendar. Detetermines datetime.dates for each day, Monday to Friday, of a given week in a defined quarter.
    """
    day = quarter[week][0]
    mon_to_fri = [day]
    for i in range(4):
        day = day + timedelta(days=1)
        mon_to_fri.append(day)
    return mon_to_fri

def fix_timeslots_by_week(timeslot_list, week, quarter):
    """
    Takes a list of Django timeslots and returns a list of corresponding datetime.datetimes for the given week of the quarter.
    """
    dates = []
    for timeslot in timeslot_list:
        actual_date = find_date_by_week(timeslot, week, quarter)
        dates.append(actual_date)
    return dates

def any_timeslot_conflicts(combos):
    """
    Takes a list of Combinations and generates a dict where each key is a Timeslot and the value is a list of the sections that are connected to this timeslot and associated with one of the Combinations in the list. So, if more than one section is associated with a Timeslot, this means there's a scheduling conflict between at least two combinations.

    Used in the HTML template to identify and label conflicts as such for the one-week calendar.
    Also used in multiple_section_timeslots_by_week to separate conflicting timeslots from non-conflicting ones.
    """
    all_timeslots = {}
    for combo in combos:
        timeslots = combo.timeslots.all()
        for timeslot in timeslots:
            if timeslot not in all_timeslots:
                all_timeslots[timeslot] = [combo.section]
            else:
                all_timeslots[timeslot] += [combo.section]
    return all_timeslots

def multiple_section_timeslots_by_week(combos, week, quarter):
    """
    For a given week of the quarter, generates a dict where each key is a sec_name and each value is a list of datetime.datetimes representing meetings for that section. Does not include datetimes that constitute a scheduling conflict (those get dealt with in a different function).
    """
    section_dict = {}
    conflicts_dict = any_timeslot_conflicts(combos)
    actual_conflicts = []
    for timeslot in conflicts_dict:
        if len(conflicts_dict[timeslot]) > 1:
            actual_conflicts.append(timeslot)
    for combo in combos:
        timeslot_list = list(combo.timeslots.all())
        for time in actual_conflicts:
            if time in timeslot_list:
                timeslot_list.remove(time)
        dates = fix_timeslots_by_week(timeslot_list, week, quarter)
        section_dict[combo.section] = dates
    return section_dict

def seminars_by_week(combos):
    week_by_week = {}
    for combo in combos:
        combo_section = combo.section
        weeks = combo_section.seminar_weeks
        delimiter = ', '
        weeks = weeks.split(delimiter)
        for week in weeks:
            week = int(week)
            # translates week 9 in fall quarter to week 10 in the backend to account for thanksgiving
            if week == 9 and combo_section.quarter == 1:
                week = 10
            if week not in week_by_week:
                week_by_week[week] = [combo]
            else:
                week_by_week[week] += [combo]
    return week_by_week

def all_combos_for_quarter(year, quarter):
    """
    Retrieves all combinations of timeslots for a given quarter
    """
    sections = Section.objects.filter(year=year, quarter=quarter)
    all_combos = []
    for section in sections:
        combos = Combination.objects.filter(section=section)
        if len(combos) > 0:
            all_combos.extend(list(combos))
    return all_combos

def combination_lookup(all_combos_quarter, quarter):
    weeks = all_combos_quarter.keys()
    weeks = list(weeks)
    weeks.sort()
    all_dates = []
    for week in weeks:
        for combo in all_combos_quarter[week]:
            dates = fix_timeslots_by_week(combo.timeslots.all(), week, quarter)
            durations = []
            for ts in combo.timeslots.all():
                durations.append(ts.duration)
            n = 0
            for date in dates:
                new_dict = {}
                new_dict['week'] = week
                new_dict['date'] = str(date.year) + '-' + str(date.month) + '-' + str(date.day)
                new_dict['time'] = in_minutes(time(date.hour, date.minute))
                new_dict['combo'] = combo.pk
                new_dict['section'] = combo.section.pk
                new_dict['id'] = str(combo.pk) + '-' + str(date.month) + '-' + str(date.day) + '-' + str(in_minutes(time(date.hour, date.minute)))
                new_dict['duration'] = durations[n]
                n = n + 1
                all_dates.append(new_dict)
    return all_dates


def conflicts_full_quarter(weeks, quarter):
    """
    weeks should be a dict where each key is a week of the quarter and each value is a list of the Combinations (i.e. sections) meeting that week. Finds Timeslot conflicts week by week and returns a dict where each key is a datetime.date (**not a datetime.datimetime**) and each value is a list of tuples. Tuple[0] is a list of the sections involved in the scheduling conflict. Tuple[1] is the datetime.datetime where there is a conflict.
    """
    quarter_conflicts = {}
    for week in weeks:
        combos = weeks[week]
        conflicts_dict = any_timeslot_conflicts(combos)
        actual_conflicts = {}
        for time in conflicts_dict:
            if len(conflicts_dict[time]) > 1:
                actual_conflicts[time] = conflicts_dict[time]
        for time in actual_conflicts:
            day = find_date_by_week(time, week, quarter)
            just_day = day.date()
            if just_day not in quarter_conflicts:
                quarter_conflicts[just_day] = [(actual_conflicts[time], day)]
            else:
                quarter_conflicts[just_day] += [(actual_conflicts[time], day)]
    return quarter_conflicts


def full_quarter_schedule(weeks, quarter):
    """
    weeks should be a dict where each key is a week of the quarter and each value is a list of the Combinations (i.e. sections) meeting that week. Uses this dict to generate a dict where each key is a week of the quarter and each value is another dict generated by multiple_section_timeslots_by_week (where meeting datetime.datetimes are organized by section).
    """
    quarter_schedule = {}
    for week in weeks:
        combos = weeks[week]
        quarter_schedule[week] = multiple_section_timeslots_by_week(combos, week, quarter)
    return quarter_schedule

def timeslots_for_quarter_by_date(quarter_sched):
    """
    Uses the dict generated by full_quarter_schedule to generate a new dict, where each key is a datetime.date and each value is a list of tuples. Tuple[0] is the section that is meeting. Tuple[1] is the datetime.datetime specifying the meeting time.
    """
    day_dict = {}
    for week in quarter_sched:
        for section in quarter_sched[week]:
            for time in quarter_sched[week][section]:
                day = time.date()
                if day not in day_dict:
                    day_dict[day] = [(section, time)]
                else:
                    day_dict[day] += [(section,time)]
    return day_dict

def conflicts_integrated(full_quarter, conflicts):
    """
    Modifies the dict generated by timeslots_For_quarter_by_date by adding all of the entries from conflicts_full_quarter to the dict. Used in the HTML template to match datetime.dates in the blank calendar to the actual meeting times listed here.
    """
    integrated = full_quarter
    for day in conflicts:
        if day in integrated:
            integrated[day] += conflicts[day]
        else:
            integrated[day] = conflicts[day]
    for day in integrated:
        if len(integrated[day]) > 1:
            integrated[day] = sorted(integrated[day], key=lambda x: x[1])
    return integrated


def quarter_table(quarter):
    """
    Generates a dict where each key is a week in the quarter and each value is a list of datetime.dates representing the Monday to Friday of that week.

    Used in the HTML template to generate the blank quarter-long calendar.
    """
    quarter_rows = {}
    for week in quarter:
        row = find_week_in_quarter(week, quarter)
        quarter_rows[week] = row
    return quarter_rows

def get_chosen_combos(form_data):
    pk_list = []
    for n in form_data:
        pk = int(n)
        pk_list.append(pk)
    combo_list = []
    for n in pk_list:
        combo = Combination.objects.get(pk=n)
        combo_list.append(combo)
    return combo_list

def active_week_combos(week_by_week, sem_week):
    if sem_week in week_by_week:
        return week_by_week[sem_week]
    else:
        no_sems = []
        return no_sems

def find_first_active_week(week_by_week):
    active_weeks = list(week_by_week.keys())
    active_weeks.sort()
    return active_weeks[0]

def make_combo_label(combo):
    """
    Doesn't look like this is currently in use
    """
    timeslot_list = combo.timeslots.all()
    new_timeslot_list = []
    for time in timeslot_list:
        new = time.get_weekday_display() + ' ' + time.start_time.strftime("%-I:%M %p")
        new_timeslot_list.append(new)
    delimiter = ', '
    timeslot_string = delimiter.join(new_timeslot_list)
    return f'{combo.section} - {timeslot_string}'

def label_combos(combos):
    display_list = []
    for combo in combos:
        display = make_combo_label(combo)
        display_list.append(display)
    display_list.sort()
    return display_list