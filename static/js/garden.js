// Garden page (garden/templates/garden/garden.html). Everything here works without reloading the page:
// share / edit / delete posts, likes, comments, the filter pills and the admin's Plant of the week.
// Errors from the server come back as JSON { message } or { errors } and are shown as toasts or under the field.

const feed = document.getElementById('post-feed');
const postModal = document.getElementById('post-modal'); // only there when logged in
const postForm = document.getElementById('post-form');

// POST with the csrf token. Gives back the response and its JSON (or {} if it wasn't JSON).
async function send(url, body) {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }, // getCookie comes from static/js/csrf.js
        body: body,
    });
    const result = await response.json().catch(() => ({}));
    return { response, result };
}

function showServerError(response, result, title) {
    if (response.status === 403) {
        title = 'Not allowed';
    } else if (response.status === 404) {
        title = 'Not found';
    }
    showToast(title, result.message || 'Please try again.', 'error');
}

function networkError() {
    showToast('Network error', 'Please check your connection and try again.', 'error');
}

// Turns a card's HTML from the server into an element
function makeElement(html) {
    const template = document.createElement('template');
    template.innerHTML = html.trim(); // made by a Django template, so the text in it is already escaped
    return template.content.firstElementChild;
}

// ---------- Form errors under each field (same as the Events pop-up) ----------

function clearErrors(form) {
    form.querySelectorAll('[data-error-for]').forEach((message) => {
        message.textContent = '';
        message.classList.add('hidden');
    });
    form.querySelectorAll('[aria-invalid]').forEach((input) => input.removeAttribute('aria-invalid'));
}

// errors looks like { caption: [{ message: "Please write a caption." }] }
function showErrors(form, errors) {
    for (const [field, fieldErrors] of Object.entries(errors)) {
        const message = form.querySelector(`[data-error-for="${field}"]`) || form.querySelector('[data-error-for="__all__"]');
        message.textContent = fieldErrors.map((error) => error.message).join(' ');
        message.classList.remove('hidden');
        const input = form.elements[field];
        if (input && input.setAttribute) {
            input.setAttribute('aria-invalid', 'true');
        }
    }
    const firstInvalid = form.querySelector('[aria-invalid="true"]');
    if (firstInvalid) {
        firstInvalid.focus();
    }
}

// ---------- Photo box in the post pop-up ----------

const ALLOWED_PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_PHOTO_SIZE = 2 * 1024 * 1024; // 2 MB, same limit as the server
let currentPhoto = ''; // when editing: the post's photo before any change

function showPhotoBox(src, name) {
    const drop = document.getElementById('photo-drop');
    const preview = document.getElementById('photo-preview');
    const img = document.getElementById('photo-preview-img');
    if (img.src.startsWith('blob:')) {
        URL.revokeObjectURL(img.src); // free the old temporary link
    }
    drop.classList.toggle('hidden', Boolean(src));
    drop.classList.toggle('flex', !src);
    preview.classList.toggle('hidden', !src);
    preview.classList.toggle('flex', Boolean(src));
    img.src = src || '';
    document.getElementById('photo-file-name').textContent = name || '';
}

function setPhotoError(text) {
    const message = postForm.querySelector('[data-error-for="photo_upload"]');
    message.textContent = text;
    message.classList.toggle('hidden', !text);
}

function pickPhoto(file) {
    setPhotoError('');
    const input = postForm.elements['photo_upload'];
    if (!file) {
        return;
    }
    // Quick check so people don't wait for the server. The server checks again for real.
    if (!ALLOWED_PHOTO_TYPES.includes(file.type) || file.size > MAX_PHOTO_SIZE) {
        input.value = '';
        setPhotoError(file.size > MAX_PHOTO_SIZE ? 'That photo is too big. Please pick one under 2 MB.' : 'Please pick a JPG, PNG or WebP photo.');
        return;
    }
    postForm.elements['remove_photo'].value = '';
    showPhotoBox(URL.createObjectURL(file), file.name);
}

