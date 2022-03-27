from django.shortcuts import render

from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader

from django import forms

from .models import Student, Timeslot
from .forms import SelectTimeslots, InitialSetup

from datetime import time

from random import choice


# preliminary work

def get_students_from_time(timeslot):
    """
    Takes an individual Timeslot object and retrieves all the Students (through ManyToMany) who are available at this time
    Makes a list of these students, substituting each Student object with this student's cnetid (for ease of processing)
    Used in get_availabilities
    """
    student_list = []
    students = timeslot.student_set.all()
    for x in students:
        cnetid = x.cnetid
        student_list.append(cnetid)
    return student_list

def get_availabilities(min_n, timeslots):
    """
    Takes all Timeslot objects and turns them into (weekday, start_time) tuples (for ease of processing).
    min_n is the minimum # of students acceptable for a timeslot (if there are fewer than n students, the timeslot gets filtered out)
    Returns a dict where the key is a timeslot tuple and the values are the students available at that time
    """
    avail_dict = {}
    for x in timeslots:
        time = x.weekday, x.start_time
        avail_students = get_students_from_time(x)
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
    min_n is an argument only because of get_availabilities
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
    Takes all of the combinations of timeslots and determines which students are available for each combination of timeslots (by using get_availabilities)
    Compares the students available for each combo to the class list and filters out combos that don't include all the students in the class list
    Returns these combos as a list
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
    Takes all of the combos from pull_students
    Makes a new dict where each key is a timeslot and its corresponding value is a list of the timeslots that are compatible with it (according to the combos from pull_students)
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
        lookup_dict[timeslot] = combo_times
        combo_times = []
    return lookup_dict

def in_minutes(time):
    """
    Takes a time formatted as a tuple, e.g., (9,00) and converts it to minutes (where 0 minutes == midnight)
    """
    return time.hour*60 + time.minute

def in_hours_and_minutes(time):
    """
    Converts a time represented in minutes (where 0 min == midnight) back to a tuple, e.g., (9,00)
    """
    return divmod(time, 60)

