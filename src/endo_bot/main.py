from __future__ import annotations

import asyncio

from endo_bot.bot.app import run_bot


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
