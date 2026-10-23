"""
Comprehensive Test Suite for Celebrio AI Celebration & Event Planner.
Covers validation rules, persona pipelines, edge cases, financial calculations,
sanitization, and Flask REST API endpoints.
"""

import unittest
import json
from models import validate_event_input, sanitize_input, PERSONA_DEFAULTS
from planner_engine import PlannerEngine
from app import app


class TestCelebrioPlanner(unittest.TestCase):
    """Unit and integration test cases."""

    def setUp(self):
        self.engine = PlannerEngine(api_key=None)  # Test with deterministic engine
        self.app = app.test_client()
        self.app.testing = True

    # -----------------------------
    # 1. Validation & Edge Cases
    # -----------------------------
    def test_valid_wedding_input(self):
        payload = {
            "event_name": "Sarah & Alex Autumn Wedding",
            "event_type": "wedding",
            "budget": 25000,
            "guest_count": 120,
            "event_date": "2026-10-15",
            "location": "Napa Valley, CA",
            "theme_preference": "Rustic Elegance"
        }
        res = validate_event_input(payload)
        self.assertEqual(res["event_name"], "Sarah &amp; Alex Autumn Wedding")
        self.assertEqual(res["budget"], 25000.0)
        self.assertEqual(res["guest_count"], 120)

    def test_missing_event_name_raises_error(self):
        payload = {"event_name": "   ", "event_type": "wedding", "budget": 10000, "guest_count": 50}
        with self.assertRaises(ValueError) as ctx:
            validate_event_input(payload)
        self.assertIn("Event name is required", str(ctx.exception))

    def test_negative_budget_raises_error(self):
        payload = {"event_name": "Birthday Party", "event_type": "birthday", "budget": -500, "guest_count": 20}
        with self.assertRaises(ValueError) as ctx:
            validate_event_input(payload)
        self.assertIn("Budget must be greater than zero", str(ctx.exception))

    def test_zero_budget_raises_error(self):
        payload = {"event_name": "Birthday Party", "event_type": "birthday", "budget": 0, "guest_count": 20}
        with self.assertRaises(ValueError) as ctx:
            validate_event_input(payload)
        self.assertIn("Budget must be greater than zero", str(ctx.exception))

    def test_non_numeric_budget_raises_error(self):
        payload = {"event_name": "Block Party", "event_type": "community", "budget": "free", "guest_count": 100}
        with self.assertRaises(ValueError) as ctx:
            validate_event_input(payload)
        self.assertIn("Budget must be a valid numeric value", str(ctx.exception))

    def test_zero_guests_raises_error(self):
        payload = {"event_name": "Solo Gala", "event_type": "custom", "budget": 5000, "guest_count": 0}
        with self.assertRaises(ValueError) as ctx:
            validate_event_input(payload)
        self.assertIn("at least 1 attendee", str(ctx.exception))

    def test_unsupported_event_type_raises_error(self):
        payload = {"event_name": "Space Mission", "event_type": "interplanetary", "budget": 5000, "guest_count": 10}
        with self.assertRaises(ValueError) as ctx:
            validate_event_input(payload)
        self.assertIn("Unsupported event type", str(ctx.exception))

    def test_xss_sanitization(self):
        dirty = "<script>alert('pwned')</script>Hello World"
        clean = sanitize_input(dirty)
        self.assertNotIn("<script>", clean)
        self.assertIn("&lt;script&gt;", clean)

    # -----------------------------
    # 2. Plan Generation Engine
    # -----------------------------
    def test_generate_wedding_plan(self):
        payload = {
            "event_name": "Grand Wedding",
            "event_type": "wedding",
            "budget": 30000,
            "guest_count": 150,
            "location": "Manhattan, NY"
        }
        plan = self.engine.generate_full_plan(payload)
        self.assertIn("budget_breakdown", plan)
        self.assertIn("milestone_timeline", plan)
        self.assertIn("vendor_checklist", plan)
        self.assertIn("personalized_ideas", plan)
        self.assertIn("financial_summary", plan)

        # Verify budget allocations match total
        total_alloc = sum(b["allocated_amount"] for b in plan["budget_breakdown"])
        self.assertAlmostEqual(total_alloc, 30000.0, places=1)

    def test_generate_birthday_plan(self):
        payload = {
            "event_name": "30th Birthday Bash",
            "event_type": "birthday",
            "budget": 3500,
            "guest_count": 30,
            "theme_preference": "Retro Arcade 80s"
        }
        plan = self.engine.generate_full_plan(payload)
        self.assertEqual(len(plan["budget_breakdown"]), len(PERSONA_DEFAULTS["birthday"]["budget_splits"]))
        self.assertGreater(len(plan["milestone_timeline"]), 0)
        self.assertEqual(len(plan["personalized_ideas"]["color_palette"]), 4)

    def test_generate_community_plan(self):
        payload = {
            "event_name": "Spring Eco Festival",
            "event_type": "community",
            "budget": 12000,
            "guest_count": 500,
            "location": "Central Park"
        }
        plan = self.engine.generate_full_plan(payload)
        self.assertIn("Permits & City Fees", [b["category"] for b in plan["budget_breakdown"]])
        # Check vendor checklist contains civic & safety items
        categories = [v["category"] for v in plan["vendor_checklist"]]
        self.assertTrue(any("City" in c or "Permit" in c or "Sanitation" in c for c in categories))

    # -----------------------------
    # 3. Chat and Vendor RFP
    # -----------------------------
    def test_heuristic_chat_cost_saving(self):
        ctx = {"event_name": "Test Wedding", "event_type": "wedding", "budget": 20000, "guest_count": 100}
        reply = self.engine.chat("How can I cut my catering and bar budget?", ctx)
        self.assertIn("Cost Optimization", reply)
        self.assertIn("bar", reply.lower())

    def test_vendor_inquiry_generation(self):
        ctx = {"event_name": "Gala 2026", "event_type": "wedding", "guest_count": 150, "location": "Austin, TX"}
        rfp = self.engine.generate_vendor_inquiry("Photography", ctx)
        self.assertIn("Subject: Inquiry & RFP", rfp)
        self.assertIn("Photography", rfp)
        self.assertIn("150 guests", rfp)

    # -----------------------------
    # 4. REST API Endpoint Tests
    # -----------------------------
    def test_api_health(self):
        resp = self.app.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["status"], "healthy")

    def test_api_presets(self):
        resp = self.app.get("/api/presets")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertIn("wedding", data["personas"])
        self.assertIn("birthday", data["personas"])
        self.assertIn("community", data["personas"])

    def test_api_validate_endpoint_valid(self):
        payload = {"event_name": "Valid Celebration", "event_type": "birthday", "budget": 1500, "guest_count": 25}
        resp = self.app.post("/api/validate", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])

    def test_api_validate_endpoint_invalid(self):
        payload = {"event_name": "", "budget": -10}
        resp = self.app.post("/api/validate", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_api_generate_plan_endpoint(self):
        payload = {
            "event_name": "Downtown Block Party",
            "event_type": "community",
            "budget": 8000,
            "guest_count": 250,
            "location": "Oakland Civic Plaza"
        }
        resp = self.app.post("/api/generate-plan", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertIn("plan", data)
        self.assertEqual(data["plan"]["event_metadata"]["event_name"], "Downtown Block Party")

    def test_api_chat_endpoint(self):
        payload = {
            "message": "Give me timeline tips",
            "event_context": {"event_name": "My Party", "budget": 2000, "guest_count": 20}
        }
        resp = self.app.post("/api/chat", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data["success"])
        self.assertIn("reply", data)


if __name__ == "__main__":
    unittest.main()
