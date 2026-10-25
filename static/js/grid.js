// The weekly grid (Change 2, D-106–D-110; Change 5, D-127). Convenience only: open a cell's
// dialog, add and remove time slots, add rows (or point at the row that is already there),
// keep the cell / row / day totals and the multi-slot hint live, and warn before leaving
// with unsaved changes. Every slot is posted as the usual entry-N-* fields and the server
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
    var first = dialog.querySelector("input:not([type=hidden]), select, [data-grid-action=close]");
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

  function addRow(dialog) {
    var category = dialog.querySelector("[data-role=new-category]").value;
    var project = category === "PROJECT" ? dialog.querySelector("[data-role=new-project]").value : "";
    var error = dialog.querySelector("[data-role=add-row-error]");
    var grid = dialog.closest("[data-week-grid]");
    var problem = !category ? "Choose a category."
      : category === "PROJECT" && !project ? "Choose a project." : "";
    error.textContent = problem;
    error.hidden = !problem;
    if (problem) return;
    var existing = grid.querySelector('tr[data-row-key="' + category + ":" + project + '"]');
    if (existing) {
      opener = null; // focus goes to the existing row, not back to "+ Add row"
      dialog.close();
      pointAt(grid, existing);
      return;
    }
    notice(grid, "");
    var body = grid.querySelector("[data-role=grid-rows]");
    htmx.ajax("GET", dialog.dataset.rowUrl, {
      target: body, swap: "beforeend", values: { category: category, project: project },
    }).then(function () {
      var empty = body.querySelector("tr.grid-empty");
      if (empty) empty.remove();
      dialog.close();
      var row = body.querySelector('tr[data-row-key="' + category + ":" + project + '"]');
      if (row) row.querySelector(".cell-button").focus();
      changed(grid);
    });
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
      open(adder, button);
    } else if (action === "insert-row") {
      addRow(dialog);
    }
  });

  document.addEventListener("change", function (event) {
    if (event.target.matches("[data-role=new-category]")) {
      var field = event.target.closest("dialog").querySelector("[data-role=new-project-field]");
      field.hidden = event.target.value !== "PROJECT";
    }
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
