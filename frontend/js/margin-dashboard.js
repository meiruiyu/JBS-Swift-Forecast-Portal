const currency = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
let marginChart = null;
let currentRows = [];

async function requestJson(url, options = {}) {
  const response = await fetch(url, { credentials: "include", ...options });
  if (response.status === 401) { window.location.href = "/login"; throw new Error("Please sign in again."); }
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Unable to load forecast data.");
  return payload;
}

async function logout(event) {
  event.preventDefault();
  await fetch("/api/logout", { method: "POST", credentials: "include" });
  window.location.href = "/login";
}

function buildQuery() {
  return new URLSearchParams({
    start_date: document.getElementById("start-date").value,
    end_date: document.getElementById("end-date").value,
    channel: document.getElementById("channel-filter").value
  });
}

function renderChart(rows) {
  const canvas = document.getElementById("margin-chart");
  const empty = document.getElementById("margin-chart-empty-state");
  marginChart?.destroy();
  if (!rows.length) { canvas.hidden = true; empty.hidden = false; return; }
  canvas.hidden = false; empty.hidden = true;
  const rawLabels = [...new Set(rows.map(row => row.date))];
  const labels = rawLabels.map(date => new Date(`${date}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" }));
  const colors = { Stores: "#174f86", "E-commerce": "#2f9e76", Vans: "#7d5bb6" };
  const datasets = [...new Set(rows.map(row => row.channel))].map(channel => ({
    label: channel,
    data: rawLabels.map(date => rows.find(row => row.date === date && row.channel === channel)?.predictedMargin ?? null),
    borderColor: colors[channel] || "#667085",
    backgroundColor: colors[channel] || "#667085",
    yAxisID: "yMargin",
    borderWidth: channel === "Vans" ? 4 : 3,
    pointRadius: channel === "Vans" ? 4 : 3,
    pointHoverRadius: 6,
    tension: 0.25,
    spanGaps: true
  }));
  marginChart = new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom", labels: { usePointStyle: true, padding: 22 } },
        tooltip: { callbacks: { label: context => `${context.dataset.label}: ${currency.format(context.parsed.y)}` } }
      },
      scales: {
        yMargin: {
          type: "linear",
          position: "left",
          title: { display: true, text: "Forecast Margin" },
          ticks: { callback: value => currency.format(value) },
          grid: { color: "#e9eef5" }
        }
      }
    }
  });
}

function renderChannels(channels) {
  const grid = document.getElementById("channel-grid");
  grid.innerHTML = channels.map(item => `<article class="channel-card"><div class="channel-card-header"><div><h3>${item.channel}</h3><p>${item.recordCount} forecast records</p></div><span class="channel-icon ${item.channel.toLowerCase().replace("-", "")}">M</span></div><div class="channel-metrics"><div><span>Total Margin</span><strong>${currency.format(item.totalMargin)}</strong></div><div><span>Average Margin</span><strong>${currency.format(item.averageMargin)}</strong></div></div></article>`).join("");
}

function renderTable(rows) {
  const readable = value => String(value).replaceAll("_", " ").replace(/\b\w/g, letter => letter.toUpperCase());
  const dateLabel = value => new Date(`${value}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  document.getElementById("forecast-results-body").innerHTML = rows.length ? rows.map(row => `
    <tr>
      <td class="result-date">${dateLabel(row.date)}</td>
      <td><span class="channel-pill channel-${row.channel.toLowerCase()}">${row.channel}</span></td>
      <td class="result-margin">${currency.format(row.predictedMargin)}</td>
      <td class="result-horizon">Day ${row.forecastHorizonDay}</td>
      <td>
        <div class="result-details">
          <span><strong>Mode</strong>${readable(row.forecastMode)}</span>
          <span><strong>Model</strong>${readable(row.modelName)}</span>
          <span><strong>Feature</strong>${readable(row.featureSet)}</span>
          <span><strong>Weather</strong>${readable(row.weatherFeatureSource)}</span>
          <span><strong>Origin</strong>${row.forecastOrigin}</span>
        </div>
      </td>
      <td><span class="availability-badge ${row.actualMarginAvailable ? "available" : "forecast-only"}">${row.actualMarginAvailable ? "Available" : "Forecast only"}</span></td>
    </tr>`).join("") : `<tr><td colspan="6">No records match the selected filters.</td></tr>`;
}

async function loadDashboard() {
  const error = document.getElementById("dashboard-filter-error");
  const button = document.getElementById("refresh-dashboard-button");
  error.textContent = ""; button.disabled = true; button.textContent = "Loading…";
  try {
    const data = await requestJson(`/api/margin-dashboard?${buildQuery()}`);
    currentRows = data.rows;
    document.getElementById("total-margin-value").textContent = currency.format(data.summary.totalMargin);
    document.getElementById("average-margin-value").textContent = currency.format(data.summary.averageMargin);
    document.getElementById("peak-margin-value").textContent = currency.format(data.summary.peakMargin);
    document.getElementById("record-count-note").textContent = `${data.summary.recordCount} forecast records`;
    document.getElementById("total-margin-note").textContent = `${data.filters.startDate} to ${data.filters.endDate}`;
    document.getElementById("last-updated-value").textContent = new Date(data.lastUpdated).toLocaleString();
    renderChart(data.rows); renderChannels(data.channels); renderTable(data.rows);
  } catch (problem) { error.textContent = problem.message; document.getElementById("system-status-value").textContent = "Unavailable"; }
  finally { button.disabled = false; button.textContent = "Refresh Dashboard"; }
}

function downloadCsv() {
  const headers = ["date","channel","predicted_margin","forecast_origin","forecast_horizon_day","forecast_mode","model_name","feature_set","weather_feature_source","actual_margin_available_flag"];
  const values = currentRows.map(row => [row.date,row.channel,row.predictedMargin,row.forecastOrigin,row.forecastHorizonDay,row.forecastMode,row.modelName,row.featureSet,row.weatherFeatureSource,row.actualMarginAvailable ? 1 : 0]);
  const csv = [headers, ...values].map(line => line.map(value => `"${String(value).replaceAll('"','""')}"`).join(",")).join("\n");
  const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" })); link.download = "filtered_recursive_margin_forecast.csv"; link.click(); URL.revokeObjectURL(link.href);
}

async function initializeDashboard() {
  const dataRange = await requestJson("/api/data-range");
  const channelSelect = document.getElementById("channel-filter");
  channelSelect.innerHTML = dataRange.channels
    .map(channel => `<option value="${channel}">${channel}</option>`)
    .join("");
  document.getElementById("start-date").min = dataRange.startDate;
  document.getElementById("start-date").max = dataRange.endDate;
  document.getElementById("start-date").value = dataRange.startDate;
  document.getElementById("end-date").min = dataRange.startDate;
  document.getElementById("end-date").max = dataRange.endDate;
  document.getElementById("end-date").value = dataRange.endDate;
  await loadDashboard();
}

document.getElementById("dashboard-filter-form").addEventListener("submit", event => { event.preventDefault(); loadDashboard(); });
document.getElementById("logout-button").addEventListener("click", logout);
document.getElementById("download-csv-button").addEventListener("click", downloadCsv);
document.getElementById("export-margin-chart-button").addEventListener("click", () => { if (!marginChart) return; const link = document.createElement("a"); link.href = marginChart.toBase64Image(); link.download = "recursive_margin_forecast.png"; link.click(); });
initializeDashboard().catch(problem => {
  document.getElementById("dashboard-filter-error").textContent = problem.message;
});
