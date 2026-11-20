# Team guide: shared stuff

Hi all! This is everything that's already shared between our modules: the base template, the navbar, colors, fonts, icons, toasts and settings. If you change something shared, please update this file too.

## 1. Make a page that uses our layout

Every page should extend `templates/base.html`. You get the navbar, fonts, colors and Tailwind for free.

```html
{% extends 'base.html' %}

{% block title %}Community - Grow Your Garden{% endblock title %}

{% block content %}
<h1 class="font-display text-[32px] leading-tight">Community</h1>
<p class="mt-1.5 text-ink-soft">Ask, answer and help each other grow</p>
{% endblock content %}
```

The blocks you can fill:

| Block | What it's for |
|---|---|
| `title` | Text in the browser tab. If you skip it, it says "Grow Your Garden". |
| `meta` | Extra things for `<head>`. You probably won't need it. |
| `content` | Your page. It's already inside a centered 1180px container with side padding, so don't add your own. |
| `header` | The navbar. You only touch it to hide the navbar, like on the Log in and Register pages (see below). |

To hide the navbar on a page, leave the `header` block empty:

```html
{% block header %}{% endblock header %}
```

Tip: put your templates in `yourapp/templates/` (like `events/templates/event_list.html`). Template names are shared across all apps, so give them names that won't clash. `event_list.html` is fine, `list.html` could clash with someone else's. Also, `base.html` and `header.html` in the root `templates/` folder are taken, and those always win: if you make your own `header.html` (say for the Figma Page Header), Django quietly gives you the navbar instead. Call it something like `community_header.html`.

## 2. Get your navbar tab highlighted

The navbar highlights a tab by looking at `app_name` in your app's `urls.py`. Use exactly one of these names:

| Tab | app_name |
|---|---|
| Garden | `garden` |
| Events | `events` |
| Encyclopedia | `encyclopedia` |
| Community | `community` |
| Achievements | `achievements` |
| Profile | `profile` |

```python
# community/urls.py
from django.urls import path
from community.views import show_questions

app_name = 'community'

urlpatterns = [
    path('', show_questions, name='show_questions'),
]
```

That's it. Every page in your app now highlights your tab, and your views don't have to pass anything extra.

## 3. Link your navbar tab

Right now most tabs link to `#`. When your page exists, open `templates/header.html`, find your tab inside `<nav>` and swap `#` for your URL:

```html
<a href="{% url 'community:show_questions' %}" class="nav-tab {% if app == 'community' %}nav-tab-active{% endif %}">Community</a>
```

Only do this once your URL actually exists. A `{% url %}` that points to a name that doesn't exist breaks every page on the site.

Sarah: the **Log in** and **Register** buttons in the navbar also link to `#` for now. They're in `templates/header.html` too, right after the `<nav>`. Swap them for your auth URLs when they're ready (and a Log out link next to the username would be nice).

The navbar avatar shows the first letter of the user's first_name, or of their username if first_name is empty.

## 4. Colors

The colors come from the Figma Design System page. Use them as Tailwind classes, e.g. `bg-brand`, `text-ink-soft`, `border-line`. Every color works with `bg-`, `text-` and `border-`.

| Class name | Hex | Use it for |
|---|---|---|
| `page` | `#eef0ea` | Page background (already set on `<body>`) |
| `surface` | `#ffffff` | Cards, inputs, pop-ups |
| `brand` | `#17653b` | Main buttons, active tab, brand text and links |
| `brand-hover` | `#0f4d2c` | Main button on hover |
| `brand-soft` | `#beffb8` | Light green boxes, the navbar pill |
| `brand-soft-hover` | `#a6f59f` | Light green on hover |
| `brand-tint` | `#e8f7df` | Very light green, secondary button hover |
| `ink` | `#17241b` | Main text, dark borders, dark buttons |
| `ink-hover` | `#2c3d31` | Dark button on hover |
| `ink-soft` | `#536057` | Secondary text (subtitles, dates) |
| `muted` | `#9aaca2` | Placeholders, very quiet text |
| `line` | `#c1c8c1` | Thin dividers |
| `pink` | `#ffb8b9` | Accent (plant tags, avatars) |
| `lilac` | `#d1d4ff` | Accent |
| `butter` | `#f5e5a8` | Accent |
| `danger` | `#e65e68` | Delete buttons, error borders |
| `danger-hover` | `#cf3f4a` | Delete button on hover |
| `danger-text` | `#c9343f` | Error messages |
| `gold` | `#928935` | Achievement stuff |

