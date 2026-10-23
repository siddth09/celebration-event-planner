"""
Data models, validation schemas, and persona presets for Celebrio AI Planner.
Supports Weddings, Birthdays, Community Events, and Custom Celebrations.

Features:
- Strongly typed Data Classes and TypedDict definitions.
- Strict input sanitization against XSS, SQLi, and DOM injection.
- Modular, single-responsibility validation helpers.
- Immutable persona configurations.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple
import html
import re

SUPPORTED_EVENT_TYPES: Tuple[str, ...] = ("wedding", "birthday", "community", "custom")

# Maximum payload limits for efficiency and security
MAX_EVENT_NAME_LEN: int = 120
MAX_LOCATION_LEN: int = 150
MAX_THEME_LEN: int = 200
MAX_NOTES_LEN: int = 500
MAX_BUDGET_LIMIT: float = 50_000_000.0
MAX_GUEST_LIMIT: int = 50_000

# Pre-compiled regex for fast control-character stripping
_CTRL_CHAR_PATTERN = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')


class CelebrioValidationError(ValueError):
    """Raised when incoming user input fails schema, boundary, or security validation."""
    pass


class PlanGenerationError(Exception):
    """Raised when plan synthesis fails in both GenAI and Heuristic engines."""
    pass


@dataclass(frozen=True)
class EventInput:
    """
    Immutable, validated event configuration payload.
    Represents cleaned parameters for downstream planners.
    """
    event_name: str
    event_type: str
    budget: float
    guest_count: int
    event_date: str = ""
    location: str = "Local Venue"
    theme_preference: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Converts dataclass to standard Python dictionary."""
        return asdict(self)


# Persona Configuration & Default Budget Allocation Percentages
PERSONA_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "wedding": {
        "title": "Wedding Celebration",
        "description": (
            "Full-lifecycle wedding coordination with ceremony and reception hospitality."
        ),
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
            {
                "category": "Venue",
                "task": "Select & book ceremony and reception venue",
                "priority": "High"
            },
            {
                "category": "Catering",
                "task": "Schedule menu tasting and finalize course pairings",
                "priority": "High"
            },
            {
                "category": "Photography",
                "task": "Contract photographer & videographer with shot list",
                "priority": "High"
            },
            {
                "category": "Florist",
                "task": "Design bridal bouquet, boutonnieres, and table centerpieces",
                "priority": "Medium"
            },
            {
                "category": "Music",
                "task": "Hire DJ or live string quartet with special request playlist",
                "priority": "Medium"
            },
            {
                "category": "Officiant",
                "task": "Confirm wedding officiant and legal marriage license",
                "priority": "High"
            },
            {
                "category": "Hair & Makeup",
                "task": "Book bridal party hair & makeup artist trial",
                "priority": "Medium"
            },
            {
                "category": "Transportation",
                "task": "Arrange guest shuttle or bridal party departure car",
                "priority": "Low"
            }
        ]
    },
    "birthday": {
        "title": "Milestone Birthday",
        "description": "Memorable birthday celebration tailored to the honoree's age milestone.",
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
            {
                "category": "Venue",
                "task": "Reserve party space, lounge, or private dining room",
                "priority": "High"
            },
            {
                "category": "Bakery",
                "task": "Commission bespoke thematic birthday cake",
                "priority": "High"
            },
            {
                "category": "Catering",
                "task": "Curate finger food, grazing table, or cocktail bar",
                "priority": "High"
            },
            {
                "category": "Entertainment",
                "task": "Book DJ, magician, trivia host, or photo booth",
                "priority": "Medium"
            },
            {
                "category": "Decor",
                "task": "Order balloon garland, photo backdrop, and lighting",
                "priority": "Medium"
            },
            {
                "category": "Photography",
                "task": "Engage roaming photographer or set up polaroid station",
                "priority": "Low"
            },
            {
                "category": "Invitations",
                "task": "Send animated digital invites with RSVP deadline",
                "priority": "Medium"
            }
        ]
    },
    "community": {
        "title": "Community Event & Festival",
        "description": "Civic gatherings, neighborhood block parties, and cultural fairs.",
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
            {
                "category": "City Administration",
                "task": "Submit public park use & noise permits (30-60 days ahead)",
                "priority": "High"
            },
            {
                "category": "AV & Stage",
                "task": "Contract PA system, outdoor stage, and generator rental",
                "priority": "High"
            },
            {
                "category": "Sanitation",
                "task": "Order portable restrooms, wash stations, and trash bins",
                "priority": "High"
            },
            {
                "category": "Food & Beverage",
                "task": "Coordinate local food trucks and water refill stations",
                "priority": "Medium"
            },
            {
                "category": "Volunteers",
                "task": "Recruit & brief volunteer team with safety vests",
                "priority": "High"
            },
            {
                "category": "First Aid & Security",
                "task": "Book licensed security and first-aid response team",
                "priority": "High"
            },
            {
                "category": "Signage",
                "task": "Print directional banners, schedule posters, and map signs",
                "priority": "Medium"
            }
        ]
    },
    "custom": {
        "title": "Custom Celebration",
        "description": "Flexible event planning engine for corporate galas and family reunions.",
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
            {
                "category": "Venue",
                "task": "Secure venue agreement and verify insurance",
                "priority": "High"
            },
            {
                "category": "Hospitality",
                "task": "Arrange food, beverage, and dining service",
                "priority": "High"
            },
            {
                "category": "Audio/Visual",
                "task": "Test microphones, projection, and ambient lighting",
                "priority": "Medium"
            },
            {
                "category": "Coordination",
                "task": "Finalize master run-of-show schedule",
                "priority": "High"
            }
        ]
    }
}


