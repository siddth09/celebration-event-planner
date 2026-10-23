"""
Comprehensive Test Suite for Celebrio AI Celebration & Event Planner.
Covers validation rules, persona pipelines, edge cases, financial calculations,
sanitization, caching efficiency, error handlers, and Flask REST API endpoints.
"""

import unittest
import json
import time
from models import validate_event_input, sanitize_input, PERSONA_DEFAULTS, CelebrioValidationError, EventInput
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
        with self.assertRaises(CelebrioValidationError) as ctx:
            validate_event_input(payload)
        self.assertIn("Event name is required", str(ctx.exception))

    def test_negative_budget_raises_error(self):
        payload = {"event_name": "Birthday Party", "event_type": "birthday", "budget": -500, "guest_count": 20}
        with self.assertRaises(CelebrioValidationError) as ctx:
            validate_event_input(payload)
        self.assertIn("Budget must be greater than zero", str(ctx.exception))

    def test_zero_budget_raises_error(self):
        payload = {"event_name": "Birthday Party", "event_type": "birthday", "budget": 0, "guest_count": 20}
        with self.assertRaises(CelebrioValidationError) as ctx:
            validate_event_input(payload)
        self.assertIn("Budget must be greater than zero", str(ctx.exception))

    def test_non_numeric_budget_raises_error(self):
        payload = {"event_name": "Block Party", "event_type": "community", "budget": "free", "guest_count": 100}
        with self.assertRaises(CelebrioValidationError) as ctx:
            validate_event_input(payload)
        self.assertIn("Budget must be a valid numeric value", str(ctx.exception))

    def test_zero_guests_raises_error(self):
        payload = {"event_name": "Solo Gala", "event_type": "custom", "budget": 5000, "guest_count": 0}
        with self.assertRaises(CelebrioValidationError) as ctx:
            validate_event_input(payload)
        self.assertIn("at least 1 attendee", str(ctx.exception))

    def test_unsupported_event_type_raises_error(self):
        payload = {"event_name": "Space Mission", "event_type": "interplanetary", "budget": 5000, "guest_count": 10}
        with self.assertRaises(CelebrioValidationError) as ctx:
            validate_event_input(payload)
        self.assertIn("Unsupported event type", str(ctx.exception))

    def test_xss_sanitization(self):
        dirty = "<script>alert('pwned')</script>Hello World"
        clean = sanitize_input(dirty)
        self.assertNotIn("<script>", clean)
        self.assertIn("&lt;script&gt;", clean)

    def test_non_dict_payload_raises_error(self):
        with self.assertRaises(CelebrioValidationError) as ctx:
            validate_event_input(["not", "a", "dict"])
        self.assertIn("Expected JSON object", str(ctx.exception))

    def test_event_input_dataclass_conversion(self):
        obj = EventInput(
            event_name="Anniversary",
            event_type="custom",
            budget=5000.0,
            guest_count=40
        )
        as_dict = obj.to_dict()
        self.assertEqual(as_dict["event_name"], "Anniversary")
        self.assertEqual(as_dict["budget"], 5000.0)

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
        total_allocated = sum(item["allocated_amount"] for item in plan["budget_breakdown"])
        self.assertAlmostEqual(total_allocated, 30000.0, delta=1.0)

    def test_generate_birthday_plan(self):
        payload = {
            "event_name": "40th Milestone Birthday",
            "event_type": "birthday",
            "budget": 4000,
            "guest_count": 35
        }
        plan = self.engine.generate_full_plan(payload)
        self.assertEqual(len(plan["budget_breakdown"]), 7)
        self.assertTrue(any("Bakery" in v["category"] for v in plan["vendor_checklist"]))

    def test_generate_community_plan(self):
        payload = {
            "event_name": "Spring Park Fest",
            "event_type": "community",
            "budget": 15000,
            "guest_count": 600
        }
        plan = self.engine.generate_full_plan(payload)
        self.assertTrue(any("Permits" in b["category"] for b in plan["budget_breakdown"]))

    def test_financial_summary_math(self):
        mock_breakdown = [
            {"allocated_amount": 1000.0, "actual_amount": 900.0},
            {"allocated_amount": 2000.0, "actual_amount": 2200.0}
        ]
        summary = self.engine._compute_financial_summary(mock_breakdown, 3000.0)
        self.assertEqual(summary["total_budget"], 3000.0)
        self.assertEqual(summary["total_allocated"], 3000.0)
        self.assertEqual(summary["total_actual"], 3100.0)
        self.assertEqual(summary["remaining_balance"], -100.0)
        self.assertTrue(summary["is_over_budget"])

    # -----------------------------
    # 3. Efficiency & Caching Tests
    # -----------------------------
    def test_heuristic_plan_caching_performance(self):
        payload = {
            "event_name": "Speed Test Event",
            "event_type": "wedding",
            "budget": 20000,
            "guest_count": 100,
            "location": "San Francisco"
        }
        # First call computes
        plan1 = self.engine.generate_full_plan(payload)
        
        # Second call hits cache
        t0 = time.perf_counter()
        plan2 = self.engine.generate_full_plan(payload)
        t1 = time.perf_counter()
        
        # Must execute in under 5 milliseconds from cache
        elapsed_ms = (t1 - t0) * 1000
        self.assertLess(elapsed_ms, 5.0)
        self.assertEqual(plan1["budget_breakdown"], plan2["budget_breakdown"])

    def test_presets_etag_and_caching(self):
        # First request
        resp1 = self.app.get("/api/presets")
        self.assertEqual(resp1.status_code, 200)
        etag = resp1.headers.get("ETag")
        self.assertIsNotNone(etag)
        self.assertIn("max-age=3600", resp1.headers.get("Cache-Control", ""))

        # Conditional request with ETag
        resp2 = self.app.get("/api/presets", headers={"If-None-Match": etag})
        self.assertEqual(resp2.status_code, 304)

    def test_security_headers_present(self):
        resp = self.app.get("/health")
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "SAMEORIGIN")

    # -----------------------------
    # 4. REST API Endpoint Tests
    # -----------------------------
    def test_health_endpoint(self):
        res = self.app.get("/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")

    def test_api_presets(self):
        res = self.app.get("/api/presets")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("wedding", data["personas"])

    def test_api_validate_valid(self):
        res = self.app.post(
            "/api/validate",
            data=json.dumps({"event_name": "Valid Gala", "budget": 5000, "guest_count": 50, "event_type": "custom"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.get_json()["success"])

    def test_api_validate_invalid(self):
        res = self.app.post(
            "/api/validate",
            data=json.dumps({"event_name": "", "budget": -50}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()["success"])

    def test_api_generate_plan_endpoint(self):
        res = self.app.post(
            "/api/generate-plan",
            data=json.dumps({
                "event_name": "API Test Birthday",
                "event_type": "birthday",
                "budget": 3000,
                "guest_count": 25
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("plan", data)

    def test_api_chat_endpoint(self):
        res = self.app.post(
            "/api/chat",
            data=json.dumps({
                "message": "How do I cut catering costs?",
                "event_context": {"budget": 10000, "guest_count": 50, "event_name": "Test Party"}
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("catering", data["reply"].lower())

    def test_api_chat_empty_message(self):
        res = self.app.post(
            "/api/chat",
            data=json.dumps({"message": "   "}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)

    def test_api_vendor_inquiry_endpoint(self):
        res = self.app.post(
            "/api/vendor-inquiry",
            data=json.dumps({
                "vendor_category": "Catering",
                "event_context": {"event_name": "Test Wedding", "guest_count": 100, "event_date": "2026-11-20"}
            }),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("Catering", data["inquiry_email"])

    # -----------------------------
    # 5. Global Error Handlers Tests
    # -----------------------------
    def test_404_not_found_handler(self):
        res = self.app.get("/api/non-existent-endpoint")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["status"], 404)

    def test_405_method_not_allowed_handler(self):
        res = self.app.post("/health")
        self.assertEqual(res.status_code, 405)
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["status"], 405)


if __name__ == "__main__":
    unittest.main()
