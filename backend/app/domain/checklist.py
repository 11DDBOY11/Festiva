"""Deterministic checklists and run-of-show templates.

Keyed by event type (wedding, birthday, community) for the Mangaluru region.
Zero LLM calls.
"""

from app.domain.schemas import ChecklistQuestion, RunOfShowSlot

# ---------------------------------------------------------------------------
# Checklist Questions by Event Type
# ---------------------------------------------------------------------------

CHECKLIST_TEMPLATES: dict[str, list[ChecklistQuestion]] = {
    "wedding": [
        ChecklistQuestion(
            category="Venue",
            item="Mangaluru Wedding Hall / Kalyana Mantapa",
            questions_to_ask_vendor=[
                "What is the exact checkout time for the bridal suite and main hall?",
                "Are outside caterers allowed without royalty fees or kitchen charges?",
                "Is AC operational continuously on generator backup during power cuts?",
                "What is the designated parking capacity for guests and buses?",
            ],
            due_phase="6 months before",
        ),
        ChecklistQuestion(
            category="Catering",
            item="Traditional Mangalorean / Coastal Feast",
            questions_to_ask_vendor=[
                "Do you provide experienced banana leaf serving staff in traditional attire?",
                "What are the per-plate rates for Udupi vegetarian vs coastal non-veg options?",
                "Are welcome drinks, ice creams, and paan counter included in the rate?",
                "Do you bring your own potable drinking water cans and clean crockery?",
            ],
            due_phase="4 months before",
        ),
        ChecklistQuestion(
            category="Decor",
            item="Floral Mandap & Stage Styling",
            questions_to_ask_vendor=[
                "Does the floral mandap quotation include fresh marigold and jasmine garlands?",
                "What time does your team need access to the hall for previous evening setup?",
                "Is stage lighting (focus spots, wash lights) included in the decor package?",
                "What is the cleanup and dismantling timeline post-muhurtham?",
            ],
            due_phase="2 months before",
        ),
        ChecklistQuestion(
            category="Photography",
            item="Candid & Cinematic Photography Team",
            questions_to_ask_vendor=[
                "How many candid photographers and traditional videographers are assigned?",
                "Are unedited high-resolution RAW photos delivered on an external drive?",
                "What is the delivery timeline for the highlight teaser and wedding photo album?",
                "Do you provide a drone for outdoor or beachside photo sessions?",
            ],
            due_phase="3 months before",
        ),
        ChecklistQuestion(
            category="Music & Sound",
            item="Traditional Nadaswaram & Sound System",
            questions_to_ask_vendor=[
                "Do you provide cordless lapel microphones for the priest during rituals?",
                "Are high-gain PA speakers installed in both the dining hall and main stage?",
                "Does the sound setup have an independent inverter/generator backup?",
            ],
            due_phase="1 month before",
        ),
    ],
    "birthday": [
        ChecklistQuestion(
            category="Venue",
            item="Party Lawn / Private Dining Hall",
            questions_to_ask_vendor=[
                "Is the party hall equipped with audio/visual projection for photo montages?",
                "Are outside cakes and dessert tables allowed without cakeage fees?",
                "Until what time at night can light music be played indoors?",
            ],
            due_phase="3 weeks before",
        ),
        ChecklistQuestion(
            category="Cake & Bakery",
            item="Custom Milestone Birthday Cake",
            questions_to_ask_vendor=[
                "Do you offer tiered fondant or fresh whipped cream customized themes?",
                "Is temperature-controlled delivery directly to the venue available?",
                (
                    "Can you provide eggless and gluten-free mini cupcakes "
                    "for guests with dietary needs?"
                ),
            ],
            due_phase="2 weeks before",
        ),
        ChecklistQuestion(
            category="Decor",
            item="Theme Balloon Arch & Photo Backdrop",
            questions_to_ask_vendor=[
                "Are balloon arches and neon signages included in the setup package?",
                "How long prior to the party does the setup crew arrive at the venue?",
                "Can the backdrop withstand coastal sea breeze if held in an open lawn?",
            ],
            due_phase="10 days before",
        ),
        ChecklistQuestion(
            category="Entertainment",
            item="Anchor / Emcee & Sound System",
            questions_to_ask_vendor=[
                "Do you organize interactive games tailored to both kids and family elders?",
                "Do you bring your own wireless microphones and Bluetooth DJ sound box?",
            ],
            due_phase="1 week before",
        ),
    ],
    "community": [
        ChecklistQuestion(
            category="Venue & Ground",
            item="Public Ground / Town Auditorium",
            questions_to_ask_vendor=[
                "Have the municipal corporation permissions and police NOC been verified?",
                "What is the electricity limit and is a dedicated high-KVA generator needed?",
                "Are there adequate drinking water points and mobile sanitation facilities?",
            ],
            due_phase="2 months before",
        ),
        ChecklistQuestion(
            category="Stage & Sound",
            item="Heavy Trussing & High-Power PA Setup",
            questions_to_ask_vendor=[
                "What is the total wattage of the line array sound system for the open crowd?",
                "Are minimum 6 wireless handheld mics provided for committee speakers?",
                "Is rain-proof waterproof tarping installed above the stage equipment?",
            ],
            due_phase="1 month before",
        ),
        ChecklistQuestion(
            category="Catering",
            item="Community Anna Santharpana Mass Meal",
            questions_to_ask_vendor=[
                "What is your continuous batch serving capacity per 30 minutes on banana leaves?",
                "Do you manage full kitchen waste disposal and leftover food packaging?",
                "Are authentic coastal vegetarian dishes (saaru, payasa, palya) prepared on site?",
            ],
            due_phase="3 weeks before",
        ),
    ],
}

