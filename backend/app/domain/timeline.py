"""Deterministic timeline generator.

Calculates milestone target dates counted backward from the event date.
Ensures all dates fall between today and the event date in strict chronological order.
Zero LLM calls.
"""

from datetime import date, timedelta

from app.domain.schemas import TimelineItem

# Milestone templates keyed by event_type.
# Each entry: (days_before_event, task_description, category, priority, owner)
TIMELINE_TEMPLATES: dict[str, list[tuple[int, str, str, str, str]]] = {
    "wedding": [
        (180, "Book wedding hall and reception venue in Mangaluru", "Venue", "high", "Host"),
        (
            120,
            "Finalize traditional Mangalorean caterer & schedule menu tasting",
            "Catering",
            "high",
            "Host",
        ),
        (
            90,
            "Book candid wedding photographer and cinematic videographer",
            "Photography",
            "high",
            "Host",
        ),
        (60, "Confirm fresh floral mandap and stage decor concepts", "Decor", "medium", "Host"),
        (
            45,
            "Finalize bridal attire, jewelry selection, and makeup artists",
            "Makeup & Attire",
            "medium",
            "Host",
        ),
        (
            30,
            "Send wedding invitations and open RSVP tracking",
            "Coordination",
            "medium",
            "Host",
        ),
        (
            14,
            "Finalize sound setup, traditional nadaswaram / DJ entry tracks",
            "Music & Sound",
            "medium",
            "Host",
        ),
        (7, "Confirm final guest headcount with caterer", "Catering", "high", "Host"),
        (
            2,
            "Pre-event venue walkthrough and advance balance check",
            "Coordination",
            "high",
            "Host",
        ),
        (0, "Wedding day execution & run-of-show coordination", "Coordination", "high", "Host"),
    ],
    "birthday": [
        (
            30,
            "Select party hall or reserve private lawn / restaurant area",
            "Venue",
            "high",
            "Host",
        ),
        (
            21,
            "Order custom theme cake and finalize dessert spread",
            "Cake & Desserts",
            "high",
            "Host",
        ),
        (
            14,
            "Confirm theme balloon arches, backdrop, and table decor",
            "Decor",
            "medium",
            "Host",
        ),
        (
            10,
            "Book party emcee, games coordinator or DJ sound setup",
            "Entertainment",
            "medium",
            "Host",
        ),
        (
            7,
            "Send digital invites and collect RSVP confirmations",
            "Coordination",
            "medium",
            "Host",
        ),
        (
            2,
            "Procure return gifts, party favors, and snacks",
            "Coordination",
            "medium",
            "Host",
        ),
        (
            0,
            "Birthday celebration execution and cake cutting ceremony",
            "Coordination",
            "high",
            "Host",
        ),
    ],
    "community": [
        (
            60,
            "Secure venue ground / auditorium permissions and local authority NOC",
            "Permits & Venue",
            "high",
            "Samithi",
        ),
        (
            45,
            "Contract stage fabricator, trussing, and high-power PA system",
            "Sound & Stage",
            "high",
            "Technical Lead",
        ),
        (
            30,
            "Finalize community Anna Santharpana / bulk meal catering service",
            "Catering",
            "high",
            "Seva Lead",
        ),
        (
            20,
            "Finalize cultural performance line-up (Yakshagana / folk dance)",
            "Cultural",
            "medium",
            "Cultural Head",
        ),
        (
            14,
            "Print publicity banners, sponsor boards, and VIP invitation cards",
            "Publicity",
            "medium",
            "Secretary",
        ),
        (
            5,
            "Deploy power backup generator and waste management bins",
            "Logistics",
            "high",
            "Logistics Lead",
        ),
        (
            2,
            "Technical dry-run: microphones, lighting, and stage seating",
            "Sound & Stage",
            "high",
            "Technical Lead",
        ),
        (
            0,
            "Community event execution, stage felicitations, and mass lunch",
            "Coordination",
            "high",
            "General Secretary",
        ),
    ],
}


def check_timeline_compression(
    event_type: str,
    event_date: date | None,
    reference_today: date | None = None,
) -> tuple[bool, str | None]:
    """Determine whether the schedule is compressed due to insufficient lead time."""
    if not event_date:
        return False, None
    today = reference_today or date.today()
    days_available = (event_date - today).days
    clean_type = event_type.lower().strip() if event_type else "wedding"
    templates = TIMELINE_TEMPLATES.get(clean_type, TIMELINE_TEMPLATES["wedding"])
    max_lead_days = max(days for days, _, _, _, _ in templates)

    if days_available < max_lead_days:
        return (
            True,
            f"Compressed timeline advisory: Event is in {days_available} days "
            f"(standard {clean_type} lead time is {max_lead_days} days). Tasks have been "
            "expedited into a compressed schedule; confirm venue and key vendor bookings urgently.",
        )
    return False, None


def generate_timeline(
    event_type: str,
    event_date: date | None,
    reference_today: date | None = None,
) -> list[TimelineItem]:
    """Generate a list of TimelineItem milestones counted back from event_date.

    Guarantees:
    - If event_date is provided, every task has a target_date.
    - reference_today <= target_date <= event_date for all tasks.
    - Strict chronological order (target_date ascending).
    - If lead time is less than standard template duration, marks compressed tasks.
    """
    clean_type = event_type.lower().strip() if event_type else "wedding"
    templates = TIMELINE_TEMPLATES.get(clean_type, TIMELINE_TEMPLATES["wedding"])

    today = reference_today or date.today()

    if not event_date:
        # Relative milestones without fixed dates
        items: list[TimelineItem] = []
        for days_before, task, category, priority, owner in templates:
            phase_name = f"{days_before} days before" if days_before > 0 else "Event Day"
            items.append(
                TimelineItem(
                    phase=phase_name,
                    days_before_event=days_before,
                    target_date=None,
                    task=task,
                    category=category,
                    owner=owner,
                    priority=priority,
                )
            )
        return items

    # If event_date is in the future, count backward and clamp to today
    total_days_available = max(0, (event_date - today).days)

    raw_items: list[tuple[date, int, str, str, str, str, bool]] = []

    for days_before, task, category, priority, owner in templates:
        # Proportionally compress or clamp days_before if event is on short notice
        is_expedited = days_before > total_days_available
        effective_days_before = min(days_before, total_days_available)
        calculated_date = event_date - timedelta(days=effective_days_before)

        # Enforce today <= calculated_date <= event_date
        if calculated_date < today:
            calculated_date = today
        if calculated_date > event_date:
            calculated_date = event_date

        raw_items.append(
            (calculated_date, effective_days_before, task, category, priority, owner, is_expedited)
        )

    # Sort strictly by calculated_date ascending, then by effective_days_before descending
    raw_items.sort(key=lambda x: (x[0], -x[1]))

    # Adjust identical or slightly out-of-order dates to maintain monotonic ordering
    curr_date = today
    final_items: list[TimelineItem] = []

    for calc_date, days_before, task, category, priority, owner, is_expedited in raw_items:
        if calc_date < curr_date:
            calc_date = curr_date
        if calc_date > event_date:
            calc_date = event_date
        curr_date = calc_date

        days_remaining = (event_date - calc_date).days
        if calc_date == event_date:
            phase_name = "Event Day"
        elif is_expedited:
            phase_name = f"{days_remaining}d before (Expedited)"
        else:
            phase_name = f"{days_remaining} days before"

        final_items.append(
            TimelineItem(
                phase=phase_name,
                days_before_event=days_remaining,
                target_date=calc_date,
                task=task,
                category=category,
                owner=owner,
                priority=priority,
            )
        )

    return final_items