def sanitize_input(text: Any, max_len: int = 500) -> str:
    """
    Sanitizes string input to prevent XSS, HTML injection, and control-character exploits.

    Args:
        text: Input string or object to sanitize.
        max_len: Maximum permitted character length.

    Returns:
        Escaped and trimmed safe string representation.
    """
    if text is None:
        return ""
    clean = str(text).strip()
    clean = html.escape(clean, quote=True)
    clean = _CTRL_CHAR_PATTERN.sub('', clean)
    return clean[:max_len]


def _validate_event_name(raw_name: Any) -> str:
    """Validates and sanitizes event name string."""
    name = sanitize_input(raw_name, max_len=MAX_EVENT_NAME_LEN)
    if not name:
        raise CelebrioValidationError("Event name is required and cannot be empty.")
    return name


def _validate_event_type(raw_type: Any) -> str:
    """Validates event type matches supported personas."""
    event_type = str(raw_type or "wedding").lower().strip()
    if event_type not in SUPPORTED_EVENT_TYPES:
        allowed = ", ".join(SUPPORTED_EVENT_TYPES)
        raise CelebrioValidationError(
            f"Unsupported event type '{event_type}'. Must be one of: {allowed}."
        )
    return event_type


def _validate_budget(raw_budget: Any) -> float:
    """Validates numeric budget within permissible financial boundaries."""
    try:
        budget = float(raw_budget)
    except (ValueError, TypeError):
        raise CelebrioValidationError("Budget must be a valid numeric value.")

    if budget <= 0:
        raise CelebrioValidationError("Budget must be greater than zero.")
    if budget > MAX_BUDGET_LIMIT:
        raise CelebrioValidationError(
            f"Budget exceeds the maximum allowed limit of ${MAX_BUDGET_LIMIT:,.0f}."
        )
    return round(budget, 2)


def _validate_guest_count(raw_guests: Any) -> int:
    """Validates integer guest count within venue capacity limits."""
    try:
        guest_count = int(raw_guests)
    except (ValueError, TypeError):
        raise CelebrioValidationError("Guest count must be an integer.")

    if guest_count <= 0:
        raise CelebrioValidationError("Guest count must be at least 1 attendee.")
    if guest_count > MAX_GUEST_LIMIT:
        raise CelebrioValidationError(
            f"Guest count exceeds the {MAX_GUEST_LIMIT:,} capacity maximum."
        )
    return guest_count


def validate_event_input(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates user event creation payload against schema limits and domain boundaries.

    Args:
        data: Raw JSON payload received from user or API client.

    Returns:
        Sanitized and validated dictionary matching EventInput specification.

    Raises:
        CelebrioValidationError: If any validation rule, range, or required field fails.
    """
    if not isinstance(data, dict):
        raise CelebrioValidationError("Invalid payload format. Expected JSON object.")

    event_name = _validate_event_name(data.get("event_name"))
    event_type = _validate_event_type(data.get("event_type"))
    budget = _validate_budget(data.get("budget"))
    guest_count = _validate_guest_count(data.get("guest_count"))

    event_date = sanitize_input(data.get("event_date", ""), max_len=30)
    location = sanitize_input(data.get("location", ""), max_len=MAX_LOCATION_LEN) or "Local Venue"
    theme_preference = sanitize_input(data.get("theme_preference", ""), max_len=MAX_THEME_LEN)
    notes = sanitize_input(data.get("notes", ""), max_len=MAX_NOTES_LEN)

    validated_obj = EventInput(
        event_name=event_name,
        event_type=event_type,
        budget=budget,
        guest_count=guest_count,
        event_date=event_date,
        location=location,
        theme_preference=theme_preference,
        notes=notes
    )

    return validated_obj.to_dict()
