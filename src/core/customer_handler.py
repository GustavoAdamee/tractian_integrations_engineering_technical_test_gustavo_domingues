from typing import List, Dict
from setup import CustomerSystemWorkorder
import os
import json
from loguru import logger

class CustomerHandler:
    def __init__(self):
        self.inbound_folder = os.getenv("DATA_INBOUND_DIR", "data/inbound")
        self.outbound_folder = os.getenv("DATA_OUTBOUND_DIR", "data/outbound")

    
    def get_workorders(self) -> List[CustomerSystemWorkorder]:
        """Get the workorder and return as a list of dicts"""
        workorders = []
        try:
            files = os.listdir(self.inbound_folder)
            json_files = [f for f in files if f.endswith('.json')]

            if not json_files:
                logger.info(f"No JSON files found in {self.inbound_folder}.")
                return workorders
            
            for file in json_files:
                file_path = os.path.join(self.inbound_folder, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        workorder_data = json.load(f)
                        workorders.append(workorder_data)
                        logger.debug(f"Successfully loaded workorder from {file}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON from file {file}: {e}")
                except Exception as e:
                    logger.error(f"Error reading file {file}: {e}")
            
            logger.info(f"Loaded {len(workorders)} workorders from {self.inbound_folder}")
            return workorders
        
        except Exception as e:
            logger.error(f"Failed to load workorders: {e}")
            return []


    def create_workorder(self, workorder: CustomerSystemWorkorder) -> None:
        """Create a workorder on outbound folder"""
        try:

            file_path = os.path.join(self.outbound_folder, f"workorder_{workorder['orderNo']}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(workorder, f, default=str, indent=4)
            
            logger.info(f"Created workorder {workorder['orderNo']} in {self.outbound_folder}")
        
        except Exception as e:
            logger.error(f"Failed to create workorder {workorder['orderNo']}: {e}")
            raise e
    


