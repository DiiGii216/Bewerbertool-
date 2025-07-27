(() => {
  // API base path. When serving frontend from the same origin as backend
  // (e.g. via a reverse proxy), an empty string is sufficient.
  const API_BASE = '';
  const app = document.getElementById('app');

  // Application state
  let candidates = [];
  let view = 'list'; // 'list' or 'candidate'
  let currentCandidate = null;
  let currentStep = 0; // 0 Einstieg, 1 Selbstreflexion, 2 Bewertung, 3 Fazit
  let sidebarVisible = false;
  let sidebarTab = 'notes'; // 'notes', 'star', 'vesier'

  const dimensions = [
    'Zielorientierung',
    'Kundenorientierung',
    'Selbstorganisation',
    'Veränderungsbereitschaft',
    'Zusammenarbeit',
    'Entwicklungsmotivation',
    'Belastbarkeit'
  ];

  const starContent = `
    <h3>STAR‑Methode</h3>
    <p>Die STAR‑Methode hilft dabei, Antworten auf Verhaltensfragen strukturiert zu geben.</p>
    <ul>
      <li><strong>Situation:</strong> Setzen Sie den Kontext und geben Sie die nötigen Details des Beispiels an.</li>
      <li><strong>Aufgabe:</strong> Beschreiben Sie, was Ihre Verantwortung in dieser Situation war.</li>
      <li><strong>Aktion:</strong> Erklären Sie, welche Schritte Sie unternommen haben.</li>
      <li><strong>Ergebnis:</strong> Teilen Sie mit, welches Ergebnis Ihre Handlungen erzielt haben.</li>
    </ul>
  `;

  const vesierContent = `
    <h3>VeSiEr‑Methode</h3>
    <p>VeSiEr steht für Verhalten, Situation, Ergebnis. Das Wortspiel erinnert an ein Visier, das beim Interview angehoben wird, um die wahren Kompetenzen zu erkennen.</p>
    <p>Stellen Sie Fragen zu:</p>
    <ul>
      <li><strong>Verhalten:</strong> Wie haben Sie es genau gemacht? Was haben Sie getan? Was war Ihr Beitrag?</li>
      <li><strong>Situation:</strong> Wo fand es statt? Wann? Wer war beteiligt? Wie waren die Rahmenbedingungen?</li>
      <li><strong>Ergebnis:</strong> Was haben Sie erreicht? Was war das Ergebnis?</li>
    </ul>
  `;

  function init() {
    fetchCandidates();
  }

  function fetchCandidates() {
    fetch(`${API_BASE}/api/candidates`)
      .then(res => res.json())
      .then(data => {
        candidates = data.candidates || [];
        render();
      })
      .catch(err => {
        console.error('Fehler beim Laden der Kandidaten:', err);
      });
  }

  function createCandidate() {
    fetch(`${API_BASE}/api/candidates`, { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        const id = data.id;
        // Reload list and open candidate once loaded
        fetchCandidates();
        openCandidate(id);
      })
      .catch(err => console.error('Fehler beim Erstellen des Kandidaten:', err));
  }

  function openCandidate(id) {
    fetch(`${API_BASE}/api/candidates/${id}`)
      .then(res => res.json())
      .then(candidate => {
        currentCandidate = candidate;
        currentStep = 0;
        view = 'candidate';
        sidebarVisible = false;
        sidebarTab = 'notes';
        render();
      })
      .catch(err => console.error('Fehler beim Laden des Kandidaten:', err));
  }

  function saveCandidate(updates, callback) {
    if (!currentCandidate) return;
    fetch(`${API_BASE}/api/candidates/${currentCandidate.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    })
      .then(res => res.json())
      .then(() => {
        // Update local copy
        Object.keys(updates).forEach(key => {
          if (key === 'ratings' && updates[key] != null) {
            currentCandidate.ratings = updates[key];
          } else {
            currentCandidate[key] = updates[key];
          }
        });
        if (callback) callback();
      })
      .catch(err => console.error('Fehler beim Speichern:', err));
  }

  function deleteCandidate(id) {
    if (!confirm('Kandidat endgültig löschen?')) return;
    fetch(`${API_BASE}/api/candidates/${id}`, { method: 'DELETE' })
      .then(() => {
        currentCandidate = null;
        view = 'list';
        fetchCandidates();
      })
      .catch(err => console.error('Fehler beim Löschen:', err));
  }

  function exportPdf() {
    if (!currentCandidate) return;
    fetch(`${API_BASE}/api/candidates/${currentCandidate.id}/export`, { method: 'POST' })
      .then(res => res.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentCandidate.id}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      })
      .catch(err => console.error('Fehler beim Exportieren:', err));
  }

  // Toggle sidebar visibility
  function toggleSidebar() {
    sidebarVisible = !sidebarVisible;
    renderSidebar();
  }

  function setSidebarTab(tab) {
    sidebarTab = tab;
    renderSidebar();
  }

  function render() {
    app.innerHTML = '';
    if (view === 'list') {
      renderListView();
    } else {
      renderCandidateView();
    }
  }

  function renderListView() {
    const container = document.createElement('div');
    container.className = 'card';
    const title = document.createElement('h2');
    title.textContent = 'Kandidatenübersicht';
    container.appendChild(title);
    const createBtn = document.createElement('button');
    createBtn.className = 'button';
    createBtn.textContent = 'Neuen Kandidaten anlegen';
    createBtn.addEventListener('click', createCandidate);
    container.appendChild(createBtn);
    // Candidate list
    const list = document.createElement('ul');
    list.className = 'candidates-list';
    candidates.forEach(item => {
      const li = document.createElement('li');
      li.className = 'candidate-item';
      const infoDiv = document.createElement('div');
      infoDiv.innerHTML = `<strong>${item.id}</strong><br><small>${item.created_at}</small>`;
      const openBtn = document.createElement('button');
      openBtn.className = 'button';
      openBtn.textContent = 'Öffnen';
      openBtn.addEventListener('click', () => openCandidate(item.id));
      li.appendChild(infoDiv);
      li.appendChild(openBtn);
      list.appendChild(li);
    });
    container.appendChild(list);
    app.appendChild(container);
  }

  function renderCandidateView() {
    if (!currentCandidate) return;
    const container = document.createElement('div');
    container.className = 'card';
    // Step navigation
    const stepNav = document.createElement('div');
    stepNav.className = 'step-nav';
    ['Einstieg', 'Selbstreflexion', '7‑Dimensionen', 'Fazit'].forEach((label, index) => {
      const btn = document.createElement('button');
      btn.textContent = label;
      if (index === currentStep) btn.classList.add('active');
      btn.addEventListener('click', () => {
        currentStep = index;
        render();
      });
      stepNav.appendChild(btn);
    });
    container.appendChild(stepNav);
    // Step content
    const contentDiv = document.createElement('div');
    switch (currentStep) {
      case 0:
        contentDiv.appendChild(renderStepIntro());
        break;
      case 1:
        contentDiv.appendChild(renderStepReflection());
        break;
      case 2:
        contentDiv.appendChild(renderStepRatings());
        break;
      case 3:
        contentDiv.appendChild(renderStepConclusion());
        break;
    }
    container.appendChild(contentDiv);
    app.appendChild(container);
    // Render sidebar and toggle handle
    renderSidebar();
  }

  function renderStepIntro() {
    const div = document.createElement('div');
    // Candidate ID and creation date
    const idGroup = document.createElement('div');
    idGroup.className = 'form-group';
    idGroup.innerHTML = `<label>ID</label><div>${currentCandidate.id}</div>`;
    div.appendChild(idGroup);
    const dateGroup = document.createElement('div');
    dateGroup.className = 'form-group';
    dateGroup.innerHTML = `<label>Erstellt am</label><div>${currentCandidate.created_at}</div>`;
    div.appendChild(dateGroup);
    // Consent checkbox
    const consentGroup = document.createElement('div');
    consentGroup.className = 'form-group';
    const consentId = 'consent-checkbox';
    consentGroup.innerHTML = `<label><input type="checkbox" id="${consentId}" ${currentCandidate.consented ? 'checked' : ''}> Einverständnis eingeholt</label>`;
    div.appendChild(consentGroup);
    // Save listener for consent
    setTimeout(() => {
      const cb = document.getElementById(consentId);
      if (cb) {
        cb.addEventListener('change', () => {
          const updates = { consented: cb.checked };
          if (cb.checked) {
            updates.consent_date = new Date().toISOString();
          } else {
            updates.consent_date = null;
          }
          saveCandidate(updates);
        });
      }
    }, 0);
    // Back to list
    const backBtn = document.createElement('button');
    backBtn.className = 'button secondary';
    backBtn.textContent = 'Zurück zur Übersicht';
    backBtn.addEventListener('click', () => {
      view = 'list';
      currentCandidate = null;
      fetchCandidates();
    });
    // Next step button
    const nextBtn = document.createElement('button');
    nextBtn.className = 'button';
    nextBtn.textContent = 'Weiter';
    nextBtn.addEventListener('click', () => {
      currentStep = 1;
      render();
    });
    const btnDiv = document.createElement('div');
    btnDiv.appendChild(backBtn);
    btnDiv.appendChild(nextBtn);
    div.appendChild(btnDiv);
    return div;
  }

  function renderStepReflection() {
    const div = document.createElement('div');
    const group = document.createElement('div');
    group.className = 'form-group';
    const textId = 'self-ref-textarea';
    group.innerHTML = `<label>Selbstreflexion</label><textarea id="${textId}">${currentCandidate.self_reflection || ''}</textarea>`;
    div.appendChild(group);
    const buttons = document.createElement('div');
    // Back
    const backBtn = document.createElement('button');
    backBtn.className = 'button secondary';
    backBtn.textContent = 'Zurück';
    backBtn.addEventListener('click', () => {
      currentStep = 0;
      render();
    });
    // Save & next
    const nextBtn = document.createElement('button');
    nextBtn.className = 'button';
    nextBtn.textContent = 'Speichern & weiter';
    nextBtn.addEventListener('click', () => {
      const textarea = document.getElementById(textId);
      const updates = { self_reflection: textarea.value.trim() };
      saveCandidate(updates, () => {
        currentStep = 2;
        render();
      });
    });
    buttons.appendChild(backBtn);
    buttons.appendChild(nextBtn);
    div.appendChild(buttons);
    return div;
  }

  function renderStepRatings() {
    const div = document.createElement('div');
    // Ratings table
    const table = document.createElement('table');
    table.className = 'ratings-table';
    const thead = document.createElement('thead');
    thead.innerHTML = '<tr><th>Dimension</th><th>Bewertung (1–5)</th></tr>';
    table.appendChild(thead);
    const tbody = document.createElement('tbody');
    const ratings = currentCandidate.ratings || {};
    dimensions.forEach(dim => {
      const tr = document.createElement('tr');
      const tdLabel = document.createElement('td');
      tdLabel.textContent = dim;
      const tdSelect = document.createElement('td');
      const select = document.createElement('select');
      select.dataset.dim = dim;
      // Empty option
      const emptyOption = document.createElement('option');
      emptyOption.value = '';
      emptyOption.textContent = '–';
      select.appendChild(emptyOption);
      for (let i = 1; i <= 5; i++) {
        const opt = document.createElement('option');
        opt.value = String(i);
        opt.textContent = String(i);
        if (String(ratings[dim]) === String(i)) {
          opt.selected = true;
        }
        select.appendChild(opt);
      }
      tdSelect.appendChild(select);
      tr.appendChild(tdLabel);
      tr.appendChild(tdSelect);
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    div.appendChild(table);
    // Navigation buttons
    const buttons = document.createElement('div');
    // Back
    const backBtn = document.createElement('button');
    backBtn.className = 'button secondary';
    backBtn.textContent = 'Zurück';
    backBtn.addEventListener('click', () => {
      currentStep = 1;
      render();
    });
    // Save & next
    const nextBtn = document.createElement('button');
    nextBtn.className = 'button';
    nextBtn.textContent = 'Speichern & weiter';
    nextBtn.addEventListener('click', () => {
      // Collect ratings
      const selects = tbody.querySelectorAll('select');
      const newRatings = {};
      selects.forEach(sel => {
        const dim = sel.dataset.dim;
        const val = sel.value;
        if (val) newRatings[dim] = parseInt(val);
      });
      saveCandidate({ ratings: newRatings }, () => {
        currentStep = 3;
        render();
      });
    });
    buttons.appendChild(backBtn);
    buttons.appendChild(nextBtn);
    div.appendChild(buttons);
    return div;
  }

  function renderStepConclusion() {
    const div = document.createElement('div');
    // Summary of ratings
    const ratings = currentCandidate.ratings || {};
    const values = Object.values(ratings).filter(v => typeof v === 'number');
    const avg = values.length > 0 ? (values.reduce((a, b) => a + b, 0) / values.length).toFixed(2) : '–';
    const summary = document.createElement('div');
    summary.className = 'form-group';
    let summaryHtml = '<strong>Zusammenfassung der Bewertungen:</strong><ul>';
    dimensions.forEach(dim => {
      summaryHtml += `<li>${dim}: ${ratings[dim] || '–'}</li>`;
    });
    summaryHtml += `</ul><p><strong>Durchschnitt:</strong> ${avg}</p>`;
    // Consistency check: ensure all dimensions rated
    if (values.length < dimensions.length) {
      summaryHtml += `<p style="color: #d9534f;">Es fehlen Bewertungen – bitte alle Dimensionen bewerten.</p>`;
    } else {
      summaryHtml += `<p style="color: #5cb85c;">Alle Bewertungen vollständig.</p>`;
    }
    summary.innerHTML = summaryHtml;
    div.appendChild(summary);
    // Conclusion text area
    const conclusionGroup = document.createElement('div');
    conclusionGroup.className = 'form-group';
    const conclusionId = 'conclusion-textarea';
    conclusionGroup.innerHTML = `<label>Fazit</label><textarea id="${conclusionId}">${currentCandidate.conclusion || ''}</textarea>`;
    div.appendChild(conclusionGroup);
    // Buttons: back, save, export, delete, list
    const buttons = document.createElement('div');
    // Back
    const backBtn = document.createElement('button');
    backBtn.className = 'button secondary';
    backBtn.textContent = 'Zurück';
    backBtn.addEventListener('click', () => {
      currentStep = 2;
      render();
    });
    // Save
    const saveBtn = document.createElement('button');
    saveBtn.className = 'button';
    saveBtn.textContent = 'Speichern';
    saveBtn.addEventListener('click', () => {
      const txt = document.getElementById(conclusionId).value.trim();
      saveCandidate({ conclusion: txt }, () => {
        alert('Fazit gespeichert');
      });
    });
    // Export
    const exportBtn = document.createElement('button');
    exportBtn.className = 'button';
    exportBtn.textContent = 'PDF exportieren';
    exportBtn.addEventListener('click', exportPdf);
    // Delete
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'button secondary';
    deleteBtn.textContent = 'Kandidat löschen';
    deleteBtn.addEventListener('click', () => deleteCandidate(currentCandidate.id));
    // Back to list
    const listBtn = document.createElement('button');
    listBtn.className = 'button secondary';
    listBtn.textContent = 'Zur Übersicht';
    listBtn.addEventListener('click', () => {
      view = 'list';
      currentCandidate = null;
      fetchCandidates();
    });
    buttons.appendChild(backBtn);
    buttons.appendChild(saveBtn);
    buttons.appendChild(exportBtn);
    buttons.appendChild(deleteBtn);
    buttons.appendChild(listBtn);
    div.appendChild(buttons);
    return div;
  }

  function renderSidebar() {
    // Remove existing sidebar and toggle if present
    const oldSidebar = document.querySelector('.sidebar');
    if (oldSidebar) oldSidebar.remove();
    const oldToggle = document.querySelector('.sidebar-toggle');
    if (oldToggle) oldToggle.remove();
    if (view !== 'candidate' || !currentCandidate) return;
    // Sidebar element
    const sidebar = document.createElement('div');
    sidebar.className = 'sidebar' + (sidebarVisible ? ' open' : '');
    // Tab navigation within sidebar
    const tabNav = document.createElement('div');
    ['notes', 'star', 'vesier'].forEach(tab => {
      const btn = document.createElement('button');
      btn.className = 'button' + (sidebarTab === tab ? '' : ' secondary');
      btn.style.marginRight = '0.5rem';
      btn.textContent = tab === 'notes' ? 'Notizen' : (tab === 'star' ? 'STAR' : 'VeSiEr');
      btn.addEventListener('click', () => setSidebarTab(tab));
      tabNav.appendChild(btn);
    });
    sidebar.appendChild(tabNav);
    // Content area
    const content = document.createElement('div');
    content.style.marginTop = '1rem';
    if (sidebarTab === 'notes') {
      const textarea = document.createElement('textarea');
      textarea.className = 'notes-area';
      textarea.value = currentCandidate.notes || '';
      textarea.addEventListener('input', () => {
        currentCandidate.notes = textarea.value;
      });
      textarea.addEventListener('blur', () => {
        saveCandidate({ notes: textarea.value.trim() });
      });
      content.appendChild(textarea);
    } else if (sidebarTab === 'star') {
      content.innerHTML = starContent;
    } else if (sidebarTab === 'vesier') {
      content.innerHTML = vesierContent;
    }
    sidebar.appendChild(content);
    document.body.appendChild(sidebar);
    // Toggle handle
    const toggle = document.createElement('div');
    toggle.className = 'sidebar-toggle';
    toggle.innerHTML = sidebarVisible ? '&raquo;' : '&laquo;';
    toggle.addEventListener('click', () => {
      sidebarVisible = !sidebarVisible;
      renderSidebar();
    });
    document.body.appendChild(toggle);
  }

  // Initialize application on DOM ready
  document.addEventListener('DOMContentLoaded', init);
})();