function setUpPhotoBox() {
    const input = postForm.elements['photo_upload'];
    const drop = document.getElementById('photo-drop');
    const dropText = document.getElementById('photo-drop-text');

    input.addEventListener('change', () => pickPhoto(input.files[0]));
    document.getElementById('photo-remove').addEventListener('click', () => {
        input.value = '';
        // Tells the server to delete the photo the post already has
        postForm.elements['remove_photo'].value = currentPhoto ? 'True' : '';
        showPhotoBox('', '');
    });
    drop.addEventListener('dragover', (event) => {
        event.preventDefault(); // otherwise the browser opens the photo in the tab
        drop.dataset.drag = '';
        dropText.textContent = 'Drop to upload';
    });
    drop.addEventListener('dragleave', () => {
        delete drop.dataset.drag;
        dropText.textContent = 'Drop a photo or browse';
    });
    drop.addEventListener('drop', (event) => {
        event.preventDefault();
        delete drop.dataset.drag;
        dropText.textContent = 'Drop a photo or browse';
        const file = event.dataTransfer.files[0];
        if (!file) {
            return;
        }
        // Put the dropped file into the real file input, so it's sent with the form
        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
        pickPhoto(file);
    });
}

// ---------- Share / edit a post ----------

let editingCard = null; // the card being edited, or null when sharing a new post

function setPlant(plantId) {
    const select = postForm.elements['plant'];
    select.value = plantId || '';
    select.dispatchEvent(new Event('change', { bubbles: true })); // plant_picker.js redraws itself on 'change'
}

// focus: 'photo' or 'plant' from the composer's Photo / Tag plant buttons
function openPostForm(card, focus) {
    editingCard = card;
    postForm.reset();
    clearErrors(postForm);
    setPhotoError('');
    postForm.elements['remove_photo'].value = '';
    const title = document.getElementById('post-modal-title');
    const submit = document.getElementById('post-submit');

    if (card) {
        // Figma C "Edit post": the same pop-up, filled in with the post
        title.textContent = 'Edit post';
        submit.textContent = 'Save changes';
        postForm.action = card.dataset.editUrl;
        postForm.elements['caption'].value = card.dataset.caption;
        setPlant(card.dataset.plantId);
        currentPhoto = card.dataset.photo;
        showPhotoBox(currentPhoto, currentPhoto ? 'Current photo' : '');
    } else {
        title.textContent = 'Share your garden';
        submit.textContent = 'Post';
        postForm.action = postForm.dataset.createUrl;
        setPlant('');
        currentPhoto = '';
        showPhotoBox('', '');
    }
    postModal.showPopover();
    if (focus === 'photo') {
        postForm.elements['photo_upload'].click(); // opens the file chooser right away
    } else if (focus === 'plant') {
        postForm.elements['plant'].focus();
    } else {
        postForm.elements['caption'].focus();
    }
}

async function savePost(event) {
    event.preventDefault();
    const submit = document.getElementById('post-submit');
    submit.disabled = true;
    clearErrors(postForm);
    try {
        const { response, result } = await send(postForm.action, new FormData(postForm));
        if (response.ok) {
            const card = makeElement(result.html);
            if (editingCard) {
                editingCard.replaceWith(card);
                showToast('Post updated', 'Your changes are saved.');
            } else {
                feed.querySelector('[data-empty-feed]')?.remove();
                feed.prepend(card); // newest first, like the feed
                showToast('Post shared', 'Your garden is on the feed.'); // Figma "Toast post"
            }
            postModal.hidePopover();
        } else if (result.errors) {
            showErrors(postForm, result.errors);
        } else {
            showServerError(response, result, 'Could not save');
        }
    } catch (error) {
        networkError();
    } finally {
        submit.disabled = false;
    }
}

async function deletePost(card) {
    if (!await confirmDelete({ title: 'Delete this post?', message: "Its likes and comments go too. This can't be undone." })) {
        return;
    }
    try {
        const { response, result } = await send(card.dataset.deleteUrl);
        if (!response.ok) {
            showServerError(response, result, 'Could not delete');
            return;
        }
        // Fade out, then remove (motion-safe: skipped when reduced motion is on)
        card.classList.add('opacity-0', 'scale-[0.98]');
        const wait = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 300;
        setTimeout(() => card.remove(), wait);
        showToast('Post deleted', "It's off the Garden feed now.");
    } catch (error) {
        networkError();
    }
}

// ---------- ••• menu ----------

function closeMenus(except) {
    document.querySelectorAll('[data-menu]:not([hidden])').forEach((menu) => {
        if (menu !== except) {
            menu.hidden = true;
            menu.previousElementSibling.setAttribute('aria-expanded', 'false');
        }
    });
}

function toggleMenu(button) {
    const menu = button.nextElementSibling;
    closeMenus(menu);
    menu.hidden = !menu.hidden;
    button.setAttribute('aria-expanded', String(!menu.hidden));
    if (!menu.hidden) {
        menu.querySelector('button').focus();
    }
}

