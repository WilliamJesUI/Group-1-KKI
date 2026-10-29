(() => {
    const editForm = document.getElementById('edit-question-form');
    const deleteBtn = document.getElementById('delete-question-btn');
    const modal = document.getElementById('edit-question-modal');

    function errorTitle(status, fallback) {
        if (status === 403) return 'Not allowed';
        if (status === 409) return 'Already answered';
        if (status === 404) return 'Not found';
        return fallback;
    }

    if (editForm) {
        editForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const submitButton = editForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            try {
                const response = await fetch(editForm.dataset.endpoint, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') },
                    body: new FormData(editForm),
                });
                const result = await response.json().catch(() => ({}));

                if (!response.ok) {
                    showToast(errorTitle(response.status, 'Could not save'),
                              result.message || 'Please try again.', 'error');
                    return;
                }
                if (modal && modal.matches(':popover-open')) modal.hidePopover();
                window.location.href = result.url; // success toast comes from messages.success
            } catch (error) {
                console.error('Error updating question:', error);
                showToast('Network error', 'Please check your connection and try again.', 'error');
            } finally {
                submitButton.disabled = false;
            }
        });
    }

    if (deleteBtn) {
        deleteBtn.addEventListener('click', async () => {
            if (!await confirmDelete({ title: 'Delete this question?', message: "This can't be undone." })) return;
            deleteBtn.disabled = true;
            try {
                const response = await fetch(deleteBtn.dataset.endpoint, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') },
                });
                const result = await response.json().catch(() => ({}));

                if (!response.ok) {
                    showToast(errorTitle(response.status, 'Could not delete'),
                              result.message || 'Please try again.', 'error');
                    deleteBtn.disabled = false;
                    return;
                }
                window.location.href = result.url; // toast shows on the list page
            } catch (error) {
                console.error('Error deleting question:', error);
                showToast('Network error', 'Please check your connection and try again.', 'error');
                deleteBtn.disabled = false;
            }
        });
    }
})();