# GROW YOUR GARDEN 🌱🌷
**Theme:** Sustainable Living - Urban Farming & Biodiversity

## 1. Application Description
**GROW YOUR GARDEN** is an interactive urban gardening platform that combines educational gardening guides with a community-driven social media space. The application helps users learn how to start and maintain their own gardens while allowing them to share their progress, photos, and tips with a network of fellow gardening enthusiasts.

**Benefit to Society:** It encourages sustainable living by empowering people to keep their environments green and grow their own produce. By hosting a healthy, educational community, it motivates beginners to adopt eco-friendly habits and promotes urban biodiversity.

## 2. Team Members (PBP Group 1 KKI)
*   **Gavrila Sarah Kartika Suoth** - 2506559071
*   **Khalifah Gigan Albhero** - 2506555224
*   **William Jesiel** - 2506637155
*   **Veronika Chebotareva** - 2606816515
*   **Ahmad Hoesin** - 2506555400
*   **Meuthia Zahra Yanuci** - 2506637060

## 3. Module Division & Work Distribution
*Note: Each module represents a complete CRUD (Create, Read, Update, Delete) implementation, and every module filters data fetched from our shared Public API.*

*   **Module 1: Profile and Authentication (Sarah)**
    *   **Description:** Handles user authentication (register, login) and profile management.
    *   **CRUD:** **Create** (Register a new user), **Read** (View user profile), **Update** (Update user profile info/bio), **Delete** (Delete user account).
    *   **API Filtering:** Users can add information about their favorite plant(s) on their profile, selecting from the API database.

*   **Module 2: Achievement System (Meuthia)**
    *   **Description:** A gamified page where users gain achievements by hitting milestones (e.g., first harvest), streaks (e.g., 3 days of planting), and personal records.
    *   **CRUD:** **Create** (Submit a claim for an achieved milestone), **Read** (View unlocked achievements), **Update** (Modify a submitted claim), **Delete** (Remove an achievement record).
    *   **API Filtering:** Users can filter their achievement board to see badges related to specific plant species fetched from the API.

*   **Module 3: Garden Page (Veronika)**
    *   **Description:** The social media core where users can see each other’s gardens and post their own.
    *   **CRUD:** **Create** (Post photo of own garden with caption), **Read** (Scroll feed of pictures), **Update** (Modify post details/leave a comment), **Delete** (Delete post).
    *   **API Filtering:** Posts can be filtered by the specific plant species tagged in the photo (fetched from the API).

*   **Module 4: Plant Event (Ahmad)**
    *   **Description:** A community organizing tool for local meetups, seed swaps, or harvest shares (e.g., "Bring your baked potato").
    *   **CRUD:** **Create** (Host an event), **Read** (Browse upcoming events), **Update** (Modify event details), **Delete** (Cancel an event).
    *   **API Filtering:** Events have a "Theme Plant." Users can search the calendar for events based on plant types fetched from the API.

*   **Module 5: Encyclopedia / Plant Directory (Albhero)**
    *   **Description:** An encyclopedia containing plant species, guides, and user collections. This module handles the core external API integration.
    *   **CRUD:** **Create** (Create personal plant collection), **Read** (Browse guides and species data), **Update** (Modify collection names, add and remove plants inside collection), **Delete** (Remove a personal plant collection).
    *   **API Filtering:** Fetches the main dataset from Trefle.io and allows users to search/filter the directory by plant attributes.

*   **Module 6: Community Q&A Forum (William)**
    *   **Description:** A Quora-style forum dedicated to troubleshooting gardening issues.
    *   **CRUD:** **Create** (Post a new Q&A thread), **Read** (Browse the forum), **Update** (Modify forum post details), **Delete** (Delete a forum post).
    *   **API Filtering:** Users tag their questions with relevant plants. The forum can be filtered by these API-fetched plant species.

