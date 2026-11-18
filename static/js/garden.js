// Garden page frontend controller.
// Handles posts, likes, comments, filters and Plant of the Week.
// Most actions work without reloading the entire page.

const feed = document.getElementById('post-feed');
const postModal = document.getElementById('post-modal');
const postForm = document.getElementById('post-form');


// Sends a POST request with the CSRF token.
// Returns both the HTTP response and the JSON result.
async function send(url, body) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: body,
    });

    const result = await response.json().catch(() => ({}));

    return { response, result };
}


// Displays server errors as toast notifications.
function showServerError(response, result, title) {

    if (response.status === 403) {
        title = 'Not allowed';

    } else if (response.status === 404) {
        title = 'Not found';
    }

    showToast(
        title,
        result.message || 'Please try again.',
        'error'
    );
}


// Handles network connection errors.
function networkError() {
    showToast(
        'Network error',
        'Please check your connection and try again.',
        'error'
    );
}


// Converts server-rendered HTML into a DOM element.
function makeElement(html) {
    const template = document.createElement('template');

    template.innerHTML = html.trim();

    return template.content.firstElementChild;
}


// ---------- Form validation errors ----------


// Clears previous validation messages.
function clearErrors(form) {

    form.querySelectorAll('[data-error-for]').forEach((message) => {
        message.textContent = '';
        message.classList.add('hidden');
    });

    form.querySelectorAll('[aria-invalid]').forEach((input) => {
        input.removeAttribute('aria-invalid');
    });
}


// Displays validation errors returned by Django.
function showErrors(form, errors) {

    for (const [field, fieldErrors] of Object.entries(errors)) {

        const message =
            form.querySelector(`[data-error-for="${field}"]`)
            || form.querySelector('[data-error-for="__all__"]');

        message.textContent = fieldErrors
            .map((error) => error.message)
            .join(' ');

        message.classList.remove('hidden');

        const input = form.elements[field];

        if (input && input.setAttribute) {
            input.setAttribute('aria-invalid', 'true');
        }
    }

    // Move focus to the first invalid field.
    const firstInvalid = form.querySelector('[aria-invalid="true"]');

    if (firstInvalid) {
        firstInvalid.focus();
    }
}


// ---------- Photo upload ----------


// Supported image formats.
const ALLOWED_PHOTO_TYPES = [
    'image/jpeg',
    'image/png',
    'image/webp'
];

// Maximum image size: 2 MB.
const MAX_PHOTO_SIZE = 2 * 1024 * 1024;

let currentPhoto = '';


// Shows or hides the image preview.
function showPhotoBox(src, name) {

    const drop = document.getElementById('photo-drop');
    const preview = document.getElementById('photo-preview');
    const img = document.getElementById('photo-preview-img');

    // Release an old temporary image URL.
    if (img.src.startsWith('blob:')) {
        URL.revokeObjectURL(img.src);
    }

    drop.classList.toggle('hidden', Boolean(src));
    drop.classList.toggle('flex', !src);

    preview.classList.toggle('hidden', !src);
    preview.classList.toggle('flex', Boolean(src));

    img.src = src || '';

    document.getElementById('photo-file-name').textContent =
        name || '';
}


// Displays photo validation errors.
function setPhotoError(text) {

    const message = postForm.querySelector(
        '[data-error-for="photo_upload"]'
    );

    message.textContent = text;
    message.classList.toggle('hidden', !text);
}


// Validates a selected photo before uploading.
function pickPhoto(file) {

    setPhotoError('');

    const input = postForm.elements['photo_upload'];

    if (!file) {
        return;
    }

    // Client-side validation improves user experience.
    // The server performs its own validation as well.
    if (
        !ALLOWED_PHOTO_TYPES.includes(file.type)
        || file.size > MAX_PHOTO_SIZE
    ) {

        input.value = '';

        setPhotoError(
            file.size > MAX_PHOTO_SIZE
                ? 'That photo is too big. Please pick one under 2 MB.'
                : 'Please pick a JPG, PNG or WebP photo.'
        );

        return;
    }

    postForm.elements['remove_photo'].value = '';

    // Create a temporary preview URL.
    showPhotoBox(
        URL.createObjectURL(file),
        file.name
    );
}


