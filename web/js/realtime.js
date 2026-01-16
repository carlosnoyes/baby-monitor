const volumeChart = document.getElementById("volumeChart");
const incidentChart = document.getElementById("incidentChart");
const volumeTicks = document.getElementById("volumeTicks");
const incidentTicks = document.getElementById("incidentTicks");

const STATUS_POLL_MS = 2000;
const VOLUME_POLL_MS = 1000;
const DEFAULT_WINDOW_MINUTES = 4 * 60;
const MAX_HISTORY_MINUTES = 4 * 60;
const HIGH_RES_MINUTES = 10;
const DOWNSAMPLE_SECONDS = 10;
const VOLUME_Y_MIN = 0;
const VOLUME_Y_MAX = 0.1;
const allSamples = [];
let lastSampleTime = 0;

const thresholdSlider = document.getElementById("thresholdSlider");
const incidentThresholdSlider = document.getElementById("incidentThresholdSlider");
const alertAfterSlider = document.getElementById("alertAfter");
const alertAfterValue = document.getElementById("alertAfterValue");
let currentThreshold = Number.NaN;
let incidentThreshold = 1;
let alertAfterMinutes = 0;

function ceilToBucket(date, minutes) {
  const bucket = minutes || 5;
  const rounded = new Date(date);
  rounded.setSeconds(0, 0);
  const remainder = rounded.getMinutes() % bucket;
  if (remainder !== 0) {
    rounded.setMinutes(rounded.getMinutes() + (bucket - remainder));
  }
  return rounded;
}

function ceilToHour(date) {
  const rounded = new Date(date);
  rounded.setMinutes(0, 0, 0);
  if (date.getMinutes() !== 0 || date.getSeconds() !== 0 || date.getMilliseconds() !== 0) {
    rounded.setHours(rounded.getHours() + 1);
  }
  return rounded;
}

function buildAxisTicks(container, startTime, endTime) {
  if (!container) {
    return;
  }
  container.innerHTML = "";
  const start = new Date(startTime);
  const end = new Date(endTime);
  const spanMs = end.getTime() - start.getTime();

  const firstHour = new Date(start);
  if (firstHour.getMinutes() !== 0 || firstHour.getSeconds() !== 0 || firstHour.getMilliseconds() !== 0) {
    firstHour.setHours(firstHour.getHours() + 1);
  }
  firstHour.setMinutes(0, 0, 0);

  for (let hour = new Date(firstHour); hour <= end; hour.setHours(hour.getHours() + 1)) {
    const pos = (hour.getTime() - start.getTime()) / spanMs;
    if (pos < 0 || pos > 1) {
      continue;
    }
    const label = document.createElement("span");
    label.className = "tick-label";
    label.textContent = hour.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    label.style.left = `${pos * 100}%`;
    container.appendChild(label);

    const halfHour = new Date(hour);
    halfHour.setMinutes(30, 0, 0);
    if (halfHour <= end && halfHour >= start) {
      const major = document.createElement("span");
      major.className = "tick-major";
      major.style.left = `${((halfHour.getTime() - start.getTime()) / spanMs) * 100}%`;
      container.appendChild(major);
    }

    const quarter = new Date(hour);
    quarter.setMinutes(15, 0, 0);
    if (quarter <= end && quarter >= start) {
      const minor = document.createElement("span");
      minor.className = "tick-minor";
      minor.style.left = `${((quarter.getTime() - start.getTime()) / spanMs) * 100}%`;
      container.appendChild(minor);
    }

    const threeQuarter = new Date(hour);
    threeQuarter.setMinutes(45, 0, 0);
    if (threeQuarter <= end && threeQuarter >= start) {
      const minor = document.createElement("span");
      minor.className = "tick-minor";
      minor.style.left = `${((threeQuarter.getTime() - start.getTime()) / spanMs) * 100}%`;
      container.appendChild(minor);
    }
  }
}

