"""Integration checks against a real MongoDB Community Server instance.

Set MONGODB_INTEGRATION_URI to a disposable MongoDB database in CI.
"""
import os
from uuid import uuid4
import pytest
from pymongo import MongoClient
from sanjay_pilot.service import SalesPilot


@pytest.mark.skipif(not os.getenv("MONGODB_INTEGRATION_URI"), reason="real MongoDB integration service not configured")
def test_mongodb_persistence_indexes_and_approval_flow():
    client = MongoClient(os.environ["MONGODB_INTEGRATION_URI"], serverSelectionTimeoutMS=5000)
    db_name = "sanjay_sales_test_" + uuid4().hex
    db = client[db_name]
    try:
        collection = db["sales_records"]
        collection.create_index([("type", 1), ("created_at", -1)], name="type_created_at")
        collection.create_index([("status", 1), ("created_at", -1)], name="status_created")
        pilot = SalesPilot(collection)

        proposal = pilot.propose_market(
            "Germany", "Evidence-backed industrial importer opportunity",
            "https://example.com/market-report", 0.72, created_by="maker@example.com"
        )
        draft = pilot.create_email_draft(
            "buyer@example.com", "Sourcing discussion",
            "Could we discuss your documented sourcing requirements?",
            created_by="maker@example.com"
        )

        # Re-open through a new collection handle to prove durable persistence,
        # rather than relying on the process-local cache or original object.
        reloaded = db["sales_records"]
        assert reloaded.find_one({"_id": proposal["_id"]})["status"] == "pending_approval"
        assert reloaded.find_one({"_id": draft["_id"]})["sent"] is False

        approved_proposal = pilot.approve_market(proposal["_id"], approved_by="reviewer@example.com")
        approved_draft = pilot.approve_email_draft(
            draft["_id"],
            {"recipient": "buyer@example.com", "subject": "Sourcing discussion",
             "body": "Could we discuss your documented sourcing requirements?"},
            approved_by="reviewer@example.com",
        )
        assert approved_proposal["approved_by"] == "reviewer@example.com"
        assert approved_draft["approved_by"] == "reviewer@example.com"
        assert approved_draft["sent"] is False
        assert reloaded.find_one({"_id": draft["_id"]})["status"] == "approved"
        with pytest.raises(LookupError):
            pilot.approve_market(proposal["_id"], approved_by="reviewer@example.com")
    finally:
        client.drop_database(db_name)
        client.close()