You can also add opacity, e.g. `bg-white/65` means white at 65%.

## 5. Fonts

| Class | Font | Use it for |
|---|---|---|
| `font-display` | DM Serif Display | Headings and big numbers |
| `font-sans` | Nunito Sans | Everything else. It's already the default, so you don't need to write it. |

Sizes we use a lot (from Figma):

```html
<h1 class="font-display text-[32px] leading-tight">Page title</h1>
<h2 class="font-display text-2xl">Section title</h2>
<h3 class="font-display text-xl">Card title</h3>
<p class="text-sm text-ink-soft">Normal small text</p>
<span class="text-[11px] font-black uppercase tracking-[0.08em] text-brand">Small label</span>
```

## 6. Copy-paste pieces

These match the Figma components.

**Card**
```html
<div class="rounded-2xl border-2 border-ink bg-surface p-4">
    ...
</div>
```

**Main button (green)**
```html
<a href="#" class="rounded-full border-2 border-ink bg-brand px-6 py-3 text-[15px] font-extrabold text-white hover:bg-brand-hover">Post</a>
```

**Secondary button (white)**
```html
<a href="#" class="rounded-full border-2 border-ink bg-surface px-6 py-3 text-[15px] font-extrabold hover:bg-brand-tint">Cancel</a>
```

**Delete button (red)**
```html
<button class="rounded-full border-2 border-ink bg-danger px-6 py-3 text-[15px] font-extrabold text-white hover:bg-danger-hover">Delete</button>
```

**Text input**
```html
<input type="text" placeholder="e.g. Cherry tomato" class="h-11 w-full rounded-full border-2 border-ink bg-surface px-4 text-sm placeholder:text-muted focus:border-brand focus:ring-1 focus:ring-brand focus:outline-none">
```

If you use a ModelForm, you can put these classes in `widgets` (see `events/forms.py` for an example).

## 7. Phones and tablets

Tailwind classes without a prefix apply to phones. Add `sm:` for 640px and up, and `lg:` for 1024px and up. This matches the breakpoints in Figma.

```html
<!-- 1 column on phones, 2 on tablets, 3 on desktop -->
<div class="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
```

Long links and words that people type (like a pasted Google Form link) wrap onto the next line by themselves, because `<main>` in `base.html` has `wrap-anywhere`, so they won't make your page scroll sideways on a phone.

## 8. Icons and images

Icons from the Figma icon set (Lucide) are in `static/img/icons/`:

`calendar`, `check`, `chevron-right`, `clock`, `image`, `map-pin`, `menu`, `search`, `upload`, `users`, `x`

```html
{% load static %}
<img src="{% static 'img/icons/clock.svg' %}" alt="" width="16" height="16">
```

If you need another icon, export it from the Figma Design System page (Icons section) instead of drawing or generating one. The logo is `static/img/logo-tomato.png`, drawn by William. 

Photos are from Pexels only. Add the credit to docs/CREDITS.md (photographer name + Pexels link).

## 9. Time zone

`TIME_ZONE` is set to `'Asia/Jakarta'` in `settings.py`. Django still saves times in UTC in the database, but it shows them in WIB on the site, and times people type into forms are read as WIB. So:

- Use `timezone.now()` from `django.utils`, not `datetime.now()`.
- `timezone.localdate()` gives today's date in Jakarta.
- In templates, `{{ post.created_at|date:"j M Y" }}` and `{{ post.created_at|time:"H:i" }}` already show WIB.

