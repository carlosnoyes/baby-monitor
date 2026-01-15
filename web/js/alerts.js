const thresholdInput = document.getElementById("threshold");
const cooldownInput = document.getElementById("cooldown");
const thresholdValue = document.getElementById("thresholdValue");
const cooldownValue = document.getElementById("cooldownValue");
const alertStatus = document.getElementById("alertStatus");
const alertOverlay = document.getElementById("alertOverlay");
const dismissAlert = document.getElementById("dismissAlert");

const POLL_MS = 2000;
let alertActive = false;
let lastAlertAt = 0;
let audioContext = null;
let beepTimer = null;

function updateLabels() {
  if (thresholdValue) {
    thresholdValue.textContent = `${thresholdInput.value} minutes`;
  }
  if (cooldownValue) {
    cooldownValue.textContent = `${cooldownInput.value} minutes`;
  }
}

function ensureAudioContext() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
  }
}

function playBeep() {
  ensureAudioContext();
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  oscillator.type = "sine";
  oscillator.frequency.value = 880;
  gain.gain.value = 0.2;
  oscillator.connect(gain);
  gain.connect(audioContext.destination);
  oscillator.start();
  oscillator.stop(audioContext.currentTime + 0.4);
}

function startAlert() {
  alertActive = true;
  lastAlertAt = Date.now();
  alertOverlay.style.display = "flex";
  if (!beepTimer) {
    playBeep();
    beepTimer = setInterval(playBeep, 2000);
  }
  alertStatus.textContent = "Status: alerting";
}

function stopAlert() {
  alertActive = false;
  alertOverlay.style.display = "none";
  if (beepTimer) {
    clearInterval(beepTimer);
    beepTimer = null;
  }
  alertStatus.textContent = "Status: monitoring";
}

async function loadStatus() {
  try {
    const response = await fetch(`/api/status?ts=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("status request failed");
    }
    const data = await response.json();
    evaluateAlert(data);
  } catch (err) {
    alertStatus.textContent = "Status: offline";
  }
}

function evaluateAlert(state) {
  const thresholdMinutes = Number(thresholdInput.value);
  const cooldownMinutes = Number(cooldownInput.value);
  const cooldownMs = cooldownMinutes * 60 * 1000;

  if (alertActive) {
    return;
  }

  const now = Date.now();
  if (lastAlertAt && now - lastAlertAt < cooldownMs) {
    return;
  }

  const currentCrying = Boolean(state.current_minute_is_crying);
  const effectiveMinutes = Number(state.effective_cry_minutes || 0);

  let shouldAlert = false;
  if (thresholdMinutes === 0) {
    shouldAlert = currentCrying;
  } else {
    shouldAlert = currentCrying && effectiveMinutes >= thresholdMinutes;
  }

  if (shouldAlert) {
    startAlert();
  }
}

thresholdInput.addEventListener("input", updateLabels);
cooldownInput.addEventListener("input", updateLabels);
dismissAlert.addEventListener("click", stopAlert);

updateLabels();
loadStatus();
setInterval(loadStatus, POLL_MS);
