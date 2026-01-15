const statusText = document.getElementById("statusText");
const statusCard = document.getElementById("statusCard");
const volumeChart = document.getElementById("volumeChart");
const incidentChart = document.getElementById("incidentChart");
const volumeTimeStart = document.getElementById("volumeTimeStart");
const volumeTimeEnd = document.getElementById("volumeTimeEnd");
const incidentTimeStart = document.getElementById("incidentTimeStart");
const incidentTimeEnd = document.getElementById("incidentTimeEnd");

const POLL_MS = 2000;
const MAX_VOLUME_MINUTES = 15;
const volumeHistory = [];

function updateStatus(data) {
  if (!data) {
    return;
  }

  if (data.is_crying) {
    statusText.textContent = "Crying";
    statusCard.classList.add("crying");
  } else {
    statusText.textContent = "Listening";
    statusCard.classList.remove("crying");
  }


  updateVolume(data);
  updateIncidentChart(data);
}

function updateVolume(data) {
  if (!volumeChart) {
    return;
  }
  const level = Number(data.volume_level || 0);
  const threshold = Number(data.volume_threshold || 0);
  const now = Date.now();
  volumeHistory.push({ t: now, level, threshold });
  const cutoff = now - MAX_VOLUME_MINUTES * 60 * 1000;
  while (volumeHistory.length && volumeHistory[0].t < cutoff) {
    volumeHistory.shift();
  }
  renderVolumeChart();
}

function renderVolumeChart() {
  if (!volumeChart) {
    return;
  }
  const width = 600;
  const height = 140;
  const padding = 10;
  const values = volumeHistory.map((point) => point.level);
  const threshold = volumeHistory.length ? volumeHistory[volumeHistory.length - 1].threshold : 0;
  const maxValue = Math.max(0.05, threshold * 1.6, ...values);

  const endTime = Date.now();
  const startTime = endTime - MAX_VOLUME_MINUTES * 60 * 1000;
  const span = MAX_VOLUME_MINUTES * 60 * 1000;

  const points = volumeHistory
    .map((point) => {
      const x = padding + ((point.t - startTime) / span) * (width - padding * 2);
      const y = height - padding - (point.level / maxValue) * (height - padding * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const thresholdY =
    height - padding - (Math.min(threshold, maxValue) / maxValue) * (height - padding * 2);
  const lastPoint = volumeHistory[volumeHistory.length - 1];
  const lastX = padding + ((lastPoint.t - startTime) / span) * (width - padding * 2);
  const lastY =
    height - padding - (lastPoint.level / maxValue) * (height - padding * 2);

  volumeChart.innerHTML = `
    <polyline
      fill="none"
      stroke="#2ec4b6"
      stroke-width="2"
      points="${points}"
    />
    <circle
      cx="${lastX.toFixed(1)}"
      cy="${lastY.toFixed(1)}"
      r="3"
      fill="#2ec4b6"
    />
    <line
      x1="${padding}"
      x2="${width - padding}"
      y1="${thresholdY.toFixed(1)}"
      y2="${thresholdY.toFixed(1)}"
      stroke="#ff6b35"
      stroke-width="1"
      stroke-dasharray="4 4"
      opacity="0.9"
    />
  `;

  if (volumeTimeStart && volumeTimeEnd) {
    const endLabel = new Date(endTime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const startLabel = new Date(startTime).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    volumeTimeStart.textContent = startLabel;
    volumeTimeEnd.textContent = endLabel;
  }
}

function updateIncidentChart(data) {
  if (!incidentChart) {
    return;
  }
  const timeline = Array.isArray(data.timeline) ? data.timeline : [];
  const recent = timeline.slice(-480);
  const buckets = [];
  let bucketCount = 0;
  for (let i = 0; i < recent.length; i += 1) {
    const event = recent[i];
    if (event.is_crying) {
      bucketCount += 1;
    }
    if ((i + 1) % 5 === 0) {
      buckets.push(bucketCount);
      bucketCount = 0;
    }
  }
  if (recent.length % 5 !== 0) {
    buckets.push(bucketCount);
  }

  renderIncidentChart(buckets);
  if (incidentTimeStart && incidentTimeEnd) {
    const end = new Date();
    const start = new Date(end.getTime() - 8 * 60 * 60 * 1000);
    incidentTimeStart.textContent = start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    incidentTimeEnd.textContent = end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
}

function renderIncidentChart(buckets) {
  const width = 600;
  const height = 140;
  const padding = 8;
  const barCount = Math.min(96, buckets.length);
  const barWidth = (width - padding * 2) / Math.max(1, barCount);

  const bars = [];
  for (let i = 0; i < barCount; i += 1) {
    const count = Math.min(5, buckets[buckets.length - barCount + i] || 0);
    const ratio = count / 5;
    const barHeight = (height - padding * 2) * ratio;
    const x = padding + i * barWidth;
    const y = height - padding - barHeight;
    const hue = 120 - ratio * 120;
    const color = `hsl(${hue}, 70%, 50%)`;
    bars.push(
      `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(
        1,
        barWidth - 1
      ).toFixed(1)}" height="${barHeight.toFixed(1)}" fill="${color}" />`
    );
  }

  incidentChart.innerHTML = bars.join("");
}

async function loadStatus() {
  try {
    const response = await fetch(`/api/status?ts=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("status request failed");
    }
    const data = await response.json();
    updateStatus(data);
  } catch (err) {
    statusText.textContent = "Offline";
    statusCard.classList.remove("crying");
  }
}

loadStatus();
setInterval(loadStatus, POLL_MS);
