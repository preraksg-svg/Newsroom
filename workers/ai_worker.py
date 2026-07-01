import asyncio
import time
import logging
from system_orchestrator import NewsroomOrchestrator

# Setup logging
logging.basicConfig(level=logging.INFO, format='[AI-WORKER] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ai_worker")

async def ai_processing_loop():
    """Layer 2: AI Processing Worker. Handles summary, headlines, scoring."""
    logger.info("Initializing Layer 2: AI Processing Worker...")
    orchestrator = NewsroomOrchestrator()
    
    while True:
        try:
            # Fetch unclustered signals
            signals = orchestrator.get_latest_raw_signals(limit=5)
            
            if not signals:
                logger.info("No pending signals for AI processing. Sleeping...")
                await asyncio.sleep(30)
                continue
            
            logger.info(f"Processing {len(signals)} signals...")
            for signal in signals:
                try:
                    # process_signal will be refactored to handle ONLY Layer 2 tasks
                    await orchestrator.process_signal(signal)
                    logger.info(f"Successfully processed signal: {signal.get('title', 'Unknown')}")
                except Exception as e:
                    logger.error(f"Failed to process signal {signal.get('id')}: {e}")
            
            # Continuous processing with small pause
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"AI Worker loop failure: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(ai_processing_loop())
