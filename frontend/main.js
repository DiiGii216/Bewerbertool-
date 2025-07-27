(() => {
  const API_BASE = "https://bewerbertool.onrender.com";
  const app = document.getElementById("app");

  async function loadCandidates() {
    const res = await fetch(`${API_BASE}/api/candidates`);
    if (!res.ok) throw new Error("Fehler beim Laden der Kandidaten");
    const data = await res.json();
    candidates = data;
    renderList();
  }

  async function saveEvaluation(candidateId, payload) {
    await fetch(`${API_BASE}/api/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: candidateId, ...payload })
    });
  }

  // Placeholder für weitere Logik
})();
