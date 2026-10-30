// Sends any <form data-ajax-form> with fetch() instead of reloading the page.
// The view must be wrapped in @ajax_redirects (growyourgarden/permissions.py). It answers with
// {"url": ..., "messages": [...]}. This file then loads that url in the background, copies the
// matching <... data-ajax-region="name"> parts into the page, and shows the messages as toasts.
// Used by Encyclopedia collections (create, rename, delete, save a plant, remove a plant).
// More info: docs/TEAM-GUIDE.md

function showMessagesAsToasts(notes) {
    notes.forEach((note) => {
        // Same as base.html: the title and the message are split at the first line break
        const [title, ...rest] = note.text.split('\n');
        showToast(title, rest.join('\n'), note.level === 'error' ? 'error' : 'success');
    });
}

async function refreshRegions(url) {
    const response = await fetch(url);
    const fresh = new DOMParser().parseFromString(await response.text(), 'text/html');
    let swapped = 0;
    document.querySelectorAll('[data-ajax-region]').forEach((region) => {
        const match = fresh.querySelector(`[data-ajax-region="${region.dataset.ajaxRegion}"]`);
        if (match) {
            // innerHTML, not replaceWith, so other scripts that hold this element (like the search) keep working
            region.innerHTML = match.innerHTML;
            swapped += 1;
        }
    });
    return swapped > 0;
}

document.addEventListener('submit', async (event) => {
    const form = event.target.closest('form[data-ajax-form]');
    // defaultPrevented: the delete pop-up (confirm_delete.js) stopped it first and sends it again after "Delete"
    if (!form || event.defaultPrevented) return;
    event.preventDefault();

    const button = event.submitter;
    if (button) button.disabled = true;
    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
        });
        const data = await response.json();
        if (!(await refreshRegions(data.url))) {
            // The new page has none of these parts (for example a different page), so just go there
            window.location.href = data.url;
            return;
        }
        if (new URL(data.url, window.location.href).pathname === window.location.pathname) {
            history.replaceState(null, '', data.url);
        }
        showMessagesAsToasts(data.messages);
    } catch (error) {
        showToast('Could not save', 'Please try again.', 'error');
    } finally {
        if (button && button.isConnected) button.disabled = false;
    }
});
