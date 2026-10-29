// Plant picker: turns a plant <select> into a search box with photos.
// Works on every <select data-plant-picker> on the page (PlantSelect in events/forms.py adds that attribute).
// The real <select> stays in the form, hidden, so saving and the error messages in event_form.js still work.
// This file only gives people a nicer way to set the select's value.

const PLANT_ICONS = '/static/img/icons/';
// The list's group headers, and the singular word for the pink tag in the closed field
const PLANT_GROUPS = {
    vegetables: ['Vegetables', 'Vegetable'],
    herbs: ['Herbs', 'Herb'],
    flowers: ['Flowers', 'Flower'],
    other: ['Other plants', 'Plant'],
};
// No photo? Then a soft category color with a Lucide icon (sprout, leaf, flower-2). Never a letter.
const SPROUT = '<path d="M7 20h10"/><path d="M10 20c5.5-2.5.8-6.4 3-10"/><path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z"/><path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/>';
const NO_PHOTO = {
    vegetables: ['bg-butter', SPROUT],
    herbs: ['bg-brand-soft', '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>'],
    flowers: ['bg-pink', '<path d="M12 5a3 3 0 1 1 3 3m-3-3a3 3 0 1 0-3 3m3-3v1M9 8a3 3 0 1 0 3 3M9 8h1m5 0a3 3 0 1 1-3 3m3-3h-1m-2 3v-1"/><circle cx="12" cy="8" r="2"/><path d="M12 10v12"/><path d="M12 22c4.2 0 7-1.667 7-5-4.2 0-7 1.667-7 5Z"/><path d="M12 22c-4.2 0-7-1.667-7-5 4.2 0 7 1.667 7 5Z"/>'],
    other: ['bg-lilac', SPROUT],
};
const svg = (paths, size) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
// Plant names go into HTML, so &, <, > and " are turned into safe codes first
const esc = (text) => text.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

