"""Entrypoint for the application."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from loguru import logger
from src.processors.inbound_processor import InboundProcessor
from src.processors.outbound_processor import OutboundProcessor


async def main():
    logger.info("Starting TracOS ↔ Client Integration Flow")

    try:
        logger.info("=== Processing inbound flow ===")
        inbound_processor = InboundProcessor()
        await inbound_processor.process()
    except Exception as e:
        logger.error(f"Error during inbound processing: {e}")

    try:
        logger.info("=== Processing outbound flow ===")
        outbound_processor = OutboundProcessor()
        await outbound_processor.process()
    except Exception as e:
        logger.error(f"Error during outbound processing: {e}")

    logger.info("=== Processing finished ===")


if __name__ == "__main__":
    asyncio.run(main())
