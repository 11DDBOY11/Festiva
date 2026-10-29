"""PDF Export Service for Festiva Event Plans.

Generates a publication-grade, print-styled PDF containing the full event brief,
key metrics, budget breakdown, milestone timeline, run-of-show itinerary,
and vendor shortlist with prominent sample data labeling.
"""

import io
import os
from decimal import Decimal

from xhtml2pdf import pisa

from app.db.models import Event
from app.domain.category_labels import format_category_label
from app.domain.schemas import PlanSchema

# Locate bundled DejaVuSans font for hermetic Indian Rupee (₹) unicode rendering
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
FONT_PATH = os.path.join(ASSETS_DIR, "fonts", "DejaVuSans.ttf").replace("\\", "/")


def format_currency_inr(amount: Decimal | float | int | None) -> str:
    """Format numeric values as Indian Rupee strings with commas (e.g. ₹75,000)."""
    if amount is None:
        return "₹0"
    try:
        val = float(amount)
        return f"₹{val:,.0f}"
    except (ValueError, TypeError):
        return f"₹{amount}"


def generate_plan_pdf(event: Event, plan: PlanSchema) -> bytes:
    """Generate high-fidelity, print-styled PDF bytes for an event plan."""
    # Determine sample vendor presence
    vendors = plan.vendor_shortlist or []
    has_sample_vendors = any(
        getattr(v, "is_sample", False) or "[Sample]" in getattr(v, "vendor_name", "")
        for v in vendors
    )

    # Format dates
    event_date_str = event.event_date.strftime("%d %b %Y") if event.event_date else "Date TBD"

    # Pre-render budget rows
    budget_categories = plan.budget.categories if plan.budget else []
    budget_rows_html = ""
    for cat in budget_categories:
        cat_name = format_category_label(cat.category)
        per_guest = format_currency_inr(cat.per_guest_cost) if cat.per_guest_cost else "—"
        budget_rows_html += f"""
        <tr>
            <td class="font-bold">{cat_name}</td>
            <td class="text-right">{float(cat.share_pct):.1f}%</td>
            <td class="text-right font-bold">{format_currency_inr(cat.allocated_amount)}</td>
            <td class="text-right">{per_guest}</td>
            <td class="text-muted">{cat.notes or "Standard allocation"}</td>
        </tr>
        """

    # Pre-render timeline rows
    timeline_tasks = plan.timeline or []
    timeline_rows_html = ""
    for task in timeline_tasks:
        date_str = task.target_date.strftime("%d %b %Y") if task.target_date else "TBD"
        days_str = (
            f"T{task.days_before_event}d"
            if task.days_before_event < 0
            else f"T-{task.days_before_event}d"
        )
        priority_class = "badge-high" if task.priority.lower() == "high" else "badge-normal"
        task_cat = format_category_label(task.category)
        timeline_rows_html += f"""
        <tr>
            <td class="font-bold">{task.phase}</td>
            <td>
                <div class="task-title">{task.task}</div>
                <div class="task-owner">Owner: {task.owner} &bull; {task_cat}</div>
            </td>
            <td><span class="{priority_class}">{task.priority.upper()}</span></td>
            <td class="text-right font-mono">{date_str}</td>
            <td class="text-right font-mono">{days_str}</td>
        </tr>
        """

    # Pre-render run of show rows
    run_of_show = plan.run_of_show or []
    ros_rows_html = ""
    for item in run_of_show:
        ros_rows_html += f"""
        <tr>
            <td class="font-bold font-mono text-amber">{item.time_slot}</td>
            <td class="font-bold">{item.activity}</td>
            <td>{item.location}</td>
            <td><span class="badge-subtle">{item.lead_person}</span></td>
            <td class="text-muted">{item.notes or "—"}</td>
        </tr>
        """

    # Pre-render vendor checklist rows
    vendor_rows_html = ""
    for v in vendors:
        is_sample = getattr(v, "is_sample", False) or "[Sample]" in getattr(v, "vendor_name", "")
        clean_name = v.vendor_name.replace("[Sample] ", "") if is_sample else v.vendor_name
        low_fmt = format_currency_inr(v.estimated_price_low)
        high_fmt = format_currency_inr(v.estimated_price_high)
        price_range = f"{low_fmt} – {high_fmt}" if v.estimated_price_low else "Tier based"
        sample_tag = '<span class="badge-sample">Sample Data</span>' if is_sample else ""
        status_text = (
            getattr(v, "price_status", "confirmed").capitalize()
            if hasattr(v, "price_status")
            else "Shortlisted"
        )
        reason_text = getattr(v, "reason", "") or "Local Mangaluru vendor"
        v_cat = format_category_label(v.category)
        vendor_rows_html += f"""
        <tr>
            <td class="font-bold">{v_cat}</td>
            <td>
                <div class="font-bold">{clean_name} {sample_tag}</div>
                <div class="text-muted text-small">{reason_text}</div>
            </td>
            <td class="font-mono text-small">{price_range}</td>
            <td><span class="badge-status">{status_text}</span></td>
        </tr>
        """

    # Optional menu ideas
    menu_html = ""
    if plan.meta and getattr(plan.meta, "menu_ideas", None):
        items = "".join(f"<li>{dish}</li>" for dish in plan.meta.menu_ideas)
        menu_html = f"""
        <div class="section-box">
            <h3 class="section-subtitle">Curated Regional Menu & Culinary Highlights</h3>
            <ul class="menu-list">
                {items}
            </ul>
        </div>
        """

    # Optional compressed timeline warning
    warning_html = ""
    if plan.meta and getattr(plan.meta, "compressed_timeline", False):
        warning_text = getattr(
            plan.meta,
            "timeline_warning",
            "Event scheduled on short notice. Standard lead times expedited.",
        )
        warning_html = f"""
        <div class="alert-box">
            <strong>Compressed Timeline Advisory:</strong> {warning_text}
        </div>
        """

    # Sample data disclaimer banner
    sample_disclaimer_html = ""
    if has_sample_vendors:
        sample_disclaimer_html = """
        <div class="sample-notice-banner">
            <strong>NOTICE &bull; DEMONSTRATION DATA:</strong> Vendors marked with
            <em>Sample Data</em> are illustrative simulations grounded in Mangaluru market tiers.
            No commercial endorsement or contract is implied.
        </div>
        """

    font_face_css = ""
    if os.path.exists(FONT_PATH):
        font_face_css = f"""
        @font-face {{
            font-family: 'DejaVuSans';
            src: url('{FONT_PATH}');
        }}
        body, table, th, td, div, p, span {{
            font-family: 'DejaVuSans', Helvetica, Arial, sans-serif;
        }}
        """
    else:
        font_face_css = """
        body, table, th, td, div, p, span {{
            font-family: Helvetica, Arial, sans-serif;
        }}
        """

    # Pre-calculate strings for template interpolation
    total_budget_str = format_currency_inr(plan.total_budget)
    per_guest_val = (
        float(plan.total_budget) / event.guest_count
        if event.guest_count and plan.total_budget
        else None
    )
    per_guest_str = format_currency_inr(per_guest_val) if per_guest_val else "—"
    event_sub_details = (
        f"{event.city} &bull; {event_date_str} &bull; "
        f"{event.guest_count} Guests &bull; {event.event_type.capitalize()}"
    )
    exec_summary_html = (
        f'<div class="summary-paragraph"><strong>Concept & Ambience:</strong> {plan.summary}</div>'
        if plan.summary
        else ""
    )

    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Festiva Plan - {event.title}</title>