function setUpPlantPicker(select) {
    // Everything the picker shows comes from the <option> tags and their data-* attributes
    const plants = [...select.options].filter((option) => option.value).map((option) => ({
        value: option.value,
        name: option.text.trim(),
        scientific: option.dataset.scientific || '',
        group: option.dataset.category in NO_PHOTO ? option.dataset.category : 'other',
        image: option.dataset.image || '',
    }));
    // An empty first option (like "Choose a theme plant...") means picking nothing is allowed
    const canBeEmpty = select.options[0]?.value === '';
    const emptyLabel = canBeEmpty ? select.options[0].text : 'Choose a plant...';

    // The field: [search icon or chosen photo] [text box] [pink tag] [remove button] [chevron], and the dropdown under it
    const picker = document.createElement('div');
    picker.className = 'group relative';
    picker.innerHTML = `
        <div data-box class="@container flex h-11 cursor-text items-center gap-2 rounded-full border-2 border-ink bg-surface pr-4 pl-1.5 text-sm focus-within:border-brand focus-within:ring-1 focus-within:ring-brand has-aria-invalid:border-danger">
            <span data-thumb class="flex w-7 shrink-0 justify-end"></span>
            <input id="${select.id}_search" type="text" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="${select.id}_list" autocomplete="off" spellcheck="false" class="h-full min-w-0 flex-1 bg-transparent placeholder:text-muted focus:outline-none @sm:group-data-chosen:flex-initial @sm:group-data-chosen:field-sizing-content">
            <span data-tag aria-hidden="true" class="mr-auto hidden shrink-0 rounded-lg bg-pink px-2 py-0.5 text-[11px] font-black uppercase leading-[1.4] tracking-[0.08em] @sm:group-data-chosen:inline-block"></span>
            <button type="button" data-clear hidden aria-label="Remove plant" class="grid size-7 shrink-0 place-items-center rounded-full text-ink-soft hover:bg-page hover:text-ink focus-visible:outline-2 focus-visible:outline-brand">${svg('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>', 14)}</button>
            <span class="pointer-events-none shrink-0 transition-transform duration-150 ease-out group-data-open:rotate-180 motion-reduce:transition-none">${svg('<path d="m6 9 6 6 6-6"/>', 16)}</span>
        </div>
        <div data-panel class="absolute inset-x-0 top-full z-20 mt-1.5 hidden flex-col overflow-hidden rounded-2xl border-2 border-ink bg-surface shadow-[4px_4px_0_0_var(--color-ink)] transition-[opacity,translate,display] transition-discrete duration-150 ease-out group-data-open:flex starting:opacity-0 motion-safe:starting:-translate-y-1 motion-reduce:transition-none">
            <div data-pills class="flex shrink-0 gap-1 overflow-x-auto border-b border-line px-4 py-2.5 [scrollbar-width:none] sm:gap-1.5"></div>
            <div id="${select.id}_list" role="listbox" aria-label="Plants" class="relative max-h-[min(340px,45dvh)] scroll-pt-9 overflow-y-auto overscroll-contain px-1.5 pb-1.5 [scrollbar-width:thin]"></div>
            <div data-empty hidden class="flex flex-col items-center gap-1.5 px-6 pt-6 pb-7 text-center">
                <span class="mb-1.5 grid size-11 place-items-center rounded-full bg-brand-tint"><img src="${PLANT_ICONS}search.svg" alt="" width="20" height="21"></span>
                <p class="font-display text-lg leading-[1.3]">No plants found</p>
                <p data-empty-text class="max-w-[280px] text-xs leading-[1.5] text-ink-soft"></p>
                <button type="button" tabindex="-1" data-reset class="mt-2 rounded-full border-2 border-ink bg-surface px-4 py-2 text-xs font-bold leading-[1.2] hover:bg-brand-tint">Show all plants</button>
            </div>
        </div>
        <p role="status" class="sr-only"></p>`;
    select.before(picker);
    const find = (selector) => picker.querySelector(selector);
    const box = find('[data-box]');
    const thumbSlot = find('[data-thumb]');
    const input = find('input');
    const tag = find('[data-tag]');
    const clearButton = find('[data-clear]');
    const panel = find('[data-panel]');
    const pills = find('[data-pills]');
    const list = find('[role="listbox"]');
    const empty = find('[data-empty]');
    const status = find('[role="status"]');

    // The real <select> goes inside the field, hidden, so has-aria-invalid: still turns the border red on errors
    box.append(select);
    select.classList.add('sr-only');
    select.tabIndex = -1;
    select.setAttribute('aria-hidden', 'true');
    select.addEventListener('focus', () => input.focus()); // event_form.js focuses the first field with an error
    // Copy aria-invalid from the select to the text box, so screen readers hear about the error too
    new MutationObserver(() => input.setAttribute('aria-invalid', select.getAttribute('aria-invalid') || 'false'))
        .observe(select, { attributeFilter: ['aria-invalid'] });
    document.querySelector(`label[for="${select.id}"]`)?.setAttribute('for', input.id);

    let isOpen = false;
    let query = ''; // the typed letters
    let group = ''; // the pressed category pill, '' means All
    let active = null; // the row Enter would pick

    // Category pills, like the Upcoming / This month / My events pills on /events/
    pills.innerHTML = [['', ['All']], ...Object.entries(PLANT_GROUPS).filter(([key]) => plants.some((p) => p.group === key))]
        .map(([key, names]) => `<button type="button" tabindex="-1" data-pill="${key}" aria-pressed="${!key}" class="shrink-0 rounded-full border-2 border-ink bg-surface px-2 py-1 text-xs font-bold leading-[1.2] hover:bg-brand-tint aria-pressed:bg-brand-soft sm:px-3">${names[0]}</button>`).join('');

    // A round photo with an ink ring, or the category icon on its soft color
    const thumb = (plant, big) => `<span data-group="${plant.group}" class="grid ${big ? 'size-10' : 'size-7'} shrink-0 place-items-center overflow-hidden rounded-full border-[1.5px] border-ink ${plant.image ? 'bg-brand-tint' : NO_PHOTO[plant.group][0]}">${plant.image
        ? `<img src="${esc(plant.image)}" alt="" loading="lazy" class="size-full object-cover">` : svg(NO_PHOTO[plant.group][1], big ? 18 : 14)}</span>`;
    // A photo that fails to load turns into the no-photo circle
    picker.addEventListener('error', (event) => {
        const circle = event.target.parentElement;
        if (circle?.dataset.group) {
            circle.outerHTML = thumb({ group: circle.dataset.group }, circle.classList.contains('size-10'));
        }
    }, true);

    // The typed letters get a soft green highlight
    function marked(text) {
        const at = query ? text.toLowerCase().indexOf(query.toLowerCase()) : -1;
        if (at < 0) {
            return esc(text);
        }
        const end = at + query.length;
        return `${esc(text.slice(0, at))}<mark class="-mx-px rounded-[3px] bg-brand-soft px-px text-ink">${esc(text.slice(at, end))}</mark>${esc(text.slice(end))}`;
    }

    const optionRow = (plant) => `
        <div role="option" id="${list.id}_${plant.value}" data-value="${plant.value}" aria-selected="${plant.value === select.value}" class="group/option flex cursor-pointer items-center gap-3 rounded-xl px-2.5 py-2 not-aria-selected:hover:bg-page not-aria-selected:data-active:bg-page aria-selected:bg-brand-tint group-data-keys:data-active:ring-2 group-data-keys:data-active:ring-brand group-data-keys:data-active:ring-inset">
            ${thumb(plant, true)}
            <span class="min-w-0 flex-1">
                <span class="block truncate text-sm font-extrabold leading-[1.3]">${marked(plant.name)}</span>
                <span class="block truncate text-xs italic leading-[1.4] text-ink-soft">${marked(plant.scientific)}</span>
            </span>
            <img src="${PLANT_ICONS}check.svg" alt="" width="18" height="18" class="invisible shrink-0 group-aria-selected/option:visible">
        </div>`;

    // Draw the plants that match the search and the pill, grouped by category under sticky headers
    function render() {
        const q = query.toLowerCase();
        // Best matches first: names that start with the letters, then a word inside the name, then the rest
        const rank = (p) => [p.name.toLowerCase().startsWith(q), p.name.toLowerCase().includes(` ${q}`), p.name.toLowerCase().includes(q), true].indexOf(true);
        const matches = plants.filter((p) => (!group || p.group === group) && (p.name + '\n' + p.scientific).toLowerCase().includes(q))
            .sort((a, b) => rank(a) - rank(b) || a.name.localeCompare(b.name));
        // While searching, the category with the best match comes first
        const order = q ? [...new Set(matches.map((p) => p.group))] : Object.keys(PLANT_GROUPS);
        list.innerHTML = order.map((key) => {
            const rows = matches.filter((p) => p.group === key);
            return rows.length ? `<div role="group" aria-label="${PLANT_GROUPS[key][0]}">
                <div aria-hidden="true" class="sticky top-0 z-10 -mx-1.5 bg-surface px-4 pt-3 pb-1.5 text-[11px] font-black uppercase leading-tight tracking-[0.08em] text-brand">${PLANT_GROUPS[key][0]} <span class="ml-0.5 text-muted">${rows.length}</span></div>
                ${rows.map(optionRow).join('')}</div>` : '';
        }).join('');
        list.hidden = !matches.length;
        empty.hidden = !!matches.length;
        const where = group ? `No ${PLANT_GROUPS[group][0].toLowerCase()} match “${query}”.` : `“${query}” isn't in our plant list yet.`;
        empty.querySelector('[data-empty-text]').textContent = `${where} Try another name${canBeEmpty ? ', or leave it empty' : ''}.`;
        status.textContent = `${matches.length || 'No'} ${matches.length === 1 ? 'plant' : 'plants'} found`;
        active = null;
        delete picker.dataset.keys;
    }

    // Press a category pill ('' means All) and redraw the list
    function showGroup(key) {
        group = key;
        pills.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', b.dataset.pill === key));
        render();
        list.scrollTop = 0;
    }

    function setActive(row) {
        active?.removeAttribute('data-active');
        active = row;
        row?.setAttribute('data-active', '');
        row?.scrollIntoView({ block: 'nearest' });
        if (row) {
            input.setAttribute('aria-activedescendant', row.id);
        } else {
            input.removeAttribute('aria-activedescendant');
        }
    }

    const chosenPlant = () => plants.find((p) => p.value === select.value);

    // Make the field match select.value. Closed: the chosen photo, name and tag. Open: the search icon.
    function syncField() {
        const plant = chosenPlant();
        if (!isOpen) {
            input.value = plant?.name || '';
            input.setSelectionRange(input.value.length, input.value.length); // unselect, so the next click selects it again
        }
        input.placeholder = isOpen ? `Search ${plants.length} plants...` : emptyLabel;
        thumbSlot.innerHTML = plant && !isOpen ? thumb(plant, false) : `<img src="${PLANT_ICONS}search.svg" alt="" width="18" height="19">`;
        tag.textContent = plant ? PLANT_GROUPS[plant.group][1] : '';
        clearButton.hidden = !plant || isOpen || !canBeEmpty;
        // data-chosen shows the tag. On wide fields (@sm) the text box also shrinks to the name, so the tag sits right after it.
        picker.toggleAttribute('data-chosen', !!plant && !isOpen);
    }
    // Other code can change the select too (for example to fill in a form). It only has to send a 'change' event.
    select.addEventListener('change', syncField);

    function choose(value) {
        select.value = value;
        select.dispatchEvent(new Event('change', { bubbles: true })); // this also runs syncField()
    }

    function open() {
        if (isOpen) {
            return;
        }
        isOpen = true;
        query = '';
        picker.dataset.open = '';
        input.setAttribute('aria-expanded', 'true');
        syncField();
        showGroup(''); // every open starts on All, so an old pill can't hide what is typed next
        // Start with the chosen plant in the middle of the list
        const chosen = list.querySelector('[aria-selected="true"]');
        list.scrollTop = chosen ? chosen.offsetTop - (list.clientHeight - chosen.offsetHeight) / 2 : 0;
        setActive(chosen);
        panel.scrollIntoView({ block: 'nearest' }); // scrolls the modal if the list would hang off its bottom
    }

    function close() {
        if (!isOpen) {
            return;
        }
        isOpen = false;
        delete picker.dataset.open;
        input.setAttribute('aria-expanded', 'false');
        setActive(null);
        if (!input.value.trim() && canBeEmpty) {
            choose(''); // an emptied box means "no plant", because the field is optional
        }
        syncField();
    }

    function pick(row) {
        choose(row.dataset.value);
        input.value = chosenPlant().name; // so close() doesn't think the box was emptied
        close();
    }

    input.addEventListener('input', () => {
        open();
        query = input.value.trim();
        render();
        setActive(query ? list.querySelector('[role="option"]') : null); // so Enter picks the best match
    });

    input.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            if (!isOpen) {
                open();
                return;
            }
            const rows = [...list.querySelectorAll('[role="option"]')];
            const step = event.key === 'ArrowDown' ? 1 : -1;
            picker.dataset.keys = ''; // shows the green ring on the row while using the keyboard
            setActive(rows[rows.indexOf(active) + step] || rows.at(step > 0 ? 0 : -1));
        } else if (event.key === 'Enter') {
            event.preventDefault(); // Enter in this box picks a plant, it never sends the form
            if (isOpen && active) {
                pick(active);
            } else {
                open();
            }
        } else if (event.key === 'Escape' && isOpen) {
            event.preventDefault(); // closes only the list, not the whole modal
            close();
        } else if (event.key === 'Tab') {
            close();
        }
    });
    input.addEventListener('blur', close);

    // Clicking anywhere on the field opens the list. Clicking the field again (not the text) closes it.
    box.addEventListener('mousedown', (event) => {
        if (event.target !== input) {
            event.preventDefault(); // keeps the focus in the text box
        }
    });
    box.addEventListener('click', (event) => {
        if (event.target.closest('[data-clear]')) {
            return;
        }
        input.focus();
        if (!isOpen) {
            open();
            input.select(); // typing replaces the chosen name
        } else if (event.target !== input) {
            close();
        }
    });
    clearButton.addEventListener('click', () => {
        choose('');
        input.focus();
    });

    // Clicks inside the dropdown must not take the focus away from the text box
    panel.addEventListener('mousedown', (event) => event.preventDefault());
    panel.addEventListener('click', (event) => {
        const row = event.target.closest('[role="option"]');
        const pill = event.target.closest('[data-pill]');
        if (row) {
            pick(row);
        } else if (pill) {
            showGroup(pill.dataset.pill);
        } else if (event.target.closest('[data-reset]')) {
            input.value = chosenPlant()?.name || ''; // back to how the box looked when it opened
            input.select();
            query = '';
            showGroup('');
        }
    });

    syncField();
    render(); // draws the rows once, hidden, so Tailwind has made their styles before the first open
}

document.querySelectorAll('select[data-plant-picker]').forEach(setUpPlantPicker);