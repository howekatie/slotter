from datetime import time
from datetime import date
from datetime import datetime
from datetime import timedelta

from django.db.models import Q

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

def convert_timeslots_in_dict_to_objects(lookup_dict, timeslots_dj):
    """
    # I'm not sure if the one dict that is being generated by this function is actually in use anywhere?? Needs checking at some point!!
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

def timeslot_pk_lookup_dict(obj_lookup_dict, timeslots_dj):
    pk_dict = {}
    for timeslot_key in obj_lookup_dict:
        ts_list = []
        for timeslot in obj_lookup_dict[timeslot_key]:
            ts_list.append(timeslot.pk)
        pk_dict[timeslot_key.pk] = ts_list
    return pk_dict

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

# CSV READING

def full_spreadsheet(raw_data):
    """
    Takes a CSV file from csv.reader and makes a line-by-line dict
    """
    sheet_dict = {}
    n = 0
    for line in raw_data:
        sheet_dict[n] = line
        n = n + 1
    return sheet_dict

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
    opener = '['
    closer = ']'
    # finds part of string containing timeslot details
    start = string.index(opener)
    end = string.index(closer)
    ts_string = string[start+1:end]
    # isolates the weekday from the rest of the string
    day_sep = ':'
    day_cut = ts_string.index(day_sep)
    day = ts_string[:day_cut]
    # isolates the two times contained in the string
    time_range = ts_string[day_cut+2:]
    time_sep = '-'
    time_cut = time_range.index(time_sep)
    start_time = time_range[:time_cut-1]
    end_time = time_range[time_cut+2:]
    # convert strings to ints and datetime.times
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    day_int = weekdays.index(day)
    start_time = datetime.strptime(start_time, '%I:%M %p').time()
    end_time = datetime.strptime(end_time, '%I:%M %p').time()
    return (day_int, start_time, end_time)

def mine_timeslots(header):
    """
    Uses the header strings from get_time_headers to return a list of tuples representing all of the timeslots in the csv
    """
    timeslot_list = []
    for string in header:
        timeslot = mine_timeslot(string)
        timeslot_list.append(timeslot)
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
    if 'him' in string:
        return 'M'
    elif 'hers' in string:
        return 'F'
    elif 'theirs' in string:
        return 'NB'
    elif 'prefer not to specify' in string:
        return 'PNS'
    elif string == '':
        return 'NS'
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

"""

Not in use -- decided that this was an unneccessary amount of checking

def make_provisional_timetable(timeslots, student_avail):
    days = [0, 1, 2, 3, 4]
    column_times = get_timeslot_column(timeslots)
    timeslot_starts = []
    for slot in timeslots:
        weekday = slot[0]
        start_time = slot[1]
        end_time = slot[2]
        start = (weekday, start_time)
        timeslot_starts.append(start)
    students = list(student_avail.keys())
    first_student = students[0]
    last_student = students[len(students)-1]
    timetable_list = []
    row_dict = {}
    for time in column_times:
        for day in days:
            if (day, time) in timeslot_starts:
                day_dict = {}
                day_dict['state'] = True
                avail_students = []
                if (day, time) in student_avail[first_student]:
                    avail_students.append(first_student)
                if (day, time) in student_avail[last_student]:
                    avail_students.append(last_student)
                day_dict['students'] = avail_students
                row_dict[day] = day_dict
            else:
                day_dict = {}
                day_dict['state'] = False
                row_dict[day] = day_dict
        row_dict['time'] = time
        timetable_list.append(row_dict)
        row_dict = {}
    for slot in timeslots:
        for row in timetable_list:
            if slot[1] < row['time'] and slot[2] > row['time']:
                day = slot[0]
                row[day]['state'] = 'continuation'
    return timetable_list

"""

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