function updateStatus(data) {
  if (!data) {
    return;
  }

  updateIncidentChart();
}

function applySamples(samples) {
  for (const sample of samples) {
    const ts = new Date(sample.t).getTime();
    if (Number.isNaN(ts)) {
      continue;
    }
    if (ts <= lastSampleTime) {
      continue;
    }
    allSamples.push({ t: ts, level: Number(sample.rms || 0) });
    lastSampleTime = Math.max(lastSampleTime, ts);
  }
}

function pruneSamples() {
  const cutoff = Date.now() - MAX_HISTORY_MINUTES * 60 * 1000;
  while (allSamples.length && allSamples[0].t < cutoff) {
    allSamples.shift();
  }
}

function renderVolumeChart() {
  if (!volumeChart) {
    return;
  }
  const width = 600;
  const height = 140;
  const padding = 10;
  const windowMinutes = DEFAULT_WINDOW_MINUTES;
  const endTime = ceilToBucket(new Date(), 5).getTime();
  const startTime = endTime - windowMinutes * 60 * 1000;
  const span = windowMinutes * 60 * 1000;
  const highResCutoff = endTime - HIGH_RES_MINUTES * 60 * 1000;

  const rawSamples = allSamples.filter((point) => point.t >= startTime && point.t <= endTime);
  const volumeSamples = [];
  const downsampled = new Map();
  for (const point of rawSamples) {
    if (point.t >= highResCutoff) {
      volumeSamples.push(point);
      continue;
    }
    const key = Math.floor(point.t / (DOWNSAMPLE_SECONDS * 1000));
    if (!downsampled.has(key)) {
      downsampled.set(key, { sum: 0, count: 0, t: key * DOWNSAMPLE_SECONDS * 1000 });
    }
    const bucket = downsampled.get(key);
    bucket.sum += point.level;
    bucket.count += 1;
  }
  for (const bucket of downsampled.values()) {
    volumeSamples.push({ t: bucket.t, level: bucket.sum / Math.max(1, bucket.count) });
  }
  volumeSamples.sort((a, b) => a.t - b.t);

  const threshold = currentThreshold;
  const maxValue = VOLUME_Y_MAX;
  const minuteStart = Math.floor(startTime / 60000);
  const minuteEnd = Math.floor(endTime / 60000);
  const buckets = new Map();

  for (const point of volumeSamples) {
    if (point.t < startTime || point.t > endTime) {
      continue;
    }
    const key = Math.floor(point.t / 60000);
    if (!buckets.has(key)) {
      buckets.set(key, { points: [], exceeded: false });
    }
    const bucket = buckets.get(key);
    bucket.points.push(point);
    if (point.level >= threshold) {
      bucket.exceeded = true;
    }
  }

  const polylines = [];
  for (let minute = minuteStart; minute <= minuteEnd; minute += 1) {
    const bucket = buckets.get(minute);
    if (!bucket || bucket.points.length === 0) {
      continue;
    }
    const points = bucket.points
      .map((point) => {
        const x = padding + ((point.t - startTime) / span) * (width - padding * 2);
        const y = height - padding - (point.level / maxValue) * (height - padding * 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
    const color = bucket.exceeded ? "#ff6b35" : "#2ec4b6";
    polylines.push(
      `<polyline fill="none" stroke="${color}" stroke-width="2" points="${points}" />`
    );
  }

  const thresholdY =
    height - padding - (Math.min(threshold, maxValue) / maxValue) * (height - padding * 2);
  const lastPoint = volumeSamples[volumeSamples.length - 1];
  const lastColor = lastPoint && lastPoint.level >= threshold ? "#ff6b35" : "#2ec4b6";
  const lastX = lastPoint
    ? padding + ((lastPoint.t - startTime) / span) * (width - padding * 2)
    : padding;
  const lastY = lastPoint
    ? height - padding - (lastPoint.level / maxValue) * (height - padding * 2)
    : height - padding;
  const shadeStart =
    alertAfterMinutes > 0
      ? padding +
        ((endTime - alertAfterMinutes * 60 * 1000 - startTime) / span) * (width - padding * 2)
      : null;

  volumeChart.innerHTML = `
    ${
      shadeStart !== null
        ? `<rect x="${shadeStart.toFixed(1)}" y="${padding}" width="${(
            width - padding - shadeStart
          ).toFixed(1)}" height="${(height - padding * 2).toFixed(1)}" fill="rgba(0,0,0,0.06)" />`
        : ""
    }
    ${polylines.join("")}
    <circle
      cx="${lastX.toFixed(1)}"
      cy="${lastY.toFixed(1)}"
      r="3"
      fill="${lastColor}"
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

  if (volumeTicks) {
    buildAxisTicks(volumeTicks, startTime, endTime);
  }
}

