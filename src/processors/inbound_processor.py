from src.core.tracos_handler import TracOsHandler
from src.core.customer_handler import CustomerHandler
from src.core.translator import Translator
from setup import TracOSWorkorder
from setup import CustomerSystemWorkorder
from loguru import logger


class InboundProcessor:
    def __init__(self):
        self.tracos_handler = TracOsHandler()
        self.customer_handler = CustomerHandler()
        self.translator = Translator()
        logger.info("InboundProcessor initialized")

    async def process(self) -> None:
        """Process inbound workorders from the customer system and create them in TracOS."""
        logger.info("Starting inbound processing")
        await self.tracos_handler.connect()
        
        inbound_workorder: list[CustomerSystemWorkorder] = []
        inbound_workorder = self.customer_handler.get_workorders()
        
        if not inbound_workorder:
            logger.info("No workorders found to process")
            await self.tracos_handler.disconnect()
            return
        
        logger.info(f"Retrieved {len(inbound_workorder)} workorders from customer system")
        
        translated_workorders: list[TracOSWorkorder] = []
        for workerorder in inbound_workorder:
            translated_workorders.append(self.translator.customer_to_tracos(workerorder))

        logger.info(f"Translated {len(translated_workorders)} workorders")

        # TODO: Check if it is necessary to add a validation step here
        # for example, it is not possible to have a status "completed" if value before was "cancelled"
        processed_count = 0
        for workorder in translated_workorders:
            try:
                await self.tracos_handler.create_workorder(workorder)
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to create workorder {workorder.id if hasattr(workorder, 'id') else 'unknown'}: {e}")

        logger.info(f"Successfully processed {processed_count}/{len(translated_workorders)} workorders")
        await self.tracos_handler.disconnect()
        logger.info("Inbound processing completed")