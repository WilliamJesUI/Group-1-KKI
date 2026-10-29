// "Share guide" style buttons: copy a link and show the Figma "Link copied" toast.
// Use on any page: <button type="button" data-share-url="{{ request.build_absolute_uri }}">Share</button>
// and load this script. showToast comes from toast.js (loaded in base.html).
document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-share-url]');
    if (!button) {
        return;
    }
    try {
        await navigator.clipboard.writeText(button.dataset.shareUrl);
        showToast('Link copied', 'Paste it anywhere to share.');
    } catch (error) {
        // Some browsers block the clipboard (for example on plain http)
        showToast('Could not copy the link', 'Copy it from the address bar instead.', 'error');
    }
});
