from src.core.tracos_handler import TracOsHandler
from src.core.customer_handler import CustomerHandler
from src.core.translator import Translator
from setup import TracOSWorkorder
from setup import CustomerSystemWorkorder

class OutboundProcessor:
    def __init__(self):
        self.tracos_handler = TracOsHandler()
        self.customer_handler = CustomerHandler()
        self.translator = Translator()

    async def process(self) -> None:
        await self.tracos_handler.connect()
        
        outbound_workorder: list[TracOSWorkorder] = []
        outbound_workorder = await self.tracos_handler.get_unsynced_workorders()

        translated_workorders: list[CustomerSystemWorkorder] = []
        for workorder in outbound_workorder:
            translated_workorders.append(self.translator.tracos_to_costumer(workorder))

        for workorder in translated_workorders:
            self.customer_handler.create_workorder(workorder)

        for workorder in outbound_workorder:
            await self.tracos_handler.mark_as_synced(workorder.get('_id'))
        
        await self.tracos_handler.disconnect()