// Adds all photo upload event listeners.
function setUpPhotoBox() {

    const input = postForm.elements['photo_upload'];
    const drop = document.getElementById('photo-drop');
    const dropText = document.getElementById('photo-drop-text');

    // Handle normal file selection.
    input.addEventListener('change', () => {
        pickPhoto(input.files[0]);
    });


    // Remove the current photo.
    document.getElementById('photo-remove').addEventListener(
        'click',
        () => {

            input.value = '';

            // Tell the backend to remove the existing photo.
            postForm.elements['remove_photo'].value =
                currentPhoto ? 'True' : '';

            showPhotoBox('', '');
        }
    );


    // Handle drag over.
    drop.addEventListener('dragover', (event) => {

        event.preventDefault();

        drop.dataset.drag = '';

        dropText.textContent = 'Drop to upload';
    });


    // Handle drag leave.
    drop.addEventListener('dragleave', () => {

        delete drop.dataset.drag;

        dropText.textContent = 'Drop a photo or browse';
    });


    // Handle dropped files.
    drop.addEventListener('drop', (event) => {

        event.preventDefault();

        delete drop.dataset.drag;

        dropText.textContent = 'Drop a photo or browse';

        const file = event.dataTransfer.files[0];

        if (!file) {
            return;
        }

        // Put the dropped file into the actual file input.
        const transfer = new DataTransfer();

        transfer.items.add(file);

        input.files = transfer.files;

        pickPhoto(file);
    });
}

// ---------- Share / edit a post ----------


// Stores the card currently being edited.
// null means that the user is creating a new post.
let editingCard = null;


// Updates the selected plant in the dropdown.
function setPlant(plantId) {

    const select = postForm.elements['plant'];

    select.value = plantId || '';

    // Notify the plant picker that the value has changed.
    select.dispatchEvent(
        new Event('change', { bubbles: true })
    );
}


// Opens the post modal for creating or editing.
function openPostForm(card, focus) {

    editingCard = card;

    postForm.reset();

    clearErrors(postForm);

    setPhotoError('');

    postForm.elements['remove_photo'].value = '';

    const title = document.getElementById('post-modal-title');

    const submit = document.getElementById('post-submit');


    if (card) {

        // Editing an existing post.
        title.textContent = 'Edit post';

        submit.textContent = 'Save changes';

        postForm.action = card.dataset.editUrl;

        postForm.elements['caption'].value =
            card.dataset.caption;

        setPlant(card.dataset.plantId);

        currentPhoto = card.dataset.photo;

        showPhotoBox(
            currentPhoto,
            currentPhoto ? 'Current photo' : ''
        );

    } else {

        // Creating a new post.
        title.textContent = 'Share your garden';

        submit.textContent = 'Post';

        postForm.action = postForm.dataset.createUrl;

        setPlant('');

        currentPhoto = '';

        showPhotoBox('', '');
    }


    // Display the modal.
    postModal.showPopover();


    // Focus the requested field.
    if (focus === 'photo') {

        postForm.elements['photo_upload'].click();

    } else if (focus === 'plant') {

        postForm.elements['plant'].focus();

    } else {

        postForm.elements['caption'].focus();
    }
}


// Submits the post form using AJAX.
async function savePost(event) {

    event.preventDefault();

    const submit = document.getElementById('post-submit');

    submit.disabled = true;

    clearErrors(postForm);

    try {

        // FormData supports both text fields and uploaded files.
        const { response, result } = await send(
            postForm.action,
            new FormData(postForm)
        );


        if (response.ok) {

            const card = makeElement(result.html);

            if (editingCard) {

                // Replace the old card after editing.
                editingCard.replaceWith(card);

                showToast(
                    'Post updated',
                    'Your changes are saved.'
                );

            } else {

                // Remove the empty state if it exists.
                feed.querySelector('[data-empty-feed]')?.remove();

                // Add the newest post at the beginning.
                feed.prepend(card);

                showToast(
                    'Post shared',
                    'Your garden is on the feed.'
                );
            }

            postModal.hidePopover();


        } else if (result.errors) {

            // Display Django form validation errors.
            showErrors(postForm, result.errors);

        } else {

            showServerError(
                response,
                result,
                'Could not save'
            );
        }

    } catch (error) {

        networkError();

    } finally {

        // Re-enable the button.
        submit.disabled = false;
    }
}


