import pytest
import datetime
from datetime import timezone
from bson import ObjectId
import sys
import os
from unittest.mock import patch

# Add the src directory to the path for importing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.translator import Translator
from setup import CustomerSystemWorkorder, TracOSWorkorder

@pytest.fixture
def translator():
    return Translator()

@pytest.fixture
def sample_tracos_workorder():
    return {
        "_id": ObjectId(),
        "number": 42,
        "status": "in_progress",
        "title": "Fix machine",
        "description": "Fix the broken machine in sector A",
        "createdAt": {"$date": "2023-05-10T18:01:57.719Z"},
        "updatedAt": {"$date": "2023-05-11T19:01:57.719Z"},
        "deleted": False
    }

@pytest.fixture
def sample_customer_workorder():
    return {
        "orderNo": 42,
        "isActive": True,
        "isCanceled": False,
        "isDeleted": False,
        "isDone": False,
        "isOnHold": False,
        "isPending": False,
        "isSynced": False,
        "summary": "Fix the broken machine in sector A",
        "creationDate": "2023-05-10T18:01:57.719Z",
        "lastUpdateDate": "2023-05-11T19:01:57.719Z",
        "deletedDate": None
    }

class TestTranslatorTracosToCustomer:
    def test_basic_translation(self, translator, sample_tracos_workorder):
        """Test basic translation from TracOS to Customer format"""
        result = translator.tracos_to_costumer(sample_tracos_workorder)
        
        assert result["orderNo"] == sample_tracos_workorder["number"]
        assert result["isActive"] == True  # status is in_progress
        assert result["isCanceled"] == False
        assert result["isDeleted"] == False
        assert result["isDone"] == False
        assert result["isOnHold"] == False
        assert result["isPending"] == False
        assert result["summary"] == sample_tracos_workorder["description"]
        assert isinstance(result["creationDate"], str)
        assert isinstance(result["lastUpdateDate"], str)

    def test_cancelled_status(self, translator, sample_tracos_workorder):
        """Test translation with cancelled status"""
        sample_tracos_workorder["status"] = "cancelled"
        result = translator.tracos_to_costumer(sample_tracos_workorder)
        assert result["isCanceled"] == True
        assert result["isActive"] == False

    def test_completed_status(self, translator, sample_tracos_workorder):
        """Test translation with completed status"""
        sample_tracos_workorder["status"] = "completed"
        result = translator.tracos_to_costumer(sample_tracos_workorder)
        assert result["isDone"] == True
        assert result["isActive"] == False

    def test_on_hold_status(self, translator, sample_tracos_workorder):
        """Test translation with on_hold status"""
        sample_tracos_workorder["status"] = "on_hold"
        result = translator.tracos_to_costumer(sample_tracos_workorder)
        assert result["isOnHold"] == True
        assert result["isActive"] == False

    def test_pending_status(self, translator, sample_tracos_workorder):
        """Test translation with pending status"""
        sample_tracos_workorder["status"] = "pending"
        result = translator.tracos_to_costumer(sample_tracos_workorder)
        assert result["isPending"] == True
        assert result["isActive"] == False

    def test_deleted_flag(self, translator, sample_tracos_workorder):
        """Test translation with deleted flag"""
        sample_tracos_workorder["deleted"] = True
        sample_tracos_workorder["deletedAt"] = {"$date": "2023-05-12T10:00:00.000Z"}
        result = translator.tracos_to_costumer(sample_tracos_workorder)
        assert result["isDeleted"] == True
        assert result["deletedDate"] is not None

    def test_missing_required_fields(self, translator):
        """Test validation of required fields"""
        incomplete_workorder = {"title": "Incomplete"}
        with pytest.raises(ValueError):
            translator.tracos_to_costumer(incomplete_workorder)


