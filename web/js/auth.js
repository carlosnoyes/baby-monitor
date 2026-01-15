function initLoginForm() {
  const form = document.getElementById("loginForm");
  if (!form) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    try {
      const data = await window.BM_API.login(email, password);
      window.BM_API.setToken(data.token);
      window.location.href = "dashboard.html";
    } catch (err) {
      alert("Login failed. Check your email and password.");
    }
  });
}

function initSettingsForm() {
  const threshold = document.getElementById("threshold");
  const cooldown = document.getElementById("cooldown");
  const enabled = document.getElementById("enabled");
  const thresholdValue = document.getElementById("thresholdValue");
  const cooldownValue = document.getElementById("cooldownValue");
  const settingsStatus = document.getElementById("settingsStatus");
  const saveSettings = document.getElementById("saveSettings");

  if (!threshold || !cooldown || !enabled) {
    return;
  }

  function updateThresholdLabel(value) {
    thresholdValue.textContent = `${value} minutes`;
  }

  function updateCooldownLabel(value) {
    if (cooldownValue) {
      cooldownValue.textContent = `${value} minutes`;
    }
  }

  threshold.addEventListener("input", () => updateThresholdLabel(threshold.value));
  cooldown.addEventListener("input", () => updateCooldownLabel(cooldown.value));

  saveSettings.addEventListener("click", async () => {
    settingsStatus.textContent = "Saving...";
    try {
      const payload = {
        threshold_seconds: Number(threshold.value) * 60,
        cooldown_seconds: Number(cooldown.value) * 60,
        enabled: enabled.checked,
      };
      const data = await window.BM_API.updateSettings(payload);
      localStorage.setItem("bm_threshold_seconds", data.threshold_seconds);
      localStorage.setItem("bm_cooldown_seconds", data.cooldown_seconds);
      settingsStatus.textContent = "Saved.";
    } catch (err) {
      settingsStatus.textContent = "Save failed. Log in again.";
    }
  });

  window.BM_API.getSettings()
    .then((data) => {
      threshold.value = Math.round(Number(data.threshold_seconds) / 60);
      cooldown.value = Math.round(Number(data.cooldown_seconds) / 60);
      enabled.checked = data.enabled;
      updateThresholdLabel(threshold.value);
      updateCooldownLabel(cooldown.value);
    })
    .catch(() => {
      settingsStatus.textContent = "Could not load settings. Log in again.";
    });
}

function initDeviceForm() {
  const tokenInput = document.getElementById("deviceToken");
  const platformInput = document.getElementById("platform");
  const button = document.getElementById("registerDevice");
  const status = document.getElementById("deviceStatus");

  if (!tokenInput || !button) {
    return;
  }

  button.addEventListener("click", async () => {
    status.textContent = "Registering...";
    try {
      await window.BM_API.registerDevice({
        token: tokenInput.value.trim(),
        platform: platformInput.value.trim() || "web",
      });
      status.textContent = "Device registered.";
      tokenInput.value = "";
    } catch (err) {
      status.textContent = "Registration failed. Log in again.";
    }
  });
}

initLoginForm();
initSettingsForm();
initDeviceForm();
