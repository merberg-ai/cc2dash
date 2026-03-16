async function postJson(url, data) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return response.json();
}

const addPrinterForm = document.getElementById('add-printer-form');
if (addPrinterForm) {
  addPrinterForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(addPrinterForm);
    const payload = Object.fromEntries(form.entries());
    const resultBox = document.getElementById('setup-result');
    try {
      const result = await postJson('/api/printers', payload);
      resultBox.textContent = JSON.stringify(result, null, 2);
      if (result.id) {
        window.location.href = `/printer/${result.id}`;
      }
    } catch (error) {
      resultBox.textContent = `Request failed: ${error}`;
    }
  });
}

const statusPanel = document.querySelector('[data-status-panel]');
if (statusPanel) {
  const printerId = statusPanel.getAttribute('data-printer-id');
  const refresh = async () => {
    try {
      const response = await fetch(`/api/status/${printerId}`);
      const data = await response.json();
      const grid = document.getElementById('status-grid');
      if (!grid) return;
      grid.innerHTML = `
        <div class="card"><span class="label">Online</span><span class="value">${data.is_online ? 'Yes' : 'No'}</span></div>
        <div class="card"><span class="label">Status</span><span class="value">${data.status ?? 'Unknown'}</span></div>
        <div class="card"><span class="label">Sub-status</span><span class="value">${data.sub_status ?? '—'}</span></div>
        <div class="card"><span class="label">File</span><span class="value">${data.current_file ?? '—'}</span></div>
        <div class="card"><span class="label">Progress</span><span class="value">${data.progress ?? '—'}</span></div>
        <div class="card"><span class="label">Nozzle</span><span class="value">${data.nozzle_temp ?? '—'} / ${data.nozzle_target ?? '—'}</span></div>
        <div class="card"><span class="label">Bed</span><span class="value">${data.bed_temp ?? '—'} / ${data.bed_target ?? '—'}</span></div>
        <div class="card"><span class="label">Elapsed</span><span class="value">${data.elapsed_seconds ?? '—'}</span></div>
        <div class="card"><span class="label">Remaining</span><span class="value">${data.remaining_seconds ?? '—'}</span></div>
      `;
    } catch (_error) {
      // keep calm and continue polling
    }
  };
  refresh();
  setInterval(refresh, 3000);
}