// Deletes a post after user confirmation.
async function deletePost(card) {

    const confirmed = await confirmDelete({
        title: 'Delete this post?',
        message: "Its likes and comments go too. This can't be undone."
    });

    if (!confirmed) {
        return;
    }

    try {

        const { response, result } = await send(
            card.dataset.deleteUrl
        );

        if (!response.ok) {

            showServerError(
                response,
                result,
                'Could not delete'
            );

            return;
        }

        // Add a fade-out animation before removing the card.
        card.classList.add(
            'opacity-0',
            'scale-[0.98]'
        );

        const wait = window.matchMedia(
            '(prefers-reduced-motion: reduce)'
        ).matches ? 0 : 300;

        setTimeout(() => card.remove(), wait);

        showToast(
            'Post deleted',
            "It's off the Garden feed now."
        );

    } catch (error) {

        networkError();
    }
}

// ---------- Post options menu ----------


// Closes all open menus except the specified one.
function closeMenus(except) {

    document.querySelectorAll('[data-menu]:not([hidden])')
        .forEach((menu) => {

            if (menu !== except) {

                menu.hidden = true;

                menu.previousElementSibling.setAttribute(
                    'aria-expanded',
                    'false'
                );
            }
        });
}


// Opens or closes a post options menu.
function toggleMenu(button) {

    const menu = button.nextElementSibling;

    closeMenus(menu);

    menu.hidden = !menu.hidden;

    button.setAttribute(
        'aria-expanded',
        String(!menu.hidden)
    );

    if (!menu.hidden) {
        menu.querySelector('button').focus();
    }
}


// ---------- Likes ----------


// Adds or removes a like without reloading the page.
async function toggleLike(button) {

    const card = button.closest('[data-post]');

    const count = button.querySelector('[data-like-count]');

    const wasLiked =
        button.getAttribute('aria-pressed') === 'true';


    // Optimistic UI: update the interface immediately.
    button.setAttribute(
        'aria-pressed',
        String(!wasLiked)
    );

    count.textContent =
        Number(count.textContent) + (wasLiked ? -1 : 1);


    // Prepare the request data.
    const body = new FormData();

    body.append('liked', String(!wasLiked));


    try {

        const { response, result } = await send(
            button.dataset.likeUrl,
            body
        );

        if (!response.ok) {

            throw Object.assign(
                new Error('server'),
                { response, result }
            );
        }

        // Use the final values returned by the server.
        button.setAttribute(
            'aria-pressed',
            String(result.liked)
        );

        count.textContent = result.like_count;


    } catch (error) {

        // Roll back the optimistic update if the request fails.
        button.setAttribute(
            'aria-pressed',
            String(wasLiked)
        );

        count.textContent =
            Number(count.textContent) + (wasLiked ? 1 : -1);


        if (error.response) {

            showServerError(
                error.response,
                error.result,
                'Could not like'
            );

        } else if (card.isConnected) {

            networkError();
        }
    }
}


// ---------- Comments ----------


// Loads comments from the backend.
async function loadComments(section, url) {

    const list = section.querySelector('[data-comment-list]');

    list.setAttribute('aria-busy', 'true');

    try {

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`status ${response.status}`);
        }

        // The response contains HTML rendered by Django.
        list.innerHTML = await response.text();

        section.dataset.loaded = 'yes';

    } catch (error) {

        networkError();

    } finally {

        list.removeAttribute('aria-busy');
    }
}


// Shows or hides the comments section.
function toggleComments(button) {

    const section = document.getElementById(
        button.getAttribute('aria-controls')
    );

    section.hidden = !section.hidden;

    button.setAttribute(
        'aria-expanded',
        String(!section.hidden)
    );


    if (!section.hidden) {

        // Load comments only the first time.
        if (!section.dataset.loaded) {

            loadComments(
                section,
                button.dataset.commentsUrl
            );
        }

        section.querySelector(
            'input[name="text"]'
        )?.focus();
    }
}


// Updates the comment counter on the post card.
function setCommentCount(card, count) {

    card.querySelector(
        '[data-comment-count]'
    ).textContent = count;
}


