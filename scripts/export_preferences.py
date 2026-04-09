"""
Export RLHF preference pairs to JSONL format for fine-tuning.
Run periodically to generate training data from human edits.
"""
import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from shared.db.models import AsyncSessionLocal, init_db
from services.rlhf.collector import PreferencePair

async def export_preferences(output_file: str = "data/preferences.jsonl"):
    os.makedirs("data", exist_ok=True)
    await init_db()

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PreferencePair).where(PreferencePair.was_edited == "yes")
        )
        pairs = result.scalars().all()

    if not pairs:
        print("No preference pairs found yet.")
        print("Run the agent, approve/edit some replies in the HITL dashboard, then run this again.")
        return

    with open(output_file, "w") as f:
        for pair in pairs:
            record = {
                "prompt": pair.prompt,
                "chosen": pair.human_edit,
                "rejected": pair.agent_draft,
                "intent": pair.intent,
                "metadata": {
                    "signal_id": pair.signal_id,
                    "account_id": pair.account_id,
                    "sentiment": pair.sentiment_score,
                }
            }
            f.write(json.dumps(record) + "\n")

    print(f"Exported {len(pairs)} preference pairs to {output_file}")
    print(f"Use this file with Hugging Face TRL for DPO fine-tuning.")

asyncio.run(export_preferences())
