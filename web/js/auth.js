function initLoginForm() {
  const form = document.getElementById("loginForm");
  const modeLogin = document.getElementById("modeLogin");
  const modeRegister = document.getElementById("modeRegister");
  const formTitle = document.getElementById("formTitle");
  const formSubtitle = document.getElementById("formSubtitle");
  const submitButton = document.getElementById("submitButton");
  const helperText = document.getElementById("helperText");
  let mode = "login";
  if (!form) {
    return;
  }

  function setMode(nextMode) {
    mode = nextMode;
    if (mode === "register") {
      formTitle.textContent = "Create account";
      formSubtitle.textContent = "Set up your account to start monitoring.";
      submitButton.textContent = "Create Account";
      helperText.textContent = "Already have an account? Log in instead.";
      modeRegister.classList.add("secondary");
      modeLogin.classList.remove("secondary");
    } else {
      formTitle.textContent = "Welcome back";
      formSubtitle.textContent = "Log in to see the live monitor and update your alert settings.";
      submitButton.textContent = "Log In";
      helperText.textContent = "New here? Create an account to get started.";
      modeLogin.classList.add("secondary");
      modeRegister.classList.remove("secondary");
    }
  }

  if (modeLogin && modeRegister) {
    modeLogin.addEventListener("click", () => setMode("login"));
    modeRegister.addEventListener("click", () => setMode("register"));
  }
  setMode("login");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    try {
      const data =
        mode === "register"
          ? await window.BM_API.register(email, password)
          : await window.BM_API.login(email, password);
      window.BM_API.setToken(data.token);
      window.location.href = "dashboard.html";
    } catch (err) {
      const message = err && err.message ? err.message : "Request failed.";
      alert(message);
    }
  });
}

function initNavAuth() {
  const authAction = document.getElementById("authAction");
  const pushLink = document.getElementById("pushLink");
  if (!authAction) {
    return;
  }

  const token = window.BM_API.getToken();
  if (token) {
    authAction.textContent = "Log Out";
    authAction.href = "#";
    if (pushLink) {
      pushLink.style.display = "inline-flex";
    }
    authAction.addEventListener("click", (event) => {
      event.preventDefault();
      localStorage.removeItem("bm_token");
      window.location.href = "dashboard.html";
    });
  } else {
    authAction.textContent = "Log In";
    authAction.href = "login.html";
    if (pushLink) {
      pushLink.style.display = "none";
    }
  }
}

initLoginForm();
initNavAuth();
