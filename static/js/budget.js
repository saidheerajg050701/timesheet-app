// Reports → Project budget (Change 12, D-170): cost to date against budget per project.
// Data only from the json_script block #budget-chart-data; the table below the chart has the
// same numbers, so nothing depends on this file.
(function () {
  var source = document.getElementById("budget-chart-data");
  var canvas = document.getElementById("budget-chart");
  if (!source || !canvas || typeof Chart === "undefined") return;
  var data = JSON.parse(source.textContent);
  // Colours come from the theme tokens in css/theme.css (D-103), as on the dashboard.
  var tokens = getComputedStyle(document.documentElement);
  function token(name, fallback) { return tokens.getPropertyValue(name).trim() || fallback; }
  var SERIES = token("--ts-chart-series", "#2563eb");
  var MUTED = token("--ts-chart-muted", "#475569");
  var GRID = token("--ts-chart-grid", "rgba(71, 85, 105, 0.14)");
  Chart.defaults.color = MUTED;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  function usd(value) {
    return "$" + Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  new Chart(canvas, {
    type: "bar",
    data: {
      labels: data.map(function (p) { return p.label; }),
      datasets: [
        { label: "Total cost to date", data: data.map(function (p) { return p.cost; }),
          backgroundColor: SERIES, borderRadius: 4, borderSkipped: "start", maxBarThickness: 14 },
        { label: "Budget", data: data.map(function (p) { return p.budget; }),
          backgroundColor: "rgba(71, 85, 105, 0.28)", borderRadius: 4, borderSkipped: "start", maxBarThickness: 14 },
      ],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      scales: {
        x: { grid: { color: GRID }, border: { display: false }, beginAtZero: true,
          ticks: { callback: function (v) { return usd(v).replace(".00", ""); } } },
        y: { grid: { display: false }, border: { display: false } },
      },
      plugins: {
        legend: { position: "bottom" },
        tooltip: { callbacks: { label: function (c) {
          return c.dataset.label + ": " + (c.parsed.x === null ? "No budget set" : usd(c.parsed.x));
        } } },
      },
    },
  });
})();
