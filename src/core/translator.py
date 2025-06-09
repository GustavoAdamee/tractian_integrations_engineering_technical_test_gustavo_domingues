from setup import CustomerSystemWorkorder
from setup import TracOSWorkorder
import datetime
from bson import ObjectId
from loguru import logger

'''
TRACOS format:

class TracOSWorkorder(TypedDict):
    _id: ObjectId
    number: int
    status: Literal["pending", "in_progress", "completed", "on_hold", "cancelled"]
    title: str
    description: str
    createdAt: datetime
    updatedAt: datetime
    deleted: bool
    deletedAt: datetime | None = None

Example:
    {
    "number": 1,
    "status": "cancelled",
    "title": "Example workorder #1",
    "description": "Example workorder #1 description",
    "createdAt": {
        "$date": "2025-05-10T18:01:57.719Z"
    },
    "updatedAt": {
        "$date": "2025-05-10T19:01:57.719Z"
    },
    "deleted": false
    }
'''

'''
COSTUMER SERVICE format:

class CustomerSystemWorkorder(TypedDict):
    orderNo: int
    isActive: bool
    isCanceled: bool
    isDeleted: bool
    isDone: bool
    isOnHold: bool
    isPending: bool
    isSynced: bool
    summary: str
    creationDate: datetime
    lastUpdateDate: datetime
    deletedDate: datetime | None = None

Example:
    {
    "orderNo": 1,
    "isCanceled": true,
    "isDeleted": false,
    "isDone": false,
    "isOnHold": false,
    "isPending": false,
    "summary": "Example workorder #1",
    "creationDate": "2025-05-10T18:01:57.763724+00:00",
    "lastUpdateDate": "2025-05-10T19:01:57.763724+00:00",
    "deletedDate": null
    }
'''

class Translator:
    def __init__(self):
        logger.info("Translator module initialized")

    def tracos_to_costumer(self, workorder: TracOSWorkorder) -> CustomerSystemWorkorder:
        logger.debug(f"Starting TracOS to Customer translation for workorder {workorder.get('number', 'unknown')}")
        
        try:
            # Validate required fields
            if not workorder.get('number'):
                logger.error("Validation failed: Work order number is required")
                raise ValueError("Work order number is required")
            if not workorder.get('status'):
                logger.error(f"Validation failed: Work order status is required for workorder {workorder.get('number')}")
                raise ValueError("Work order status is required")
            if not workorder.get('createdAt'):
                logger.error(f"Validation failed: Work order createdAt is required for workorder {workorder.get('number')}")
                raise ValueError("Work order createdAt is required")
            
            logger.debug(f"Validation passed for workorder {workorder.get('number')}")
            
            status = workorder.get('status')
            is_canceled = status == 'cancelled'
            is_done = status == 'completed'
            is_on_hold = status == 'on_hold'
            is_pending = status == 'pending'
            is_active = status == 'in_progress'
            is_deleted = workorder.get('deleted', False)
            is_synced = False

            creation_date = self.date_to_iso_8601(workorder.get('createdAt')).isoformat()
            last_update_date = self.date_to_iso_8601(workorder.get('updatedAt')).isoformat()
            deleted_date = self.date_to_iso_8601(workorder.get('deletedAt')).isoformat() if workorder.get('deletedAt') is not None else None

            result = CustomerSystemWorkorder(
                orderNo=workorder.get('number'),
                isActive=is_active,
                isCanceled=is_canceled,
                isDeleted=is_deleted,
                isDone=is_done,
                isOnHold=is_on_hold,
                isPending=is_pending,
                isSynced=is_synced,
                summary=workorder.get('description'),
                creationDate=creation_date,
                lastUpdateDate=last_update_date,
                deletedDate=deleted_date
            )
            
            logger.info(f"Successfully translated TracOS workorder {workorder.get('number')} to Customer format")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to translate TracOS workorder {workorder.get('number', 'unknown')} to Customer format: {str(e)}")
            raise

    def customer_to_tracos(self, workorder: CustomerSystemWorkorder) -> TracOSWorkorder:
        logger.debug(f"Starting Customer to TracOS translation for workorder {workorder.get('orderNo', 'unknown')}")
        
        try:
            # Validate required fields
            if not workorder.get('orderNo'):
                logger.error("Validation failed: Customer work order number is required")
                raise ValueError("Customer work order number is required")
            
            logger.debug(f"Validation passed for customer workorder {workorder.get('orderNo')}")
            
            status = 'pending'
            if workorder.get('isCanceled'):
                status = 'cancelled'
            elif workorder.get('isDone'):
                status = 'completed'
            elif workorder.get('isOnHold'):
                status = 'on_hold'
            elif workorder.get('isActive'):
                status = 'in_progress'

            created_at = self.date_to_iso_8601(workorder.get('creationDate'))
            updated_at = self.date_to_iso_8601(workorder.get('lastUpdateDate'))
            deleted_at = self.date_to_iso_8601(workorder.get('deletedDate')) if workorder.get('deletedDate') else None

            result = TracOSWorkorder(
                _id=ObjectId(),
                number=workorder.get('orderNo'),
                status=status,
                title=workorder.get('summary'),
                description=workorder.get('summary'),
                createdAt=created_at,
                updatedAt=updated_at,
                deleted=workorder.get('isDeleted', False),
                deletedAt=deleted_at,
                isSynced=False
            )
            
            logger.info(f"Successfully translated Customer workorder {workorder.get('orderNo')} to TracOS format")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to translate Customer workorder {workorder.get('orderNo', 'unknown')} to TracOS format: {str(e)}")
            raise

    def date_to_iso_8601(self, date) -> str:
        if date is None:
            logger.debug("Date conversion: received None, returning empty string")
            return ""
        
        try:
            original_date = date
            
            # Handle MongoDB date format
            if isinstance(date, dict) and '$date' in date:
                logger.debug("Detected MongoDB date format")
                date = date['$date']
            
            # Handle string dates
            if isinstance(date, str):
                if 'T' in date:
                    date = datetime.datetime.fromisoformat(date.replace('Z', '+00:00'))
                    logger.debug("Parsed ISO format string to datetime")
                else:
                    date = datetime.datetime.fromisoformat(date)
                    logger.debug("Parsed simple format string to datetime")
            
            # Ensure UTC timezone
            if date.tzinfo is None:
                date = date.replace(tzinfo=datetime.timezone.utc)
                logger.debug("Added UTC timezone to naive datetime")
            elif date.tzinfo != datetime.timezone.utc:
                date = date.astimezone(datetime.timezone.utc)
                logger.debug("Converted timezone to UTC")
            
            # result = date.isoformat()
            logger.debug(f"Date conversion successful: {original_date} -> {date}")
            return date
            
        except Exception as e:
            logger.error(f"Failed to convert date {date} to ISO 8601 format: {str(e)}")
            raise ValueError(f"Invalid date format: {date}")