## 10. Static files and deployment

Shared CSS, JS and images go in the `static/` folder at the project root. WhiteNoise is set up, so they also work on PWS. After you add new static files, PWS picks them up when it runs `collectstatic` during deploy.

If our PWS address ever changes, update it in both `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in settings.py, otherwise every POST (forms and fetch) fails with a 403 on PWS even though it works on localhost.

## 11. Sending data with fetch (AJAX)

Django blocks POST requests that don't carry a CSRF token. For normal forms, `{% csrf_token %}` handles it. For `fetch`, use `getCookie()`. It's in `static/js/csrf.js` and `base.html` already loads it on every page, so don't copy it into your own JS files.

```js
const response = await fetch(url, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
    body: new FormData(form),
});
const result = await response.json().catch(() => ({}));  // {} if the server didn't send JSON, like a 500 error page
```

One gotcha: Django only creates the `csrftoken` cookie once a page with `{% csrf_token %}` has been shown. If your page has no form at all (just buttons that use fetch), add `@ensure_csrf_cookie` to the view that shows the page:

```python
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def show_questions(request):
    ...
```

For a full example of a fetch view and its JS, see `create_event_ajax` in `events/views.py` and `static/js/event_form.js`.

## 12. Toasts (little pop-up messages)

Toasts are the small boxes that pop up in the bottom-right corner and disappear after 3 seconds. Like the Toast in Figma, they have a bold title and an optional smaller message under it, green for success and pink for errors. `base.html` already has everything, so you don't need to add anything to your page.

**From a view (most common).** Use Django's messages. Put the title and the message in one text with `\n` (a line break) between them. The toast shows on the next page the user sees, so it works great right before a redirect:

```python
from django.contrib import messages

def delete_question(request, question_id):
    ...
    question.delete()
    messages.success(request, "Question deleted\nIt's off the Community page now.")
    return redirect("community:show_questions")
```

No `\n` is fine too, then the toast only has a title: `messages.success(request, "Question deleted")`. For an error, use `messages.error(request, "Couldn't save your answer\nPlease try again.")` and it turns pink.

**From JavaScript.** Call `showToast(title, message, type)` (it's in `static/js/toast.js`, loaded on every page). It's the same order as Tutorial 5, so the tutorial's `showToast('Success', 'New project added successfully!', 'success')` works as is:

```js
showToast("Saved to your garden", "You can find it on your Garden page.");
showToast("Something went wrong", "Please try again.", "error");
showToast("Copied!");  // just a title
```

A few things to know:
- Don't print `{{ messages }}` in your own template. `base.html` already shows them, so you'd get them twice.
- If your fetch view redirects the page with JS afterwards (`window.location.href = ...`), you can still use `messages.success` in the view. It shows up on the page you land on.
- `showToast()` works from any script, even one inside your `{% block content %}`.
- Taps go through a toast to whatever is under it, so a toast never blocks a button on phones.
- Toasts appear behind an open popup (popovers sit on top of everything). Show the toast after the popup closes.
- Toasts slide in from the right and slide back out when they leave, like the Figma prototype. People who turned on "reduce motion" get a plain fade instead. That's handled for you.


## 13. "Are you sure?" pop-up before deleting

Don't use the browser's `confirm()` box. It looks different on every browser and doesn't match Figma. Every page already has our own pop-up (`templates/confirm_delete_modal.html`, with the same look and animation as the Events delete pop-up). You open it in one of two ways.

**From JavaScript (AJAX deletes).** `confirmDelete()` waits for the click and gives back `true` for "Yes, delete" and `false` for Cancel, Esc or a click outside. Your function must be `async`:

```js
deleteButton.addEventListener('click', async () => {
    if (!await confirmDelete({ title: 'Delete this answer?', message: "This can't be undone." })) return;
    // ... your fetch() that deletes it ...
});
```

You can change the red button's text too: `confirmDelete({ title: 'Remove Sweet basil?', confirmLabel: 'Yes, remove' })`.

**On a normal form, no JavaScript needed.** Add `data-confirm-title` (and optionally `data-confirm-message`) to the `<form>`. The form is only sent after "Yes, delete":

```html
<form method="post" action="{% url 'encyclopedia:delete_collection' item.id %}"
      data-confirm-title="Delete this collection?"
      data-confirm-message="Only the list goes away. The plants stay in the encyclopedia.">
    {% csrf_token %}
    <button type="submit">Delete</button>
