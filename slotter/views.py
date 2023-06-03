from django.shortcuts import render

from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import loader

from django.views.decorators.csrf import ensure_csrf_cookie

from django.core.files.storage import FileSystemStorage

from django import forms

from .models import Student, Timeslot, Section, Combination
from .utils import get_students_from_time, get_availabilities, make_class_list, make_combinations, pull_students, will_combo_together, convert_to_timeslot_object, convert_timeslot_list_to_objects, convert_timeslots_in_dict_to_objects, in_minutes, in_hours_and_minutes, timetable_range, timetable, find_rowspans, determine_timeslot_duration, timetable_with_rowspans, write_out_n, availabilities_by_timeslot, student_availability, any_required_timeslots, least_available_students, reverse_keys_and_vals, recommended_pairings, timeslot_choice_field, add_blank_field, working_combos_django, working_combos_pk, combo_lookup_dict_pk, student_cap_by_timeslot, make_selected_timeslots_list, make_selected_timeslots_list_dj, get_just_selected_timeslots, selected_timeslots_for_json, students_for_json, students_cnet_to_pk, selected_avail_dict, convert_to_student_object, convert_avail_dict, student_choice_field, student_choices_by_timeslot, tally_student_availability, make_pronoun_choices, make_student_combinations, student_combos_for_selected_timeslots, sort_timeslots_by_length, no_overlap, gut_options, gut_options_final, gut_for_all_times, working_student_combos, make_assignments, convert_assgs_pk, checkbox_count, display_students, matches_existing_combo, unique_timeslot_combo, stringify_assigned_student_numbers, destring_student_breakdown, combination_timeslot_assgned_students_lookup, timeslot_in_minutes, sort_timeslots, label_combo_by_timeslots, combo_dicts_for_display, define_week, define_quarter, find_date_by_week, fix_timeslots_by_week, convert_to_pyth_time, convert_list_to_pyth_time, find_week_in_quarter, any_timeslot_conflicts, quarter_table, multiple_section_timeslots_by_week, full_quarter_schedule, timeslots_for_quarter_by_date, conflicts_full_quarter, conflicts_integrated, get_chosen_combos, seminars_by_week, active_week_combos, find_first_active_week, basic_student_data, full_spreadsheet, get_time_headers, mine_timeslot, mine_timeslots, mine_student_availability, get_earliest_start, get_latest_end, get_timeslot_column, timeslot_durations, add_student, add_students, add_timeslot, add_timeslots, student_avail_starts, save_students, save_timeslots, add_timeslots_to_students, provisional_timetable, timeslot_pk_lookup_dict, all_combos_for_quarter, combination_lookup, check_csv, destring_int_keys, write_csv_text, find_thanksgiving, fall_first_monday, winter_first_monday, spring_first_monday, summer_first_monday, set_first_monday, json_time, json_time_dict, json_week_by_week_cal, combo_count_by_section, sections_meeting_same_week, saved_timeslot_combinations_lookup, combo_count_overlapping_weeks, natural_sort, sorted_section_choices
from .forms import SelectTimeslots, InitialSetup, HandpickByTimeslot, HandpickStudents, RefineAssignments, ChooseSection, SaveTimeslotCombo, CalendarViews, JumpWeek, ChooseQuarter, ImportSectionCSV, ConfirmCSVImport, CreateSection, ShowSavedCombos
from datetime import time, date, datetime, timedelta

from random import choice

import csv

from json import dumps, load, loads  

def index(request):
    return render(request, 'slotter/index.html', {})

def server_error(request):
    context = {}
    response = render(request, 'slotter/500.html', context=context)
    response.status_code = 500
    return response

def page_not_found(request, exception):
    context = {}
    response = render(request, 'slotter/404.html', context=context)
    response.status_code = 404
    return response

