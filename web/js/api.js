const API = {
  getToken() {
    return localStorage.getItem("bm_token");
  },

  setToken(token) {
    localStorage.setItem("bm_token", token);
  },

  async request(path, options = {}) {
    const headers = options.headers || {};
    const token = this.getToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const response = await fetch(path, { ...options, headers });
    return response;
  },

  async login(email, password) {
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = data.error || "login failed";
      throw new Error(message);
    }
    return data;
  },

  async register(email, password) {
    const response = await fetch("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = data.error || "register failed";
      throw new Error(message);
    }
    return data;
  },

  async getSettings() {
    const response = await this.request("/api/settings");
    if (!response.ok) {
      throw new Error("settings fetch failed");
    }
    return response.json();
  },

  async updateSettings(payload) {
    const response = await this.request("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error("settings update failed");
    }
    return response.json();
  },

  async registerDevice(payload) {
    const response = await this.request("/api/devices/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error("device registration failed");
    }
    return response.json();
  },
};

window.BM_API = API;
