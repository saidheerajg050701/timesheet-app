// Convenience only: enable the inputs that apply to each row's category, and remove rows.
// The server checks every rule again when saving (D-35–D-43).
(function () {
  var TIMED = ["PROJECT", "MEETING", "TRAINING", "OTHER", "BREAK"];
  var LEAVE = ["PTO", "SICK", "HOLIDAY"];

  function sync(row) {
    var select = row.querySelector("[data-role=category]");
    if (!select) return;
    var category = select.value;
    row.querySelectorAll("[data-role=project]").forEach(function (el) {
      el.disabled = category !== "PROJECT";
    });
    row.querySelectorAll("[data-role=time]").forEach(function (el) {
      el.disabled = LEAVE.indexOf(category) >= 0;
    });
    row.querySelectorAll("[data-role=hours]").forEach(function (el) {
      el.disabled = TIMED.indexOf(category) >= 0;
    });
  }

  function syncAll() {
    document.querySelectorAll("#entry-rows > tr").forEach(sync);
  }

  document.addEventListener("change", function (event) {
    if (event.target.matches("[data-role=category]")) sync(event.target.closest("tr"));
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