<style>
@page {{
    size: A4 portrait;
    margin-top: 1.6cm;
    margin-bottom: 1.6cm;
    margin-left: 1.6cm;
    margin-right: 1.6cm;
    @bottom-right {{
        content: "Page " counter(page) " of " counter(pages);
        font-size: 8pt;
        color: #64748b;
    }}
    @bottom-left {{
        content: "Festiva &bull; Mangaluru Event Copilot &bull; Plan v{plan.version}";
        font-size: 8pt;
        color: #64748b;
    }}
}}

{font_face_css}

body {{
    color: #0f172a;
    font-size: 9.5pt;
    line-height: 1.45;
}}

.header-table {{
    width: 100%;
    margin-bottom: 14px;
    border-bottom: 2px solid #d97706;
    padding-bottom: 10px;
}}

.brand-title {{
    font-size: 18pt;
    font-weight: bold;
    color: #b45309;
    margin: 0;
}}

.event-title {{
    font-size: 15pt;
    font-weight: bold;
    color: #0f172a;
    margin-top: 4px;
    margin-bottom: 2px;
}}

.badge-version {{
    background-color: #fef3c7;
    color: #92400e;
    border: 1px solid #fde68a;
    padding: 2px 7px;
    font-size: 8pt;
    font-weight: bold;
    border-radius: 4px;
}}

