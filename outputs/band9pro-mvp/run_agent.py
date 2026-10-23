"""Run one bounded Agent/Webhook batch from environment variables."""
from __future__ import annotations

import json
import os

from agent_client import AgentConfig, AgentRunner


def main() -> None:
    config = AgentConfig(
        local_api=os.environ["BAND_LOCAL_API"],
        agent_token=os.environ["AGENT_TOKEN"],
        webhook_url=os.environ["BAND_WEBHOOK_URL"],
        webhook_secret=os.environ["BAND_WEBHOOK_SECRET"],
    )
    runner = AgentRunner(config)
    try:
        print(json.dumps(runner.run_once(), ensure_ascii=False))
    finally:
        runner.close()


if __name__ == "__main__":
    main()
