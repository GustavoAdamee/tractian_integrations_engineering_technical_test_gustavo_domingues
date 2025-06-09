import pytest
import os
import json
import tempfile
import shutil
from unittest import mock
from src.core.customer_handler import CustomerHandler


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing and clean up after"""
    temp_inbound_dir = tempfile.mkdtemp()
    temp_outbound_dir = tempfile.mkdtemp()
    
    with mock.patch.dict(os.environ, {
        'DATA_INBOUND_DIR': temp_inbound_dir,
        'DATA_OUTBOUND_DIR': temp_outbound_dir
    }):
        yield temp_inbound_dir, temp_outbound_dir
    
    # Clean up directories after test completes
    shutil.rmtree(temp_inbound_dir)
    shutil.rmtree(temp_outbound_dir)


@pytest.fixture
def customer_handler(temp_dirs):
    """Create a CustomerHandler instance with patched environment variables"""
    handler = CustomerHandler()
    return handler


@pytest.fixture
def sample_workorder():
    """Create a sample workorder for testing"""
    return {
        "orderNo": 1,
        "isCanceled": True,
        "isDeleted": False,
        "isDone": False, 
        "isOnHold": False,
        "isPending": False,
        "summary": "Example workorder #1",
        "creationDate": "2025-05-10T18:01:57.763724+00:00",
        "lastUpdateDate": "2025-05-10T19:01:57.763724+00:00",
        "deletedDate": None
    }


def test_get_workorders_empty_directory(customer_handler):
    """Test get_workorders when inbound directory is empty"""
    workorders = customer_handler.get_workorders()
    assert len(workorders) == 0


def test_get_workorders_with_valid_json(customer_handler, temp_dirs, sample_workorder):
    """Test get_workorders with valid JSON files"""
    temp_inbound_dir, _ = temp_dirs
    
    # Create sample JSON files
    file_path = os.path.join(temp_inbound_dir, "workorder_1.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_workorder, f)
    
    # Create another sample JSON file
    sample_workorder2 = dict(sample_workorder)
    sample_workorder2["orderNo"] = 2
    file_path2 = os.path.join(temp_inbound_dir, "workorder_2.json")
    with open(file_path2, 'w', encoding='utf-8') as f:
        json.dump(sample_workorder2, f)
    
    workorders = customer_handler.get_workorders()
    assert len(workorders) == 2
    assert workorders[0]["orderNo"] == 2
    assert workorders[1]["orderNo"] == 1


def test_create_workorder_success(customer_handler, temp_dirs, sample_workorder):
    """Test create_workorder successfully creates a file"""
    _, temp_outbound_dir = temp_dirs
    
    customer_handler.create_workorder(sample_workorder)
    
    expected_file_path = os.path.join(temp_outbound_dir, f"workorder_{sample_workorder['orderNo']}.json")
    assert os.path.exists(expected_file_path)
    
    # Verify the content
    with open(expected_file_path, 'r', encoding='utf-8') as f:
        saved_workorder = json.load(f)
    
    assert saved_workorder["orderNo"] == sample_workorder["orderNo"]
    assert saved_workorder["summary"] == sample_workorder["summary"]


def test_customer_handler_workflow(temp_dirs, sample_workorder):
    """Test complete CustomerHandler workflow"""
    temp_inbound_dir, temp_outbound_dir = temp_dirs
    
    # Create the handler with our test environment
    handler = CustomerHandler()
    
    # 1. Create a sample workorder file
    file_path = os.path.join(temp_inbound_dir, "workorder_1.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_workorder, f)
        
    # 2. Test get_workorders retrieves the workorder
    workorders = handler.get_workorders()
    assert len(workorders) == 1
    assert workorders[0]["orderNo"] == sample_workorder["orderNo"]
    
    # 3. Test create_workorder creates a file in outbound directory
    handler.create_workorder(workorders[0])
    
    # 4. Verify the workorder was created in outbound directory
    expected_file_path = os.path.join(temp_outbound_dir, f"workorder_{sample_workorder['orderNo']}.json")
    assert os.path.exists(expected_file_path)

