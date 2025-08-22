from typing import Dict


class ATRIndicator:
    """Calculate ATR-based support and resistance levels."""

    @staticmethod
    def calculate(price: float, atr: float) -> Dict[str, float]:
        """Return ATR-based level map using Fibonacci ratios."""
        if atr == 0:
            return {}

        levels = {
            "level_0_382": price + (atr * 0.382),
            "level_0_618": price + (atr * 0.618),
            "level_1_000": price + atr,
            "level_1_618": price + (atr * 1.618),
            "level_2_618": price + (atr * 2.618),
            "level_neg_0_382": price - (atr * 0.382),
            "level_neg_0_618": price - (atr * 0.618),
            "level_neg_1_000": price - atr,
            "level_neg_1_618": price - (atr * 1.618),
            "level_neg_2_618": price - (atr * 2.618),
        }

        return {key: round(value, 4) for key, value in levels.items()}
