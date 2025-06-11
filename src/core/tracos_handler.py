from motor.motor_asyncio import AsyncIOMotorClient
from setup import TracOSWorkorder
from typing import List, Dict, Any
from datetime import datetime, timezone
from loguru import logger
import os
import asyncio

class TracOsHandler:
    def __init__(self):
        self.mongo_db_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = os.getenv("MONGO_DATABASE", "tractian")
        self.collection_name = os.getenv("MONGO_COLLECTION", "workorders")
        
        self.max_retries = int(os.getenv("MONGO_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("MONGO_RETRY_DELAY", "1.0"))
        
        self.client = None
        self.db = None
        self.collection = None
        logger.info("TracOsHandler module initialized")

    async def _retry_operation(self, operation, *args, **kwargs):
        """Generic retry wrapper for MongoDB operations"""
        last_exception = None   # Store the last exception to raise if all retries fail
        
        for attempt in range(self.max_retries + 1):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    logger.warning(f"MongoDB operation failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}")
                    await asyncio.sleep(self.retry_delay)   # Sleep before retrying
                    
                    # Try to reconnect on connection errors
                    if "connection" in str(e).lower():
                        await self._reconnect()
                    
                    # TODO: Implement immediate fail for critical errors
                else:
                    logger.error(f"MongoDB operation failed after {self.max_retries + 1} attempts: {e}")
        
        raise last_exception

    async def _reconnect(self):
        """Attempt to reconnect to MongoDB"""
        try:
            if self.client:
                self.client.close()
            
            self.client = AsyncIOMotorClient(self.mongo_db_uri)
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            await self.client.admin.command('ping')
            logger.info("Successfully reconnected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to reconnect to MongoDB: {e}")
            raise

    async def connect(self) -> None:
        """Connect to MongoDB with retry logic"""
        # Skip connection if client is already set (for testing)
        if self.client is not None:
            logger.info("Using pre-configured MongoDB client (test mode)")
            return
        
        async def _connect_operation():
            self.client = AsyncIOMotorClient(self.mongo_db_uri)
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            await self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB at {self.mongo_db_uri}")
        
        await self._retry_operation(_connect_operation)

    async def disconnect(self) -> None:
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def parse_data(self, doc: Dict[str, Any]) -> TracOSWorkorder:
        """Parse MongoDB document into TracOSWorkorder object
        
        This function helps normalize the data structure and ensures
        the isSynced field is properly handled.
        """
        
        workorder = TracOSWorkorder(
            _id=doc["_id"],
            number=doc["number"],
            status=doc["status"],
            title=doc["title"],
            description=doc["description"],
            createdAt=doc["createdAt"],
            updatedAt=doc["updatedAt"],
            deleted=doc["deleted"],
            deletedAt=doc.get("deletedAt")
        )
        
        # Convert to dictionary to add the isSynced field
        workorder_dict = dict(workorder)
        
        # Add isSynced=False if it doesn't exist
        # if "isSynced" not in workorder_dict:
        #     workorder_dict["isSynced"] = False
            
        return workorder_dict

    async def get_unsynced_workorders(self) -> List[TracOSWorkorder]:
        """Read workorders from MongoDB that need to be synced with retry logic"""
        
        async def _get_operation():
            # Query for records that either have isSynced=False OR don't have the field
            query = {
                "$or": [
                    {"isSynced": False},
                    {"isSynced": {"$exists": False}}
                ]
            }
            
            cursor = self.collection.find(query)
            workorders = []

            async for doc in cursor:
                workorder = self.parse_data(doc)
                workorders.append(workorder)
                
            logger.info(f"Fetched {len(workorders)} unsynced workorders from MongoDB")
            return workorders
        
        return await self._retry_operation(_get_operation)

    async def create_workorder(self, workorder: TracOSWorkorder) -> None:
        """Write workorder to MongoDB with retry logic"""
        
        async def _create_operation():
            workorder_dict = dict(workorder)
            
            existing_doc = await self.collection.find_one({"number": workorder_dict["number"]})
            
            if existing_doc:
                original_id = existing_doc["_id"]
                if "_id" in workorder_dict:
                    del workorder_dict["_id"]
                    
                result = await self.collection.update_one(
                    {"_id": original_id},
                    {"$set": workorder_dict}
                )
                logger.info(f"Workorder with number {workorder_dict['number']} updated successfully")
            else:
                result = await self.collection.insert_one(workorder_dict)
                logger.info(f"New workorder created with ID: {result.inserted_id}")
        
        await self._retry_operation(_create_operation)

    async def mark_as_synced(self, workorder_id) -> None:
        """Mark workorder as synced with retry logic"""
        
        async def _mark_operation():
            utc_time = datetime.now(timezone.utc)
            result = await self.collection.update_one(
                {"_id": workorder_id},
                {"$set": {"isSynced": True, "syncedAt": utc_time}}
            )
            if result.modified_count == 0:
                logger.warning(f"No workorder found with ID: {workorder_id}")
                return
            logger.info(f"Marked workorder {workorder_id} as synced at {utc_time}")
        
        await self._retry_operation(_mark_operation)
