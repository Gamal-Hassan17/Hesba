document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.dataset.confirm || "هل أنت متأكد؟";
      if (!window.confirm(message)) event.preventDefault();
    });
  });

  // Populate datetime-local inputs that should default to the current local time.
  document.querySelectorAll('input[type="datetime-local"]:not([value])').forEach((input) => {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    input.value = now.toISOString().slice(0, 16);
  });
});
