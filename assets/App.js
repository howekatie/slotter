import React from 'react';
import { useState, useEffect } from "react";

let xhr, startTime, endTime;
const SEMINARS = JSON.parse(document.getElementById('seminar-list').textContent);
const STUDENTS = JSON.parse(document.getElementById('student-list').textContent);
const COMBOSTATUS = JSON.parse(document.getElementById('unique-combo').textContent);

const ERRORS = [
  {
    error: "twoplus",
    tripped: false,
    pronouns: [],
  },
  {
    error: "even",
    tripped: false,
    pronouns: [],
  },
  {
    error: "nocombos",
    tripped: false,
    pronouns: [],
  },
];

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';')
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        // Does this cookie string begin with the name we want?
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue
  }

  const csrftoken = getCookie('csrftoken')

function Reset({ onResetClick, autofill, students }) {
  // button that resets all prev selections
  let disState = false;
  let buttonState = "operation-button";
  let count = 0;
  for (let student of students) {
    if (student.selection !== null) {
      count = count + 1;
    }
  }
  if (autofill === false || count === 0) {
    // button is disabled if no selections have been made
    disState = true;
    buttonState = "disabled";
  }
  return (
    <button onClick={onResetClick} className={buttonState} disabled={disState}>
      Reset
    </button>
  );
}

function DownloadCSV({ students, onCSVClick }) {
  let buttonState = "operation-button";
  let disState = false;
  for (let student of students) {
    if (student.selection === null) {
      disState = true;
      buttonState = "disabled"
    }
  }
  return (
    <button className={buttonState} disabled={disState} onClick={onCSVClick}>
    Download CSV
    </button>
  );
}

function AutofillRest({
  onAutofillClick,
  students,
  pronounFilters,
  clicked,
  errors,
}) {
  /*
  button to autoselect students for remaining slots in each seminar
  pressable if at least one student has been selected or if one groupby pronoun option has been selected (and there are no pronoun-related errors)
  disables if there are no selections left to be made (n.b. clicked is kind of redundant right now??)
  */
  let count = 0;
  for (let student of students) {
    if (student.selection !== null) {
      count = count + 1;
    }
  }
  let pronounCount = 0;
  for (let pronoun of pronounFilters) {
    if (pronoun.selection !== null) {
      pronounCount = pronounCount + 1;
    }
  }
  let errorCount = 0;
  for (let error of errors) {
    if (error.tripped === true) {
      errorCount = errorCount + 1;
    }
  }
  let disState = true;
  let buttonState = "disabled";
  if (clicked === true) {
    disState = true;
    buttonState = "disabled";
  } else if (
    errorCount === 0 &&
    ((count > 0 && count < students.length) || pronounCount > 0)
  ) {
    disState = false;
    buttonState = "operation-button";
  }
  return (
    <button
      disabled={disState}
      onClick={onAutofillClick}
      className={buttonState}
    >
      Autofill rest
    </button>
  );
}

function ReRoll({ onReRollClick, autofill }) {
  /*
  button that selects a different configuration of students based on previously selected parameters (grouping specific students in a seminar, grouping by pronouns)
  only enabled if 'autofill rest' has been pressed
  */
  let disState = false;
  let buttonState = "operation-button";
  if (autofill === false) {
    disState = true;
    buttonState = "disabled";
  }
  return (
    <button disabled={disState} onClick={onReRollClick} className={buttonState}>
      Re-roll
    </button>
  );
}

function GroupByPronounsToggle({ onGroupByToggleClick, buttonState }) {
  // button that toggles visibility of groupby pronoun options
  let buttonText = "Group by pronouns \u25BC";
  if (buttonState === true) {
    buttonText = "Group by pronouns \u25B2";
  }
  return (
    <button className="operation-button" onClick={onGroupByToggleClick}>
      {buttonText}
    </button>
  );
}

function FilterSpecifier({
  spec,
  label,
  onSpecClick,
  pronounState,
  pronounSelection,
}) {
  /* 
  button tied to a pronoun used by at least one student in the class
  specifies how to filter students by pronoun (current options -- even split, two or more)
  enabled when the corresponding pronoun buton has been selected
  toggles on/off with pressing or if another filtering option has been selected
  */
  let buttonState, disState;
  if (pronounState === true) {
    if (pronounSelection !== spec) {
      buttonState = "off";
      disState = false;
    } else if (pronounSelection === spec) {
      buttonState = "on";
      disState = false;
    }
  } else if (pronounState === false) {
    buttonState = "disabled";
    disState = true;
  }
  return (
    <button className={buttonState} onClick={onSpecClick} disabled={disState}>
      {label}
    </button>
  );
}

