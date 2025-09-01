from __future__ import annotations

import random
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import UserMessage
from pydantic import BaseModel, Field

mcp: FastMCP = FastMCP("Dice Roller")


class RollResult(BaseModel):
    notation: str = Field(description="The original dice notation, normalised.")
    result: int = Field(description="The result of the dice roll.")
    raw_total: int = Field(
        description=(
            "The result of all dice rolls added together without any "
            "modifiers applied."
        )
    )
    roll_results: list[int] = Field(description="The individual results of each roll.")


class Roll(BaseModel):
    count: int = Field(ge=1, le=1000, description="The number of dice to roll.")
    sides: int = Field(ge=2, le=1000, description="The number of sides on the dice.")
    modifier: int = Field(
        default=0, description="The modifier to add or subtract from the dice."
    )

    def roll(self, rng: random.Random) -> RollResult:
        """
        Roll the dice using the given RNG and return a result object.
        """
        notation: str = self._generate_notation()
        total: int = 0
        rolls: list[int] = []
        for _ in range(self.count):
            roll = self._roll_single(rng)
            rolls.append(roll)
            total += roll
        modified_total = total + self.modifier
        return RollResult(
            notation=notation,
            result=modified_total,
            raw_total=total,
            roll_results=rolls,
        )

    def _roll_single(self, rng: random.Random) -> int:
        """Roll a single dice."""
        return rng.randint(1, self.sides)

    def _generate_notation(self) -> str:
        """
        Generate the dice notation from attributes.
        """
        mod = ""
        if self.modifier > 0:
            mod = f"+{self.modifier}"
        elif self.modifier < 0:
            mod = f"{self.modifier}"
        return f"{self.count}d{self.sides}{mod}"


DICE_REGEX = re.compile(r"^(\d+)?d(\d+)(?:([+-])(\d+))?$", re.IGNORECASE)


def parse_notation(notation: str) -> Roll:
    """
    Parse a given dice notation into a Roll object.
    """
    notation = notation.strip()
    m = DICE_REGEX.match(notation)
    if not m:
        raise ValueError(
            "Invalid dice notation. Use forms like 'd20', '1d6', '2d12+2', '5d6-8' etc."
        )

    count = m.group(1)
    if not count or count == "":
        count = 1
    else:
        count = int(count)

    sides = int(m.group(2))
    if sides <= 1:
        raise ValueError(f"Invalid count of sides '{sides}' must be at least 2")

    operator = m.group(3)
    modifier: int = 0
    if operator:
        modifier = int(m.group(4))
        match operator:
            case "+":
                modifier *= 1
            case "-":
                modifier *= -1
            case _:
                raise ValueError(f"Invalid modifier operator '{operator}'")

    return Roll(count=count, sides=sides, modifier=modifier)


@mcp.tool(
    name="roll",
    title="Roll Dice",
    description=(
        "Roll a dice based upon standard dice notation "
        "(e.g. 1d6, 2d20+1 etc. see rules://dice for more info), "
        "with an optional seed number for the random number generator."
    ),
)
def roll(notation: str, seed: Optional[int] = None) -> RollResult:
    roll = parse_notation(notation)
    rng: random.Random = random.Random(seed) if seed is not None else random.Random()
    return roll.roll(rng)


@mcp.resource(
    "rules://dice",
    name="rules",
    title="Dice Rules",
    description="Reference rules for dice notation.",
)
def dice_rules() -> str:
    return """
Dice notation takes the form XdY+Z:
- X = number of dice (default 1 if omitted)
- Y = sides per die (minimum 2)
- Z = optional modifier, added or subtracted
Examples:
  - `d20` roll one 20-sided die
  - `3d6+2` roll three six-sided dice and add 2
  - `1d10` roll one 10-sided die
  - `36d12-10` roll 36 12-sided dice and subtract 10 from the total
"""


@mcp.prompt(
    title="How to use dice notation",
)
def dice_help(example: str = "3d6+2") -> list[dict]:
    return [
        UserMessage(
            "Explain how to write dice notation and give a few examples. "
            f"Include what '{example}' means. Reference rules://dice if needed."
        ),
    ]


if __name__ == "__main__":
    mcp.run()