## 4. External Public API Integration
*   **API Name:** Trefle.io (https://trefle.io/)
*   **Usage:** Trefle is an open botanical data source indexing over 400,000 plant species. Albhero's module will use this API to fetch detailed, scientifically accurate plant data to populate our shared database with a minimum of 50 main data records. All other modules will read from this shared database to satisfy their individual API filtering requirements
*   **Docs:** https://docs.trefle.io/ (section 8 explains how we use it)
* See [8. How Our API Part Works](#8-how-our-api-part-works) for the details.


## 5. Application User Roles
*   **Gardener (Regular User):** Can browse the encyclopedia, post photos of their garden, claim achievements, RSVP to events, and participate in the Q&A forum.
*   **Admin/Moderator:** Has all Gardener privileges, plus the authority to verify achievement claims, moderate forum discussions, remove inappropriate social posts, and manage the event calendar.

**How to make someone a moderator:** log in to `/admin/` with a superuser (`python manage.py createsuperuser` locally), open **Users**, pick the person, tick **Staff status** and save. A staff account sees a Delete button on every event, garden post, question and answer, and can approve or reject badge claims in `/admin/`.

## 6. Project Links
*   **Figma Design:** [https://www.figma.com/design/Rgarm0NKaaezYTwWCWxCSb/Untitled?node-id=0-1&t=0N0NtdJeEtON4oHQ-1](https://www.figma.com/design/Rgarm0NKaaezYTwWCWxCSb/Untitled?node-id=0-1&t=0N0NtdJeEtON4oHQ-1)
*   **PWS Deployment:** [https://william-jesiel-growyourgarden.pws.cs.ui.ac.id](https://william-jesiel-growyourgarden.pws.cs.ui.ac.id)


## 7. Running It Locally

You need Python 3.10 or newer and git.

1. Clone the repo and go into it:
   ```bash
   git clone https://github.com/WilliamJesUI/Group-1-KKI.git
   cd Group-1-KKI
   ```
2. Make a virtual environment and turn it on:
   ```bash
   python -m venv env
   source env/bin/activate        # Windows: env\Scripts\activate
   ```
3. Install the packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Make a file called `.env` in the project folder (it's ignored by git). For local work it only needs:
   ```
   PRODUCTION=False
   TREFLE_TOKEN=your-token-here
   ```
   The token is only needed to rebuild the plant list (see section 8). Without it the site still runs, because the plants are already saved in the repo.
   With `PRODUCTION=False` you get Django's debug pages and a local SQLite database. On PWS we set `PRODUCTION=True`, which turns debug off and uses PostgreSQL. PWS also has `SECRET_KEY`, `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `SCHEMA` and `TREFLE_TOKEN` in its Environs tab. None of those values are in the repo.
5. Set up the database and make an account for the admin page:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
   `migrate` also loads our starter plant list into the database.
6. Start the server:
   ```bash
   python manage.py runserver
   ```
   Then open http://127.0.0.1:8000/. The admin page is at http://127.0.0.1:8000/admin/.

## 8. How Our API Part Works

Our plant data comes from [Trefle](https://trefle.io/) ([documentation](https://docs.trefle.io/)), an open botanical database. Instead of calling Trefle on every page load, we fetch the plants once and keep them in our own database. That keeps the site fast, and it keeps working even when Trefle is down.

1. We wrote a list of the plants we want in `plants/data/plant_list.csv` (name, scientific name, category).
2. The command `python manage.py build_plant_list` looks up each plant on Trefle and saves the results in `plants/data/plants.json`.
3. When the site deploys, a data migration loads that file into the shared `Plant` table, so the live site starts with all the plants.
4. Every module links to the `Plant` table (for example, an event's theme plant), so each module can filter its own data by plant.

| File | What it does |
|---|---|
| `plants/models.py` | The `Plant` model: name, category, difficulty, sunlight, watering, photo and more |
| `plants/services/http.py` | One small function that calls an API and turns any failure into a simple error |
| `plants/services/trefle.py` | Searches Trefle and fetches one species. Answers are cached for a day |
| `plants/mapping.py` | Turns Trefle's raw numbers into the words our design uses (for example "Full sun", "Easy") |
| `plants/management/commands/build_plant_list.py` | The command that builds `plants.json` from the plant list |
| `plants/data/plants.json` | The saved plants that get loaded on deploy |

- **The Trefle token stays private.** It lives in `.env` on our laptops and in the PWS Environs tab, never in the code or on GitHub.
- **Trefle doesn't have everything.** It has no watering info and only some sunlight info, so `plants/mapping.py` fills the gaps with simple rules. Plants filled in this way are marked `care_estimated`, and their page says the care tips are a general guide.

To rebuild the plant list yourself: get a free token at [trefle.io](https://trefle.io/), put it in `.env` as `TREFLE_TOKEN`, then run `python manage.py build_plant_list` (it takes a few minutes, because it waits between requests) and `python manage.py migrate`.

Plant data: [Trefle](https://trefle.io/), CC BY 4.0. Photo credits are in [docs/CREDITS.md](docs/CREDITS.md).

## 9. Running the Tests

```bash
python manage.py test
```

To see the test coverage:

```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

The same checks run automatically on every pull request and every push to `main` through GitHub Actions (`.github/workflows/tests.yml`). The run fails if a migration is missing or coverage drops under 80%.

## 10. Screenshots

| Landing page | Encyclopedia |
|---|---|
| ![Landing page](docs/screenshots/landing.png) | ![Encyclopedia](docs/screenshots/encyclopedia.png) |
| **Plant page** | **Events** |
| ![Plant page](docs/screenshots/plant-page.png) | ![Events](docs/screenshots/events.png) |
| **Garden** | **Community** |
| ![Garden](docs/screenshots/garden.png) | ![Community](docs/screenshots/community.png) |
| **Achievements** | **Profile** |
| ![Achievements](docs/screenshots/achievements.png) | ![Profile](docs/screenshots/profile.png) |
| **Dark mode** (moon button next to your name) | |
| ![Dark mode](docs/screenshots/dark-mode.png) | |

## 11. Quality and Security Notes

- **Custom login check for AJAX:** `growyourgarden/permissions.py` has an `ajax_login_required` decorator. A guest who clicks Like, RSVP or Delete gets a JSON 403 with a friendly message (shown as a toast) instead of a redirect page inside a fetch call.
- **Owner or moderator only:** every edit and delete view checks the owner on the server (`can_delete`), not only by hiding buttons.
- **CSRF on every fetch:** all AJAX calls send the `X-CSRFToken` header from `static/js/csrf.js`.
- **API down plan:** plant data is fetched from Trefle once and saved in `plants/data/plants.json`, which a data migration loads. If Trefle is down the site still has all 78 plants. Live Trefle lookups are cached for a day with Django's cache.
- **Lighter queries:** list pages use `select_related`, `prefetch_related` and `annotate` so a page doesn't run one query per card.
- **Secrets stay out of git:** the database password and the Trefle token come from `.env` locally and from PWS Environs in production (`SECRET_KEY` can be set there too).

## 12. AI Disclosure

We used AI as a helper while building Grow Your Garden, and we want to be clear about how. This section covers which tools we used, how we prompted them, what they did in each module, and where they got things wrong and we had to fix it ourselves.

### Tools

| Tool | What we used it for |
|---|---|
| Claude (claude.ai and the Claude Code extension in VS Code) | Explaining Django and Tailwind concepts, planning features in small steps, debugging errors, reviewing branches before merging, drafting tests and docs |
| Claude with the Figma connector | Help laying out some screens and states from our existing design system |

### How we prompted (our strategy)

We gave the AI a few fixed rules up front (in a `CLAUDE.md` file and in the project instructions) and kept them for the whole project:

1. **Explain, don't hand over.** The AI explains each change step by step. Mostly we typed the code in ourselves. For bigger changes near the deadline it prepared a patch file, which we read, applied, tested and committed ourselves.
2. **Figma first.** Any visible change gets designed in Figma before any code is written, because Figma is our source of truth.
3. **Small commits.** One small change at a time, with `feat:`, `fix:`, `test:`, `docs:`, `refactor:` and `style:` prefixes.
4. **We run git.** The AI never commits, pushes or merges. Every pull request is opened and merged by one of us.
5. **No secrets and no AI images.** No passwords or API keys in chats, and no AI-generated images anywhere on the site or in Figma. Photos come from Pexels, Wikimedia Commons or PlantNet, with credits in `docs/CREDITS.md`.

Prompts were short and in plain words, usually with a screenshot or an error message attached. Some real examples:

| Goal | Example prompt |
|---|---|
| Plan a feature | "add a theme plant to events so people can filter events by plant, design it in figma first" |
| Check the repo | "its merged can u like check every single thing rn" |
| Debug | (screenshot of a failing test) "what is this thing, and tell me my next step" |
| Review a teammate's branch | "look at every branch not yet merged, whats wrong, whats left" |
| Push back on a result | "hmmm its still old people, fix that" (about a cover photo) |
| Prioritize near the deadline | "give a list of whats wrong and whats my best course of action" |

### How each of us used AI

Each member describes their own use. Where we have a shared chat, the link is there so you can see how we actually asked.

**Ahmad (Plant Event, shared plants app, landing page)**
Chat log: https://docs.google.com/document/d/1ILOSwIeja5XF-AcynPT6ewbHHPLcRfaQ1PaMWiH9sx8/edit?usp=sharing
I used Claude mostly as a tutor and reviewer. I asked it to explain Django and Tailwind ideas I hadn't met in the tutorials (AJAX with fetch, data migrations, `select_related`), to break each feature into small steps, and to look at my errors when a test failed. Near the deadline it also checked teammates' branches before we merged them, ran a browser test of every page, and prepared some larger fixes as patch files, which I read, applied, tested and committed myself. The design choices, the plant list and what to cut were mine.

**William (Community)**
Chat: https://claude.ai/share/51e8891b-fee8-467a-8eb9-5526f769d0ff
I mainly asked AI how a feature in Django works, and used it as an assistant to keep my designs consistent with my teammates' designs. I also used it for repetitive code: instead of typing all of it myself, I asked the AI to write it and then replaced the variables so it fit my module.

**Veronika (Garden)**
I used AI as a mentor to help me navigate complex parts of Django. I asked specific questions about how to combine Django forms with AJAX (Fetch API) so the page wouldn't reload, and for help debugging merge conflicts when combining my branch with the team's `main`. The AI often gave me generic code that didn't match our folder structure: it suggested form fields that didn't exist in our final model, and it wrote JavaScript using standard CSS classes instead of our Tailwind utilities. I rewrote the JavaScript to match our `base.html`, fixed the `id` and class names in the templates so the scripts would find the buttons, and resolved the Git merge conflicts myself (especially in `settings.py` and `header.html`), where the AI got confused by my teammates' overlapping code.

**Sarah (Auth & Profile)**
I used AI mainly as a helper throughout the development process. I asked it to help organize my tasks into to-do lists so I could keep track of what needed to be done and decide which tasks to prioritize. I also used it as a reference when working with Git, especially when pulling updates from the team's main branch and merging them into my own branch, so I understood the steps and didn't accidentally overwrite or break files other members had worked on. I didn't rely entirely on its suggestions: it couldn't always see the latest state of our codebase or every change made by other members, so I checked the relevant files and reviewed each step myself, and after merging I verified that everything worked and my changes didn't interfere with anyone else's work.

**Albhero (Encyclopedia)**
I used AI to guide my learning and help fix errors throughout the development of my module. Using an external API was very unfamiliar to me, so I made many mistakes and was sometimes unsure where to go next. That is why I needed constant guidance, and why AI was quite important for me personally.

My prompt strategy: I first studied the steps to build the module and wrote my own code. On the side, I asked the AI to make its own independent version of the module. Then I compared the two and looked at the differences. This let me learn and fix errors in my own code at the same time. The final result combines both.

Limitations: the AI sometimes made mistakes or misunderstood instructions. For example, when I removed the authentication module (which was only there for testing), the AI's version also removed the whole login and register button from the header. Each time this happened I fixed the code by hand and left most of the AI's version out of the final result.

**Meuthia (Achievements)**
I used AI mostly to guide my learning and help fix errors while building the Achievements module. I wrote my own code first and used AI to explain the parts I didn't understand, then compared its suggestions with my code to find and fix mistakes. The AI sometimes misunderstood what I wanted or gave code that didn't fit our project, so I checked and fixed those parts myself before using anything. After the AI gave its response, i always made sure to think, question, verity, and reflect.

### Where the AI fell short, and what we fixed by hand

| What went wrong | How we noticed | What we did |
|---|---|---|
| It guessed instead of checking the real code (an import that already existed, a query speed-up in the wrong view) | While typing the code in, or in PR review | Asked it to re-read the actual file before answering |
| Trefle's common names were wrong for 43 of 60 plants (Trefle's "Carrot" is a wild weed) | Checking the first fetch by hand | Matched plants only by exact scientific name, and kept our own English names |
| Trefle has no watering data and only some sunlight data | Same check | Simple rules fill the gaps, and those plants are marked `care_estimated` with "Care tips are a general guide" on the page |
| PlantNet photos kept timing out, so pages loaded slowly | DevTools Network tab | Saved small copies of every photo in `static/img/plants/` with credits |
| It made an AI-generated cover image in Figma, which breaks our no-AI-images rule | We caught it in review | Deleted it, used a licensed Pexels photo and credited it |
| The cover photo cropped people's faces on desktop | Looking at the page | Fixed the crop position (PR #38) |
| It couldn't put the cover photo into Figma (uploads are blocked from its sandbox, and pasting the image as text came out corrupted) | It checked the result and stopped | The Figma plate keeps a colour placeholder for now |
| It once ran `git checkout` in a project folder and left it half switched | The terminal | Recovered by hand; since then the AI only reads that folder |
| Merges sometimes undid shared files (the navbar went back to an old version twice) | Failing tests after the merge | Fixed in follow-up PRs (#33), and the tests now check the navbar |
| A teammate's branch would have crashed the landing page by renaming a database relation | It test-merged the branch before it was merged | Changed the landing page to count badges in a way that doesn't depend on that name (PR #41) |
| It can't reach our PWS site or Wikipedia from its sandbox | Its own error messages | It tested a local copy; we checked every change on PWS ourselves and ran the Wikipedia fetch on our laptops |
| A database change worked on our laptops (SQLite) but crashed on PWS (PostgreSQL), because old goals stored the plant as text | Testing the migration on a real PostgreSQL database before deploying | Rewrote the migration to link old goals to the matching plant first |
| Running tests in parallel hid some failures | Different results between runs | We run the full suite one at a time before every merge |
| VS Code showed "errors" on Tailwind `@apply` and Django `{{ }}` inside style attributes | Problems panel | Confirmed they're false positives from the CSS linter, not real bugs |

### What AI did not do

- It did not commit, push or merge anything. Every change went in through one of us, after we ran the tests.
- It did not make decisions for the team. Design choices, which plants to include, what to cut near the deadline and every merge were our call.
- It did not see secrets. Database passwords and the Trefle token stay in `.env` and the PWS Environs tab.

Checks we ran on the final version: 540 unit tests plus 2 Selenium tests, with statement and branch coverage above 90% (94% at our last full measurement).

We also added a GitHub Actions check (`.github/workflows/tests.yml`) that runs every test on each pull request, so a broken change shows up before anyone merges it.