function PronounButton({ label, onPronounClick, pronounState, specifiers }) {
  // button group that filters by the pronoun selected; {specifiers} are the group of FilterSpecifier buttons associated with the main pronoun button
  let buttonOn;
  if (pronounState === true) {
    buttonOn = "on";
  } else {
    buttonOn = "off";
  }
  return (
    <div className="pronoun-button-row">
      <button className={buttonOn} onClick={onPronounClick}>
        {label}
      </button>
      {specifiers}
    </div>
  );
}

function SaveTimeslotButton ({ onSaveTSClick }) {
  return (
    <button type="button" className="save_ts" onClick={onSaveTSClick}>Save timeslots</button>
    );
}

function Button({
  name,
  selection,
  timeId,
  onButtonClick,
  disabled,
  only,
  autofill,
}) {
  /*
  button for assigning student to a seminar time
  tied to a Seminar component
  possible button states: 'on' if selected, 'only' if must be selected for a time (but hasn't yet been selected), 'disabled' if selected already for a different time, 'off' if still selectable for a time
  */
  let buttonStyle;
  let disState = false;
  if (selection === timeId && autofill === false) {
    buttonStyle = "on";
  } else if (selection === timeId && autofill === true) {
    buttonStyle = "autofill-selected";
  } else if (disabled.includes(timeId)) {
    buttonStyle = "disabled";
    disState = true;
  } else if (only === true) {
    buttonStyle = "only";
  } else {
    buttonStyle = "off";
  }
  return (
    <button className={buttonStyle} onClick={onButtonClick} disabled={disState}>
      {name}
    </button>
  );
}

function Seminar({ label, remaining, buttons, students, timeId }) {
  //includes all the student Button components for a given seminar time, a list of students selected so far, a count for remaining student slots left in the seminar time
  const selectedStudents = students.map((student) => {
    let name = student.first_name + " " + student.last_name;
    let listKey = student.id + timeId;
    return <li key={listKey}>{name}</li>;
  });
  return (
    <div className="ts-container">
      <p className="timeslot-header">{label}</p>
      <p className="slot-count">Remaining slots: {remaining}</p>
      <div className="seminar">
        <div className="list_container">{selectedStudents}</div>
      </div>
      <div className="button_container">{buttons}</div>
    </div>
  );
}

