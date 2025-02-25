from typing import Dict, List, Any
from decimal import Decimal, ROUND_HALF_UP

'''
Calculate `selling_price` by applying the markup percentage to `price->net`.
If the `price->currency` differs from the request `Currency`, convert using the provided
exchange rates.
Update response fields: `selling_price`, `markup`, `exchange_rate`, and `selling_currency`.
Note - this can be make Genric based on responses of all services
'''

class PricingResponseConverter:
    """Handles price calculations and currency conversions for hotel responses."""

    def __init__(self, target_currency: str = "USD", exchange_rates: Dict[str, float] = None):
        """
        Initialize converter with financial rules.
        :param target_currency: ISO currency code for conversions
        :param exchange_rates: Dictionary of currency conversion rates 
                             (e.g., {'USD': 1.0, 'EUR': 0.85})
        """
        self.target_currency = target_currency.upper()
        self.exchange_rates = exchange_rates or {"USD": 1.0}
        self._validate_exchange_rates()

    def convert(self, response_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process all hotel entries in the response"""
        for hotel in response_data['data']['hotels']:
            hotel.update(self._process_hotel(hotel))
        return response_data

    def _process_hotel(self, hotel: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual hotel entry"""
        price_data = hotel.get("price", {})
        if not price_data:
            return hotel  # Skip processing if price data is missing

        net = self._to_decimal(price_data.get("net", 0))
        markup = self._to_decimal(price_data.get("markup", 0)) / 100
        original_currency = price_data.get("currency", "USD").upper()

        # Calculate selling price
        selling_price = net * (1 + markup)

        # Convert currency if needed
        exchange_rate = self._get_exchange_rate(original_currency)
        converted_price = selling_price * exchange_rate if original_currency != self.target_currency else selling_price

        # Update price details
        return {
            **hotel,
            "price": {
                **price_data,
                "selling_price": self._round(converted_price),
                "selling_currency": self.target_currency,
                "exchange_rate": self._round(exchange_rate),
            }
        }

    def _validate_exchange_rates(self):
        """Ensure required exchange rates exist"""
        if self.target_currency not in self.exchange_rates:
            raise ValueError(f"Missing exchange rate for target currency: {self.target_currency}")

    def _get_exchange_rate(self, source_currency: str) -> Decimal:
        """Retrieve exchange rate between source and target currency"""
        source_currency = source_currency.upper()
        if source_currency == self.target_currency:
            return Decimal("1.0")
        if source_currency not in self.exchange_rates:
            raise ValueError(f"Missing exchange rate for: {source_currency}")
        return Decimal(str(self.exchange_rates[self.target_currency])) / Decimal(str(self.exchange_rates[source_currency]))

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        """Convert input to Decimal, defaulting to 0 if invalid"""
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return Decimal("0")

    @staticmethod
    def _round(value: Decimal) -> float:
        """Round Decimal to two decimal places using financial rounding"""
        return float(value.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP))