function updateIncidentChart() {
  if (!incidentChart) {
    return;
  }
  const samples = allSamples;
  const bucketMinutes = 5;
  const totalMinutes = DEFAULT_WINDOW_MINUTES;
  const bucketCount = totalMinutes / bucketMinutes;
  const endTime = ceilToBucket(new Date(), bucketMinutes);
  const startTime = new Date(endTime.getTime() - totalMinutes * 60 * 1000);

  const minuteHits = new Map();
  for (const sample of samples) {
    const ts = new Date(sample.t).getTime();
    if (Number.isNaN(ts)) {
      continue;
    }
    if (ts < startTime.getTime() || ts >= endTime.getTime()) {
      continue;
    }
    const minuteKey = Math.floor(ts / 60000);
    if (!minuteHits.has(minuteKey)) {
      minuteHits.set(minuteKey, false);
    }
    if (Number(sample.level || 0) >= currentThreshold) {
      minuteHits.set(minuteKey, true);
    }
  }

  const buckets = new Array(bucketCount).fill(0);
  for (let i = 0; i < totalMinutes; i += 1) {
    const minuteTime = new Date(startTime.getTime() + i * 60 * 1000);
    const minuteKey = Math.floor(minuteTime.getTime() / 60000);
    const hit = minuteHits.get(minuteKey) || false;
    const bucketIndex = Math.floor(i / bucketMinutes);
    if (hit) {
      buckets[bucketIndex] += 1;
    }
  }

  renderIncidentChart(buckets, startTime, endTime);
  if (incidentTicks) {
    buildAxisTicks(incidentTicks, startTime, endTime);
  }
}

function renderIncidentChart(buckets, startTime, endTime) {
  const width = 600;
  const height = 140;
  const padding = 8;
  const barCount = buckets.length;
  const barWidth = (width - padding * 2) / Math.max(1, barCount);
  const thresholdY =
    height - padding - (incidentThreshold / 5) * (height - padding * 2);
  const span = endTime.getTime() - startTime.getTime();
  const shadeStart =
    alertAfterMinutes > 0
      ? padding +
        ((endTime.getTime() - alertAfterMinutes * 60 * 1000 - startTime.getTime()) / span) *
          (width - padding * 2)
      : null;

  const bars = [];
  for (let i = 0; i < barCount; i += 1) {
    const count = Math.min(5, buckets[i] || 0);
    const ratio = count / 5;
    const barHeight = (height - padding * 2) * ratio;
    const x = padding + i * barWidth;
    const y = height - padding - barHeight;
    const color = count >= incidentThreshold ? "#ff6b35" : "#2ec4b6";
    bars.push(
      `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(
        1,
        barWidth - 1
      ).toFixed(1)}" height="${barHeight.toFixed(1)}" fill="${color}" />`
    );
  }

  incidentChart.innerHTML = `
    ${
      shadeStart !== null
        ? `<rect x="${shadeStart.toFixed(1)}" y="${padding}" width="${(
            width - padding - shadeStart
          ).toFixed(1)}" height="${(height - padding * 2).toFixed(1)}" fill="rgba(0,0,0,0.06)" />`
        : ""
    }
    ${bars.join("")}
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
    // ignore transient failures
  }
}

