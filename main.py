# https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.hypergeom.html
from fastapi import FastAPI
from pydantic import BaseModel, Field
from scipy.stats import hypergeom
import re

app = FastAPI()

# Defines the shape of an incoming req body
# Pydantic validates types and constraints (gt/ge)
class HypergeometricRequest(BaseModel):
    population_size: int = Field(gt=0)              # total items in the pool
    successes_in_population: int = Field(ge=0)      # how many "hits" exist
    draws: int = Field(gt=0)                        # how many items are drawn w/o replacement
    at_least: int = Field(default=1, ge=0)          # threshold for the "probability" field


@app.post("/probability/hypergeometric")
def hypergeometric(req: HypergeometricRequest):
    # The max number of successes possible in this draw.
    # Bound by whichever is smaller, you can't draw more success than cards you drew,
    # and you can't draw more successes than exist in the pool.
    max_k = min(req.draws, req.successes_in_population)

    # Probability of exaclty k successess [0, max_k].
    # hypergeom.pmf returns a numpy float, so it's wrapped in float()
    # to keep the response JSON-serializable.
    distribution = [
        float(hypergeom.pmf(k, req.population_size, req.successes_in_population, req.draws))
        for k in range(max_k + 1)
    ]

    probability = sum(distribution[req.at_least:])

    return {"distribution": distribution, "probability": probability}

def parse_dice_notation(notation: str):
    # Matches strings like "2d6+3" or "1d20-2" or "1d20"
    # Group 1: # of dice, Group 2: sides per die, Group 3: sign + number (optional)
    # Python int() handles leading sign directly, so group 3 is captured as one group
    match = re.match(r"^(\d+)d(\d+)([+-]\d+)?$", notation)
    if not match:
        return None     # signals malformed input to the caller

    count = int(match.group(1))
    sides = int(match.group(2))
    # Modifier defaults to 0 when absent
    modifier = int(match.group(3)) if match.group(3) else 0

    return count, sides, modifier
