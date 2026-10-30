// "Claim badge" without a page reload. The form still works without JavaScript (the view then redirects back).
// The view answers with {"message": "Title\nmessage", "state": "PENDING" | "APPROVED" | ...}.
document.addEventListener('submit', async (event) => {
    const form = event.target.closest('[data-claim-form]');
    if (!form) return;
    event.preventDefault();
    const button = form.querySelector('button');
    button.disabled = true;
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
        });
        const data = await response.json();
        const [title, message = ''] = data.message.split('\n');
        showToast(title, message, response.ok ? 'success' : 'error');
        if (data.state === 'PENDING') {
            // Same pill the page shows for a pending claim after a reload
            const pill = document.createElement('span');
            pill.className = 'shrink-0 rounded-full bg-butter px-3 py-1 text-[11px] font-black uppercase tracking-[0.08em]';
            pill.textContent = 'Pending approval';
            form.replaceWith(pill);
        } else {
            button.disabled = false;
        }
    } catch {
        showToast('Could not claim', 'Please check your connection and try again.', 'error');
        button.disabled = false;
    }
});
