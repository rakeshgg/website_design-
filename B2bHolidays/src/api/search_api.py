from typing import Dict, Any
import random


class FakeHotelAPI:
    """A dynamic fake hotel API that generates mock search responses."""

    def __init__(self, num_hotels: int = 3):
        """Initialize the fake hotel API with a configurable number of hotels."""
        self.num_hotels = num_hotels

    def _generate_hotel_data(self) -> Dict[str, Any]:
        """
        Generate a single mock hotel entry.
        Returns:
            Dict[str, Any]: A dictionary containing hotel details.
        """
        return {
            "id": f"A#{random.randint(1, 1000)}",
            "hotelCodeSupplier": str(random.randint(10000000, 99999999)),
            "market": "US",
            "price": {
                "net": round(random.uniform(100, 300), 2),
                "currency": "USD",
                "markup": round(random.uniform(3.0, 10.0), 2),
                "exchange_rate": 1.0,
            },
        }

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the hotel search request and generate a structured response.
        Args:
            request (Dict[str, Any]): The incoming hotel search request.
        Returns:
            Dict[str, Any]: A structured response with status, data, and message.
        """
        try:
            session_id = request["session_id"]
            if not session_id:
                return {"status": 400, "data": None, "message": "Invalid Session ID"}
            if request["ServiceType"] != "HotelSearchRequest":
                return {"status": 400, "data": None, "message": "Invalid ServiceType"}
            # Generate mock hotel data
            hotel_data = [self._generate_hotel_data() for _ in range(self.num_hotels)]
            return {
                "status": 200,
                "data": {
                    "session_id": session_id,
                    "hotels": hotel_data,
                },
                "message": "Search successful",
            }
        except KeyError as e:
            return {"status": 400, "data": None, "message": f"Missing field: {str(e)}"}
        except Exception as e:
            return {"status": 500, "data": None, "message": f"Internal Server Error: {str(e)}"}
