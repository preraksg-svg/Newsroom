import asyncio
import sys
import os

sys.path.append(os.getcwd())
from system_orchestrator import NewsroomOrchestrator

async def main():
    orch = NewsroomOrchestrator()
    print("Running newsroom orchestrator...")
    res = await orch.run_full_pipeline()
    print("Orchestrator run result:", res)

if __name__ == "__main__":
    asyncio.run(main())
