// Team charts (FR-6). Data only from the json_script block #team-data (D-80); every chart
// has a table with the same numbers. Same style and validated colour as the dashboard.
(function () {
  var source = document.getElementById("team-data");
  if (!source || typeof Chart === "undefined") return;
  var data = JSON.parse(source.textContent);
  // Colours come from the theme tokens in css/theme.css (D-103); the fallbacks are the same values.
  var tokens = getComputedStyle(document.documentElement);
  function token(name, fallback) { return tokens.getPropertyValue(name).trim() || fallback; }
  var SERIES = token("--ts-chart-series", "#2563eb"); // validated for the light surface
  var MUTED = token("--ts-chart-muted", "#475569"); // reference line and axis text
  var GRID = token("--ts-chart-grid", "rgba(71, 85, 105, 0.14)");
  Chart.defaults.color = MUTED;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  var axis = { grid: { color: GRID }, border: { display: false }, beginAtZero: true };
  var noGrid = { grid: { display: false }, border: { display: false } };
  function label(c) {
    var value = c.parsed[c.chart.options.indexAxis === "y" ? "x" : "y"];
    return c.dataset.label + ": " + Number(value).toFixed(2) + " h";
  }

  var hours = document.getElementById("team-hours-chart");
  if (hours) {
    new Chart(hours, {
      data: {
        labels: data.weeks.map(function (w) { return w.label; }),
        datasets: [
          { type: "bar", label: "Hours worked", data: data.weeks.map(function (w) { return w.worked; }),
            backgroundColor: SERIES, borderRadius: 4, borderSkipped: "bottom", maxBarThickness: 28 },
          { type: "line", label: "Expected", data: data.weeks.map(function (w) { return w.expected; }),
            borderColor: MUTED, borderDash: [6, 4], borderWidth: 2, pointRadius: 0, stepped: "middle" },
        ],
      },
      options: {
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: { y: axis, x: noGrid },
        plugins: { legend: { position: "bottom" }, tooltip: { callbacks: { label: label } } },
      },
    });
  }

  var projects = document.getElementById("team-projects-chart");
  if (projects) {
    new Chart(projects, {
      type: "bar",
      data: {
        labels: data.projects.map(function (p) { return p.label; }),
        datasets: [{ label: "Hours", data: data.projects.map(function (p) { return p.hours; }),
          backgroundColor: SERIES, borderRadius: 4, borderSkipped: "start", maxBarThickness: 22 }],
      },
      options: {
        indexAxis: "y",
        maintainAspectRatio: false,
        scales: { x: axis, y: noGrid },
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: label } } },
      },
    });
  }
})();
