// The weekly grid (Change 2, D-106–D-110; Change 5, D-127; Change 7, D-129; Change 10, D-152;
// Change 10b, D-157). Convenience only:
// open a cell's dialog, add and remove time slots, add rows (or point at the row that is
// already there), change or delete a whole row (the server re-draws the grid as typed), keep
// the cell / row / day totals and the multi-slot hint live, and warn before leaving with
// unsaved changes. Every slot is posted as the usual entry-N-* fields and the server
// checks every rule again when saving; it also recomputes the day summary below the grid.
(function () {
  var dirty = false;
  var opener = null;

  function minutesOf(value) {
    var match = /^(\d{1,2}):(\d{2})/.exec(value || "");
    return match ? Number(match[1]) * 60 + Number(match[2]) : null;
  }

  function leaveMinutes(text) {
    text = (text || "").trim();
    if (!text) return 0;
    if (text.indexOf(":") >= 0) {
      var parts = text.split(":");
      return (Number(parts[0]) || 0) * 60 + (Number(parts[1]) || 0);
    }
    var hours = Number(text);
    return isFinite(hours) && hours > 0 ? Math.round(hours * 60) : 0;
  }

  function slotMinutes(slot) {
    var hours = slot.querySelector("[data-role=hours]");
    if (hours) return leaveMinutes(hours.value);
    var start = minutesOf(slot.querySelector("[data-role=start]").value);
    var end = minutesOf(slot.querySelector("[data-role=end]").value);
    return start !== null && end !== null && end > start ? end - start : 0;
  }

  function text(minutes) {
    return (minutes / 60).toFixed(2);
  }

  function slotTime(slot) {
    // "08:00–13:00" (leave: "4.00 h"), as Cell.slot_times writes it on the server.
    var hours = slot.querySelector("[data-role=hours]");
    if (hours) return text(leaveMinutes(hours.value)) + " h";
    return slot.querySelector("[data-role=start]").value + "–" + slot.querySelector("[data-role=end]").value;
  }

  function showHint(cell, filled, minutes) {
    // "8.00 · 2 slots" with the slot times as tooltip and in the accessible name (D-127).
    var button = cell.querySelector(".cell-button");
    var count = filled.length;
    var times = filled.map(slotTime).join(", ");
    cell.querySelector("[data-role=cell-hours]").textContent = count ? text(minutes) : "";
    cell.querySelector("[data-role=cell-meta]").textContent = count > 1 ? " · " + count + " slots" : "";
    if (count > 1) button.title = times;
    else button.removeAttribute("title");
    button.setAttribute("aria-label", button.dataset.label + ": " + (count ? text(minutes) : "0.00")
      + " hours, " + (count ? count + " slot" + (count === 1 ? "" : "s") : "empty")
      + (count > 1 ? " (" + times + ")" : "")
      + (button.getAttribute("aria-invalid") === "true" ? ", has errors" : ""));
  }

  // --- totals -------------------------------------------------------------------------
  function refresh(grid) {
    var dayTotals = [0, 0, 0, 0, 0, 0, 0];
    grid.querySelectorAll("tbody tr.grid-row").forEach(function (row) {
      var rowTotal = 0;
      row.querySelectorAll("td.grid-cell").forEach(function (cell, day) {
        var slots = cell.querySelectorAll("dialog [data-role=slots] .grid-slot");
        if (!cell.querySelector("[data-role=slots]")) return; // read-only grid: server totals
        var minutes = 0;
        slots.forEach(function (slot) {
          var value = slotMinutes(slot);
          minutes += value;
          var shown = slot.querySelector("[data-role=slot-hours]");
          if (shown) shown.textContent = value ? text(value) + " h" : "";
        });
        // The empty slot offered when the dialog opens isn't a slot yet (it is never posted).
        showHint(cell, Array.from(slots).filter(function (slot) { return !isEmpty(slot); }), minutes);
        rowTotal += minutes;
        if (row.dataset.kind === "work") dayTotals[day] += minutes;
      });
      if (row.querySelector("[data-role=slots]")) {
        row.querySelector("[data-role=row-total]").textContent = text(rowTotal);
      }
    });
    if (!grid.querySelector("[data-role=slots]")) return;
    grid.querySelectorAll("[data-role=day-total]").forEach(function (cell, day) {
      cell.textContent = text(dayTotals[day]);
    });
    grid.querySelector("[data-role=week-total]").textContent = text(
      dayTotals.reduce(function (a, b) { return a + b; }, 0)
    );
  }

  function changed(grid) {
    dirty = true;
    refresh(grid);
    document.body.dispatchEvent(new Event("rows-changed")); // the server's day summary
  }

  // --- slots --------------------------------------------------------------------------
  function nextIndex() {
    var used = Array.from(document.querySelectorAll(".grid-slot[data-index]"), function (s) {
      return Number(s.dataset.index);
    });
    var table = document.querySelector(".week-grid[data-next-index]");
    var floor = table ? Number(table.dataset.nextIndex) : 0;
    return Math.max.apply(null, [floor].concat(used.map(function (i) { return i + 1; })));
  }

  function addSlot(dialog) {
    var template = dialog.querySelector("template[data-role=slot-template]");
    var holder = dialog.querySelector("[data-role=slots]");
    var index = String(nextIndex());
    holder.insertAdjacentHTML("beforeend", template.innerHTML.split("__INDEX__").join(index));
    var slot = holder.lastElementChild;
    slot.querySelector("input:not([type=hidden])").focus();
    return slot;
  }

  function isEmpty(slot) {
    return Array.from(slot.querySelectorAll("input:not([type=hidden])")).every(function (input) {
      return !input.value.trim();
    });
  }

  // --- dialogs ------------------------------------------------------------------------
  function open(dialog, from) {
    opener = from || null;
    if (!dialog.open) dialog.showModal();
    var slots = dialog.querySelector("[data-role=slots]");
    var row = dialog.closest("tr.grid-row");
    // An empty cell starts with one slot; a work or Break cell that already has slots lists
    // them and offers one more, empty and focused, ready to fill (D-127). Leave keeps one.
    if (slots && (!slots.children.length || row.dataset.kind !== "leave")) {
      addSlot(dialog); // focuses the new slot's first field
      return;
    }
    var first = dialog.querySelector("input:not([type=hidden]), select")
      || dialog.querySelector("[data-grid-action=close]");
    if (first) first.focus();
  }

  document.addEventListener("close", function (event) {
    var dialog = event.target;
    if (!dialog.matches || !dialog.matches("dialog.cell-dialog")) return;
    dialog.querySelectorAll(".grid-slot").forEach(function (slot) {
      if (isEmpty(slot)) slot.remove(); // nothing typed: not posted at all (D-107)
    });
    var grid = dialog.closest("[data-week-grid]");
    if (grid) refresh(grid);
    if (opener && document.contains(opener)) opener.focus();
    opener = null;
  }, true);

  // --- add a row ----------------------------------------------------------------------
  function notice(grid, message) {
    var area = grid.querySelector("[data-role=grid-notice]");
    area.textContent = "";
    if (!message) return;
    var p = document.createElement("p");
    p.className = "grid-notice";
    p.textContent = message;
    area.appendChild(p);
  }

  function pointAt(grid, row) {
    // "+ Add row" for a row that is already there: no error, show that row instead (D-127).
    var label = row.dataset.rowLabel;
    notice(grid, row.dataset.kind === "leave"
      ? label + " already has a row. Click a day to enter or change its hours."
      : label + " already has a row. Click a day to add another time slot (for example 2:00 PM – 5:00 PM).");
    row.classList.remove("is-highlighted");
    void row.offsetWidth; // restart the highlight when it is pointed at twice in a row
    row.classList.add("is-highlighted");
    clearTimeout(row.highlightTimer);
    row.highlightTimer = setTimeout(function () { row.classList.remove("is-highlighted"); }, 3000);
    var first = row.querySelector(".cell-button");
    first.focus({ preventScroll: true });
    var still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    row.scrollIntoView({ block: "center", inline: "nearest", behavior: still ? "auto" : "smooth" });
  }

  // --- project and task choices (Change 10, D-152) ------------------------------------
  function chosen(dialog) {
    // The category, project and task picked in a dialog, and the grid row key they make.
    var category = dialog.querySelector("[data-role=new-category]").value;
    var isProject = category === "PROJECT";
    var project = isProject ? dialog.querySelector("[data-role=new-project]").value : "";
    var task = isProject ? dialog.querySelector("[data-role=new-task]").value : "";
    var key = category + ":" + project + (task ? ":" + task : "");
    var problem = !category ? "Choose a category."
      : isProject && !project ? "Choose a project."
      : isProject && !task ? "Choose a task." : "";
    return { category: category, project: project, task: task, key: key, problem: problem };
  }

  function fillTasks(dialog) {
    // Only the chosen project's allowed, active tasks (the server checks them again).
    var select = dialog.querySelector("[data-role=new-task]");
    var category = dialog.querySelector("[data-role=new-category]").value;
    var project = dialog.querySelector("[data-role=new-project]").value;
    var source = document.getElementById("task-choices");
    var choices = source ? JSON.parse(source.textContent) : {};
    var keep = select.value || select.dataset.current || "";
    select.length = 1; // keep "Choose…"
    (choices[project] || []).forEach(function (choice) {
      select.add(new Option(choice[1], choice[0], false, choice[0] === keep));
    });
    dialog.querySelector("[data-role=new-task-field]").hidden = category !== "PROJECT" || !project;
  }

  function addRow(dialog) {
    var pick = chosen(dialog);
    var category = pick.category, project = pick.project, task = pick.task;
    var error = dialog.querySelector("[data-role=add-row-error]");
    var grid = dialog.closest("[data-week-grid]");
    error.textContent = pick.problem;
    error.hidden = !pick.problem;
    if (pick.problem) return;
    var existing = grid.querySelector('tr[data-row-key="' + pick.key + '"]');
    if (existing) {
      opener = null; // focus goes to the existing row, not back to "+ Add row"
      dialog.close();
      pointAt(grid, existing);
      return;
    }
    notice(grid, "");
    var body = grid.querySelector("[data-role=grid-rows]");
    htmx.ajax("GET", dialog.dataset.rowUrl, {
      target: body, swap: "beforeend", values: { category: category, project: project, task: task },
    }).then(function () {
      var empty = body.querySelector("tr.grid-empty");
      if (empty) empty.remove();
      dialog.close();
      var row = body.querySelector('tr[data-row-key="' + pick.key + '"]');
      if (row) row.querySelector(".cell-button").focus();
      changed(grid);
    });
  }

  // --- row actions: change project / category, delete (D-129, D-130) --------------------
  function filledSlots(row) {
    return Array.from(row.querySelectorAll("[data-role=slots] .grid-slot")).filter(function (slot) {
      return !isEmpty(slot);
    });
  }

  function slotsText(row, count) {
    if (row.dataset.kind === "leave") return count + (count === 1 ? " leave entry" : " leave entries");
    return count + (count === 1 ? " time slot" : " time slots");
  }

  function changeNotes(dialog) {
    // Say before saving what the change does: merge into an existing row, or Break pay.
    var row = dialog.closest("tr.grid-row");
    var pick = chosen(dialog);
    var category = pick.category, key = pick.key;
    var target = !pick.problem && key !== row.dataset.rowKey
      && row.closest("[data-week-grid]").querySelector('tr[data-row-key="' + key + '"]');
    var merge = dialog.querySelector("[data-role=merge-note]");
    merge.textContent = target ? target.dataset.rowLabel + " already has a row this week: the "
      + slotsText(row, filledSlots(row).length) + " of this row will be added to it." : "";
    merge.hidden = !target;
    var fromBreak = row.dataset.kind === "break";
    var note = dialog.querySelector("[data-role=break-note]");
    note.textContent = category === "BREAK" && !fromBreak
      ? "Break is unpaid: these hours will no longer count as worked time."
      : fromBreak && category !== "BREAK" ? "These hours will count as worked time." : "";
    note.hidden = !note.textContent;
  }

  function rowAction(row, values, focusKey) {
    // Post the week as typed; the server returns the whole grid with the row changed.
    var grid = row.closest("[data-week-grid]");
    var tableId = grid.querySelector("table.week-grid").id;
    values["row-key"] = row.dataset.rowKey;
    return htmx.ajax("POST", grid.dataset.rowsUrl, {
      source: grid, target: grid, swap: "outerHTML", values: values,
    }).then(function () {
      if (document.contains(grid)) return; // refused: the message is in the open dialog
      opener = null;
      var fresh = document.getElementById(tableId).closest("[data-week-grid]");
      changed(fresh);
      var area = fresh.querySelector("[data-role=grid-notice]");
      notice(fresh, area.dataset.notice);
      var focus = focusKey && fresh.querySelector('tr[data-row-key="' + focusKey + '"] .row-actions-toggle');
      (focus || fresh.querySelector("[data-grid-action=add-row]")).focus();
    }).catch(function () {}); // a network error leaves the grid as it was
  }

  document.body.addEventListener("htmx:responseError", function (event) {
    var error = document.querySelector("dialog[open] [data-role=row-error]");
    if (!error) return;
    var status = event.detail.xhr.status;
    error.textContent = status === 400 ? event.detail.xhr.responseText
      : "This week can't be changed any more. Reload the page to see it.";
    error.hidden = false;
  });

  // --- project search box (Change 10b, D-157): static/js/project_search.js ---------------
  // It announces "project-chosen" (also with an empty value when typing clears a choice).
  document.addEventListener("project-chosen", function (event) {
    var dialog = event.target.closest("dialog");
    if (!dialog || !dialog.closest("[data-week-grid]")) return;
    fillTasks(dialog);
    if (dialog.matches("[data-role=change-row-dialog]")) changeNotes(dialog);
  });

  function resetProject(dialog) {
    // ⋮ Change row opens on the row's own project again, whatever was typed last time.
    window.ProjectSearch.reset(dialog.querySelector("[data-role=new-project-field]"));
  }

  // --- events -------------------------------------------------------------------------
  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-grid-action]");
    if (!button) return;
    var action = button.dataset.gridAction;
    var dialog = button.closest("dialog");
    if (action === "open") {
      event.preventDefault();
      open(document.getElementById(button.getAttribute("aria-controls")), button);
    } else if (action === "close") {
      dialog.close();
    } else if (action === "add-slot") {
      addSlot(dialog);
      changed(dialog.closest("[data-week-grid]"));
    } else if (action === "remove-slot") {
      var grid = dialog.closest("[data-week-grid]");
      button.closest(".grid-slot").remove();
      var next = dialog.querySelector("[data-grid-action=add-slot]");
      if (next) next.focus();
      changed(grid);
    } else if (action === "add-row") {
      var adder = button.closest("[data-week-grid]").querySelector("#add-row-dialog");
      adder.querySelector("[data-role=add-row-error]").hidden = true;
      fillTasks(adder);
      open(adder, button);
    } else if (action === "insert-row") {
      addRow(dialog);
    } else if (action === "change-row" || action === "delete-row") {
      var row = button.closest("tr.grid-row");
      var toggle = row.querySelector(".row-actions-toggle");
      var count = filledSlots(row).length;
      if (action === "delete-row" && !count) {
        rowAction(row, { "row-action": "delete" }); // nothing typed in it: no question to ask
        return;
      }
      var panel = row.querySelector("[data-role=" + action + "-dialog]");
      panel.querySelector("[data-role=row-error]").hidden = true;
      if (action === "change-row") {
        resetProject(panel);
        fillTasks(panel);
        changeNotes(panel);
      } else {
        var minutes = filledSlots(row).reduce(function (sum, slot) { return sum + slotMinutes(slot); }, 0);
        panel.querySelector("[data-role=delete-text]").textContent = "Delete "
          + panel.dataset.rowName + "? This removes "
          + slotsText(row, count) + " (" + text(minutes) + " h) from this week.";
      }
      open(panel, toggle);
    } else if (action === "confirm-change") {
      var changing = dialog.closest("tr.grid-row");
      var pick = chosen(dialog);
      var problem = dialog.querySelector("[data-role=row-error]");
      problem.textContent = pick.problem;
      problem.hidden = !problem.textContent;
      if (!problem.hidden) return;
      if (pick.key === changing.dataset.rowKey) {
        dialog.close(); // nothing to change
        return;
      }
      rowAction(changing, {
        "row-action": "change", "new-category": pick.category, "new-project": pick.project,
        "new-task": pick.task,
      }, pick.key);
    } else if (action === "confirm-delete") {
      rowAction(dialog.closest("tr.grid-row"), { "row-action": "delete" });
    }
  });

  document.addEventListener("change", function (event) {
    if (event.target.matches("[data-role=new-category]")) {
      var field = event.target.closest("dialog").querySelector("[data-role=new-project-field]");
      field.hidden = event.target.value !== "PROJECT";
    }
    if (event.target.matches("[data-role=new-category]")) {
      fillTasks(event.target.closest("dialog"));
    }
    var changing = event.target.closest("[data-role=change-row-dialog]");
    if (changing) changeNotes(changing);
  });

  document.addEventListener("input", function (event) {
    var grid = event.target.closest("[data-week-grid]");
    if (grid && event.target.closest(".grid-slot")) changed(grid);
  });

  document.addEventListener("keydown", function (event) {
    // Enter in a slot field moves on instead of submitting the whole week by accident.
    if (event.key === "Enter" && event.target.closest(".grid-slot")) {
      event.preventDefault();
      event.target.closest("dialog").querySelector("[data-grid-action=close]").focus();
    }
  });

  document.addEventListener("submit", function (event) {
    if (!event.target.querySelector("[data-week-grid]")) return;
    event.target.querySelectorAll(".grid-slot").forEach(function (slot) {
      if (isEmpty(slot)) slot.remove();
    });
    dirty = false; // leaving by saving is fine
  });

  window.addEventListener("beforeunload", function (event) {
    if (!dirty) return;
    event.preventDefault();
    event.returnValue = ""; // the browser shows its own "leave this page?" question
  });

  document.querySelectorAll("[data-week-grid]").forEach(refresh);
})();