# ---------------------------------------------------------------------------
# Run of Show Hourly Schedules by Event Type
# ---------------------------------------------------------------------------

RUN_OF_SHOW_TEMPLATES: dict[str, list[RunOfShowSlot]] = {
    "wedding": [
        RunOfShowSlot(
            time_slot="08:30 - 09:30",
            activity="Vendor arrival, floral mandap inspection, sound mic testing",
            location="Main Hall & Stage",
            lead_person="Host & Decor Lead",
            notes="Verify fresh jasmine garlands and priest microphone.",
        ),
        RunOfShowSlot(
            time_slot="09:30 - 10:30",
            activity="Breakfast counter opens for guests; bridal party final touch-up",
            location="Dining Hall & Bridal Suite",
            lead_person="Catering Head",
            notes="Idli, vada, sheera, and coastal filter coffee service.",
        ),
        RunOfShowSlot(
            time_slot="10:30 - 11:30",
            activity="Traditional Muhurtham rituals and priest chantings",
            location="Mandap",
            lead_person="Family Elders & Priest",
            notes="Candid photographer takes primary family close-ups.",
        ),
        RunOfShowSlot(
            time_slot="11:30 - 12:30",
            activity="Mangalasutra Dharana, saptapadi, and garland exchange",
            location="Mandap",
            lead_person="Couple & Parents",
            notes="Flower petal shower coordinated with traditional instrumental entry.",
        ),
        RunOfShowSlot(
            time_slot="12:30 - 14:30",
            activity="Grand traditional Mangalorean banana leaf lunch feast",
            location="Dining Hall",
            lead_person="Catering Team Lead",
            notes="Staggered seating in batches of 100-150 guests.",
        ),
        RunOfShowSlot(
            time_slot="14:30 - 15:30",
            activity="Stage felicitations, guest photos with couple, and blessings",
            location="Main Stage",
            lead_person="Lead Photographer",
            notes="Fast-paced queue management for relative photo album.",
        ),
        RunOfShowSlot(
            time_slot="15:30 - 16:30",
            activity="Send-off for extended guests, vendor settlements, and hall checkout",
            location="Foyer & Reception",
            lead_person="Host",
            notes="Hand over advance balances and verify hall return checklist.",
        ),
    ],
    "birthday": [
        RunOfShowSlot(
            time_slot="18:00 - 18:30",
            activity="Decor finalization, cake table styling, and background music check",
            location="Party Hall",
            lead_person="Host",
            notes="Confirm cake temperature and lighting above cake table.",
        ),
        RunOfShowSlot(
            time_slot="18:30 - 19:15",
            activity="Guest arrival, welcome drinks, coastal finger snacks, and mixer",
            location="Lounge & Lawn",
            lead_person="Catering Team",
            notes="Live appetizer pass-around and photo backdrop portraits.",
        ),
        RunOfShowSlot(
            time_slot="19:15 - 20:00",
            activity="Fun party games, video montage playback, and milestone speeches",
            location="Main Stage",
            lead_person="Emcee / Host",
            notes="Projector video screen playback and crowd trivia.",
        ),
        RunOfShowSlot(
            time_slot="20:00 - 20:30",
            activity="Grand birthday cake cutting ceremony and celebration toast",
            location="Center Stage",
            lead_person="Birthday Celebrant & Family",
            notes="Sparkler candles and theme celebration song.",
        ),
        RunOfShowSlot(
            time_slot="20:30 - 22:00",
            activity="Buffet dinner spread, dessert counter, and informal social time",
            location="Dining Area",
            lead_person="Catering Head",
            notes="Fresh dessert counters and coastal specialty dishes.",
        ),
        RunOfShowSlot(
            time_slot="22:00 - 22:30",
            activity="Return gift distribution, final group selfies, and farewell",
            location="Exit Foyer",
            lead_person="Host",
            notes="Hand personalized return gifts to departing guests.",
        ),
    ],
    "community": [
        RunOfShowSlot(
            time_slot="14:30 - 15:30",
            activity="Sound balance, wireless mic test, stage seating for dignitaries",
            location="Main Stage",
            lead_person="Technical Lead",
            notes="Confirm DG generator synchronization and audio coverage.",
        ),
        RunOfShowSlot(
            time_slot="15:30 - 16:15",
            activity="Inauguration: Traditional Deepa Prajwalana & prayer song",
            location="Stage",
            lead_person="Samithi President",
            notes="Dignitaries light ceremonial oil lamp on stage.",
        ),
        RunOfShowSlot(
            time_slot="16:15 - 18:00",
            activity="Cultural presentations, local Yakshagana performance & music",
            location="Stage & Pandal",
            lead_person="Cultural Coordinator",
            notes="Coordinate artist stage entries and lighting cues.",
        ),
        RunOfShowSlot(
            time_slot="18:00 - 19:00",
            activity="Community felicitations, awards distribution, and address",
            location="Stage",
            lead_person="General Secretary",
            notes="Shawl and memento presentations for community achievers.",
        ),
        RunOfShowSlot(
            time_slot="19:00 - 21:00",
            activity="Community Anna Santharpana mass banana leaf dinner",
            location="Dining Hall / Pandal",
            lead_person="Seva Volunteers Lead",
            notes="Pure vegetarian coastal meal served continuously in queues.",
        ),
        RunOfShowSlot(
            time_slot="21:00 - 21:30",
            activity="Vote of thanks, volunteer appreciation, and venue cleanup",
            location="Main Ground",
            lead_person="Samithi Lead",
            notes="Final sound down, stage clearance, and waste collection check.",
        ),
    ],
}


def get_checklist_for_event(event_type: str) -> list[ChecklistQuestion]:
    """Retrieve vendor checklist questions for an event type."""
    clean_type = event_type.lower().strip() if event_type else "wedding"
    return list(CHECKLIST_TEMPLATES.get(clean_type, CHECKLIST_TEMPLATES["wedding"]))


def get_run_of_show_for_event(event_type: str) -> list[RunOfShowSlot]:
    """Retrieve run-of-show schedule for an event type."""
    clean_type = event_type.lower().strip() if event_type else "wedding"
    return list(RUN_OF_SHOW_TEMPLATES.get(clean_type, RUN_OF_SHOW_TEMPLATES["wedding"]))
