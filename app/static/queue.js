const runForm = document.querySelector('#run-order');
const selector = document.querySelector('#case');
const note = document.querySelector('#run-note');
function sourceURL(key) {
  const url = new URL(window.location.href);
  url.searchParams.set('sample', selector.value);
  url.searchParams.delete('key');
  if (key) url.searchParams.set('key', key);
  return url;
}
selector.addEventListener('change', () => window.location.assign(sourceURL()));
runForm.addEventListener('submit', async event => {
  event.preventDefault();
  const action = runForm.querySelector('button');
  action.disabled = true;
  note.hidden = false;
  note.textContent = '正在计算停靠与差价';
  try {
    const response = await fetch('/api/dockets', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({sample:selector.value})});
    const dossier = await response.json();
    if (!response.ok) throw new Error(dossier.message || '原件无法入账');
    const next = sourceURL(dossier.key);
    if (next.href === window.location.href) note.textContent = '已复用同一批次';
    else window.location.assign(next);
  } catch (problem) {
    note.textContent = problem.message || '清算失败，请重试';
  } finally {
    action.disabled = false;
  }
});
const stayPicker = document.querySelector('#stay-picker');
stayPicker?.addEventListener('change', () => {
  for (const pane of document.querySelectorAll('[data-fee-stop]')) {
    pane.hidden = pane.dataset.feeStop !== stayPicker.value;
  }
});
