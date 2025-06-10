import pytest
import pytest_asyncio
import os
import json
import tempfile
import shutil
from unittest import mock
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient

from setup import TracOSWorkorder, CustomerSystemWorkorder
from src.main import main
from src.core.tracos_handler import TracOsHandler


@pytest_asyncio.fixture
async def ephemeral_environment():
    """Create ephemeral MongoDB, inbound and outbound directories"""
    # Create temporary directories
    temp_inbound_dir = tempfile.mkdtemp()
    temp_outbound_dir = tempfile.mkdtemp()
    
    # Create mock MongoDB client
    mongo_client = AsyncMongoMockClient()
    db = mongo_client["test_tractian"]
    collection = db["test_workorders"]
    
    # Patch environment variables
    env_patch = mock.patch.dict(os.environ, {
        'MONGO_URI': 'mongodb://mock',
        'MONGO_DATABASE': 'test_tractian',
        'MONGO_COLLECTION': 'test_workorders',
        'DATA_INBOUND_DIR': temp_inbound_dir,
        'DATA_OUTBOUND_DIR': temp_outbound_dir
    })
    
    # Create a factory function that returns configured TracOsHandler instances
    def create_mock_tracos_handler():
        handler = TracOsHandler()
        handler.client = mongo_client
        handler.db = db
        handler.collection = collection
        return handler
    
    # Patch TracOsHandler in all the places it's imported (like a fake component)
    inbound_patch = mock.patch('src.processors.inbound_processor.TracOsHandler', side_effect=create_mock_tracos_handler)
    outbound_patch = mock.patch('src.processors.outbound_processor.TracOsHandler', side_effect=create_mock_tracos_handler)
    
    with env_patch, inbound_patch, outbound_patch:
        try:
            yield {
                'mongo_client': mongo_client,
                'db': db,
                'collection': collection,
                'inbound_dir': temp_inbound_dir,
                'outbound_dir': temp_outbound_dir
            }
        finally:
            # Cleanup
            shutil.rmtree(temp_inbound_dir, ignore_errors=True)
            shutil.rmtree(temp_outbound_dir, ignore_errors=True)
            mongo_client.close()


@pytest.fixture
def sample_tracos_workorders():
    """Create sample TracOS workorders for testing"""
    base_time = datetime.now(timezone.utc) - timedelta(days=1)
    
    return [
        TracOSWorkorder(
            _id=ObjectId(),
            number=100,
            status="completed",
            title="TracOS Workorder 100",
            description="Completed maintenance task",
            createdAt=base_time,
            updatedAt=base_time + timedelta(hours=2),
            deleted=False,
            deletedAt=None
        ),
        TracOSWorkorder(
            _id=ObjectId(),
            number=101,
            status="pending",
            title="TracOS Workorder 101", 
            description="Pending inspection task",
            createdAt=base_time + timedelta(hours=1),
            updatedAt=base_time + timedelta(hours=3),
            deleted=False,
            deletedAt=None
        )
    ]


@pytest.fixture
def sample_customer_workorders():
    """Create sample Customer workorders for testing"""
    base_time = datetime.now(timezone.utc) - timedelta(days=1)
    
    return [
        {
            "orderNo": 200,
            "isActive": False,
            "isCanceled": False,
            "isDeleted": False,
            "isDone": True,
            "isOnHold": False,
            "isPending": False,
            "isSynced": False,
            "summary": "Customer Workorder 200 - Equipment repair",
            "creationDate": (base_time).isoformat(),
            "lastUpdateDate": (base_time + timedelta(hours=4)).isoformat(),
            "deletedDate": None
        },
        {
            "orderNo": 201,
            "isActive": True,
            "isCanceled": False,
            "isDeleted": False,
            "isDone": False,
            "isOnHold": False,
            "isPending": False,
            "isSynced": False,
            "summary": "Customer Workorder 201 - Preventive maintenance",
            "creationDate": (base_time + timedelta(hours=2)).isoformat(),
            "lastUpdateDate": (base_time + timedelta(hours=5)).isoformat(),
            "deletedDate": None
        }
    ]


