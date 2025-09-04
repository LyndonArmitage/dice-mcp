from __future__ import annotations

import random
import re
from typing import Optional

import mcp.types as types
from fastmcp import Context, FastMCP
from fastmcp.prompts.prompt import PromptMessage, TextContent
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
    notation_explained: str = Field(description="The dice notation explained in text.")
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
        notation_explained = self.as_text()
        return RollResult(
            notation=notation,
            notation_explained=notation_explained,
            result=modified_total,
            raw_total=total,
            roll_results=rolls,
        )

    def as_text(self) -> str:
        """
        Return a human readable explanation of the notation
        """
        dice_txt = "dice" if self.count > 1 else "die"
        count_text = f"Roll {self.count} {self.sides} sided {dice_txt}"
        mod_text = "."
        if self.modifier != 0:
            if self.modifier < 0:
                mod_text = f", subtract {abs(self.modifier)} from the result."
            elif self.modifier > 0:
                mod_text = f", add {self.modifier} to the result."
        return f"{count_text}{mod_text}"

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
                raise ValueError(
                    f"Invalid modifier operator '{operator}', "
                    "supported operators are '+' and '-'"
                )

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
def roll(notation: str = "1d6", seed: Optional[int] = None) -> RollResult:
    roll = parse_notation(notation)
    rng: random.Random = random.Random(seed) if seed is not None else random.Random()
    return roll.roll(rng)


@mcp.resource(
    "rules://dice",
    name="rules",
    title="Dice Rules",
    description="Reference rules for dice notation.",
    mime_type="text/markdown",
)
def dice_rules() -> str:
    return """
Dice notation takes the form XdYoZ:
- X = number of dice (default 1 if omitted)
- Y = sides per die (minimum 2)
- o = optional operation to do to the result
- Z = optional modifier, used by the operation
Examples:
  - `d20` roll one 20-sided die
  - `3d6+2` roll three six-sided dice and add 2
  - `1d10` roll one 10-sided die
  - `36d12-10` roll 36 12-sided dice and subtract 10 from the total

Supported operations are:
 - Addition with +
 - Subtraction with -
""".strip()


@mcp.resource(
    "explain://{dice_notation}",
    name="explain_notation",
    title="Explain Dice Notation",
    description="Explains the given dice annotation in text",
    mime_type="text/plain",
)
def explain_notation(dice_notation: str = "2d6+12") -> str:
    roll = parse_notation(dice_notation)
    return roll.as_text()


@mcp.prompt(
    title="How to use dice notation",
    description="Get information on how to use dice notation.",
)
async def dice_help(example: str = "2d6+2", ctx: Context = None) -> list[dict]:
    result = await ctx.read_resource("rules://dice")
    result_content = types.TextResourceContents(
        uri="rules://dice", mimeType="text/markdown", text=str(result[0].content)
    )

    embedded = types.EmbeddedResource(type="resource", resource=result_content)

    message = (
        "Explain how to write dice notation and give a few examples. "
        f"Include what '{example}' means. Reference rules://dice if needed."
    )
    return [
        PromptMessage(role="user", content=embedded),
        PromptMessage(role="user", content=TextContent(type="text", text=message)),
    ]


if __name__ == "__main__":
    mcp.run()
