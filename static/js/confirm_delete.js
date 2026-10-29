// Shared "Are you sure?" pop-up for deleting things (templates/confirm_delete_modal.html).
// Use it instead of the browser's confirm() box, so every module looks the same.
//
// 1) In your own JavaScript (AJAX deletes):
//      if (!await confirmDelete({ title: 'Delete this answer?', message: "This can't be undone." })) return;
//    It waits until the user clicks, then gives back true ("Yes, delete") or false (Cancel, Esc, or a click outside).
//
// 2) On a normal form, no JavaScript needed:
//      <form method="post" action="..." data-confirm-title="Delete this collection?" data-confirm-message="The plants stay.">
//    Submitting the form opens the pop-up first, and only sends the form after "Yes, delete".
//
// More info: docs/TEAM-GUIDE.md

function confirmDelete({ title, message = '', confirmLabel = 'Yes, delete' }) {
    const modal = document.getElementById('confirm-delete-modal');
    const okButton = modal.querySelector('[data-confirm-ok]');
    const cancelButton = modal.querySelector('[data-confirm-cancel]');

    // textContent, not innerHTML, so a title like a plant name can't inject HTML
    modal.querySelector('#confirm-delete-title').textContent = title;
    modal.querySelector('#confirm-delete-message').textContent = message;
    okButton.textContent = confirmLabel;

    return new Promise((resolve) => {
        let answer = false;

        const onOk = () => { answer = true; modal.hidePopover(); };
        const onCancel = () => modal.hidePopover();
        // "toggle" fires when the pop-up closes for any reason (buttons, Esc, click outside)
        const onToggle = (event) => {
            if (event.newState !== 'closed') return;
            okButton.removeEventListener('click', onOk);
            cancelButton.removeEventListener('click', onCancel);
            modal.removeEventListener('toggle', onToggle);
            resolve(answer);
        };

        okButton.addEventListener('click', onOk);
        cancelButton.addEventListener('click', onCancel);
        modal.addEventListener('toggle', onToggle);
        modal.showPopover();
        cancelButton.focus(); // the safe choice is focused, so Enter doesn't delete by accident
    });
}

// Forms with data-confirm-title ask first. Listens on the whole page, so forms added later by AJAX work too.
document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!form.dataset.confirmTitle || form.dataset.confirmed === 'yes') return;
    event.preventDefault();
    const ok = await confirmDelete({ title: form.dataset.confirmTitle, message: form.dataset.confirmMessage || '' });
    if (ok) {
        form.dataset.confirmed = 'yes';
        form.requestSubmit(); // sends it again, and other submit listeners (like AJAX ones) still run
        delete form.dataset.confirmed;
    }
});