async def setup_initial_data(env, tracos_workorders, customer_workorders):
    """Insert initial data into MongoDB and file system"""
    # Insert TracOS workorders into MongoDB (these should be synced to customer)
    for workorder in tracos_workorders:
        workorder_dict = dict(workorder)
        await env['collection'].insert_one(workorder_dict)
    
    # Create customer workorder files (these should be synced to TracOS)
    for workorder in customer_workorders:
        file_path = os.path.join(env['inbound_dir'], f"{workorder['orderNo']}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(workorder, f, indent=4)


@pytest.mark.asyncio
async def test_end_to_end_flow(ephemeral_environment, sample_tracos_workorders, sample_customer_workorders):
    """Test complete end-to-end integration flow"""
    env = ephemeral_environment
    
    # Setup initial data
    await setup_initial_data(env, sample_tracos_workorders, sample_customer_workorders)
    
    # Verify initial state
    initial_mongo_count = await env['collection'].count_documents({})
    initial_inbound_files = len([f for f in os.listdir(env['inbound_dir']) if f.endswith('.json')])
    initial_outbound_files = len([f for f in os.listdir(env['outbound_dir']) if f.endswith('.json')])
    
    assert initial_mongo_count == 2, "Should have 2 TracOS workorders in MongoDB"
    assert initial_inbound_files == 2, "Should have 2 customer workorder files in inbound"
    assert initial_outbound_files == 0, "Should have no files in outbound initially"
    
    # Run the main application workflow
    await main()
    
    # Verify inbound processing (Customer -> TracOS)
    final_mongo_count = await env['collection'].count_documents({})
    assert final_mongo_count == 4, "Should have 4 workorders in MongoDB after inbound processing"
    
    # Verify the customer workorders were translated and stored in MongoDB
    customer_wo_200 = await env['collection'].find_one({"number": 200})
    customer_wo_201 = await env['collection'].find_one({"number": 201})
    
    assert customer_wo_200 is not None, "Customer workorder 200 should be in MongoDB"
    assert customer_wo_201 is not None, "Customer workorder 201 should be in MongoDB"
    assert customer_wo_200["status"] == "completed", "Workorder 200 should have 'completed' status"
    assert customer_wo_201["status"] == "in_progress", "Workorder 201 should have 'in_progress' status"
    
    # Verify outbound processing (TracOS -> Customer)
    final_outbound_files = len([f for f in os.listdir(env['outbound_dir']) if f.endswith('.json')])
    assert final_outbound_files >= 2, "Should have at least 2 files in outbound after processing"
    
    # Verify specific outbound files exist and have correct content
    outbound_files = [f for f in os.listdir(env['outbound_dir']) if f.endswith('.json')]
    outbound_numbers = []
    
    for file in outbound_files:
        file_path = os.path.join(env['outbound_dir'], file)
        with open(file_path, 'r', encoding='utf-8') as f:
            workorder_data = json.load(f)
            outbound_numbers.append(workorder_data['orderNo'])
            
            # Verify the structure is correct for customer system
            assert 'orderNo' in workorder_data
            assert 'isCanceled' in workorder_data
            assert 'isDone' in workorder_data
            assert 'summary' in workorder_data
    
    # Check that original TracOS workorders were processed to outbound
    assert 100 in outbound_numbers, "TracOS workorder 100 should be in outbound"
    assert 101 in outbound_numbers, "TracOS workorder 101 should be in outbound"
    
    # Verify sync status was updated in MongoDB
    synced_workorders = []
    async for doc in env['collection'].find({"isSynced": True}):
        synced_workorders.append(doc)
    
    assert len(synced_workorders) >= 2, "At least 2 workorders should be marked as synced"
    
    # Verify syncedAt timestamp exists for synced workorders
    for workorder in synced_workorders:
        assert 'syncedAt' in workorder, "Synced workorders should have syncedAt timestamp"
        assert workorder['syncedAt'] is not None, "syncedAt should not be None"


@pytest.mark.asyncio
async def test_end_to_end_flow_data_integrity(ephemeral_environment):
    """Test that data integrity is maintained through the complete flow"""
    env = ephemeral_environment
    
    # Create a specific workorder to track through the entire flow
    test_workorder = TracOSWorkorder(
        _id=ObjectId(),
        number=999,
        status="on_hold",
        title="Data Integrity Test Workorder",
        description="Testing data consistency through translation",
        createdAt=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        updatedAt=datetime(2025, 1, 15, 11, 45, 0, tzinfo=timezone.utc),
        deleted=False,
        deletedAt=None
    )
    
    # Insert into MongoDB
    await env['collection'].insert_one(dict(test_workorder))
    
    # Run the workflow
    await main()
    
    # Verify the workorder was translated to customer format in outbound
    outbound_file = os.path.join(env['outbound_dir'], 'workorder_999.json')
    assert os.path.exists(outbound_file), "Workorder 999 should exist in outbound"
    
    with open(outbound_file, 'r', encoding='utf-8') as f:
        customer_workorder = json.load(f)
    
    # Verify data integrity through translation
    assert customer_workorder['orderNo'] == 999
    assert customer_workorder['isOnHold'] == True, "Status 'on_hold' should translate to isOnHold=True"
    assert customer_workorder['isDone'] == False
    assert customer_workorder['isCanceled'] == False
    assert customer_workorder['summary'] == "Testing data consistency through translation"
    
    # Verify the original workorder was marked as synced
    synced_workorder = await env['collection'].find_one({"number": 999})
    assert synced_workorder['isSynced'] == True, "Original workorder should be marked as synced"
    assert 'syncedAt' in synced_workorder, "Should have syncedAt timestamp"