// ---------- Likes ----------

async function toggleLike(button) {
    const card = button.closest('[data-post]');
    const count = button.querySelector('[data-like-count]');
    const wasLiked = button.getAttribute('aria-pressed') === 'true';
    // Optimistic: change the heart right away, and put it back if the server says no
    button.setAttribute('aria-pressed', String(!wasLiked));
    count.textContent = Number(count.textContent) + (wasLiked ? -1 : 1);
    const body = new FormData();
    body.append('liked', String(!wasLiked));
    try {
        const { response, result } = await send(button.dataset.likeUrl, body);
        if (!response.ok) {
            throw Object.assign(new Error('server'), { response, result });
        }
        // The server's numbers win, in case someone else liked it meanwhile
        button.setAttribute('aria-pressed', String(result.liked));
        count.textContent = result.like_count;
    } catch (error) {
        button.setAttribute('aria-pressed', String(wasLiked));
        count.textContent = Number(count.textContent) + (wasLiked ? 1 : -1);
        if (error.response) {
            showServerError(error.response, error.result, 'Could not like');
        } else if (card.isConnected) {
            networkError();
        }
    }
}

// ---------- Comments ----------

async function loadComments(section, url) {
    const list = section.querySelector('[data-comment-list]');
    list.setAttribute('aria-busy', 'true');
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`status ${response.status}`);
        }
        list.innerHTML = await response.text(); // made by a Django template, so already escaped
        section.dataset.loaded = 'yes';
    } catch (error) {
        networkError();
    } finally {
        list.removeAttribute('aria-busy');
    }
}

function toggleComments(button) {
    const section = document.getElementById(button.getAttribute('aria-controls'));
    section.hidden = !section.hidden;
    button.setAttribute('aria-expanded', String(!section.hidden));
    if (!section.hidden) {
        if (!section.dataset.loaded) {
            loadComments(section, button.dataset.commentsUrl);
        }
        section.querySelector('input[name="text"]')?.focus();
    }
}

function setCommentCount(card, count) {
    card.querySelector('[data-comment-count]').textContent = count;
}

async function addComment(form) {
    const card = form.closest('[data-post]');
    const input = form.elements['text'];
    const submit = form.querySelector('button[type="submit"]');
    input.removeAttribute('aria-invalid');
    if (!input.value.trim()) {
        input.setAttribute('aria-invalid', 'true');
        showToast('Empty comment', 'Please write a comment first.', 'error');
        input.focus();
        return;
    }
    submit.disabled = true;
    try {
        const { response, result } = await send(form.action, new FormData(form));
        if (response.ok) {
            const list = card.querySelector('[data-comment-list]');
            list.querySelector('[data-no-comments]')?.remove();
            // Before "Show all", so the newest comment is at the bottom of the shown ones
            const showAll = list.querySelector('[data-show-all-comments]');
            list.insertBefore(makeElement(result.html), showAll);
            setCommentCount(card, result.comment_count);
            form.reset();
        } else if (result.errors) {
            input.setAttribute('aria-invalid', 'true');
            showToast('Could not comment', result.errors.text?.[0]?.message || 'Please try again.', 'error');
        } else {
            showServerError(response, result, 'Could not comment');
        }
    } catch (error) {
        networkError();
    } finally {
        submit.disabled = false;
        input.focus();
    }
}

async function deleteComment(button) {
    if (!await confirmDelete({ title: 'Delete this comment?', message: "This can't be undone." })) {
        return;
    }
    const card = button.closest('[data-post]');
    try {
        const { response, result } = await send(button.dataset.deleteComment);
        if (!response.ok) {
            showServerError(response, result, 'Could not delete');
            return;
        }
        button.closest('[data-comment]').remove();
        setCommentCount(card, result.comment_count);
        showToast('Comment deleted');
    } catch (error) {
        networkError();
    }
}

// ---------- Filter pills (same idea as Events, static/js/event_filters.js) ----------

let latestFeedRequest = 0; // so an old, slow response can't replace a newer one

function feedUrl(filter) {
    const params = new URLSearchParams({ filter: filter });
    const plantFilter = document.getElementById('garden-plant-filter');
    if (plantFilter) {
        params.set('plant', plantFilter.dataset.plant); // keep the plant filter when switching pills
    }
    return '?' + params.toString();
}