// Sends a new comment to the backend.
async function addComment(form) {

    const card = form.closest('[data-post]');

    const input = form.elements['text'];

    const submit = form.querySelector(
        'button[type="submit"]'
    );


    input.removeAttribute('aria-invalid');


    // Prevent empty comments.
    if (!input.value.trim()) {

        input.setAttribute('aria-invalid', 'true');

        showToast(
            'Empty comment',
            'Please write a comment first.',
            'error'
        );

        input.focus();

        return;
    }


    submit.disabled = true;


    try {

        const { response, result } = await send(
            form.action,
            new FormData(form)
        );


        if (response.ok) {

            const list = card.querySelector(
                '[data-comment-list]'
            );

            // Remove the empty state.
            list.querySelector('[data-no-comments]')?.remove();


            // Keep the Show All button at the end.
            const showAll = list.querySelector(
                '[data-show-all-comments]'
            );

            list.insertBefore(
                makeElement(result.html),
                showAll
            );


            // Update the comment counter.
            setCommentCount(
                card,
                result.comment_count
            );

            form.reset();


        } else if (result.errors) {

            input.setAttribute('aria-invalid', 'true');

            showToast(
                'Could not comment',
                result.errors.text?.[0]?.message
                    || 'Please try again.',
                'error'
            );

        } else {

            showServerError(
                response,
                result,
                'Could not comment'
            );
        }


    } catch (error) {

        networkError();

    } finally {

        submit.disabled = false;

        input.focus();
    }
}


// Deletes an existing comment.
async function deleteComment(button) {

    const confirmed = await confirmDelete({
        title: 'Delete this comment?',
        message: "This can't be undone."
    });

    if (!confirmed) {
        return;
    }


    const card = button.closest('[data-post]');


    try {

        const { response, result } = await send(
            button.dataset.deleteComment
        );

        if (!response.ok) {

            showServerError(
                response,
                result,
                'Could not delete'
            );

            return;
        }


        // Remove the comment from the page.
        button.closest('[data-comment]').remove();


        // Update the counter.
        setCommentCount(
            card,
            result.comment_count
        );

        showToast('Comment deleted');


    } catch (error) {

        networkError();
    }
}

// ---------- Filter pills ----------


// Tracks the latest request to prevent outdated responses.
let latestFeedRequest = 0;


// Builds the URL for the selected filter.
function feedUrl(filter) {

    const params = new URLSearchParams({
        filter: filter
    });

    const plantFilter = document.getElementById(
        'garden-plant-filter'
    );

    // Keep the selected plant when changing categories.
    if (plantFilter) {

        params.set(
            'plant',
            plantFilter.dataset.plant
        );
    }

    return '?' + params.toString();
}


// Loads the selected feed without reloading the whole page.
async function loadFeed(filter, history) {

    const url = feedUrl(filter);

    const requestId = ++latestFeedRequest;


    // Update the active filter button.
    document.querySelectorAll(
        '#garden-filter-pills [data-filter]'
    ).forEach((pill) => {

        if (pill.dataset.filter === filter) {

            pill.setAttribute(
                'aria-current',
                'page'
            );

        } else {

            pill.removeAttribute('aria-current');
        }
    });


    // Update browser history.
    if (history === 'push') {

        window.history.pushState(
            null,
            '',
            url
        );
    }


    feed.setAttribute('aria-busy', 'true');


    try {

        // Request only the feed HTML partial.
        const response = await fetch(
            url + '&partial=1'
        );

        if (!response.ok) {
            throw new Error(`status ${response.status}`);
        }

        const html = await response.text();


        // Only the newest request is allowed to update the feed.
        if (requestId === latestFeedRequest) {

            feed.innerHTML = html;
        }


    } catch (error) {

        if (requestId === latestFeedRequest) {

            // Fall back to a normal page load.
            window.location.href = url;
        }

    } finally {

        if (requestId === latestFeedRequest) {

            feed.removeAttribute('aria-busy');
        }
    }
}


// Handle browser Back and Forward buttons.
window.addEventListener('popstate', () => {

    loadFeed(
        new URLSearchParams(
            window.location.search
        ).get('filter') || 'all',

        'none'
    );
});