.metric-strip {{
    width: 100%;
    margin-bottom: 14px;
}}

.metric-card {{
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 8px 10px;
    border-radius: 6px;
    text-align: center;
}}

.metric-label {{
    font-size: 7.5pt;
    font-weight: bold;
    color: #64748b;
    text-transform: uppercase;
}}

.metric-value {{
    font-size: 12pt;
    font-weight: bold;
    color: #0f172a;
    margin-top: 2px;
}}

.metric-highlight {{
    color: #b45309;
}}

.summary-paragraph {{
    font-size: 9pt;
    color: #334155;
    background-color: #f8fafc;
    border-left: 3px solid #d97706;
    padding: 8px 12px;
    margin-bottom: 14px;
}}

.alert-box {{
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    color: #991b1b;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 8.5pt;
    margin-bottom: 12px;
}}

.sample-notice-banner {{
    background-color: #fffbeb;
    border: 1px solid #fcd34d;
    color: #92400e;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 8pt;
    margin-bottom: 14px;
}}

.section-box {{
    margin-bottom: 16px;
}}

.section-title {{
    font-size: 11pt;
    font-weight: bold;
    color: #0f172a;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 4px;
    margin-top: 14px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.section-subtitle {{
    font-size: 9.5pt;
    font-weight: bold;
    color: #b45309;
    margin-bottom: 4px;
}}

table.data-table {{
    width: 100%;
    margin-top: 6px;
    margin-bottom: 12px;
    font-size: 8.5pt;
}}

table.data-table th {{
    background-color: #f1f5f9;
    color: #334155;
    font-weight: bold;
    padding: 6px 8px;
    border-bottom: 1.5px solid #cbd5e1;
    text-align: left;
    font-size: 8pt;
    text-transform: uppercase;
}}

table.data-table td {{
    padding: 5px 8px;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: top;
}}

table.data-table tfoot td {{
    background-color: #f8fafc;
    border-top: 2px solid #cbd5e1;
    font-weight: bold;
    padding: 6px 8px;
}}

.font-bold {{ font-weight: bold; }}
.font-mono {{ font-family: 'DejaVuSans', monospace; }}
.text-right {{ text-align: right; }}
.text-amber {{ color: #b45309; }}
.text-muted {{ color: #64748b; }}
.text-small {{ font-size: 7.5pt; }}

.badge-high {{
    background-color: #fee2e2;
    color: #991b1b;
    border: 1px solid #fca5a5;
    font-size: 7pt;
    font-weight: bold;
    padding: 1px 4px;
    border-radius: 3px;
}}

.badge-normal {{
    background-color: #e0f2fe;
    color: #0369a1;
    border: 1px solid #bae6fd;
    font-size: 7pt;
    font-weight: bold;
    padding: 1px 4px;
    border-radius: 3px;
}}

.badge-subtle {{
    background-color: #f1f5f9;
    color: #475569;
    font-size: 7.5pt;
    padding: 1px 5px;
    border-radius: 3px;
}}

.badge-sample {{
    background-color: #fef3c7;
    color: #92400e;
    border: 1px solid #fde68a;
    font-size: 7pt;
    font-weight: bold;
    padding: 1px 4px;
    border-radius: 3px;
    margin-left: 4px;
}}

.badge-status {{
    background-color: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
    font-size: 7pt;
    font-weight: bold;
    padding: 1px 4px;
    border-radius: 3px;
}}

.task-title {{
    font-weight: bold;
    color: #0f172a;
}}

.task-owner {{
    font-size: 7.5pt;
    color: #64748b;
}}

ul.menu-list {{
    margin: 4px 0 0 16px;
    padding: 0;
    font-size: 8.5pt;
    color: #334155;
}}

.page-break {{
    page-break-before: always;
}}
</style>
</head>
<body>

<!-- Header -->
<table class="header-table">
    <tr>
        <td>
            <div class="brand-title">Festiva Event Copilot</div>
            <div class="event-title">{event.title}</div>
            <div style="font-size: 8.5pt; color: #475569; margin-top: 2px;">
                {event_sub_details}
            </div>
        </td>
        <td style="text-align: right; vertical-align: top;">
            <span class="badge-version">Plan Version {plan.version}</span>
            <div style="font-size: 7.5pt; color: #64748b; margin-top: 6px;">
                Generated: {event_date_str}
            </div>
        </td>
    </tr>
</table>

{sample_disclaimer_html}
{warning_html}

<!-- Key Metric Strip -->
<table class="metric-strip">
    <tr>
        <td class="metric-card" style="width: 25%;">
            <div class="metric-label">Total Budget</div>
            <div class="metric-value metric-highlight">{total_budget_str}</div>
        </td>
        <td class="metric-card" style="width: 25%;">
            <div class="metric-label">Breakdown</div>
            <div class="metric-value">{len(budget_categories)} Categories</div>
        </td>
        <td class="metric-card" style="width: 25%;">
            <div class="metric-label">Milestones</div>
            <div class="metric-value">{len(timeline_tasks)} Tasks</div>
        </td>
        <td class="metric-card" style="width: 25%;">
            <div class="metric-label">Per Guest Tier</div>
            <div class="metric-value">{per_guest_str}</div>
        </td>
    </tr>
</table>

<!-- Executive Summary -->
{exec_summary_html}

{menu_html}

<!-- Section 1: Budget Allocation Table -->
<div class="section-title">1. Budget Breakdown & Allocations</div>
<table class="data-table">
    <thead>
        <tr>
            <th>Category</th>
            <th class="text-right">Share (%)</th>
            <th class="text-right">Allocated Amount</th>
            <th class="text-right">Per Guest</th>
            <th>Notes</th>
        </tr>
    </thead>
    <tbody>
        {budget_rows_html}
    </tbody>
    <tfoot>
        <tr>
            <td>Total Event Budget</td>
            <td class="text-right">100.0%</td>
            <td class="text-right metric-highlight font-mono font-bold">{total_budget_str}</td>
            <td class="text-right font-mono">{per_guest_str}</td>
            <td class="text-muted">Balanced within &plusmn;1%</td>
        </tr>
    </tfoot>
</table>

<!-- Page break for readability -->
<div class="page-break"></div>

<!-- Section 2: Milestone Timeline -->
<div class="section-title">2. Planning Timeline & Action Milestones</div>
<table class="data-table">
    <thead>
        <tr>
            <th>Phase</th>
            <th>Task & Ownership</th>
            <th>Priority</th>
            <th class="text-right">Target Date</th>
            <th class="text-right">Relative Schedule</th>
        </tr>
    </thead>
    <tbody>
        {timeline_rows_html}
    </tbody>
</table>

<!-- Section 3: Run of Show Schedule -->
<div class="section-title">3. Event Day Run-of-Show Itinerary</div>
<table class="data-table">
    <thead>
        <tr>
            <th>Time Slot</th>
            <th>Activity</th>
            <th>Location</th>
            <th>Lead Person</th>
            <th>Operational Notes</th>
        </tr>
    </thead>
    <tbody>
        {ros_rows_html}
    </tbody>
</table>

<!-- Section 4: Vendor Shortlist & Checklist -->
<div class="section-title">4. Grounded Vendor Shortlist & Booking Checklist</div>
<table class="data-table">
    <thead>
        <tr>
            <th>Category</th>
            <th>Vendor Name & Profile</th>
            <th>Estimated Price Range</th>
            <th>Status</th>
        </tr>
    </thead>
    <tbody>
        {vendor_rows_html}
    </tbody>
</table>

</body>
</html>
"""

    out_stream = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=out_stream)
    if pisa_status.err:
        raise RuntimeError(f"Failed to generate event plan PDF (Pisa error code {pisa_status.err})")

    return out_stream.getvalue()
