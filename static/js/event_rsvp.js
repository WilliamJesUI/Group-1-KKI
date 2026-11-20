// RSVP buttons (templates: events/templates/event_rsvp_button.html).
// One click listener for the whole page, so it works for every RSVP button, wherever it is.
// getCookie comes from static/js/csrf.js.

const AVATAR_CLASS = 'flex size-10 items-center justify-center rounded-full border-2 border-ink text-xs font-bold';

// Make one avatar from the RSVP answer (avatar_data in events/views.py): the person's photo,
// or their initials on their own color, the same as everywhere else on the site
function makeAvatar(person, sizeClasses) {
    if (person.picture) {
        const photo = document.createElement('img');
        photo.src = person.picture;
        photo.alt = '';
        photo.className = `${sizeClasses} object-cover`;
        return photo;
    }
    const avatar = document.createElement('span');
    avatar.className = `${sizeClasses} ${person.bg_class}`;
    avatar.textContent = person.initials; // textContent, not innerHTML, so names can't inject HTML
    return avatar;
}

// The same avatar as a link to the person's profile (the "who's going" row on the event page).
// -mr-2 goes on the link so the circles still overlap like before.
function makeAvatarLink(person) {
    const avatar = makeAvatar(person, AVATAR_CLASS);
    if (!person.profile_url) {
        avatar.classList.add('-mr-2');
        return avatar;
    }
    const link = document.createElement('a');
    link.href = person.profile_url;
    link.title = person.name;
    link.setAttribute('aria-label', `${person.name}'s profile`);
    link.className = '-mr-2 flex transition-transform duration-150 hover:scale-102';
    link.append(avatar);
    return link;
}

// The "+N" circle for everyone without an avatar
function makeMore(count, sizeClasses) {
    const more = document.createElement('span');
    more.className = sizeClasses;
    more.textContent = `+${count}`;
    return more;
}

// Card footers: up to 2 avatars, a green "+N" for everyone else, or "0 going" when nobody is going.
// .card-avatar is defined in event_card_styles.html, so it's styled right away.
function updateCardAvatars(eventId, result) {
    document.querySelectorAll(`[data-card-avatars="${eventId}"]`).forEach((row) => {
        row.replaceChildren(); // remove the old avatars
        result.attendee_avatars.slice(0, 2).forEach((person) => {
            row.append(makeAvatar(person, 'card-avatar'));
        });
        const more = result.going_count - 2;
        if (more > 0) {
            row.append(makeMore(more, 'card-avatar card-avatar-more'));
        }
        row.classList.toggle('hidden', result.going_count === 0);
    });
    document.querySelectorAll(`[data-going-label="${eventId}"]`).forEach((label) => {
        // "N going" is shown when nobody is going yet, otherwise it's only read out by screen readers
        label.classList.toggle('sr-only', result.going_count > 0);
    });
}

// Update every "N going" and avatar row on the page for this event
function updateGoing(eventId, result) {
    document.querySelectorAll(`[data-going-count="${eventId}"]`).forEach((count) => {
        count.textContent = result.going_count;
    });
    document.querySelectorAll(`[data-attendee-avatars="${eventId}"]`).forEach((row) => {
        row.replaceChildren(); // remove the old avatars
        result.attendee_avatars.forEach((person) => {
            row.append(makeAvatarLink(person));
        });
        if (result.more_going > 0) {
            row.append(makeMore(result.more_going, `${AVATAR_CLASS} bg-lilac`));
        }
        row.classList.toggle('hidden', result.attendee_avatars.length === 0);
    });
    updateCardAvatars(eventId, result);
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
    const wantsToGo = button.getAttribute('aria-pressed') !== 'true';
    const body = new FormData();
    body.append('going', wantsToGo ? 'true' : 'false');

    // Disabling the button sends keyboard focus back to the page, so remember if it had focus
    const hadFocus = document.activeElement === button;
    button.disabled = true; // so a double click doesn't send twice
    let response;
    try {
        response = await fetch(button.dataset.rsvpUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: body,
        });
    } catch (err) {
        // fetch only fails like this when the request never got an answer (offline, server down)
        showToast('Could not reach the server', 'Check your internet and try again.', 'error');
        button.disabled = false;
        if (hadFocus) {
            button.focus();
        }
        return;
    }
    try {
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
            showToast('Could not RSVP', result.message || `Something went wrong (status ${response.status}).`, 'error');
            return;
        }
        // Every RSVP button for this event (e.g. on a card and in "Next up") shows the new state
        document.querySelectorAll(`[data-rsvp-url][data-event-id="${button.dataset.eventId}"]`).forEach((other) => {
            other.setAttribute('aria-pressed', result.going ? 'true' : 'false');
        });
        updateGoing(button.dataset.eventId, result);
        pop(button);
        // showToast(title, message, type) comes from static/js/toast.js
        if (result.going) {
            showToast("You're going", "It's in My events now.");
        } else {
            showToast('RSVP cancelled', "It's no longer in My events.");
        }
    } catch (err) {
        // The RSVP was saved, but drawing the new avatars broke (for example an old copy of this file)
        showToast('Saved, but the page is out of date', 'Please refresh the page.', 'error');
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
