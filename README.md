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
    *   **CRUD:** **Create** (Add a plant to a personal collection), **Read** (Browse guides and species data), **Update** (Modify collection names), **Delete** (Remove a species from a collection).
    *   **API Filtering:** Fetches the main dataset from Trefle.io and allows users to search/filter the directory by plant attributes.

*   **Module 6: Community Q&A Forum (William)**
    *   **Description:** A Quora-style forum dedicated to troubleshooting gardening issues.
    *   **CRUD:** **Create** (Post a new Q&A thread), **Read** (Browse the forum), **Update** (Modify forum post details), **Delete** (Delete a forum post).
    *   **API Filtering:** Users tag their questions with relevant plants. The forum can be filtered by these API-fetched plant species.

## 4. External Public API Integration
*   **API Name:** Trefle.io (https://trefle.io/)
*   **Usage:** Trefle is an open botanical data source indexing over a million plants. Albhero's module will use this API to fetch detailed, scientifically accurate plant data to populate our shared database with a minimum of 50 main data records. All other modules will read from this shared database to satisfy their individual API filtering requirements.

## 5. Application User Roles
*   **Gardener (Regular User):** Can browse the encyclopedia, post photos of their garden, claim achievements, RSVP to events, and participate in the Q&A forum.
*   **Admin/Moderator:** Has all Gardener privileges, plus the authority to verify achievement claims, moderate forum discussions, remove inappropriate social posts, and manage the event calendar.

## 6. Project Links
*   **Figma Design:** [figma link]
*   **PWS Deployment:** [pws link]