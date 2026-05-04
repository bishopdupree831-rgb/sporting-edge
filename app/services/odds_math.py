from __future__ import annotations


def american_to_decimal(odds: int) -> float:
    if odds == 0:
        raise ValueError("odds cannot be zero")
    return 1 + (odds / 100 if odds > 0 else 100 / abs(odds))


def implied_probability(odds: int) -> float:
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)


def expected_value(probability: float, odds: int, stake: float = 1.0) -> float:
    decimal = american_to_decimal(odds)
    profit = stake * (decimal - 1)
    return probability * profit - (1 - probability) * stake


def fair_american_odds(probability: float) -> int:
    probability = min(0.99, max(0.01, probability))
    if probability >= 0.5:
        return round(-(probability / (1 - probability)) * 100)
    return round(((1 - probability) / probability) * 100)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
