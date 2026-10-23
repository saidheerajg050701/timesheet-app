// Convenience only: enable the inputs that apply to each row's category, show each row's
// hours as you type, and remove rows. The server checks every rule again when saving
// (D-35–D-43) and recalculates hours from the times itself.
(function () {
  var TIMED = ["PROJECT", "MEETING", "TRAINING", "OTHER", "BREAK"];
  var LEAVE = ["PTO", "SICK", "HOLIDAY"];

  function minutesOf(value) {
    var match = /^(\d{1,2}):(\d{2})/.exec(value || "");
    return match ? Number(match[1]) * 60 + Number(match[2]) : null;
  }

  function updateHours(row) {
    var select = row.querySelector("[data-role=category]");
    var hours = row.querySelector("[data-role=hours]");
    if (!select || !hours || TIMED.indexOf(select.value) < 0) return;
    var times = row.querySelectorAll("[data-role=time]");
    var start = minutesOf(times[0] && times[0].value);
    var end = minutesOf(times[1] && times[1].value);
    hours.value = start !== null && end !== null && end > start ? ((end - start) / 60).toFixed(2) : "";
  }

  function sync(row) {
    var select = row.querySelector("[data-role=category]");
    if (!select) return;
    var category = select.value;
    var timed = TIMED.indexOf(category) >= 0;
    row.querySelectorAll("[data-role=project]").forEach(function (el) {
      el.disabled = category !== "PROJECT";
    });
    row.querySelectorAll("[data-role=time]").forEach(function (el) {
      el.disabled = LEAVE.indexOf(category) >= 0;
    });
    row.querySelectorAll("[data-role=hours]").forEach(function (el) {
      el.readOnly = timed; // shown, calculated from the times
      el.tabIndex = timed ? -1 : 0;
    });
    updateHours(row);
  }

  function syncAll() {
    document.querySelectorAll("#entry-rows > tr").forEach(sync);
  }

  document.addEventListener("change", function (event) {
    if (event.target.matches("[data-role=category]")) sync(event.target.closest("tr"));
  });
  document.addEventListener("input", function (event) {
    if (event.target.matches("[data-role=time]")) updateHours(event.target.closest("tr"));
  });
  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-action=remove-row]");
    if (!button) return;
    button.closest("tr").remove();
    document.body.dispatchEvent(new Event("rows-changed"));
  });
  document.addEventListener("htmx:afterSwap", syncAll);
  syncAll();
})();
