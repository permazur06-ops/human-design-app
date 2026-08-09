document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#hd-form");

  if (!form) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const button = form.querySelector('button[type="submit"]');
    const result = document.querySelector("#result");

    if (button) {
      button.disabled = true;
      button.textContent = "Calcul en cours…";
    }

    if (result) {
      result.innerHTML = "<p>Création de votre BodyGraph…</p>";
    }

    try {
      const formData = new FormData(form);

      const response = await fetch("/chart", {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        throw new Error("Erreur lors du calcul");
      }

      const html = await response.text();

      if (result) {
        result.innerHTML = html;
        result.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (error) {
      if (result) {
        result.innerHTML =
          "<p>Une erreur est survenue. Vérifiez les informations saisies et réessayez.</p>";
      }
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = "Générer mon BodyGraph";
      }
    }
  });
});
