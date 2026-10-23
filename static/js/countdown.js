// Live countdown for elements with data-deadline (ISO 8601). The server renders the first
// value and enforces the deadline; this only keeps the text fresh.
(function () {
  function format(ms) {
    var minutes = Math.floor(ms / 60000);
    if (minutes <= 0) return "deadline passed — reload the page";
    var days = Math.floor(minutes / 1440);
    var hours = Math.floor((minutes % 1440) / 60);
    var parts = days ? [days + " d"] : [];
    if (days || hours) parts.push(hours + " h");
    parts.push((minutes % 60) + " min");
    return parts.join(" ");
  }
  function tick() {
    document.querySelectorAll("[data-deadline]").forEach(function (el) {
      el.textContent = format(new Date(el.dataset.deadline) - new Date());
    });
  }
  tick();
  setInterval(tick, 30000);
})();
