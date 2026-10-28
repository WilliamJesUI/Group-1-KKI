// "Yes, delete" in the Delete event pop-up (event_delete_modal.html).
// Sends the form with fetch instead of reloading the page. On success the server sends back the Events page url,
// and the "Event deleted" toast shows there. On an error the message from the server shows as a red toast.
// getCookie comes from static/js/csrf.js, showToast from static/js/toast.js.

const deleteForm = document.getElementById('delete-event-form');

if (deleteForm) {
    deleteForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const button = deleteForm.querySelector('button[type="submit"]');
        button.disabled = true; // so a double click can't send two requests
        button.textContent = 'Deleting...';

        try {
            const response = await fetch(deleteForm.action, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
            });
            // A 404 page isn't JSON, so fall back to an empty object
            const result = await response.json().catch(() => ({}));
            if (response.ok) {
                window.location.href = result.url;
                return;
            }
            showToast('Could not delete', result.message || 'This event may already be gone. Try refreshing.', 'error');
        } catch {
            showToast('Could not delete', 'Please check your connection and try again.', 'error');
        }

        button.disabled = false;
        button.textContent = 'Yes, delete';
        document.getElementById('delete-event-modal').hidePopover();
    });
}