</form>
```

A few things to know:
- "Cancel" is focused when it opens, so pressing Enter never deletes by accident.
- The title and message are shown as plain text, so it's safe to put a user's own text (like a plant or collection name) in them.
- This only asks. Your view must still check the user is allowed to delete (owner or moderator).
## 14. Who can delete what (moderators)

A **moderator** is any account with "Staff status" ticked in `/admin/` (Users, pick the user, tick the box). The rule for the whole site:

- Everyone can edit and delete **their own** posts, comments, answers and so on.
- Moderators can **delete anything** to keep the site clean (spam, rude stuff).
- Moderators **can't edit** other people's words. Delete is fine, rewriting what someone said isn't.
- Admin-only jobs (like picking the Garden "Plant of the week") are moderators only.

The checks live in one place, `growyourgarden/permissions.py`, so every module works the same way:

```python
from growyourgarden.permissions import ajax_login_required, ajax_moderator_required, can_delete, is_moderator

@require_POST
@ajax_login_required("Please log in to delete this.")      # JSON 403 with this message when logged out
def delete_answer(request, answer_id):
    answer = get_object_or_404(Answer, pk=answer_id)
    if not can_delete(request.user, answer.author):         # the author, or a moderator
        return JsonResponse({"message": "You can only delete your own answers."}, status=403)
    answer.delete()
    return JsonResponse({"deleted": True})

@require_POST
@ajax_moderator_required("Only moderators can do this.")    # JSON 403 for everyone else
def pin_post(request, post_id):
    ...
```

In templates, show the Delete button with the same rule. In the view, set it on each item (`item.can_delete = can_delete(request.user, item.author)`) and use `{% if item.can_delete %}` in the template. The `message` in the JSON 403 works with `showToast()` (section 12), so the page can just show it.

### What a moderator can do in each module

| Module | Moderator can | Moderator can't |
| --- | --- | --- |
| Garden | Delete any post or comment, pick the "Plant of the week" | Edit someone else's post |
| Events | Delete any event (the event page shows a "Moderator" box with only Delete) | Edit someone else's event |
| Community | Delete any question (even one that already has answers, the answers go with it) and any answer | Edit someone else's question or answer |
| Encyclopedia | Nothing extra. Saved plants and collections are private to each user | |
| Achievements | Approve badge claims in `/admin/` (a plain staff user also needs the badge permissions ticked under **User permissions**, a superuser has them all) | See or change other people's goals (they're private) |

### How to make someone a moderator

1. Log in to `/admin/` with a superuser account.
2. Go to **Users**, pick the user.
3. Tick **Staff status**, then click **Save**.

No superuser yet? Make one with `python manage.py createsuperuser`. A superuser is staff too, so they're a moderator straight away. Moderating on the site pages only needs Staff status, you don't need to tick any permissions for that.

## 15. The landing page shows your module

The home page at `/` (the `home` app) shows a small preview of every module: the newest Garden posts, the next events, a shelf of plants, the newest questions and the most claimed badges. It reads your tables in `home/services.py`, and only reads, never writes.

- Each part is wrapped in `safely()`. If your table breaks, only your part shows an empty state, the rest of the page still loads.
- If you rename a model field that the landing page uses (for example `Post.image_url`, `Event.start_time`, `Question.title`, `Milestone.icon`), run `python manage.py test home` before you push. Those tests break first and tell you what to fix.
- Your URL names are used there too (`garden:show_garden`, `events:show_event`, `encyclopedia:detail`, `community:show_question_thread`, `achievements:show_achievements`). Keep the names the same.