async function loadFeed(filter, history) {
    const url = feedUrl(filter);
    const requestId = ++latestFeedRequest;
    document.querySelectorAll('#garden-filter-pills [data-filter]').forEach((pill) => {
        if (pill.dataset.filter === filter) {
            pill.setAttribute('aria-current', 'page');
        } else {
            pill.removeAttribute('aria-current');
        }
    });
    if (history === 'push') {
        window.history.pushState(null, '', url);
    }
    feed.setAttribute('aria-busy', 'true');
    try {
        // &partial=1 only goes to the server, so refresh and the back button load the full page
        const response = await fetch(url + '&partial=1');
        if (!response.ok) {
            throw new Error(`status ${response.status}`);
        }
        const html = await response.text();
        if (requestId === latestFeedRequest) {
            feed.innerHTML = html;
        }
    } catch (error) {
        if (requestId === latestFeedRequest) {
            window.location.href = url; // fall back to a normal page load
        }
    } finally {
        if (requestId === latestFeedRequest) {
            feed.removeAttribute('aria-busy');
        }
    }
}

window.addEventListener('popstate', () => {
    loadFeed(new URLSearchParams(window.location.search).get('filter') || 'all', 'none');
});

// ---------- Plant of the week (moderators only) ----------

const weekForm = document.getElementById('week-form');

async function saveWeekPlant(event) {
    event.preventDefault();
    const submit = weekForm.querySelector('button[type="submit"]');
    submit.disabled = true;
    clearErrors(weekForm);
    try {
        const { response, result } = await send(weekForm.action, new FormData(weekForm));
        if (response.ok) {
            document.getElementById('plant-of-the-week').replaceWith(makeElement(result.html));
            document.getElementById('week-modal').hidePopover();
            showToast('Plant of the week saved', 'Everyone sees it on the Garden page now.');
        } else if (result.errors) {
            showErrors(weekForm, result.errors);
        } else {
            showServerError(response, result, 'Could not save');
        }
    } catch (error) {
        networkError();
    } finally {
        submit.disabled = false;
    }
}

// ---------- One click and one submit listener for the whole page ----------
// Listening on the document means cards added later (new posts, filtered feeds) work too.

document.addEventListener('click', (event) => {
    const target = event.target;
    const openForm = target.closest('[data-open-post-form]');
    if (openForm && postForm) {
        openPostForm(null, openForm.dataset.openPostForm);
        return;
    }
    const menuButton = target.closest('[data-menu-button]');
    if (menuButton) {
        toggleMenu(menuButton);
        return;
    }
    if (!target.closest('[data-menu]')) {
        closeMenus(null); // a click anywhere else closes an open ••• menu
    }
    const editButton = target.closest('[data-edit-post]');
    if (editButton) {
        closeMenus(null);
        openPostForm(editButton.closest('[data-post]'));
        return;
    }
    const deleteButton = target.closest('[data-delete-post]');
    if (deleteButton) {
        closeMenus(null);
        deletePost(deleteButton.closest('[data-post]'));
        return;
    }
    const likeButton = target.closest('[data-like-url]');
    if (likeButton) {
        toggleLike(likeButton);
        return;
    }
    const commentsButton = target.closest('[data-comments-url]');
    if (commentsButton) {
        toggleComments(commentsButton);
        return;
    }
    const showAll = target.closest('[data-show-all-comments]');
    if (showAll) {
        loadComments(showAll.closest('[data-comments]'), showAll.dataset.showAllComments);
        return;
    }
    const deleteCommentButton = target.closest('[data-delete-comment]');
    if (deleteCommentButton) {
        deleteComment(deleteCommentButton);
        return;
    }
    const pill = target.closest('a[data-filter]');
    // Let Ctrl/Cmd/Shift-click open the link in a new tab like normal
    if (pill && !event.ctrlKey && !event.metaKey && !event.shiftKey) {
        event.preventDefault();
        loadFeed(pill.dataset.filter, 'push');
    }
});

// Esc closes an open ••• menu and puts the focus back on its button
document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') {
        return;
    }
    const open = document.querySelector('[data-menu]:not([hidden])');
    if (open) {
        closeMenus(null);
        open.previousElementSibling.focus();
    }
});

document.addEventListener('submit', (event) => {
    if (event.target.matches('[data-comment-form]')) {
        event.preventDefault();
        addComment(event.target);
    }
});

if (postForm) {
    postForm.addEventListener('submit', savePost);
    setUpPhotoBox();
}
if (weekForm) {
    weekForm.addEventListener('submit', saveWeekPlant);
}
