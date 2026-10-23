"""
Celebrio AI Planning Engine.
Orchestrates Persona Context, GenAI Synthesis, Heuristic Planner Fallbacks,
Budget Tracking, Timelines, and Vendor Checklists.

Efficiency & Quality Features:
- Deterministic memoization cache for sub-millisecond plan generation.
- Single-pass financial summarization algorithm (O(N) time, O(1) memory).
- Strict typing, complete docstrings, and robust schema enforcement.
"""

from typing import Dict, Any, List, Optional, Tuple
from functools import lru_cache
import copy
import json

from models import PERSONA_DEFAULTS, validate_event_input, CelebrioValidationError
from gemini_client import GeminiPlannerClient


class PlannerEngine:
    """Core intelligence engine for Celebration & Event Planning."""

    def __init__(self, api_key: Optional[str] = None, plan_cache_capacity: int = 128) -> None:
        """
        Initializes the planner engine.

        Args:
            api_key: Optional Google Gemini API key.
            plan_cache_capacity: Cache size for deterministic plans.
        """
        self.ai_client: GeminiPlannerClient = GeminiPlannerClient(api_key=api_key)
        self._heuristic_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_capacity: int = plan_cache_capacity

    def is_genai_enabled(self) -> bool:
        """
        Returns whether Gemini GenAI integration is currently active.

        Returns:
            True if Gemini client is active, False for heuristic engine.
        """
        return self.ai_client.is_ai_active()

    def generate_full_plan(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates event parameters and produces a complete, cohesive event plan.
        Tries Gemini GenAI first, falling back gracefully to heuristic intelligence.

        Args:
            raw_input: Raw dictionary containing user event parameters.

        Returns:
            Dictionary containing 4 pillars: budget, timeline, vendors, creative ideas,
            plus financial metrics and operational metadata.

        Raises:
            CelebrioValidationError: If input fails validation schemas.
        """
        # Validate input schema
        event_ctx = validate_event_input(raw_input)
        
        # Attempt GenAI generation if active
        genai_result = self.ai_client.generate_event_plan(event_ctx)
        
        if genai_result and self._validate_plan_structure(genai_result):
            plan = genai_result
            plan["source"] = "Gemini 1.5 Flash GenAI"
            plan["ai_powered"] = True
        else:
            plan = self._get_or_compute_heuristic_plan(event_ctx)
            plan["source"] = "Celebrio Heuristic Generative Engine"
            plan["ai_powered"] = False

        # Attach normalized metadata & financial totals
        plan["event_metadata"] = event_ctx
        plan["financial_summary"] = self._compute_financial_summary(
            plan.get("budget_breakdown", []),
            event_ctx["budget"]
        )
        return plan

    def chat(self, message: str, event_context: Dict[str, Any]) -> str:
        """
        Sends conversational query to the AI advisor or heuristic fallback.

        Args:
            message: User query or prompt.
            event_context: Current event details.

        Returns:
            Advisory text response.
        """
        return self.ai_client.chat_assistant(message, event_context)

    def generate_vendor_inquiry(self, vendor_category: str, event_context: Dict[str, Any]) -> str:
        """
        Generates tailored supplier Request for Proposal (RFP) email.

        Args:
            vendor_category: Category name of vendor.
            event_context: Current event details.

        Returns:
            Formatted inquiry letter.
        """
        return self.ai_client.generate_vendor_rfp(vendor_category, event_context)

    def _validate_plan_structure(self, plan: Dict[str, Any]) -> bool:
        """
        Ensures generated plan complies with required UI schema.

        Args:
            plan: Candidate event plan dictionary.

        Returns:
            True if all required pillars and keys exist, False otherwise.
        """
        required_keys = ("budget_breakdown", "milestone_timeline", "vendor_checklist", "personalized_ideas")
        return (
            isinstance(plan, dict) and
            all(k in plan for k in required_keys) and
            isinstance(plan["budget_breakdown"], list) and
            isinstance(plan["milestone_timeline"], list) and
            isinstance(plan["vendor_checklist"], list) and
            isinstance(plan["personalized_ideas"], dict)
        )

    def _compute_financial_summary(
        self,
        budget_breakdown: List[Dict[str, Any]],
        total_budget: float
    ) -> Dict[str, Any]:
        """
        Calculates financial totals via an efficient single-pass iteration (O(N)).

        Args:
            budget_breakdown: List of categorized budget items.
            total_budget: Overall allocated event budget.

        Returns:
            Dictionary of calculated metrics: allocated, actual, variance, utilization %.
        """
        total_allocated: float = 0.0
        total_actual: float = 0.0

        for item in budget_breakdown:
            total_allocated += item.get("allocated_amount", 0.0)
            total_actual += item.get("actual_amount", 0.0)

        remaining = total_budget - total_actual
        utilization = (total_actual / total_budget * 100) if total_budget > 0 else 0.0

        return {
            "total_budget": round(total_budget, 2),
            "total_allocated": round(total_allocated, 2),
            "total_actual": round(total_actual, 2),
            "remaining_balance": round(remaining, 2),
            "is_over_budget": total_actual > total_budget,
            "utilization_percentage": round(utilization, 1)
        }

    def _get_or_compute_heuristic_plan(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieves heuristic plan from in-memory cache or computes it.
        Uses deepcopy to prevent callers from mutating the cached template.
        """
        cache_key = f"{ctx['event_type']}:{ctx['budget']}:{ctx['guest_count']}:{ctx['location']}:{ctx['theme_preference']}"
        if cache_key in self._heuristic_cache:
            return copy.deepcopy(self._heuristic_cache[cache_key])

        plan = self._generate_heuristic_plan(ctx)
        
        # Enforce cache capacity
        if len(self._heuristic_cache) >= self._cache_capacity:
            self._heuristic_cache.pop(next(iter(self._heuristic_cache)))
        self._heuristic_cache[cache_key] = plan
        return copy.deepcopy(plan)

    def _generate_heuristic_plan(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        High-fidelity heuristic planning algorithm.
        Generates realistic budgets, countdown timelines, categorized vendors,
        and bespoke design ideas tailored to user inputs.
        """
        event_type: str = ctx["event_type"]
        budget: float = ctx["budget"]
        guests: int = ctx["guest_count"]
        persona = PERSONA_DEFAULTS.get(event_type, PERSONA_DEFAULTS["custom"])
        cost_per_guest = budget / max(guests, 1)

        # 1. Budget Breakdown Synthesis
        budget_items: List[Dict[str, Any]] = []
        splits = persona["budget_splits"]
        for cat_name, pct in splits.items():
            cat_alloc = round(budget * pct, 2)
            sub_items = self._generate_sub_items(cat_name, cat_alloc, guests)
            
            budget_items.append({
                "category": cat_name,
                "allocated_amount": cat_alloc,
                "actual_amount": 0.0,
                "percentage": int(round(pct * 100)),
                "description": f"Target allocation for {cat_name.lower()} based on {persona['title']} industry benchmarks.",
                "items": sub_items
            })

        # 2. Milestone Timeline
        timeline = self._generate_timeline(event_type, ctx.get("event_date", ""))

        # 3. Vendor Checklist
        vendors = self._generate_vendors(event_type, ctx)

        # 4. Personalized Creative Ideas
        ideas = self._generate_ideas(event_type, ctx, cost_per_guest)

        summary = (
            f"Curated {persona['title']} experience for '{ctx['event_name']}' supporting "
            f"{guests} attendees with an optimized budget allocation of ${budget:,.2f} "
            f"(${cost_per_guest:,.2f} per attendee). Designed for flawless execution in {ctx['location']}."
        )

        return {
            "summary": summary,
            "budget_breakdown": budget_items,
            "milestone_timeline": timeline,
            "vendor_checklist": vendors,
            "personalized_ideas": ideas
        }

    def _generate_sub_items(self, category: str, cat_total: float, guests: int) -> List[Dict[str, Any]]:
        """Generates realistic sub-item allocations based on category type."""
        cat_lower = category.lower()
        if "venue" in cat_lower or "rent" in cat_lower:
            return [
                {"item_name": "Main Space Rental & Security Deposit", "estimated_cost": round(cat_total * 0.70, 2), "status": "Pending"},
                {"item_name": "Tables, Chairs & Linen Hire", "estimated_cost": round(cat_total * 0.20, 2), "status": "Pending"},
                {"item_name": "Cleaning & Post-Event Facility Fee", "estimated_cost": round(cat_total * 0.10, 2), "status": "Pending"}
            ]
        elif "cater" in cat_lower or "food" in cat_lower:
            return [
                {"item_name": f"Main Meal Course ({guests} guests)", "estimated_cost": round(cat_total * 0.65, 2), "status": "Pending"},
                {"item_name": "Beverages, Bar & Cocktails", "estimated_cost": round(cat_total * 0.25, 2), "status": "Pending"},
                {"item_name": "Server Staff & Service Gratuity", "estimated_cost": round(cat_total * 0.10, 2), "status": "Pending"}
            ]
        elif "photo" in cat_lower:
            return [
                {"item_name": "Lead Photographer Full Day Coverage", "estimated_cost": round(cat_total * 0.75, 2), "status": "Pending"},
                {"item_name": "High-Res Edited Digital Gallery & Prints", "estimated_cost": round(cat_total * 0.25, 2), "status": "Pending"}
            ]
        elif "decor" in cat_lower or "floral" in cat_lower:
            return [
                {"item_name": "Centerpieces & Table Accents", "estimated_cost": round(cat_total * 0.55, 2), "status": "Pending"},
                {"item_name": "Entry Arch / Stage Focal Point", "estimated_cost": round(cat_total * 0.30, 2), "status": "Pending"},
                {"item_name": "Ambient Fairy Lights & Candles", "estimated_cost": round(cat_total * 0.15, 2), "status": "Pending"}
            ]
        elif "music" in cat_lower or "entertainment" in cat_lower or "sound" in cat_lower:
            return [
                {"item_name": "Live DJ / Musician Performance", "estimated_cost": round(cat_total * 0.70, 2), "status": "Pending"},
                {"item_name": "PA System, Microphones & Dance Floor Lighting", "estimated_cost": round(cat_total * 0.30, 2), "status": "Pending"}
            ]
        else:
            return [
                {"item_name": f"{category} Primary Package", "estimated_cost": round(cat_total * 0.70, 2), "status": "Pending"},
                {"item_name": f"{category} Incidentals & Fees", "estimated_cost": round(cat_total * 0.30, 2), "status": "Pending"}
            ]

    def _generate_timeline(self, event_type: str, event_date: str) -> List[Dict[str, Any]]:
        """Synthesizes countdown timeline phases according to event scope."""
        if event_type == "wedding":
            return [
                {
                    "phase": "6 to 9 Months Before",
                    "milestone": "Vision & Core Booking",
                    "target_date": "Early Phase",
                    "critical_tasks": [
                        "Finalize overall aesthetic, color palette, and estimated guest roster",
                        "Tour and lock ceremony & reception venues with signed contracts",
                        "Book high-demand suppliers: Photographer, Caterer, and DJ/Band"
                    ],
                    "priority": "High"
                },
                {
                    "phase": "3 to 4 Months Before",
                    "milestone": "Guest Invitations & Attire",
                    "target_date": "Mid Phase",
                    "critical_tasks": [
                        "Send formal wedding invitations with RSVP deadline",
                        "Order floral arrangements and schedule cake tasting",
                        "Finalize bridal party garments and fittings"
                    ],
                    "priority": "High"
                },
                {
                    "phase": "4 to 6 Weeks Before",
                    "milestone": "Details & Confirmations",
                    "target_date": "Late Phase",
                    "critical_tasks": [
                        "Obtain marriage license from municipal authority",
                        "Finalize ceremony script and vows with officiant",
                        "Lock down song playlist (first dance, processional, must-plays)"
                    ],
                    "priority": "Medium"
                },
                {
                    "phase": "1 Week Before & Day-Of",
                    "milestone": "Final Run-of-Show",
                    "target_date": event_date or "Event Week",
                    "critical_tasks": [
                        "Confirm final guest count with caterer and venue manager",
                        "Rehearsal dinner run-through with bridal party",
                        "08:00 AM Hair & Makeup; 02:00 PM Photo Session; 04:30 PM Ceremony; 06:00 PM Reception Dinner"
                    ],
                    "priority": "High"
                }
            ]
        elif event_type == "birthday":
            return [
                {
                    "phase": "4 to 6 Weeks Before",
                    "milestone": "Theme & Venue Reservation",
                    "target_date": "Early Phase",
                    "critical_tasks": [
                        "Decide party concept and lock in date/time",
                        "Secure venue, private room, or prepare home space",
                        "Send digital invitations and track RSVPs"
                    ],
                    "priority": "High"
                },
                {
                    "phase": "2 to 3 Weeks Before",
                    "milestone": "Food, Sweets & Entertainment",
                    "target_date": "Mid Phase",
                    "critical_tasks": [
                        "Commission custom milestone birthday cake",
                        "Plan food menu, drink pairings, and snack bars",
                        "Order customized balloon installation and themed props"
                    ],
                    "priority": "Medium"
                },
                {
                    "phase": "Day-Of Run-of-Show",
                    "milestone": "Celebration Execution",
                    "target_date": event_date or "Party Day",
                    "critical_tasks": [
                        "12:00 PM Venue setup, balloon inflation, and audio check",
                        "03:00 PM Host welcome & signature cocktail service",
                        "05:00 PM Birthday toast, cake cutting ceremony, and highlights video",
                        "06:30 PM Dance floor and celebratory games"
                    ],
                    "priority": "High"
                }
            ]
        elif event_type == "community":
            return [
                {
                    "phase": "60 to 90 Days Before",
                    "milestone": "Civic Approvals & Logistics",
                    "target_date": "Early Phase",
                    "critical_tasks": [
                        "Submit public assembly, park use, and amplified sound permits",
                        "Engage community leaders, sponsors, and vendors",
                        "Design volunteer roles, recruitment drives, and safety protocols"
                    ],
                    "priority": "High"
                },
                {
                    "phase": "30 Days Before",
                    "milestone": "Equipment & Outreach",
                    "target_date": "Mid Phase",
                    "critical_tasks": [
                        "Contract sound stage, generator, and portable sanitation units",
                        "Launch social media promo, neighborhood flyers, and press release",
                        "Map emergency exit lanes, first aid station, and recycling bins"
                    ],
                    "priority": "High"
                },
                {
                    "phase": "Event Day Operation",
                    "milestone": "Live Festival Management",
                    "target_date": event_date or "Festival Day",
                    "critical_tasks": [
                        "07:00 AM Vendor load-in, stage rigging, and sanitation inspection",
                        "09:30 AM Volunteer safety briefing and walkie-talkie check",
                        "10:00 AM Public gates open with community kickoff speech",
                        "04:00 PM Closing remarks, prize drawings, and eco-cleanup crew"
                    ],
                    "priority": "High"
                }
            ]
        else:
            return [
                {
                    "phase": "Planning Phase (T-30 Days)",
                    "milestone": "Concept & Bookings",
                    "target_date": "Month Prior",
                    "critical_tasks": ["Reserve space", "Confirm attendee list", "Book suppliers"],
                    "priority": "High"
                },
                {
                    "phase": "Execution (Day-Of)",
                    "milestone": "Event Operations",
                    "target_date": event_date or "Event Day",
                    "critical_tasks": ["Setup & sound check", "Guest check-in", "Event program"],
                    "priority": "High"
                }
            ]

    def _generate_vendors(self, event_type: str, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Builds categorized vendor tasks with questions to ask and priority."""
        raw_vendors = PERSONA_DEFAULTS.get(event_type, PERSONA_DEFAULTS["custom"])["default_vendors"]
        enhanced_vendors = []
        for idx, v in enumerate(raw_vendors):
            cat = v["category"]
            questions = [
                f"What is your package rate and cancellation policy for {ctx['guest_count']} attendees?",
                f"How many hours of setup/breakdown do you require on-site?",
                f"Can you provide a Certificate of Insurance (COI) naming the venue?"
            ]
            enhanced_vendors.append({
                "id": f"v-{idx+1}",
                "category": cat,
                "task": v["task"],
                "status": "Not Contacted",
                "priority": v["priority"],
                "recommended_booking_window": "3 to 6 months prior" if v["priority"] == "High" else "1 to 2 months prior",
                "key_questions_to_ask": questions
            })
        return enhanced_vendors

    def _generate_ideas(self, event_type: str, ctx: Dict[str, Any], cost_per_guest: float) -> Dict[str, Any]:
        """Synthesizes creative personalized concepts tailored to context."""
        theme_pref = ctx.get("theme_preference") or ""

        if event_type == "wedding":
            return {
                "theme_title": theme_pref or "Enchanted Twilight & Modern Elegance",
                "color_palette": [
                    {"name": "Champagne Rose", "hex": "#E0A899"},
                    {"name": "Ivory Silk", "hex": "#FFFBF5"},
                    {"name": "Sage Eucalyptus", "hex": "#8A9A86"},
                    {"name": "Warm Gold", "hex": "#D4AF37"}
                ],
                "signature_features": [
                    "Audio Guestbook: Vintage rotary phone where guests record heartfelt voicemail memories",
                    "Champagne Wall: Tower of flute glasses serving as the table escort card display",
                    "Late-Night Snack Surprise: Gourmet mini sliders and churro bites brought out at 10 PM"
                ],
                "curated_food_and_drinks": [
                    "Signature 'His & Hers' Cocktails: Smoked Rosemary Bourbon Old Fashioned & Elderflower French 75",
                    "Artisanal Farm-to-Table grazing stations highlighting local seasonal cheeses and micro-greens"
                ],
                "entertainment_and_activities": [
                    "Live acoustic guitar during ceremony transitioning into high-energy brass-infused DJ set",
                    "360-degree slow motion video glam booth with custom couple monogram overlay"
                ],
                "favors_or_takeaways": "Personalized organic olive oil bottles or wildflower seed packets in embossed linen bags.",
                "cost_saving_ai_recommendation": (
                    f"With ${cost_per_guest:.0f}/guest, substitute elaborate imported floral table runners with "
                    "reusable potted ferns, Italian ruscus greenery, and glowing clustered pillar candles. "
                    "This cuts decor costs by approximately 40% while creating a warm, lush, cinematic atmosphere."
                )
            }
        elif event_type == "birthday":
            return {
                "theme_title": theme_pref or "Neon Glow & Retro Glam Lounge",
                "color_palette": [
                    {"name": "Electric Violet", "hex": "#7928CA"},
                    {"name": "Cyber Magenta", "hex": "#FF0080"},
                    {"name": "Midnight Slate", "hex": "#1A1A2E"},
                    {"name": "Luminous Teal", "hex": "#00DFD8"}
                ],
                "signature_features": [
                    "Bespoke LED Neon Sign with honoree's name / catchphrase atop a lush greenery photo wall",
                    "Interactive Polaroid Guest Book with metallic pens and tape for instant scrapbook messages",
                    "Milestone Nostalgia Corner: Framed photo timeline of memories across the decades"
                ],
                "curated_food_and_drinks": [
                    "Custom Birthday Libation: 'The Milestone Elixir' (Violet Gin Sour with edible glitter rim)",
                    "Interactive Taco Bar or Bao Bun Station featuring chef-curated sauces and toppings"
                ],
                "entertainment_and_activities": [
                    "Custom Honoree Trivia Game hosted through guest smartphones with funny prizes",
                    "Silent Disco headset hour for high-energy dancing without noise complaints"
                ],
                "favors_or_takeaways": "Custom enamel pins, branded cookies with edible portrait print, or mini hangover survival kits.",
                "cost_saving_ai_recommendation": (
                    "Rather than hiring a full catering waitstaff, opt for high-end elevated buffet stations "
                    "or partner with a trendy local food truck. Saves approximately 25% on labor and dish rental fees."
                )
            }
        elif event_type == "community":
            return {
                "theme_title": theme_pref or "Unity in Bloom: Community Cultural Harvest",
                "color_palette": [
                    {"name": "Terracotta Amber", "hex": "#E07A5F"},
                    {"name": "Deep Ocean Teal", "hex": "#264653"},
                    {"name": "Sunflower Gold", "hex": "#F4A261"},
                    {"name": "Lush Forest", "hex": "#2A9D8F"}
                ],
                "signature_features": [
                    "Collaborative Community Mural: Canvas where all attendees paint their handprints or positive wishes",
                    "Maker & Artisan Village: Dedicated booths showcasing local micro-businesses and craftspeople",
                    "Zero-Waste Station: Volunteer-staffed composting and water refill station discouraging single-use plastic"
                ],
                "curated_food_and_drinks": [
                    "Multicultural Food Truck Alley with affordable $5 sample-sized portions for family tasting",
                    "Local cider, craft kombucha, and freshly squeezed lemonade stands"
                ],
                "entertainment_and_activities": [
                    "Main Stage showcases local youth dance troupes, acoustic acts, and community choir",
                    "Kids Discovery Zone with face painting, giant Jenga, sack races, and STEM robotics demo"
                ],
                "favors_or_takeaways": "Reusable organic cotton tote bags sponsored by local businesses containing community resource guides.",
                "cost_saving_ai_recommendation": (
                    "Partner with local high school audio/visual clubs and community colleges for stage production, "
                    "and exchange free vendor booth space for local marketing sponsorships to offset city permit and AV costs."
                )
            }
        else:
            return {
                "theme_title": theme_pref or "Modern Horizon Celebration",
                "color_palette": [
                    {"name": "Sapphire Blue", "hex": "#0F4C81"},
                    {"name": "Platinum Silver", "hex": "#E5E5E5"},
                    {"name": "Gold Accent", "hex": "#D4AF37"},
                    {"name": "Charcoal Black", "hex": "#222222"}
                ],
                "signature_features": ["Interactive welcome lounge", "Digital projection mapping", "Custom welcome gifts"],
                "curated_food_and_drinks": ["Craft beverage pairings and chef-curated small bites"],
                "entertainment_and_activities": ["Live musical accompaniment and networking game"],
                "favors_or_takeaways": "Artisanal confection boxes with personalized monogram.",
                "cost_saving_ai_recommendation": "Bundle venue and AV rentals through a single preferred vendor to negotiate a 15% aggregate discount."
            }