// ---------- Plant of the Week ----------


// This form exists only for moderators.
const weekForm = document.getElementById('week-form');


// Saves the moderator's Plant of the Week selection.
async function saveWeekPlant(event) {

    event.preventDefault();

    const submit = weekForm.querySelector(
        'button[type="submit"]'
    );

    submit.disabled = true;

    clearErrors(weekForm);


    try {

        const { response, result } = await send(
            weekForm.action,
            new FormData(weekForm)
        );


        if (response.ok) {

            // Replace the old sidebar with the updated HTML.
            document.getElementById(
                'plant-of-the-week'
            ).replaceWith(
                makeElement(result.html)
            );


            document.getElementById(
                'week-modal'
            ).hidePopover();


            showToast(
                'Plant of the week saved',
                'Everyone sees it on the Garden page now.'
            );


        } else if (result.errors) {

            showErrors(
                weekForm,
                result.errors
            );

        } else {

            showServerError(
                response,
                result,
                'Could not save'
            );
        }


    } catch (error) {

        networkError();

    } finally {

        submit.disabled = false;
    }
}

// ---------- Global event listeners ----------


// Event delegation:
// One document listener handles buttons, including dynamically added posts.
document.addEventListener('click', (event) => {

    const target = event.target;


    // Open the create-post modal.
    const openForm = target.closest('[data-open-post-form]');

    if (openForm && postForm) {

        openPostForm(
            null,
            openForm.dataset.openPostForm
        );

        return;
    }


    // Open or close the post options menu.
    const menuButton = target.closest('[data-menu-button]');

    if (menuButton) {

        toggleMenu(menuButton);

        return;
    }


    // Close menus when clicking outside.
    if (!target.closest('[data-menu]')) {

        closeMenus(null);
    }


    // Edit an existing post.
    const editButton = target.closest('[data-edit-post]');

    if (editButton) {

        closeMenus(null);

        openPostForm(
            editButton.closest('[data-post]')
        );

        return;
    }


    // Delete a post.
    const deleteButton = target.closest('[data-delete-post]');

    if (deleteButton) {

        closeMenus(null);

        deletePost(
            deleteButton.closest('[data-post]')
        );

        return;
    }


    // Like or unlike a post.
    const likeButton = target.closest('[data-like-url]');

    if (likeButton) {

        toggleLike(likeButton);

        return;
    }


    // Expand or collapse comments.
    const commentsButton = target.closest('[data-comments-url]');

    if (commentsButton) {

        toggleComments(commentsButton);

        return;
    }


    // Load all comments.
    const showAll = target.closest('[data-show-all-comments]');

    if (showAll) {

        loadComments(
            showAll.closest('[data-comments]'),
            showAll.dataset.showAllComments
        );

        return;
    }


    // Delete a comment.
    const deleteCommentButton = target.closest(
        '[data-delete-comment]'
    );

    if (deleteCommentButton) {

        deleteComment(deleteCommentButton);

        return;
    }


    // Handle category filter clicks.
    const pill = target.closest('a[data-filter]');


    // Preserve normal browser behaviour for Ctrl/Cmd/Shift clicks.
    if (
        pill
        && !event.ctrlKey
        && !event.metaKey
        && !event.shiftKey
    ) {

        event.preventDefault();

        loadFeed(
            pill.dataset.filter,
            'push'
        );
    }

});


// Close an open menu when the user presses Escape.
document.addEventListener('keydown', (event) => {

    if (event.key !== 'Escape') {
        return;
    }

    const open = document.querySelector(
        '[data-menu]:not([hidden])'
    );

    if (open) {

        closeMenus(null);

        open.previousElementSibling.focus();
    }
});


// Handle comment form submissions.
document.addEventListener('submit', (event) => {

    if (event.target.matches('[data-comment-form]')) {

        event.preventDefault();

        addComment(event.target);
    }
});


// Initialize the post form only if it exists.
if (postForm) {

    postForm.addEventListener(
        'submit',
        savePost
    );

    setUpPhotoBox();
}


// Initialize the moderator form only if it exists.
if (weekForm) {

    weekForm.addEventListener(
        'submit',
        saveWeekPlant
    );
}