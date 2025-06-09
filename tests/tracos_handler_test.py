import pytest
from src.core.tracos_handler import TracOsHandler
from setup import TracOSWorkorder
from mongomock_motor import AsyncMongoMockClient
from datetime import datetime

@pytest.mark.asyncio
async def test_tracos_handler_workflow():
    """Test complete TracOsHandler workflow with in-memory MongoDB"""
    # Create a mock MongoDB client directly
    mongo_client = AsyncMongoMockClient()
    
    # Create and configure the handler with our mock client
    handler = TracOsHandler()
    handler.client = mongo_client
    handler.db = mongo_client["test_tractian"]
    handler.collection = handler.db["test_workorders"]
    
    try:
        # 1. Test adding a workorder with isSynced=False|None
        workorder = TracOSWorkorder(
            _id="integration_test_123",
            number="WO-INT-001",
            status="created",
            title="Integration Test",
            description="Testing full workflow",
            createdAt="2025-05-10T18:01:57.719+00:00",  # Use the MongoDB format
            updatedAt="2025-05-10T19:01:57.719+00:00",  # Use the MongoDB format
            deleted=False,
        )

        # 1. Add the workorder to the collection
        await handler.create_workorder(workorder)
        
        # 2. Test get_workorders returns unsynced workorders
        unsynced = await handler.get_workorders()
        assert len(unsynced) == 1
        assert unsynced[0]["_id"] == "integration_test_123"
        
        # 3. Test mark_as_synced updates the sync flag
        await handler.mark_as_synced("integration_test_123")
        
        # 4. Verify if "syncedAt" is on the correct date format
        updated_workorder = await handler.collection.find_one({"_id": "integration_test_123"})
        assert isinstance(updated_workorder["syncedAt"], (str, datetime))

    finally:
        # Clean up
        try:
            await mongo_client.drop_database("test_tractian")
        except:
            pass
        mongo_client.close()
        if handler.client:
            await handler.disconnect()