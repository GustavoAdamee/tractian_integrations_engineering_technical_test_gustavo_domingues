from src.core.tracos_handler import TracOsHandler
from src.core.customer_handler import CustomerHandler
from src.core.translator import Translator
from setup import TracOSWorkorder
from setup import CustomerSystemWorkorder
from loguru import logger


class OutboundProcessor:
    def __init__(self):
        self.tracos_handler = TracOsHandler()
        self.customer_handler = CustomerHandler()
        self.translator = Translator()
        logger.info("OutboundProcessor initialized")

    async def process(self) -> None:
        """Process outbound workorders from TracOS and create them in the customer system."""
        logger.info("Starting outbound processing")
        await self.tracos_handler.connect()
        
        outbound_workorder: list[TracOSWorkorder] = []
        outbound_workorder = await self.tracos_handler.get_unsynced_workorders()

        if not outbound_workorder:
            logger.info("No unsynced workorders found to process")
            await self.tracos_handler.disconnect()
            return

        logger.info(f"Retrieved {len(outbound_workorder)} unsynced workorders from TracOS")

        translated_workorders: list[CustomerSystemWorkorder] = []
        for workorder in outbound_workorder:
            translated_workorders.append(self.translator.tracos_to_costumer(workorder))

        logger.info(f"Translated {len(translated_workorders)} workorders")

        processed_count = 0
        for workorder in translated_workorders:
            try:
                self.customer_handler.create_workorder(workorder)
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to create workorder in customer system {workorder.id if hasattr(workorder, 'id') else 'unknown'}: {e}")

        logger.info(f"Successfully created {processed_count}/{len(translated_workorders)} workorders in customer system")

        synced_count = 0
        for workorder in outbound_workorder:
            try:
                await self.tracos_handler.mark_as_synced(workorder.get('_id'))
                synced_count += 1
            except Exception as e:
                logger.error(f"Failed to mark workorder {workorder.get('_id', 'unknown')} as synced: {e}")
        
        logger.info(f"Successfully marked {synced_count}/{len(outbound_workorder)} workorders as synced")
        await self.tracos_handler.disconnect()
        logger.info("Outbound processing completed")