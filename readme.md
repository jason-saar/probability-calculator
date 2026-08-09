# Probability Calculator Microservice

## Description

A headless microservice that computes probability distributions for two use cases: hypergeometric draws (e.g. odds of drawing a specific card from a deck) and dice roll notation (e.g. "2d6+3").

## Running the service

Install dependencies:

```pip install fastapi uvicorn scipy```

Start the server:

```uvicorn main:app --port 8002```

The service will be available at `http://localhost:8002`.

## Communication Contract

### Requesting Data

Send an HTTP POST to `/probability/hypergeometric` or `/probability/dice` with a JSON body.

**POST /probability/hypergeometric**

| Field | Type | Description |
|---|---|---|
| population_size | integer | Total items in the pool. **required**, must be > 0 |
| successes_in_population | integer | How many "hits" exist in the pool. **required**, must be ≥ 0 |
| draws | integer | How many items are drawn without replacement. **required**, must be > 0 |
| at_least | integer | Threshold used to compute the summary probability (defaults to 1) |

```python
import requests

res = requests.post("http://localhost:8002/probability/hypergeometric", json={
    "population_size": 60,
    "successes_in_population": 4,
    "draws": 7,
    "at_least": 1
})
```

**POST /probability/dice**

| Field | Type | Description |
|---|---|---|
| dice | string | Dice notation, e.g. `"2d6+3"`. **required** |

```python
import requests

res = requests.post("http://localhost:8002/probability/dice", json={
    "dice": "2d6+3"
})
```

### Receiving Data

**POST /probability/hypergeometric** responds with a JSON object containing the full probability distribution (probability of exactly *k* successes, indexed from 0) and a summary `probability` field, the probability of drawing at least `at_least` successes.

```json
{
    "distribution": [0.513, 0.361, 0.114, 0.012],
    "probability": 0.487
}
```

```python
if res.status_code == 200:
    data = res.json()
    print("Probability:", data["probability"])
else:
    print("Failed:", res.json()["detail"])
```

**POST /probability/dice** responds with a JSON object containing the min, max, and expected value of the roll, plus the full probability distribution (mapping each possible outcome to its probability).

```json
{
    "min": 5,
    "max": 15,
    "expected_value": 10.0,
    "distribution": {
        "5": 0.0278,
        "6": 0.0556,
        "7": 0.0833
    }
}
```

```python
if res.status_code == 200:
    data = res.json()
    print(data["min"], data["max"], data["expected_value"])
else:
    print("Failed:", res.json()["detail"])
```

If `dice` is malformed (doesn't match the pattern `(int)d(int)[+-int]`, e.g. `"2d6+3"` or `"1d20-2"`), the service returns 400 with a JSON object containing a `detail` field describing the error.