class TestTranslatorCustomerToTracos:
    def test_basic_translation(self, translator, sample_customer_workorder):
        """Test basic translation from Customer to TracOS format"""
        result = translator.customer_to_tracos(sample_customer_workorder)
        
        assert isinstance(result["_id"], ObjectId)
        assert result["number"] == sample_customer_workorder["orderNo"]
        assert result["status"] == "in_progress"  # isActive == True
        assert result["title"] == sample_customer_workorder["summary"]
        assert result["description"] == sample_customer_workorder["summary"]
        assert isinstance(result["createdAt"], datetime.datetime)
        assert isinstance(result["updatedAt"], datetime.datetime)
        assert result["deleted"] == False
        assert result["deletedAt"] is None

    def test_cancelled_status(self, translator, sample_customer_workorder):
        """Test translation with cancelled status"""
        sample_customer_workorder["isCanceled"] = True
        sample_customer_workorder["isActive"] = False
        result = translator.customer_to_tracos(sample_customer_workorder)
        assert result["status"] == "cancelled"

    def test_done_status(self, translator, sample_customer_workorder):
        """Test translation with done status"""
        sample_customer_workorder["isDone"] = True
        sample_customer_workorder["isActive"] = False
        result = translator.customer_to_tracos(sample_customer_workorder)
        assert result["status"] == "completed"

    def test_on_hold_status(self, translator, sample_customer_workorder):
        """Test translation with on hold status"""
        sample_customer_workorder["isOnHold"] = True
        sample_customer_workorder["isActive"] = False
        result = translator.customer_to_tracos(sample_customer_workorder)
        assert result["status"] == "on_hold"

    def test_pending_status(self, translator, sample_customer_workorder):
        """Test translation with pending status"""
        sample_customer_workorder["isPending"] = True
        sample_customer_workorder["isActive"] = False
        result = translator.customer_to_tracos(sample_customer_workorder)
        assert result["status"] == "pending"

    def test_deleted_flag(self, translator, sample_customer_workorder):
        """Test translation with deleted flag"""
        sample_customer_workorder["isDeleted"] = True
        sample_customer_workorder["deletedDate"] = "2023-05-12T10:00:00.000Z"
        result = translator.customer_to_tracos(sample_customer_workorder)
        assert result["deleted"] == True
        assert result["deletedAt"] is not None

    def test_missing_required_fields(self, translator):
        """Test validation of required fields"""
        incomplete_workorder = {"summary": "Incomplete"}
        with pytest.raises(ValueError):
            translator.customer_to_tracos(incomplete_workorder)


class TestDateConversion:
    def test_mongo_date_format(self, translator):
        """Test conversion of MongoDB date format"""
        mongo_date = {"$date": "2023-05-10T18:01:57.719Z"}
        result = translator.date_to_iso_8601(mongo_date)
        expected = datetime.datetime(2023, 5, 10, 18, 1, 57, 719000, tzinfo=datetime.timezone.utc)
        assert result == expected
    
    def test_iso_string_format(self, translator):
        """Test conversion of ISO string format"""
        iso_date = "2023-05-10T18:01:57.719Z"
        result = translator.date_to_iso_8601(iso_date)
        expected = datetime.datetime(2023, 5, 10, 18, 1, 57, 719000, tzinfo=datetime.timezone.utc)
        assert result == expected
    
    def test_datetime_object(self, translator):
        """Test conversion of datetime object"""
        dt = datetime.datetime(2023, 5, 10, 18, 1, 57, 719000)
        result = translator.date_to_iso_8601(dt)
        expected = datetime.datetime(2023, 5, 10, 18, 1, 57, 719000, tzinfo=datetime.timezone.utc)
        assert result == expected
    
    def test_datetime_with_timezone(self, translator):
        """Test conversion of datetime with timezone"""
        dt = datetime.datetime(2023, 5, 10, 18, 1, 57, 719000, tzinfo=timezone.utc)
        result = translator.date_to_iso_8601(dt)
        expected = datetime.datetime(2023, 5, 10, 18, 1, 57, 719000, tzinfo=datetime.timezone.utc)
        assert result == expected
    
    def test_invalid_format(self, translator):
        """Test handling of invalid date formats"""
        with pytest.raises(ValueError):
            translator.date_to_iso_8601("not-a-date")