@ensure_csrf_cookie
def start(request):
    section_choices = sorted_section_choices()
    form1 = ChooseSection(section_choices=section_choices)
    active_section = request.session.get('active_section')
    if request.method == 'POST':
        if request.POST.get('section'):
            form1 = ChooseSection(request.POST or None, section_choices=section_choices)
            chosen_section_pk = int(request.POST['section'])
            sec = Section.objects.get(pk=chosen_section_pk)
            chosen_section = Section.objects.get(pk=chosen_section_pk).name
            request.session['section'] = chosen_section
            request.session['section_pk'] = chosen_section_pk
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
            saved_combos = list(section_dj.combination_set.all())
            labeled_combos = combo_dicts_for_display(saved_combos)
            combo_lookup = dumps(combination_timeslot_assgned_students_lookup(section_dj))
            form2 = InitialSetup(section=chosen_section_pk)
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
                'saved_combos': saved_combos,
                'combo_lookup': combo_lookup,
                'labeled_combos': labeled_combos,
                'sec': sec,
                })
        elif request.POST.get('min_students'):
            chosen_section_pk = request.session.get('section_pk')
            form2 = InitialSetup(request.POST or None, section=chosen_section_pk)
            if form2.is_valid():
                request.session['combination_string'] = ''
                request.session['min_students'] = form2.cleaned_data['min_students']
                request.session['n_seminars'] = form2.cleaned_data['n_seminars']
                return HttpResponseRedirect('/slotter/timeslots/')
            else:
                chosen_section_pk = request.session.get('section_pk')
                class_list = Student.objects.filter(section__pk=chosen_section_pk)
                class_size = len(class_list)
                timeslots = Timeslot.objects.filter(section__pk=chosen_section_pk)
                n_possible_timeslots = len(timeslots)
                section_dj = Section.objects.get(pk=chosen_section_pk)
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
    section_choices = sorted_section_choices()
    form0 = ChooseSection(section_choices=section_choices)
    active_section_pk = request.session.get('active_section')
    if request.method == 'POST':
        if request.POST.get('section'):
            form0 = ChooseSection(request.POST, section_choices=section_choices)
            sec_pk = int(request.POST['section'])
            active_section = Section.objects.get(pk=sec_pk)
            request.session['active_section'] = sec_pk
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
    if request.session.get('combination_string') != '' or request.session.get('combination_string') != None:
        combination_string = request.session.get('combination_string')
    min_students = request.session.get('min_students')
    n_seminars = request.session.get('n_seminars')
    sec_name = request.session.get('section')
    sec_pk = request.session.get('section_pk')
    sec_obj = Section.objects.get(pk=sec_pk)
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
    working_combos_dj = working_combos_django(working_combos, timeslots_dj)
    student_caps = student_cap_by_timeslot(min_n, timeslots_dj, sec_name)
    timeslot_choices_no_blank = timeslot_choice_field(timeslots_dj, working_combos_dj, lookup_dict)
    timeslot_choices = add_blank_field(timeslot_choices_no_blank)
    pk_lookup_dict = timeslot_pk_lookup_dict(lookup, timeslots_dj)
    working_combos_by_pk = working_combos_pk(working_combos_dj)
    pk_combo_lookup = combo_lookup_dict_pk(pk_lookup_dict, working_combos_by_pk)
    json_dump = dumps(pk_lookup_dict)
    json_dump2 = dumps(pk_combo_lookup)

    # other section filters
    same_week_secs = sections_meeting_same_week(sec_obj)
    saved_combo_lookup = dumps(saved_timeslot_combinations_lookup(same_week_secs))
    saved_combo_count = dumps(combo_count_overlapping_weeks(same_week_secs))
    show_combos_form = ShowSavedCombos(section_list=same_week_secs)

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
        'sec_pk': sec_pk,
        'same_week_secs': same_week_secs,
        'saved_combo_lookup': saved_combo_lookup,
        'saved_combo_count': saved_combo_count,
        'show_combos_form': show_combos_form,
        'combination_string': combination_string,
    }
    return HttpResponse(template.render(context, request))

@ensure_csrf_cookie
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
    timeslot_list.sort()
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
        'handpick_selections': handpick_selections,
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
        n_students = request.session.get('n_students' + str(n))
        tup = (selection, n_students)
        timeslot_list.append(tup)
        n = n + 1
    timeslot_objs_list = []
    for tup in timeslot_list:
        if Timeslot.objects.get(pk=tup[0]):
            ts = Timeslot.objects.get(pk=tup[0])
            timeslot_objs_list.append(ts)
    timeslot_objs_list = sort_timeslots(timeslot_objs_list)
    sorted_timeslot_tup_list = []
    for timeslot in timeslot_objs_list:
        for tup in timeslot_list:
            if timeslot.pk == tup[0]:
                sorted_timeslot_tup_list.append(tup)
    existing_combos = Combination.objects.filter(section=section)
    unique_combo = unique_timeslot_combo(existing_combos, timeslot_objs_list)
    assgned_student_breakdown = stringify_assigned_student_numbers(sorted_timeslot_tup_list)
    dict_response = {}
    # only creates a new Timeslot Combo for this section if there isn't already one with the exact same timeslots saved
    if unique_combo == True:
        new_combo = Combination(section=section, assigned_students_breakdown=assgned_student_breakdown)
        new_combo.save()
        for ts in  timeslot_objs_list:
            new_combo.timeslots.add(ts)
        new_combo.save()
        dict_response[new_combo.pk] = 'saved'
    else:
        dict_response['not_unique'] = 'not_saved'
    response = JsonResponse(dict_response)
    return response

def delete_timeslot_combo(request):
    combination_pk = load(request)['combo_pk']
    combo = Combination.objects.filter(pk=combination_pk)
    combo.delete()
    dict_response = {}
    dict_response['deleted'] = combination_pk
    response = JsonResponse(dict_response)
    return response

