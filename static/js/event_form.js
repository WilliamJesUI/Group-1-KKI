// "Host an event" pop-up: sends the form with fetch and shows errors without reloading the page
const hostEventForm = document.getElementById('host-event-form');

// Read a cookie value, used to get the CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Remove the red borders and messages from the last attempt
function clearErrors() {
    hostEventForm.querySelectorAll('[data-error-for]').forEach((message) => {
        message.textContent = '';
        message.classList.add('hidden');
    });
    hostEventForm.querySelectorAll('[aria-invalid]').forEach((input) => {
        input.removeAttribute('aria-invalid');
    });
}

// Show each error from Django under its field, e.g. { name: [{ message: "Please give your event a name." }] }
function showErrors(errors) {
    for (const [field, fieldErrors] of Object.entries(errors)) {
        const message = hostEventForm.querySelector(`[data-error-for="${field}"]`)
            || hostEventForm.querySelector('[data-error-for="__all__"]');
        message.textContent = fieldErrors.map((error) => error.message).join(' ');
        message.classList.remove('hidden');

        const input = hostEventForm.elements[field];
        if (input) {
            input.setAttribute('aria-invalid', 'true');
        }
    }
}

async function publishEvent(event) {
    event.preventDefault();
    const submitButton = hostEventForm.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    clearErrors();

    try {
        const response = await fetch(hostEventForm.action, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') },
            body: new FormData(hostEventForm),
        });
        const result = await response.json().catch(() => ({}));

        if (response.ok) {
            // Go to the new event's page
            window.location.href = result.url;
        } else if (result.errors) {
            showErrors(result.errors);
        } else {
            showErrors({ __all__: [{ message: result.message || `Something went wrong (status ${response.status}).` }] });
        }
    } catch (error) {
        showErrors({ __all__: [{ message: 'Could not reach the server. Please try again.' }] });
    } finally {
        submitButton.disabled = false;
    }
}

if (hostEventForm) {
    hostEventForm.addEventListener('submit', publishEvent);

    // Open the browser's date and time picker when the field is clicked
    hostEventForm.querySelectorAll('input[type="date"], input[type="time"]').forEach((input) => {
        input.addEventListener('click', () => input.showPicker?.());
    });
}
