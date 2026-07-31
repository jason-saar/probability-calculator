from fastapi import FastAPI
from pydantic import BaseModel, Field
from scipy.stats import hypergeom
import re
from collections import Counter

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

def dice_range_stats(counts: int, sides: int, modifier: int):
    # Worst case: every die rolls 1
    min_value = counts * 1 + modifier
    # Best case: every die rolls its max value
    max_value = counts * sides + modifier
    # Avg roll of a single die is (1 + sides) / 2
    # Expected values add linearly across independent dice,
    # so multiply by count, then add the modifier
    expected_value = counts * (1 + sides) / 2 + modifier
    return min_value, max_value, expected_value

def combine(dist_a: Counter, dist_b: Counter) -> Counter:
    # For every possible outcome pair, the combined sum's weight
    # is the product of the two individual weights.
    # Example: combine({1: 1, 2: 1}, {1: 1, 2: 1}) - 2d2/coins
    #          -> Counter({2: 1}, {3: 2}, {4: 1})
    # i.e. one way to roll a 2, two ways to roll a 3, one way to roll a 4
    combined = Counter()
    for outcome_a, count_a in dist_a.items():
        for outcome_b, count_b in dist_b.items():
            combined[outcome_a + outcome_b] += count_a * count_b
    return combined

def dice_distribution(count: int, sides: int, modifier: int) -> Counter:
    # Distribution for a single die: each face has weight 1
    single_die = Counter({face: 1 for face in range(1, sides + 1)})

    # Starting point before any dice are rolled. Let's the first combine()
    # call fold in the first die without needing special-case logic.
    total = Counter({0: 1})
    for _ in range(count):
        total = combine(total, single_die)

    # Modifier applied once to the whole roll, added after all dice have been
    # combined.
    shifted = Counter({outcome + modifier: weight for outcome, weight in total.items()})
    return shifted

def normalize(distribution: Counter, sides: int, count: int) -> dict:
    # Normalizes dice distribution outcomes into actual probabilities
    total_outcomes = sides ** count
    return {outcome: weight / total_outcomes for outcome, weight in distribution.items()}