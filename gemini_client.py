"""
Gemini GenAI Client with resilient fallback architecture, structured JSON parsing,
and prompt engineering for Celebrio Celebration & Event Planner.
"""

import os
import json
import re
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CelebrioGeminiClient")

# Lazy-loaded google-generativeai
genai = None
try:
    import google.generativeai as _genai
    genai = _genai
except ImportError:
    logger.warning("google-generativeai not installed; operating in heuristic fallback mode.")


class GeminiPlannerClient:
    """Wrapper around Gemini API with automatic fallback and structured output parsing."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.client_ready = False
        self.model = None

        if self.api_key and genai:
            try:
                genai.configure(api_key=self.api_key)
                # Attempt to initialize with modern fast model
                self.model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash",
                    generation_config={
                        "temperature": 0.4,
                        "top_p": 0.95,
                        "max_output_tokens": 4096,
                    }
                )
                self.client_ready = True
                logger.info("Gemini 1.5 Flash client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}. Falling back to heuristic planner.")
                self.client_ready = False
        else:
            logger.info("No GEMINI_API_KEY supplied. Planner will run in deterministic heuristic mode.")

    def is_ai_active(self) -> bool:
        return self.client_ready and self.model is not None

    def generate_event_plan(self, event_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Uses Gemini to generate a complete event plan (Budget, Timeline, Vendors, Ideas).
        Returns parsed JSON dict, or None on API failure.
        """
        if not self.is_ai_active():
            return None

        prompt = f"""
You are Celebrio AI, an elite event planner and financial coordinator.
Create a comprehensive, production-ready event plan in valid JSON format for the following event:

EVENT DETAILS:
- Name: {event_context.get('event_name')}
- Type: {event_context.get('event_type')}
- Total Budget: ${event_context.get('budget'):,.2f} USD
- Expected Guests: {event_context.get('guest_count')}
- Target Date: {event_context.get('event_date') or 'Not specified'}
- Venue/Location: {event_context.get('location')}
- Style/Theme Preference: {event_context.get('theme_preference') or 'Curate best fit'}
- Additional Notes: {event_context.get('notes') or 'None'}

REQUIREMENTS:
Return a single JSON object with EXACTLY this structure (do not wrap in markdown or backticks):
{{
  "summary": "2-sentence inspiring overview of the event vision and logistical focus",
  "budget_breakdown": [
    {{
      "category": "Category Name",
      "allocated_amount": 1234.56,
      "percentage": 25,
      "description": "Specific inclusions and vendor cost targets",
      "items": [
        {{"item_name": "Specific sub-item", "estimated_cost": 500.00, "status": "Pending"}}
      ]
    }}
  ],
  "milestone_timeline": [
    {{
      "phase": "e.g., 6+ Months Out / 4 Weeks Out / Week Of / Day-Of Run-of-Show",
      "milestone": "Title of milestone",
      "target_date": "Relative or concrete date",
      "critical_tasks": ["Action item 1", "Action item 2"],
      "priority": "High"
    }}
  ],
  "vendor_checklist": [
    {{
      "category": "Vendor Type (e.g. Venue, Catering, Photo/Video, Music, Rentals, Security)",
      "task": "Specific actionable vendor milestone",
      "recommended_booking_window": "e.g. 6-9 months before",
      "priority": "High",
      "key_questions_to_ask": ["Specific interview question 1", "Question 2"]
    }}
  ],
  "personalized_ideas": {{
    "theme_title": "Creative Theme Name",
    "color_palette": [
      {{"name": "Color Name", "hex": "#HEXCODE"}},
      {{"name": "Color Name", "hex": "#HEXCODE"}},
      {{"name": "Color Name", "hex": "#HEXCODE"}},
      {{"name": "Color Name", "hex": "#HEXCODE"}}
    ],
    "signature_features": ["Feature idea 1", "Feature idea 2", "Feature idea 3"],
    "curated_food_and_drinks": ["Culinary/Bar concept 1", "Culinary/Bar concept 2"],
    "entertainment_and_activities": ["Activity 1", "Activity 2"],
    "favors_or_takeaways": "Personalized guest takeaway idea",
    "cost_saving_ai_recommendation": "Clever, high-impact way to save 10-15% on this specific budget without compromising attendee experience"
  }}
}}
Make sure all numbers in budget_breakdown sum to approximately ${event_context.get('budget'):.2f}.
"""
        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text.strip()
            
            # Clean possible markdown fence code blocks
            clean_json = raw_text
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
            if match:
                clean_json = match.group(1)
            else:
                brace_match = re.search(r'(\{[\s\S]*\})', raw_text)
                if brace_match:
                    clean_json = brace_match.group(1)

            parsed = json.loads(clean_json)
            logger.info("Successfully generated and parsed Gemini AI plan.")
            return parsed
        except Exception as e:
            logger.error(f"Gemini API call or JSON parsing failed: {e}. Reverting to heuristic engine.")
            return None

    def chat_assistant(self, message: str, event_context: Dict[str, Any]) -> str:
        """Interactive conversational advisor."""
        if not self.is_ai_active():
            # Heuristic response generator
            return self._heuristic_chat_reply(message, event_context)

        system_prompt = (
            f"You are Celebrio AI, an expert celebration and event planner. "
            f"Current active event: {event_context.get('event_name', 'Upcoming Event')} "
            f"({event_context.get('event_type', 'celebration')}), Budget: ${event_context.get('budget', 0):,.2f}, "
            f"Guests: {event_context.get('guest_count', 0)}, Location: {event_context.get('location', 'Local')}. "
            f"Provide insightful, friendly, highly specific, and actionable advice. "
            f"Keep responses concise (150-250 words) with bullet points where helpful."
        )

        try:
            full_prompt = f"{system_prompt}\n\nUser Question: {message}\nCelebrio AI Advice:"
            response = self.model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            return self._heuristic_chat_reply(message, event_context)

    def generate_vendor_rfp(self, vendor_category: str, event_context: Dict[str, Any]) -> str:
        """Auto-generates a professional vendor quote / RFP email."""
        if not self.is_ai_active():
            return self._heuristic_rfp(vendor_category, event_context)

        prompt = f"""
Write a polite, highly professional Request for Proposal (RFP) / vendor inquiry email to a {vendor_category} vendor.
Event Name: {event_context.get('event_name')}
Event Type: {event_context.get('event_type')}
Event Date: {event_context.get('event_date') or 'TBD'}
Guest Count: {event_context.get('guest_count')}
Location: {event_context.get('location')}
Specific Vibe: {event_context.get('theme_preference') or 'Elegant & Memorable'}

Include:
- Clear subject line
- Warm introduction & event overview
- Specific questions regarding availability, package inclusions, setup requirements, and deposit/cancellation terms
- Professional sign-off placeholder
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"RFP generation failed: {e}")
            return self._heuristic_rfp(vendor_category, event_context)

    def _heuristic_chat_reply(self, message: str, ctx: Dict[str, Any]) -> str:
        """Contextual heuristic advisor fallback when Gemini is offline."""
        q = message.lower()
        budget = ctx.get('budget', 5000)
        guests = ctx.get('guest_count', 50)
        etype = ctx.get('event_type', 'celebration')
        cost_per_guest = budget / max(guests, 1)

        if "cut" in q or "save" in q or "reduce" in q or "cheaper" in q:
            return (
                f"💡 **Cost Optimization for your {etype.capitalize()}:**\n\n"
                f"1. **Adjust the Beverage Service:** Shift from an open full premium bar to signature cocktails plus wine/beer. This typically cuts bar expenditure by 22-30%.\n"
                f"2. **Catering Strategy:** With {guests} guests (${cost_per_guest:.0f}/guest available), consider gourmet action stations or family-style dining over formal plated courses.\n"
                f"3. **Florals & Ambience:** Repurpose ceremony florals into reception centerpieces, and supplement with elegant warm ambient candlelight.\n"
                f"4. **Digital Invitations:** Use interactive digital RSVP platforms with custom video invites to save $400-$900 on stationery and postage."
            )
        elif "timeline" in q or "schedule" in q or "when" in q:
            return (
                f"⏱️ **Master Timeline Recommendation:**\n\n"
                f"• **T-90 Days:** Lock down venue agreement and primary caterer.\n"
                f"• **T-45 Days:** Distribute invitations and collect dietary restrictions.\n"
                f"• **T-14 Days:** Finalize headcount with all suppliers and draft hourly run-of-show.\n"
                f"• **Day-of Event:** Build in a 30-minute buffer before guest arrival for unexpected vendor logistics."
            )
        elif "permit" in q or "legal" in q or "license" in q:
            return (
                f"📋 **Compliance & Permit Guidance for {ctx.get('location', 'your venue')}:**\n\n"
                f"• **Park / Public Space Permit:** Required if holding a community gathering or amplified music outdoors.\n"
                f"• **Special Occasion Liquor License:** Check city regulations if alcohol is served or sold.\n"
                f"• **Sound Decibel Limits:** Most municipal ordinances enforce 85dB caps after 10:00 PM.\n"
                f"• **Certificate of Insurance (COI):** Ensure third-party vendors (bounce houses, food trucks, stages) provide minimum $1M liability coverage."
            )
        else:
            return (
                f"✨ **Celebrio Advisor Insight for {ctx.get('event_name', 'Your Celebration')}:**\n\n"
                f"With a planned budget of ${budget:,.2f} for {guests} guests (${cost_per_guest:.2f} per person), "
                f"the key to a remarkable {etype} is intentional hospitality. Focus 60% of your resources on what guests "
                f"experience directly—sensational food, memorable entertainment, and seamless flow. "
                f"Would you like recommendations on vendor contracts, day-of run-of-show, or theme ideas?"
            )

    def _heuristic_rfp(self, vendor_category: str, ctx: Dict[str, Any]) -> str:
        """Deterministic RFP email generator."""
        return (
            f"Subject: Inquiry & RFP: {ctx.get('event_name')} - {vendor_category} Services\n\n"
            f"Dear {vendor_category} Team,\n\n"
            f"I hope this message finds you well. I am reaching out to inquire about your availability "
            f"and packages for an upcoming {ctx.get('event_type')} titled '{ctx.get('event_name')}'.\n\n"
            f"Event Overview:\n"
            f"- Date: {ctx.get('event_date') or 'Upcoming / TBD'}\n"
            f"- Expected Attendees: {ctx.get('guest_count')} guests\n"
            f"- Venue / Location: {ctx.get('location')}\n"
            f"- Estimated Theme & Vibe: {ctx.get('theme_preference') or 'Modern & Joyful'}\n\n"
            f"Could you please share:\n"
            f"1. Your standard package pricing and itemized inclusions for this party size.\n"
            f"2. Your setup and breakdown window requirements.\n"
            f"3. Your reservation deposit and cancellation policy.\n\n"
            f"Looking forward to exploring how we might collaborate to create an unforgettable event.\n\n"
            f"Warm regards,\n"
            f"Event Organizing Team\n"
            f"Contact: {ctx.get('event_name')} Committee"
        )