async function loadVolume() {
  try {
    const response = await fetch(`/api/volume?minutes=${MAX_HISTORY_MINUTES}&ts=${Date.now()}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error("volume request failed");
    }
    const data = await response.json();
    const samples = Array.isArray(data.samples) ? data.samples : [];
    const threshold = Number(data.threshold || 0);
    if (!Number.isFinite(currentThreshold)) {
      const initial = Math.min(VOLUME_Y_MAX, Math.max(VOLUME_Y_MIN, threshold));
      currentThreshold = initial;
      if (thresholdSlider) {
        thresholdSlider.value = String(initial);
      }
    }
    applySamples(samples);
    pruneSamples();
    renderVolumeChart();
    updateIncidentChart();
  } catch (err) {
    // ignore transient failures
  }
}

async function pollNewSamples() {
  try {
    const response = await fetch(`/api/volume?minutes=1&ts=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("poll request failed");
    }
    const data = await response.json();
    const samples = Array.isArray(data.samples) ? data.samples : [];
    applySamples(samples);
    pruneSamples();
    renderVolumeChart();
    updateIncidentChart();
  } catch (err) {
    // ignore transient failures
  }
}

function initThresholdSlider() {
  if (!thresholdSlider) {
    return;
  }
  thresholdSlider.min = String(VOLUME_Y_MIN);
  thresholdSlider.max = String(VOLUME_Y_MAX);
  thresholdSlider.step = "0.001";
  thresholdSlider.addEventListener("input", () => {
    currentThreshold = Number(thresholdSlider.value);
    localStorage.setItem("bm_volume_threshold", String(currentThreshold));
    renderVolumeChart();
    updateIncidentChart();
  });
  const stored = Number(localStorage.getItem("bm_volume_threshold"));
  if (Number.isFinite(stored) && stored >= VOLUME_Y_MIN && stored <= VOLUME_Y_MAX) {
    currentThreshold = stored;
    thresholdSlider.value = String(stored);
  }
}

function initIncidentThresholdSlider() {
  if (!incidentThresholdSlider) {
    return;
  }
  incidentThresholdSlider.min = "0";
  incidentThresholdSlider.max = "5";
  incidentThresholdSlider.step = "1";
  const stored = Number(localStorage.getItem("bm_incident_threshold"));
  if (Number.isFinite(stored)) {
    incidentThreshold = stored;
    incidentThresholdSlider.value = String(stored);
  } else {
    incidentThreshold = Number(incidentThresholdSlider.value);
  }
  incidentThresholdSlider.addEventListener("input", () => {
    incidentThreshold = Number(incidentThresholdSlider.value);
    localStorage.setItem("bm_incident_threshold", String(incidentThreshold));
    updateIncidentChart();
  });
}

function initAlertAfterSlider() {
  if (!alertAfterSlider || !alertAfterValue) {
    return;
  }
  const stored = Number(localStorage.getItem("bm_alert_after_minutes"));
  if (Number.isFinite(stored)) {
    alertAfterMinutes = stored;
    alertAfterSlider.value = String(stored);
  }
  alertAfterValue.textContent = String(alertAfterMinutes);
  alertAfterSlider.addEventListener("input", () => {
    alertAfterMinutes = Number(alertAfterSlider.value);
    localStorage.setItem("bm_alert_after_minutes", String(alertAfterMinutes));
    alertAfterValue.textContent = String(alertAfterMinutes);
    renderVolumeChart();
    updateIncidentChart();
  });
}

loadStatus();
loadVolume();
initThresholdSlider();
initIncidentThresholdSlider();
initAlertAfterSlider();
setInterval(loadStatus, STATUS_POLL_MS);
setInterval(pollNewSamples, VOLUME_POLL_MS);
