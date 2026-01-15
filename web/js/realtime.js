const statusText = document.getElementById("statusText");
const statusCard = document.getElementById("statusCard");
const cryTimer = document.getElementById("cryTimer");
const lastUpdate = document.getElementById("lastUpdate");

const thresholdInfo = document.getElementById("thresholdInfo");
const cooldownInfo = document.getElementById("cooldownInfo");

const POLL_MS = 2000;

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${String(secs).padStart(2, "0")}`;
}

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

  cryTimer.textContent = formatDuration(data.duration_seconds || 0);
  if (data.last_updated_at) {
    const when = new Date(data.last_updated_at);
    lastUpdate.textContent = `Last update: ${when.toLocaleTimeString()}`;
  }
}

async function loadStatus() {
  try {
    const response = await fetch("/api/status");
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

function applyLocalSettings() {
  const threshold = localStorage.getItem("bm_threshold_seconds");
  const cooldown = localStorage.getItem("bm_cooldown_seconds");
  if (thresholdInfo && threshold) {
    const minutes = Math.round(Number(threshold) / 60);
    thresholdInfo.textContent = `Notify after ${minutes} minutes`;
  }
  if (cooldownInfo && cooldown) {
    const minutes = Math.round(Number(cooldown) / 60);
    cooldownInfo.textContent = `Cooldown ${minutes} minutes`;
  }
}

applyLocalSettings();
loadStatus();
setInterval(loadStatus, POLL_MS);
