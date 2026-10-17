// RSVP buttons (templates: events/templates/event_rsvp_button.html).
// One click listener for the whole page, so it works for every RSVP button, wherever it is.
// getCookie comes from static/js/csrf.js.

const AVATAR_COLORS = ['bg-lilac', 'bg-pink', 'bg-butter', 'bg-brand-soft'];
const AVATAR_CLASS = 'flex size-10 items-center justify-center rounded-full border-2 border-ink text-xs font-bold';

// Make an avatar circle like the ones in event_detail.html
function makeAvatar(text, colorClass, overlap) {
    const avatar = document.createElement('span');
    avatar.className = `${overlap ? '-mr-2 ' : ''}${AVATAR_CLASS} ${colorClass}`;
    avatar.textContent = text; // textContent, not innerHTML, so names can't inject HTML
    return avatar;
}

// Update every "N going" and avatar row on the page for this event
function updateGoing(eventId, result) {
    document.querySelectorAll(`[data-going-count="${eventId}"]`).forEach((count) => {
        count.textContent = result.going_count;
    });
    document.querySelectorAll(`[data-attendee-avatars="${eventId}"]`).forEach((row) => {
        row.replaceChildren(); // remove the old avatars
        result.attendee_initials.forEach((initials, i) => {
            row.append(makeAvatar(initials, AVATAR_COLORS[i % AVATAR_COLORS.length], true));
        });
        if (result.more_going > 0) {
            row.append(makeAvatar(`+${result.more_going}`, 'bg-lilac', false));
        }
        row.classList.toggle('hidden', result.attendee_initials.length === 0);
    });
}

// The Figma "pop": 1 -> 1.2 -> 1 in 300ms. Skipped for people who turned on reduced motion.
function pop(button) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return;
    }
    button.animate(
        [{ transform: 'scale(1)' }, { transform: 'scale(1.2)' }, { transform: 'scale(1)' }],
        { duration: 300, easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)' },
    );
}

async function sendRsvp(button) {
    const error = button.closest('[data-rsvp]').querySelector('[data-rsvp-error]');
    const wantsToGo = button.getAttribute('aria-pressed') !== 'true';
    const body = new FormData();
    body.append('going', wantsToGo ? 'true' : 'false');

    // Disabling the button sends keyboard focus back to the page, so remember if it had focus
    const hadFocus = document.activeElement === button;
    button.disabled = true; // so a double click doesn't send twice
    error.classList.add('hidden');
    try {
        const response = await fetch(button.dataset.rsvpUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: body,
        });
        const result = await response.json().catch(() => ({}));
        if (response.ok) {
            // Every RSVP button for this event (e.g. on a card and in "Next up") shows the new state
            document.querySelectorAll(`[data-rsvp-url][data-event-id="${button.dataset.eventId}"]`).forEach((other) => {
                other.setAttribute('aria-pressed', result.going ? 'true' : 'false');
            });
            updateGoing(button.dataset.eventId, result);
            pop(button);
            showToast(result.going ? "You're going" : 'RSVP cancelled'); // from static/js/toast.js
        } else {
            error.textContent = result.message || `Something went wrong (status ${response.status}).`;
            error.classList.remove('hidden');
        }
    } catch (err) {
        error.textContent = 'Could not reach the server. Please try again.';
        error.classList.remove('hidden');
    } finally {
        button.disabled = false;
        if (hadFocus) {
            button.focus(); // so Tab keeps going from the RSVP button
        }
    }
}

document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-rsvp-url]');
    if (button) {
        event.preventDefault();
        sendRsvp(button);
    }
});
