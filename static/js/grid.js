// The weekly grid (Change 2, D-106–D-110). Convenience only: open a cell's dialog, add and
// remove time slots, add rows, keep the cell / row / day totals live, and warn before leaving
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
        cell.querySelector("[data-role=cell-hours]").textContent = slots.length ? text(minutes) : "";
        var count = cell.querySelector(".cell-count");
        if (count) count.textContent = slots.length > 1 ? slots.length : "";
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
    if (slots && !slots.children.length) addSlot(dialog); // an empty cell starts with one slot
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
  function addRow(dialog) {
    var category = dialog.querySelector("[data-role=new-category]").value;
    var project = category === "PROJECT" ? dialog.querySelector("[data-role=new-project]").value : "";
    var error = dialog.querySelector("[data-role=add-row-error]");
    var grid = dialog.closest("[data-week-grid]");
    var problem = !category ? "Choose a category."
      : category === "PROJECT" && !project ? "Choose a project."
      : grid.querySelector('tr[data-row-key="' + category + ":" + project + '"]')
        ? "That row is already in the grid; click one of its days instead." : "";
    error.textContent = problem;
    error.hidden = !problem;
    if (problem) return;
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