def timetable_range(working_timeslots):
    """
    Takes the list of working timeslots from will_combo_together and strips away the day tuple (t[0])
    Determines what the earliest and latest times are from among these
    Returns a list of the range of times starting from the earliest and ending in the latest in 30 min increments
    This list of times is what determines what the time column in the HTML scheduling table will look like
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

def convert_to_timeslot_object(pyth_time, timeslots_dj):
    """
    Takes a tuple representing a time and returns the existing corresponding Timeslot object
    """
    for timeslot in timeslots_dj:
        dj_tuple = (timeslot.weekday, timeslot.start_time)
        if dj_tuple == pyth_time:
            return timeslot

def timetable(column_times, timeslots, timeslots_dj):
    """
    Creates the content for each HTML table cell (does not include the header row)
    Each key is just a time derived from timetable_range and the values (formatted as a list) represent subsequent cells in the same table row
    If the day/time represented by a cell corresponds with a timeslot, the value just is the Timeslot object
    If there is no corresponding timeslot for that day/time cell, the value is None
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
    Assigns a Timeslot.duration to each Timeslot in the list
    This ensures that in the HTML table that gets generated, the rowspan n is correct for each timeslot.
    Duration is expressed in terms of 30 min increments, so if a Timeslot's start time and end time are 30 minutes apart, the duration of this timeslot is 1.
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
    Takes an integer and returns the written version if it is between 0 and 9, otherwise just returns the int itself
    Right now, this is just being used in the template to write out the number of timeslots that need to be selected (totally for aesthetic purposes)
    """
    written_numbers = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",}
    if n in written_numbers:
        return written_numbers[n]
    else:
        return n

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

def working_combos_django(combos, timeslots_dj):
    # playing around with Django's forms to validate timeslot selections
    # using ChoiceField and checking selections against the list generated here
    # ChoiceField is a bit silly, since it cleans all of the submitted data and returns strings
    # this is why there is a string conversion as a part of this function
    # I guess I could redo the form with ModelChoiceField instead?
    new_combos = []
    new_combo = []
    for combo in combos:
        for timeslot in combo:
            converted = convert_to_timeslot_object(timeslot, timeslots_dj)
            converted = str(converted)
            new_combo.append(converted)
        new_combo.sort()
        new_combos.append(new_combo)
        new_combo = []
    return new_combos

def student_cap_by_timeslot(min_n, timeslots_dj):
    student_caps = {}
    avail = get_availabilities(min_n, timeslots_dj)
    for timeslot in avail:
        students = avail[timeslot]
        cap = len(students)
        new_time = str(convert_to_timeslot_object(timeslot, timeslots_dj))
        student_caps[new_time] = cap
    return student_caps

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

def working_student_combos(timelist, master_dict):
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

def only_combos_without_these_students(students, assg):
    """
    Uses without_these_students() to return a new dict with only those assignments that don't contain the relevant students together
    """
    filtered_assg = {}
    for key in assg:
        verdicts = []
        for timeslot in assg[key]:
            combo = assg[key][timeslot]
            verdict = without_these_students(students, combo)
            verdicts.append(verdict)
        if all(verdicts):
            filtered_assg[key] = assg[key]
    return filtered_assg

def display_assgs(assg):
    """
    Returns the actual dict that gets unpacked in the HTML template. Takes the assignment dict (or the filtered assignment dict -- still need to wire that in properly at some point) and returns the full assignment dict if there are less than 15 possible combos. If there are 15+, then it uses random.choice() to pick 10 possibilities to display instead.
    """
    if len(assg) <= 15:
        return assg
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
        return sample_dict

# note to self -- it would be good to write a function that records the combos that don't actually produce any results so that this can be saved (maybe to the db?) as a result that shouldn't be tried again

# the actual views    

def index(request):
    return HttpResponse("Hello, world. This is where the scheduling magic happens.")

def start(request):
    if request.method == 'POST':
        form = InitialSetup(request.POST)
        if form.is_valid():
            request.session['min_students'] = request.POST['min_students']
            request.session['n_seminars'] = request.POST['n_seminars']
            return HttpResponseRedirect('/slotter/timeslots/')
    else:
        form = InitialSetup()
    template = loader.get_template('slotter/start.html')
    context = {'form': form,}
    return HttpResponse(template.render(context, request))

def timeslots(request):
    min_students = request.session.get('min_students')
    n_seminars = request.session.get('n_seminars')
    sec_name = "Disco Elysium"
    n = int(n_seminars)
    min_n = int(min_students)
    timeslots_dj = Timeslot.objects.filter(section__name=sec_name)
    timeslots_pyth = list(get_availabilities(min_n, timeslots_dj).keys())
    class_list_dj = Student.objects.filter(section__name=sec_name)
    class_list = make_class_list(class_list_dj)
    all_time_combos = make_combinations(n, timeslots_pyth)
    avail = get_availabilities(min_n, timeslots_dj)
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
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",]
    durations = determine_timeslot_duration(working_timeslots_dj)
    lookup = convert_timeslots_in_dict_to_objects(lookup_dict, timeslots_dj)
    option_list = timeslot_options(n)
    max_students = len(class_list) - (n-1)*2
    template = loader.get_template('slotter/timeslots.html')
    context = {
    'table': table, 'weekdays': weekdays, 'durations': durations, 'lookup': lookup, 'n': n, 'n_written_out': n_written_out, 'min_students': min_students, 'n_seminars': n_seminars, 'n_possibilities': n_possibilities, 'option_list': option_list, 'max_students': max_students,}
    return HttpResponse(template.render(context, request))

def assign_students(request):
    min_n = 3
    n_timeslots = 4
    sec_name = "Disco Elysium"
    timeslots_dj = Timeslot.objects.filter(section__name=sec_name)
    class_list_dj = Student.objects.filter(section__name=sec_name)
    class_list = make_class_list(class_list_dj)
    avail = get_availabilities(min_n, timeslots_dj)
    timeslots_pyth = list(avail.keys())
    all_time_combos = make_combinations(n_timeslots, timeslots_pyth)
    working_combos = pull_students(avail, all_time_combos, class_list)
    timeslot1 = list(will_combo_together(timeslots_pyth, working_combos).keys())[1]
    timeslot2 = list(will_combo_together(timeslots_pyth, working_combos).keys())[0]
    timeslot3 = list(will_combo_together(timeslots_pyth, working_combos).keys())[4]
    timeslot4 = list(will_combo_together(timeslots_pyth, working_combos).keys())[3]
    timeslot_list = [(timeslot1, 2), (timeslot2, 2), (timeslot3, 3), (timeslot4, 2)]
    student1 = list(Student.objects.all())[1]
    student2 =  list(Student.objects.all())[3]
    students = [student1, student2]
    combos = student_combos_for_selected_timeslots(timeslot_list, avail)
    sorted_timeslot_list = sort_timeslots_by_length(timeslot_list, avail)
    working = working_student_combos(sorted_timeslot_list, combos)
    assignments = make_assignments(working, combos)
    dj_assignments = convert_assgs(assignments, class_list_dj, timeslots_dj)
    # just a test - filtering out combos with Harry and Evrart
    filtered = only_combos_without_these_students(students, dj_assignments)
    n_assignments = len(assignments)
    table = display_assgs(dj_assignments)
    template = loader.get_template('slotter/assign_students.html')
    context = {
    'assignments': assignments, 'n_assignments': n_assignments, 'table': table,}
    return HttpResponse(template.render(context, request))

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
    avail = get_availabilities(min_n, timeslots_dj)
    timeslots_pyth = list(get_availabilities(min_n, timeslots_dj).keys())
    all_time_combos = make_combinations(n, timeslots_pyth)
    working_combos_pyth = pull_students(avail, all_time_combos, class_list)
    lookup_dict = will_combo_together(timeslots_pyth, working_combos_pyth)
    tslots = list(convert_timeslots_in_dict_to_objects(lookup_dict, timeslots_dj).keys())
    working_combos = working_combos_django(working_combos_pyth, timeslots_dj)
    student_caps = student_cap_by_timeslot(min_n, timeslots_dj)
    timeslot_list = []
    for x in tslots:
        tup = (x, x)
        timeslot_list.append(tup)
    timeslots = timeslot_list
    form = SelectTimeslots(request.POST or None, t=timeslots, number=n, max_s=max_students, class_t=class_total, combos=working_combos, caps=student_caps,)
    if request.method == 'POST':
        if form.is_valid():
            return HttpResponseRedirect('/slotter/timeslots/')
    else:
        form = SelectTimeslots(t=timeslots, number=n, max_s=max_students, class_t=class_total, combos=working_combos, caps=student_caps,)
    template = loader.get_template('slotter/choose_timeslots.html')
    context = {'form': form, 'timeslots': timeslots,}
    return HttpResponse(template.render(context, request))


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