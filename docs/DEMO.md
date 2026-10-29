# Festiva AI — Click-by-Click Demo Walkthrough

This document outlines the exact, reproducible demonstration flow for Festiva AI, showcasing the 21st Birthday Celebration in Mangaluru.

---

## Demo Script Summary

| Step | Action | Expected Output | Screenshot / Artifact |
| :--- | :--- | :--- | :--- |
| **1. Landing Page** | Visit root URL (`/`) | Public hero, 3 CTAs, "How it works" 3-step workflow, features grid, sample-data disclosure | `docs/images/demo_00_landing_page.png` |
| **2. One-Click Demo Auth** | Click **"Try the demo"** | Auto-logs in as `demo@festiva.ai` and directly opens the Mangaluru birthday celebration modal | Authenticated session |
| **3. Plan v1 Inspection** | Review Budget, Venue, Timeline | Total budget ₹75,000, 80 guests. Category shares sum to exactly 100.0%. Sample Data badge on Venue card | `docs/images/demo_01_plan_v1.png` |
| **4. Natural Language Refine**| Switch to "Suggestions / Changes" tab. Input prompt: *"Rain is likely, make it weather-safe and reduce décor by ₹10,000"* | Side-by-side diff: Décor decreases by ₹10,000, Contingency increases by ₹10,000. Total ₹75,000 preserved | `docs/images/demo_02_diff_proposal.png` |
| **5. Accept Diff Proposal** | Click **"Accept Proposal"** | Version increments from v1 to v2. Plan v2 displays Contingency & Reserve with ₹10,000 | `docs/images/demo_03_plan_v2.png` |
| **6. Vendor Inquiry Drafter** | Switch to "Vendors & Checklist", click **"Draft Inquiry"** for Catering | Grounded message pre-populated with headcount (80), date (20 Nov 2026), and budget questions | `docs/images/demo_04_draft_message_dialog.png` |
| **7. Printable PDF Export** | Click **"Export PDF"** button | High-resolution PDF with Unicode ₹ rupee symbols, itemized budget table, and execution timeline | Downloaded PDF |

---

## Detailed Step-by-Step Instructions

### Step 1: Public Landing Page
1. Navigate to `http://127.0.0.1:3000` (or production URL).
2. For unauthenticated visitors, Festiva presents a clean, responsive landing page:
   - **Hero Pitch:** *"Plan celebrations with complete clarity & confidence — Tell Festiva your occasion, date, guests and budget, and get a complete, editable event plan in minutes."*
   - **Primary CTAs:** *"Try the demo"*, *"Create an event"*, *"Log in"*.
   - **Transparency Disclosure:** Clear notice that vendor directories and prices are demonstration datasets grounded in Mangaluru benchmarks.

### Step 2: One-Click Demo Launch
1. Click **"Try the demo"** on the hero banner.
2. The application automatically authenticates using the seeded demo credentials (`demo@festiva.ai` / `DemoFestiva2026!`) and launches directly into the event workspace.

### Step 3: Inspect Plan v1
1. The **Plan View Modal** opens for *"21st Birthday Party - Mangaluru Coastal Celebration"*:
   - **Event Profile:** 80 guests, ₹75,000 total budget, 20 Nov 2026, Mangaluru.
   - **Budget Allocation:**
     - Food & Beverage: ₹32,000 (42.7%)
     - Venue Rental: ₹16,250 (21.7%)
     - Décor & Ambiance: ₹13,000 (17.3%)
     - Entertainment & Photography: ₹9,750 (13.0%)
     - Contingency & Reserve: ₹4,000 (5.3%)
     - **Integrity Guarantee:** Shares sum to 100.0% ± 0.1%, amounts sum exactly to ₹75,000.
   - **Venue Showcase:** Prominent card showcasing sample Mangaluru venue with transparent "Sample Data" pill and external Google Maps redirect.

### Step 4: Refine with Copilot
1. Click the **"Suggestions / Changes"** tab in the segmented modal navigation.
2. In the proposal prompt input, enter:
   ```text
   Rain is likely, make it weather-safe and reduce décor by ₹10,000
   ```
3. Click **"Preview Changes"**.
4. Festiva evaluates the proposal through the *"LLM proposes, code decides"* diff engine:
   - Décor is adjusted from ₹13,000 down to ₹3,000 (-₹10,000).
   - The ₹10,000 is safely reallocated to Contingency & Reserve (₹4,000 -> ₹14,000).
   - Overall event budget remains locked at ₹75,000.
   - Rain safety setting `weather_safe: true` is activated with outdoor weather-proofing tasks added.

### Step 5: Accept Diff to Create Plan v2
1. Review the side-by-side proposed diff card.
2. Click **"Accept Proposal"**.
3. The server generates immutable Plan version 2. Plan v2 shows the updated budget table with visible Contingency & Reserve line of ₹14,000.

### Step 6: Grounded Vendor Message Drafter
1. Click the **"Vendors & Checklist"** tab.
2. Under Catering, click **"Draft Message"**.
3. Festiva generates a professional inquiry message grounded in the event facts:
   - Mentions date (20 Nov 2026) and headcount (80 guests).
   - Inquires about coastal buffet arrangements, vegetarian snack options, and service setup.
   - Provides ready-to-copy text for email or WhatsApp.

### Step 7: Export Printable PDF
1. In the modal header, click **"Export PDF"**.
2. The browser downloads `festiva_plan_<event_id>_v2.pdf`.
3. Inspect the PDF:
   - Correct Unicode Indian Rupee (`₹`) symbol formatting.
   - Clean, balanced budget table summing to ₹75,000.
   - Chronological timeline and day-of run-of-show.
   - Honest "Notice: Demonstration Data" label.

