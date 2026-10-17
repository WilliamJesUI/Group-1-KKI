// Toast notifications (Figma "Toast"): a small box in the bottom-right with a bold title and an optional
// smaller message under it. It hides itself after 3 seconds.
// Use from any page, in the same order as Tutorial 5:
//   showToast('Event published', 'You can find it on the Events page.')
//   showToast('Could not save', 'Please try again.', 'error')
// Django messages are shown as toasts automatically, see base.html.
// More info: docs/TEAM-GUIDE.md

const TOAST_VISIBLE_MS = 3000;

// Makes one line of the toast. textContent, not innerHTML, so the text can't inject HTML.
function makeToastLine(className, text) {
    const line = document.createElement('p');
    line.className = className; // .toast-title and .toast-message are defined in base.html
    line.textContent = text;
    return line;
}

function showToast(title, message = '', type = 'success') {
    const area = document.getElementById('toast-area');
    const toast = document.createElement('div');
    toast.className = type === 'error' ? 'toast toast-error' : 'toast';
    toast.append(makeToastLine('toast-title', title));
    if (message) {
        toast.append(makeToastLine('toast-message', message));
    }
    area.append(toast);

    // Slide up 8px and fade in (250ms). With reduced motion: fade only, no sliding.
    // Browsers without animate() just show and hide the toast without animation.
    const canAnimate = typeof toast.animate === 'function';
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const hidden = reduceMotion ? { opacity: 0 } : { opacity: 0, transform: 'translateY(8px)' };
    const shown = reduceMotion ? { opacity: 1 } : { opacity: 1, transform: 'translateY(0)' };
    if (canAnimate) {
        toast.animate([hidden, shown], { duration: 250, easing: 'ease-out' });
    }

    setTimeout(() => {
        if (canAnimate) {
            toast.animate([shown, hidden], { duration: 250, easing: 'ease-in', fill: 'forwards' });
        }
        // A plain timer removes it, so it goes away even if the animation never runs (for example in a background tab)
        setTimeout(() => toast.remove(), 250);
    }, TOAST_VISIBLE_MS);
}

// Show the Django messages that base.html put on the page as data-toast-message attributes.
// Reading them from HTML attributes (instead of writing them into a script) means Django has already escaped them.
// A message can be "Title\nMessage": the first line break splits it. Without one, the whole text is the title.
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-toast-message]').forEach((item) => {
        const text = item.dataset.toastMessage;
        const lineBreak = text.indexOf('\n');
        if (lineBreak === -1) {
            showToast(text, '', item.dataset.toastType);
        } else {
            showToast(text.slice(0, lineBreak), text.slice(lineBreak + 1), item.dataset.toastType);
        }
        item.remove();
    });
});