function SaveTimeslotBox({comboStatus}) {
  // the box that appears allowing the user to save this particular combination of timeslots, if the possibilities for assigning students look good to them
  // comboStatus is an object with "value" as a key. If this combination of timeslots already exists (determined in the backend), the value is false and the box does not appear.
  let saveBoxDis;
  if (comboStatus.value === false) {
    saveBoxDis = "none";
  } else {
    saveBoxDis = "block";
  }

  function fadeInSaveMessage() {
      let timeslotsSaveMessage = document.getElementById("ts_saved_message");
      timeslotsSaveMessage.style.opacity = 100;
    }

  function fadeSaveBox() {
      let saveTimeslotsBox = document.getElementById("save_ts_box");
      saveTimeslotsBox.style.opacity = 0;
    }

  function popSaveBox() {
      let saveTimeslotsBox = document.getElementById("save_ts_box");
      saveTimeslotsBox.style.display = "none";
    }

  function handleSaveTimeslots() {
    // hits the save_timeslots_combo view, which does the actual work -- body of the message is empty, since the view works off of existing session data
    // the rest is just a matter of acknowledging the save to the user and popping this div out of view
    let timeslotsSaveMessage = document.getElementById("ts_saved_message");
    fetch('/slotter/save_timeslots/', {
      method: 'POST',
      mode: "same-origin",
      headers: {
        "X-CSRFToken": csrftoken,
        "Accept": "network/json",
        "Content-Type": "network/json",
      },
      body: {}
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .then(timeslotsSaveMessage.style.display = "inline-block")
    .then(timeslotsSaveMessage.style.opacity = 0)
    .then(setTimeout(fadeInSaveMessage, 100))
    .then(setTimeout(fadeSaveBox, 1200))
    .then(setTimeout(popSaveBox, 1600))
  }

  return (
    <div className="save_timeslots_container" id="save_ts_box" style={{ display: saveBoxDis }}>
      <span class="standout">Happy with what you see?</span>
      <div class="save_ts_text">
        Save this combination of timeslots so that you can figure out student assignments later, see these timeslots while picking timeslots for a different section, or see all of your selected timeslots together in <a href="/slotter/calendar/">Calendar Mode</a>.
      </div>
      <SaveTimeslotButton onSaveTSClick={() => handleSaveTimeslots()} />
        <span id="ts_saved_message">- Saved!</span>
    </div>
    );
}

function SeminarRosterPicker({ seminars, students, errors, comboStatus }) {
  // the main component!

  function timesCorrection(students, allComboKeys) {
    /*
    removes a time (or times) from student.times if there are no actual student combos that this student is a part of for that given time
    so, basically, a student could be theoretically available for a given time but in practice should not be selected, since there will be no viable combinations they can be a part of -- this function corrects for that
    */
    for (let student of students) {
      if (student.times.length > 1) {
        for (let time of student.times) {
          if (inACombo(student.id, time, allComboKeys) === false) {
            let index = student.times.indexOf(time);
            student.times.splice(index, 1);
          }
        }
      }
    }
  }

  function initialOnlies(stds) {
    /*
    used when no selections have been made -- finds students who are available for only one seminar time and identifies them as such with student.only
    downstream effect is that the associated student button uses the 'only' class for its style
    */
    for (let student of stds) {
      if (student.times.length === 1) {
        student.only = true;
      }
    }
  }

  function findIfOnly(stds, remainingCombos) {
    /*
    identifies if a student can only be selected for one time now that some other student selections have been made (narrowing down the remaining possible combinations)
    downstream effect is the style used on the relevant button for this student
    */
    for (let student of stds) {
      if (student.times.length > 1) {
        let trues = 0;
        for (let time of student.times) {
          if (inACombo(student.id, time, remainingCombos)) {
            trues = trues + 1;
          }
        }
        if (trues === 1) {
          student.only = true;
        } else if (trues > 1) {
          student.only = false;
        }
      }
    }
  }

  const [onOff, setOnOff] = useState(students); // main state -- keeps track of each student and which seminar the student has been selected for (if any yet) -- see students.js
  const [seminarCount, setSeminarCount] = useState(seminars); // seminar data -- keeps track of number of student slots remaining for each seminar time
  const [selectionHistory, setSelectionHistory] = useState(
    JSON.parse(JSON.stringify(students)) // used by handleAutofill() -- records current state of onOff (so, basically currently selected students) and uses this to hold those students as fixed if autofill is used, making re-roll possible
  );
  const [autofillPressed, setAutofillPressed] = useState(false);
  const [autofillErrors, setAutofillErrors] = useState(errors);
  const [groupByPronouns, setGroupByPronouns] = useState(false);

  const [comboData, setComboData] = useState({});
  const [comboCount, setComboCount] = useState(Object.keys(comboData).length); // not currently in use (commented out) but identifies possible student combinations remaining as selections are made
  const [staticComboCount, setStaticComboCount] = useState(Object.keys(comboData).length);
  const [loaderOpacity, setLoaderOpacity] = useState(1)
  const [curtainOpacity, setCurtainOpacity] = useState(1)
  const [curtainDisplay, setCurtainDisplay] = useState("block")

  const allComboKeys = Object.keys(comboData);
 
  useEffect(() => {
    xhr = new XMLHttpRequest();
    startTime = performance.now()
    xhr.onreadystatechange = alertContents;
    xhr.open("GET", "/slotter/assignment_churn/", true);
    xhr.send();
  }, []);

  function alertContents() {
    if (xhr.readyState === XMLHttpRequest.DONE) {
      endTime = performance.now()
      let loadingTime = (endTime - startTime) / 1000
      console.log(loadingTime)
      let response = xhr.responseText;
      let data = JSON.parse(response)
      setComboCount(Object.keys(data).length)
      setStaticComboCount(Object.keys(data).length)
      setComboData(data)
      setLoaderOpacity(0)
      setTimeout(() => {
        setCurtainOpacity(0)
      }, 1000)
      setTimeout(() => {
        setCurtainDisplay("none")
      }, 1000)
    }
  }

/*
  useEffect(() => {
    fetch('/slotter/assignment_churn/')
    .then(response => response.json())
    .then((data) => {
      setComboCount(Object.keys(data).length)
      setStaticComboCount(Object.keys(data).length)
      setComboData(data)
    })
    .then(() => setLoaderOpacity(0))
    .then(() => setTimeout(() => {
      setCurtainOpacity(0)
    }, 1000))
    .then(() => setTimeout(() => {
      setCurtainDisplay("none")
    }, 1000))
  }, []);
*/

  function countSelections(timeId, stds) {
    let count = 0;
    for (let student of stds) {
      if (student.selection === timeId) {
        count = count + 1;
      }
    }
    return count;
  }

  function updateSlots(slots, selections) {
    return slots - selections;
  }

  function inACombo(studentId, timeId, remainingCombos) {
    for (let combo of remainingCombos) {
      if (comboData[combo][timeId].includes(studentId)) {
        return true;
      }
    }
    return false;
  }

  function toggleDisableds(stds, time, selections, remainingCombos) {
    for (let student of stds) {
      if (!student.disabled.includes(time.id)) {
        if (student.selection && student.selection !== time.id) {
          student.disabled.push(time.id);
        } else if (selections === time.slots && student.selection !== time.id) {
          student.disabled.push(time.id);
        } else if (
          student.selection === null &&
          student.times.includes(time.id)
        ) {
          if (inACombo(student.id, time.id, remainingCombos) === false) {
            student.disabled.push(time.id);
          }
        }
      } else {
        if (
          selections < time.slots &&
          student.selection === null &&
          inACombo(student.id, time.id, remainingCombos) === true
        ) {
          let index = student.disabled.indexOf(time.id);
          student.disabled.splice(index, 1);
        }
      }
    }
  }

  function getStudents(time, stds) {
    let studentSelections = [];
    for (let student of stds) {
      if (student.selection === time.id) {
        studentSelections.push(student.id);
      }
    }
    return studentSelections;
  }

  function allInCombo(time, studentSelections, combo) {
    for (let student of studentSelections) {
      if (!combo[time.id].includes(student)) {
        return false;
      }
    }
    return true;
  }

  function liveOption(combo, seminars, stds) {
    let verdicts = [];
    for (let time of seminars) {
      let stdsSelected = getStudents(time, stds);
      let verdict = allInCombo(time, stdsSelected, combo);
      verdicts.push(verdict);
    }
    return !verdicts.includes(false);
  }

  function liveCombos(combos, seminars, stds) {
    let comboList = [];
    for (let combo in combos) {
      let verdict = liveOption(combos[combo], seminars, stds);
      if (verdict === true) {
        comboList.push(combo);
      }
    }
    return comboList;
  }

  function updateCounts(seminars, onOff, remainingCombos) {
    for (let time of seminars) {
      let selections = countSelections(time.id, onOff);
      toggleDisableds(onOff, time, selections, remainingCombos);
      let remainingSlots = updateSlots(time.slots, selections);
      time.remaining = remainingSlots;
    }
  }

  function handleButton(stdId, timeId, slots) {
    let newOnOff = onOff.slice();
    let selections = countSelections(timeId, newOnOff);
    console.log(selections);
    for (let student of newOnOff) {
      if (student.id === stdId) {
        if (student.selection !== timeId && selections < slots) {
          student.selection = timeId;
        } else {
          student.selection = null;
          resetComboError();
        }
      }
    }
    let newSeminarCount = seminarCount.slice();
    let remainingCombos = liveCombos(comboData, seminars, newOnOff);
    console.log(remainingCombos, 'remaining combos')
    let newComboCount = remainingCombos.length;
    updateCounts(newSeminarCount, newOnOff, remainingCombos);
    findIfOnly(newOnOff, remainingCombos);
    setComboCount(newComboCount);
    setOnOff(newOnOff);
    setSelectionHistory(JSON.parse(JSON.stringify(onOff)));
    console.log(selectionHistory, "new");
    setSeminarCount(newSeminarCount);
    setAutofillPressed(false);
  }

  function handleReset() {
    let newOnOff = onOff.slice();
    for (let student of newOnOff) {
      student.selection = null;
      student.disabled = [];
      student.only = false;
    }
    let newSeminarCount = seminarCount.slice();
    for (let time of newSeminarCount) {
      time.remaining = time.slots;
    }
    let newErrors = autofillErrors.slice();
    for (let error of newErrors) {
      error.tripped = false;
      error.pronouns = [];
    }
    let newSelectionHistory = selectionHistory.slice();
    for (let student of newSelectionHistory) {
      student.selection = null;
    }
    initialOnlies(newOnOff);
    setOnOff(newOnOff);
    setSelectionHistory(newSelectionHistory);
    setSeminarCount(newSeminarCount);
    setComboCount(allComboKeys.length);
    setAutofillPressed(false);
    setAutofillErrors(newErrors);
    resetPronouns();
  }

  function randomishNumber(max) {
    return Math.floor(Math.random() * max);
  }

  function handleGroupByPronouns() {
    let newGroupByPronouns = groupByPronouns;
    newGroupByPronouns = newGroupByPronouns ? false : true;
    setGroupByPronouns(newGroupByPronouns);
  }

  function handleAutofill(stds, pronouns) {
    console.log("history", selectionHistory);
    let currentCombos = liveCombos(comboData, seminars, stds);
    for (let pro of pronouns) {
      console.log(currentCombos, "# combos");
      if (pro.selection !== null) {
        if (pro.selection === "even") {
          currentCombos = findEvenSplit(pro.pronoun, currentCombos, stds);
        } else if (pro.selection === "twoplus") {
          currentCombos = findTwoPlus(pro.pronoun, currentCombos, stds);
        }
      }
    }
    let max = currentCombos.length;
    let newErrors = autofillErrors.slice();
    let errors = 0;
    for (let error of newErrors) {
      if (error.error === "nocombos") {
        error.tripped = max === 0;
        errors = error.tripped ? errors + 1 : errors;
      } else if (error.tripped === true) {
        errors = errors + 1;
      }
    }
    setAutofillErrors(newErrors);
    if (errors === 0) {
      setAutofillPressed(true);
      let selectedComboKey = currentCombos[randomishNumber(max)];
      let selectedCombo = comboData[selectedComboKey];
      let newOnOff = onOff.slice();
      for (let time in selectedCombo) {
        for (let student of selectedCombo[time]) {
          for (let s of newOnOff) {
            if (s.id === student) {
              s.selection = Number(time);
            }
          }
        }
      }
      let newSeminarCount = seminarCount.slice();
      let remainingCombos = liveCombos(comboData, seminars, newOnOff);
      let newComboCount = max;
      updateCounts(newSeminarCount, newOnOff, remainingCombos);
      setComboCount(newComboCount);
      setOnOff(newOnOff);
      setSeminarCount(newSeminarCount);
    }
  }

  function handleCSV(selectedCombo) {
    fetch('/slotter/set_csv_session_data/', {
      method: 'POST',
      mode: "same-origin",
      headers: {
        "X-CSRFToken": csrftoken,
        "Accept": "network/json",
        "Content-Type": "network/json",
      },
      body: JSON.stringify(selectedCombo)
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .then(() => window.location.href = '/slotter/write_assignments_csv/');
  }

  const sems = [];
  for (let timeslot of seminarCount) {
    let label = timeslot.day + ", " + timeslot.start_time;
    let buttons = [];
    let studentList = [];
    for (let student of onOff) {
      if (student.selection === timeslot.id) {
        studentList.push(student);
      }
      if (student.times.includes(timeslot.id)) {
        let index = onOff.indexOf(student);
        let studentAutofillHistory = selectionHistory[index];
        let selectedForAutofill = false;
        if (
          student.id === studentAutofillHistory.id &&
          student.selection === studentAutofillHistory.selection &&
          autofillPressed === true
        ) {
          selectedForAutofill = true;
        }
        let name = student.first_name + " " + student.last_name;
        buttons.push(
          <Button
            id={student.id}
            name={name}
            selection={student.selection}
            timeId={timeslot.id}
            onButtonClick={() =>
              handleButton(student.id, timeslot.id, timeslot.slots)
            }
            disabled={student.disabled}
            only={student.only}
            autofill={selectedForAutofill}
          />
        );
      }
    }
    sems.push(
      <Seminar
        label={label}
        remaining={timeslot.remaining}
        buttons={buttons}
        students={studentList}
        timeId={timeslot.id}
      />
    );
  }
  let pronouns = [];
  let pronounButtons = [];

  const pronounLabels = {
    F: "she/her",
    M: "he/him",
    NB: "they/them",
  };

  for (let student of students) {
    for (let pronoun of student.pronouns) {
      if (!pronouns.includes(pronoun)) {
        pronouns.push(pronoun);
      }
    }
  }

  let pronounStates = [];
  for (let p of pronouns) {
    let proState = {
      pronoun: p,
      on: false,
      selection: null,
    };
    pronounStates.push(proState);
  }

  const [pronounFilters, setPronounFilters] = useState(pronounStates);

  for (let p of pronounFilters) {
    let label = pronounLabels[p.pronoun];

    let specButtons = [
      <FilterSpecifier
        spec={"even"}
        label={"Even split"}
        onSpecClick={() => handleSpecification("even", p.pronoun)}
        pronounState={p.on}
        pronounSelection={p.selection}
      />,
      <FilterSpecifier
        spec={"twoplus"}
        label={"Two or more"}
        onSpecClick={() => handleSpecification("twoplus", p.pronoun)}
        pronounState={p.on}
        pronounSelection={p.selection}
      />,
    ];

    pronounButtons.push(
      <PronounButton
        label={label}
        onPronounClick={() => handlePronoun(p.pronoun)}
        pronounState={p.on}
        specifiers={specButtons}
      />
    );
  }

  function resetPronouns() {
    let newPronouns = pronounFilters.slice();
    for (let p of newPronouns) {
      p.on = false;
      p.selection = null;
    }
    setPronounFilters(newPronouns);
  }

  function resetComboError() {
    let newErrors = autofillErrors.slice();
    for (let e of newErrors) {
      if (e.error === "nocombos") {
        e.tripped = false;
      }
    }
    setAutofillErrors(newErrors);
  }

  function pronounCount(p) {
    let studentsUsingPro = students.filter((s) => s.pronouns.includes(p));
    return studentsUsingPro.length;
  }

  function pronounSpecValidation(pronoun, spec) {
    let count = pronounCount(pronoun);
    if (spec === "twoplus") {
      return count >= 2;
    } else if (spec === "even") {
      return count >= seminars.length;
    }
  }

  function handlePronoun(p) {
    let newPronouns = pronounFilters.slice();
    for (let pro of newPronouns) {
      if (pro.pronoun === p) {
        if (pro.on === true) {
          pro.on = false;
          resetComboError();
          pro.selection = null;
          let newErrors = autofillErrors.slice();
          resetErrors(newErrors, pro.pronoun);
          setAutofillErrors(newErrors);
        } else {
          pro.on = true;
        }
        setPronounFilters(newPronouns);
        console.log(pronounFilters);
      }
    }
  }

  function resetErrors(newErrors, pronoun) {
    for (let e of newErrors) {
      if (e.pronouns.includes(pronoun)) {
        let i = e.pronouns.indexOf(pronoun);
        e.pronouns.splice(i, 1);
        if (e.pronouns.length === 0) {
          e.tripped = false;
        }
      }
    }
  }

  function handleSpecification(spec, pronoun) {
    let newPronouns = pronounFilters.slice();
    for (let pro of newPronouns) {
      if (pro.pronoun === pronoun) {
        let newErrors = autofillErrors.slice();
        resetErrors(newErrors, pronoun);
        if (pro.selection !== spec) {
          pro.selection = spec;
          resetComboError();
          if (!pronounSpecValidation(pronoun, spec)) {
            console.log(spec);
            for (let e of newErrors) {
              if (e.error === spec) {
                e.pronouns.push(pronoun);
                e.tripped = true;
              }
            }
          }
        } else {
          pro.selection = null;
        }
        setAutofillErrors(newErrors);
        console.log(autofillErrors);
        setPronounFilters(newPronouns);
        console.log(pronounFilters);
      }
    }
  }

  let errorBoxDisplay;

  function writeErrorMessages() {
    let errors = [];
    for (let e of autofillErrors) {
      if (e.error === "nocombos" && e.tripped === true) {
        errors.push(
          "Sorry, there are no valid assignments that fit the parameters you've selected. Deselect one or more and try again."
        );
      }
      if (e.pronouns.length > 0) {
        if (e.pronouns.length === 1 && e.error === "twoplus") {
          errors.push(
            `Too few students use ${e.pronouns[0]} to assign them together in groups of 2 or more.`
          );
        } else if (e.pronouns.length === 1 && e.error === "even") {
          errors.push(
            `Too few students use ${e.pronouns[0]} to split them evenly between all seminar groups.`
          );
        } else if (e.error === "twoplus") {
          let pros = e.pronouns.join(", ");
          errors.push(
            `Too few students use ${pros} to assign them together in groups of 2 or more.`
          );
        } else if (e.error === "even") {
          let pros = e.pronouns.join(", ");
          errors.push(
            `Too few students use ${pros} to split them evenly between all seminar groups.`
          );
        }
      }
    }
    return errors;
  }

  let errorMessages = writeErrorMessages();

  console.log(errorMessages);

  if (errorMessages.length === 0) {
    errorBoxDisplay = "hidden";
  } else {
    errorBoxDisplay = "visible";
  }

  let pronounContainerDisplay = groupByPronouns ? "block" : "none";

  function findTwoPlus(pronoun, comboList, allStudents) {
    let twoPlus = [];
    for (let combo of comboList) {
      let stopped = false;
      for (let time in comboData[combo]) {
        let students = comboData[combo][time];
        let matches = allStudents.filter(
          (student) =>
            students.includes(student.id) && student.pronouns.includes(pronoun)
        );
        if (matches.length === 1) {
          stopped = true;
          break;
        }
      }
      if (stopped === false) {
        twoPlus.push(combo);
      }
    }
    return twoPlus;
  }

  function evenPronounDistribution(seminarNo, pronoun, students) {
    let distribution = [];
    let relevantStudents = students.filter((student) =>
      student.pronouns.includes(pronoun)
    );
    if (relevantStudents.length % seminarNo === 0) {
      let n = relevantStudents.length / seminarNo;
      for (let i = 0; i < seminarNo; i++) {
        distribution.push(n);
      }
      return distribution;
    } else {
      let baseN = Math.floor(relevantStudents.length / seminarNo);
      let remainder = relevantStudents.length % seminarNo;
      for (let i = 1; i <= seminarNo; i++) {
        if (i <= remainder) {
          distribution.push(baseN + 1);
        } else {
          distribution.push(baseN);
        }
      }
      return distribution.sort();
    }
  }

  function findEvenSplit(pronoun, comboList, allStudents) {
    let evenSplit = [];
    let distribPattern = evenPronounDistribution(
      Object.keys(seminars).length,
      pronoun,
      allStudents
    );
    for (let combo of comboList) {
      let pattern = [];
      for (let time in comboData[combo]) {
        let students = comboData[combo][time];
        let matches = allStudents.filter(
          (student) =>
            students.includes(student.id) && student.pronouns.includes(pronoun)
        );
        pattern.push(matches.length);
      }
      pattern.sort();
      if (identicalArray(pattern, distribPattern)) {
        evenSplit.push(combo);
      }
    }
    console.log(distribPattern);
    return evenSplit;
  }

  function identicalArray(arr1, arr2) {
    if (arr1.length !== arr2.length) {
      return false;
    }
    for (let i = 0; i < arr1.length; i++) {
      if (arr1[i] !== arr2[i]) {
        return false;
      }
    }
    return true;
  }

  let remainingCombos = liveCombos(comboData, seminars, onOff)
  let selectedCombo = null
  if (remainingCombos.length === 1) {
    selectedCombo = comboData[parseInt(remainingCombos[0])]
  }

  return (
    <div id="main-container">
      <div id="loader-curtain" style={{opacity: curtainOpacity, display: curtainDisplay}}>
      <div id="loader-div" style={{opacity: loaderOpacity}}>
        <svg
      id="slotting_loader"
      data-name="Layer 1"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 281.27 120.21"
    >
      <defs>
        <style>{".cls-0{fill:#f0532f}.cls-3{fill:#231f20}"}</style>
      </defs>
      <path
        id="loader_square"
        className="cls-0"
        d="M60.11 0H93.55V33.44H60.11z"
      />
      <path
        id="loader_circle"
        className="cls-0"
        d="M76.76 0C64.81 0 56.51 8.75 56.51 19.41s8.33 19.37 20.21 19.37 20.43-8.65 20.43-19.37S88.82 0 76.76 0z"
      />
      <path
        id="loader_s"
        className="cls-3"
        d="M3.02 68.49c5.06 2.92 8.65 3.73 11.74 3.73 4.08 0 6.26-1.16 6.26-3.09-.04-2.36-2.81-2.64-9.07-4.01C7.66 64.24.7 62.59.7 54.26c0-7.45 5.31-11.95 15.68-11.95 5.7 0 10.58 1.02 15.36 3.3l-2.81 8.47c-3.8-1.55-8.12-2.95-12.23-2.95-3.62 0-4.96 1.48-4.92 3.02 0 1.79 1.97 2.5 6.89 3.16 7.7 1.37 14.31 3.02 14.31 11.07s-7.31 12.76-17.05 12.76c-6.12 0-10.41-.7-15.93-3.66l3.02-9z"
      />
      <g id="loader_back_letters">
        <path
          id="loader_first_t"
          className="cls-3"
          d="M111.63 33.4l7.8-.07v10.12h10.58v9.32h-10.58v12.8c0 4.54 2.25 5.7 5.17 5.7h6.08l-.07 8.89h-7.07c-8.19 0-14.94-2.21-14.94-14.48v-12.9h-5.8v-8.3l5.52-2.11 3.3-8.96z"
        />
        <path
          id="loader_second_t"
          className="cls-3"
          d="M143.13 33.4l7.8-.07v10.12h10.58v9.32h-10.58v12.8c0 4.54 2.25 5.7 5.17 5.7h6.08l-.07 8.89h-7.07c-8.19 0-14.94-2.21-14.94-14.48v-12.9h-5.8v-8.3l5.52-2.11 3.3-8.96z"
        />
        <path
          id="loader_i"
          className="cls-3"
          d="M175.44 27.88c3.94 0 6.5 2.64 6.5 5.77s-2.57 5.73-6.54 5.73-6.47-2.64-6.47-5.73 2.57-5.77 6.5-5.77zm-5.55 15.57h10.93v36.46h-10.93V43.46z"
        />
        <path
          id="loader_n"
          className="cls-3"
          d="M228.7 79.92h-10.93v-19.3c0-6.75-2.95-8.96-7.17-8.96-5.38 0-8.72 4.22-8.72 9.95v18.32h-10.86V43.46h8.75l.67 2.78c3.02-2.14 7.38-3.94 11.74-3.94 11.6 0 16.52 6.86 16.52 18.07v19.55z"
        />
        <path
          id="loader_g"
          className="cls-3"
          d="M276.27 41.03v7.49h-3.09c-1.2 0-2.36.42-3.34.95.95 1.79 1.48 3.76 1.48 5.84 0 7.63-6.54 13.61-17.23 13.61-2.53 0-4.78-.32-6.82-.95-.49.81-.74 1.72-.7 2.46 0 2.04 2.5 2.21 4.22 2.21h6.68c11.6 0 16.28 5.27 16.28 11.11 0 8.86-8.79 13.46-19.93 13.46-10.2 0-19.3-3.55-19.3-11.64 0-2.46 1.83-5.27 4.22-7.49-1.69-1.48-2.57-3.52-2.57-5.73 0-3.06 1.79-6.01 4.18-8.54-2.18-2.32-3.34-5.27-3.34-8.51 0-7.52 6.47-13.85 17.12-13.85 3.8 0 7.07.81 9.7 2.18 1.69-1.3 4.01-2.6 7.03-2.6h5.41zm-30.38 39.41c-.21 0-.39-.04-.6-.04-.84 1.09-1.48 2.32-1.48 3.76 0 3.52 4.32 4.57 9.84 4.57s9.18-1.93 9.18-4.61-2.78-3.73-6.79-3.73l-10.16.04zm8.23-19.3c3.9 0 6.68-2.39 6.68-5.94s-2.78-5.87-6.68-5.87-6.54 2.39-6.54 5.87 2.78 5.94 6.54 5.94z"
        />
      </g>
      <path
        id="loader_l"
        className="cls-3"
        d="M45.35 61.74c0-5.26 2.03-10.06 5.52-13.57V30.38H40.01V66.8c0 10.09 2.57 13.15 13.57 13.15h2.29v-1.06c-6.47-3.24-10.51-9.7-10.51-17.15z"
      />
      <rect
        id="loader_underline"
        y={85.86}
        width={56.33}
        height={10.18}
        rx={3.6}
        ry={3.6}
        fill="#ffcc04"
      />
      <path
        id="loader_hexagon"
        className="cls-0"
        d="M86.99 39.05L66.67 39.05 56.51 21.45 66.67 3.85 86.99 3.85 97.16 21.45 86.99 39.05z"
      />
    </svg>
      </div>
      </div>
      <div id="main-contents">
        <h1>Wow, there are {staticComboCount} possible assignments!</h1>
        <SaveTimeslotBox comboStatus={comboStatus} />  
        <div id="all-timeslots">{sems}</div>
        <div id="button-legend">
          <div id="button-legend-title">Legend:</div>
          <div>
            <button type="button" className="off">Selectable</button>
            <button type="button" className="only">Must select for timeslot</button>
            <button type="button" className="on">Selected</button>
            <button type="button" className="autofill-selected">Fixed autofill selection</button>
          </div>
        </div>
        {/*<p>Remaining combos: {comboCount}</p>*/}
        <div id="autofill-buttons-container">
          <AutofillRest
            onAutofillClick={() => handleAutofill(onOff, pronounFilters)}
            students={onOff}
            pronounFilters={pronounFilters}
            clicked={autofillPressed}
            errors={autofillErrors}
          />
          <ReRoll
            onReRollClick={() =>
              handleAutofill(selectionHistory, pronounFilters)
            }
            autofill={autofillPressed}
          />
          <GroupByPronounsToggle
            onGroupByToggleClick={() => handleGroupByPronouns()}
            buttonState={groupByPronouns}
          />
        </div>
        <Reset
          onResetClick={() => handleReset()}
          autofill={null}
          students={onOff}
        />
        <DownloadCSV students={onOff} onCSVClick={() => handleCSV(selectedCombo)} />
        <div
          className="pronoun-container"
          style={{ display: pronounContainerDisplay }}
        >
          {/*
          <h2>Autofill Options</h2>
          <li>
            assign some students to specific timeslots (above) and autofill the
            rest
          </li>
          <li>group students by the pronouns they use</li>
          <li>
            click <b>re-roll</b> to see a different assignment that meets the
            selected parameters
          </li>
          */}
          {pronounButtons}
        </div>
        {/*
        <Reset
          onResetClick={() => handleReset()}
          autofill={autofillPressed}
          students={onOff}
        />
        */}
        <div className={"error-box"} style={{ visibility: errorBoxDisplay }}>
          {" "}
          {errorMessages}{" "}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <SeminarRosterPicker
      seminars={SEMINARS}
      students={STUDENTS}
      errors={ERRORS}
      comboStatus={COMBOSTATUS}
    />
  );
}