def set_timeslot_session_data(request):
    combination_string = load(request)['combo_data']
    if combination_string != None or combination_string != '':
        timeslot_list = destring_student_breakdown(combination_string)
        n_seminars = len(timeslot_list)
        section = int(request.session.get('section_pk'))
        students = Student.objects.filter(section__pk=section)
        min_students = divmod(len(students), n_seminars)[0]
        request.session['min_students'] = min_students
        request.session['n_seminars'] = n_seminars
        request.session['combination_string'] = combination_string
        dict_response = {}
        dict_response['min_students'] = min_students
        dict_response['n_seminars'] = n_seminars
        dict_response['combination_string'] = combination_string
        response = JsonResponse(dict_response)
        return response

def set_csv_session_data(request):
    csv_data = load(request)
    if csv_data != None or csv_data != '':
        request.session['csv_data'] = csv_data
        dict_response = {}
        dict_response['csv_data'] = csv_data
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
    combos = student_combos_for_selected_timeslots(timeslot_list, avail)
    sorted_timeslot_list = sort_timeslots_by_length(timeslot_list, avail)
    working = working_student_combos(sorted_timeslot_list, combos, passed_ten)
    assignments = make_assignments(working, combos)
    dj_assignments_test = convert_assgs_pk(assignments, class_list_dj, timeslots_dj)

    response = JsonResponse(dj_assignments_test)
    return response

def import_schedules(request):
    section_choices = sorted_section_choices()
    if request.method == 'POST':
        if request.POST.get('section'):
            form = ImportSectionCSV(request.POST, request.FILES, section_choices=section_choices)
            if form.is_valid():
                chosen_section = request.POST['section']
                section = Section.objects.get(pk=chosen_section)
                request.session['active_section'] = chosen_section
                open_sheet = csv.reader(request.FILES['spreadsheet'].read().decode('utf-8').splitlines())
                full_sheet = check_csv(open_sheet)
                if isinstance(full_sheet, dict):
                    header = get_time_headers(full_sheet)
                    student_data = basic_student_data(full_sheet)
                    header_timeslots = mine_timeslots(header)
                    if isinstance(header_timeslots[0], dict) == False:
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
                        associated_students = len(Student.objects.filter(section__pk=section.pk))
                        json_sheet = dumps(full_sheet)
                        form2 = ConfirmCSVImport(json_data=json_sheet, assoc_students=associated_students)
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
                            'prov_timetable': prov_timetable,
                            'form2': form2,
                            'json_sheet': json_sheet,
                            })
                    else:
                        time_format_errors = header_timeslots
                        return render(request, 'slotter/import_schedules.html', {
                        'time_format_errors': time_format_errors,
                        'section': section,
                        'chosen_section': chosen_section,
                        'form': form,
                    })

                else:
                    csv_errors = full_sheet
                    return render(request, 'slotter/import_schedules.html', {
                        'csv_errors': csv_errors,
                        'section': section,
                        'chosen_section': chosen_section,
                        'form': form,
                    })
        elif request.POST.get('spreadsheet_data'):
            json_sheet = request.POST.get('spreadsheet_data')
            section_pk = request.session['active_section']
            section = Section.objects.get(pk=section_pk)
            associated_students = len(Student.objects.filter(section__pk=section.pk))
            form2 = ConfirmCSVImport(request.POST or None, json_data=json_sheet, assoc_students=associated_students)
            if form2.is_valid():
                if request.POST.get('confirm_delete'):
                    active_section_timeslots = Timeslot.objects.filter(section=section)
                    active_section_students = Student.objects.filter(section=section)
                    for timeslot in active_section_timeslots:
                        timeslot.section.remove(section)
                    for student in active_section_students:
                        student.delete()
                    active_section_timeslots = section.timeslot_set.all()
                    active_section_students = Student.objects.filter(section=section)
                repythonized_sheet = loads(json_sheet)
                full_sheet = destring_int_keys(repythonized_sheet)
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
            form = ImportSectionCSV(initial={'section': active_section_pk}, section_choices=section_choices)
        else:
            form = ImportSectionCSV(section_choices=section_choices)
    template = loader.get_template('slotter/import_schedules.html')
    context = {
        'form': form,
    }
    return HttpResponse(template.render(context, request))

def csv_guidelines(request):
    context = {}
    template = loader.get_template('slotter/csv_guidelines.html')
    return HttpResponse(template.render(context, request))

def write_assignments_csv(request):
    json_csv_data = destring_int_keys(request.session.get('csv_data'))
    csv_list = write_csv_text(json_csv_data)
    sec_pk = request.session.get('section_pk')
    section = Section.objects.get(pk=sec_pk)
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="%s Meeting Assignments.csv"' % section },
    )
    fieldnames = ['Timeslot', 'Student']
    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for entry in csv_list:
        writer.writerow(entry)
    return response