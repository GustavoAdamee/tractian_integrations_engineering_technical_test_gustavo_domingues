from src.core.tracos_handler import TracOsHandler
from src.core.customer_handler import CustomerHandler
from src.core.translator import Translator
from setup import TracOSWorkorder
from setup import CustomerSystemWorkorder

class InboundProcessor:
    def __init__(self):
        self.tracos_handler = TracOsHandler()
        self.customer_handler = CustomerHandler()
        self.translator = Translator()

    async def process(self) -> None:
        await self.tracos_handler.connect()
        
        inbound_workorder: list[CustomerSystemWorkorder] = []
        inbound_workorder = self.customer_handler.get_workorders()
        
        translated_workorders: list[TracOSWorkorder] = []
        for workerorder in inbound_workorder:
            translated_workorders.append(self.translator.customer_to_tracos(workerorder))

        # TODO: Check if it is necessary to add a validation step here
        # for example, it is not possible to have a status "completed" if value before was "cancelled"
        for workorder in translated_workorders:
            await self.tracos_handler.create_workorder(workorder)

        await self.tracos_handler.disconnect()