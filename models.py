"""
Data models, validation schemas, and persona presets for Celebrio AI Planner.
Supports Weddings, Birthdays, and Community Events.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import html
import re

SUPPORTED_EVENT_TYPES = ("wedding", "birthday", "community", "custom")

# Persona Configuration & Default Budget Allocation Percentages
PERSONA_DEFAULTS = {
    "wedding": {
        "title": "Wedding Celebration",
        "description": "Full-lifecycle wedding coordination with ceremony, reception, and guest hospitality.",
        "icon": "💍",
        "budget_splits": {
            "Venue & Rentals": 0.35,
            "Catering & Bar": 0.28,
            "Photography & Video": 0.12,
            "Decor & Floral": 0.10,
            "Music & Entertainment": 0.07,
            "Stationery & Favors": 0.03,
            "Emergency Contingency": 0.05
        },
        "default_vendors": [
            {"category": "Venue", "task": "Select & book ceremony and reception venue", "priority": "High"},
            {"category": "Catering", "task": "Schedule menu tasting and finalize course pairings", "priority": "High"},
            {"category": "Photography", "task": "Contract photographer & videographer with shot list", "priority": "High"},
            {"category": "Florist", "task": "Design bridal bouquet, boutonnieres, and table centerpieces", "priority": "Medium"},
            {"category": "Music", "task": "Hire DJ or live string quartet with special request playlist", "priority": "Medium"},
            {"category": "Officiant", "task": "Confirm wedding officiant and legal marriage license", "priority": "High"},
            {"category": "Hair & Makeup", "task": "Book bridal party hair & makeup artist trial", "priority": "Medium"},
            {"category": "Transportation", "task": "Arrange guest shuttle or bridal party departure car", "priority": "Low"}
        ]
    },
    "birthday": {
        "title": "Milestone Birthday",
        "description": "Memorable birthday celebration tailored to the honoree's age milestone and passions.",
        "icon": "🎂",
        "budget_splits": {
            "Venue & Space": 0.30,
            "Food & Beverages": 0.32,
            "Entertainment & Games": 0.15,
            "Decor & Balloons": 0.10,
            "Custom Cake & Sweets": 0.05,
            "Favors & Keepsakes": 0.03,
            "Contingency Reserve": 0.05
        },
        "default_vendors": [
            {"category": "Venue", "task": "Reserve party space, lounge, or private dining room", "priority": "High"},
            {"category": "Bakery", "task": "Commission bespoke thematic birthday cake", "priority": "High"},
            {"category": "Catering", "task": "Curate finger food, grazing table, or cocktail bar", "priority": "High"},
            {"category": "Entertainment", "task": "Book DJ, magician, trivia host, or photo booth", "priority": "Medium"},
            {"category": "Decor", "task": "Order balloon garland, photo backdrop, and lighting", "priority": "Medium"},
            {"category": "Photography", "task": "Engage roaming photographer or set up polaroid station", "priority": "Low"},
            {"category": "Invitations", "task": "Send animated digital invites with RSVP deadline", "priority": "Medium"}
        ]
    },
    "community": {
        "title": "Community Event & Festival",
        "description": "Civic gatherings, neighborhood block parties, charity fundraisers, and cultural fairs.",
        "icon": "🎪",
        "budget_splits": {
            "Permits & City Fees": 0.12,
            "Venue / Park Rental": 0.22,
            "Stage & Sound Equipment": 0.20,
            "Food Trucks & Refreshments": 0.18,
            "Safety, Sanitation & EMS": 0.12,
            "Signage & Promotion": 0.08,
            "Weather / Emergency Buffer": 0.08
        },
        "default_vendors": [
            {"category": "City Administration", "task": "Submit public park use & noise permits (30-60 days ahead)", "priority": "High"},
            {"category": "AV & Stage", "task": "Contract PA system, outdoor stage, and generator rental", "priority": "High"},
            {"category": "Sanitation", "task": "Order portable restrooms, wash stations, and trash bins", "priority": "High"},
            {"category": "Food & Beverage", "task": "Coordinate local food trucks and water refill stations", "priority": "Medium"},
            {"category": "Volunteers", "task": "Recruit & brief volunteer team with safety vests", "priority": "High"},
            {"category": "First Aid & Security", "task": "Book licensed security and first-aid response team", "priority": "High"},
            {"category": "Signage", "task": "Print directional banners, schedule posters, and map signs", "priority": "Medium"}
        ]
    },
    "custom": {
        "title": "Custom Celebration",
        "description": "Flexible event planning engine for corporate galas, anniversaries, and family reunions.",
        "icon": "✨",
        "budget_splits": {
            "Venue & Hospitality": 0.35,
            "Food & Drink": 0.30,
            "AV & Production": 0.15,
            "Decor & Ambience": 0.10,
            "Marketing / Collateral": 0.05,
            "Contingency": 0.05
        },
        "default_vendors": [
            {"category": "Venue", "task": "Secure venue agreement and verify insurance", "priority": "High"},
            {"category": "Hospitality", "task": "Arrange food, beverage, and dining service", "priority": "High"},
            {"category": "Audio/Visual", "task": "Test microphones, projection, and ambient lighting", "priority": "Medium"},
            {"category": "Coordination", "task": "Finalize master run-of-show schedule", "priority": "High"}
        ]
    }
}


def sanitize_input(text: Any, max_len: int = 500) -> str:
    """Sanitize string input to prevent XSS and strip control characters."""
    if text is None:
        return ""
    clean = str(text).strip()
    clean = html.escape(clean)
    clean = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean)
    return clean[:max_len]


def validate_event_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates user event creation payload.
    Raises ValueError with descriptive human-readable errors for invalid inputs.
    """
    if not isinstance(data, dict):
        raise ValueError("Invalid payload format. Expected JSON object.")

    event_name = sanitize_input(data.get("event_name", ""), max_len=120)
    if not event_name:
        raise ValueError("Event name is required and cannot be empty.")

    event_type = str(data.get("event_type", "wedding")).lower().strip()
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(
            f"Unsupported event type '{event_type}'. Must be one of: {', '.join(SUPPORTED_EVENT_TYPES)}."
        )

    # Validate Budget
    raw_budget = data.get("budget", 0)
    try:
        budget = float(raw_budget)
    except (ValueError, TypeError):
        raise ValueError("Budget must be a valid numeric value.")
    
    if budget <= 0:
        raise ValueError("Budget must be greater than zero.")
    if budget > 50_000_000:
        raise ValueError("Budget exceeds the maximum allowed limit of $50,000,000.")

    # Validate Guest Count
    raw_guests = data.get("guest_count", 0)
    try:
        guest_count = int(raw_guests)
    except (ValueError, TypeError):
        raise ValueError("Guest count must be an integer.")

    if guest_count <= 0:
        raise ValueError("Guest count must be at least 1 attendee.")
    if guest_count > 50_000:
        raise ValueError("Guest count exceeds the 50,000 capacity maximum.")

    event_date = sanitize_input(data.get("event_date", ""), max_len=30)
    location = sanitize_input(data.get("location", ""), max_len=150) or "Local Venue"
    theme_preference = sanitize_input(data.get("theme_preference", ""), max_len=200)
    notes = sanitize_input(data.get("notes", ""), max_len=500)

    return {
        "event_name": event_name,
        "event_type": event_type,
        "budget": round(budget, 2),
        "guest_count": guest_count,
        "event_date": event_date,
        "location": location,
        "theme_preference": theme_preference,
        "notes": notes
    }
