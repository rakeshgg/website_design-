from typing import Dict, Type, Tuple, Any, Optional
from src.processors.xml_processor import parse_xml
from src.processors.response_converter import PricingResponseConverter
from src.api.login_api import FakeLogin
from src.api.search_api import FakeHotelAPI
from src.core.exceptions import (
    InvalidHotelResponseError,
    InvalidHotelRequestError
)

class HotelEngine:
    """
    Handles hotel-related operations such as searching hotel details, 
    room details, policy, provisional booking, booking, 
    cancellation, and processing requests.
    """

    def __init__(self) -> None:
        """Initializes the HotelEngine with default values."""
        self.handler_class: Type[HotelSearchProcessor] = HotelSearchProcessor
        self.handler_classes: Dict[str, Type[HotelSearchProcessor]] = {
            "search_hotel": HotelSearchProcessor
        }
        self.handler_req: Optional[Dict[str, Any]] = None
        self.handler_res: Optional[Dict[str, Any]] = None
        self.api_constant: Optional[str] = None
        self.status_code: Optional[int] = None
        self.user: Optional[str] = None

    def get_handler(self, handler_name: str) -> Type[Any]:
        """
        Retrieves the appropriate handler class based on the provided handler name.

        Args:
            handler_name (str): The name of the handler to retrieve.

        Returns:
            Type[HotelSearchProcessor]: The handler class associated with the given name.
        """
        self.handler_class = self.handler_classes.get(handler_name)
        if not self.handler_class:
            raise ValueError(f"Handler '{handler_name}' not found.")

        self.api_constant = handler_name
        return self.handler_class

    @classmethod
    def handle_req_service_error(cls, json_data: Dict[str, Any], query_type: str) -> None:
        """
        Handles errors that occur during request validation.

        Args:
            json_data (Dict[str, Any]): Data for the request validation.
            query_type (str): The type of query being processed.
        """
        if not json_data or json_data.get("status") == "error":
            error_details = "\n".join(json_data.get("errors", []))
            raise InvalidHotelRequestError(
                f"Invalid hotel request for {query_type}: {error_details}"
            )

    @classmethod
    def handle_response_service_error(cls, response_obj: Dict[str, Any], query_type: str) -> None:
        """
        Handles errors that occur during service response processing.

        Args:
            response_obj (Dict[str, Any]): The response data.
            query_type (str): The type of query being processed.
        """
        if not response_obj or str(response_obj.get("status")) not in ["200", "201"]:
            error_details = response_obj.get("message", "Unknown error")
            raise InvalidHotelResponseError(
                f"Invalid hotel API response for {query_type}: {error_details}"
            )

    def authenticate_and_create_session(self, params: Dict[str, Any]) -> str:
        """
        Logs in the user using the supplier API and creates a session.

        Sessions are cached for efficient validation, using the 
        Object Pool Pattern to optimize login operations.

        Args:
            params (Dict[str, Any]): Login request parameters.

        Returns:
            str: Session ID.
        """
        login_obj = FakeLogin.login(params)
        self.handle_response_service_error(login_obj, "login_api")
        return login_obj["session_id"]

    def process(self, xml_req: str) -> Tuple[Dict[str, Any], int]:
        """
        Processes the XML request using the appropriate handler.
        Args:
            xml_req (str): The XML request payload.
        Returns:
            Tuple[Dict[str, Any], int]: A tuple containing the processed response and status code.
        """
        self.handler_req = self.handler_class.validate_build_request(xml_req)
        response_obj = self.handler_class.process_request(self.handler_req)
        self.handler_res = self.handler_class.process_response(response_obj)
        return self.handler_res


class HotelSearchProcessor:
    """
    Handles hotel search requests by validating the XML request, 
    processing the API call, and transforming the response.
    """

    query_type: str = "search_hotel"

    @classmethod
    def validate_build_request(cls, xml_req: str) -> Dict[str, Any]:
        """
        Parses and validates the XML request before processing.

        Args:
            xml_req (str): The XML request payload.

        Returns:
            Dict[str, Any]: The parsed and validated request JSON.
        """
        req_json = parse_xml(xml_req, "search_req")
        HotelEngine.handle_req_service_error(req_json, cls.query_type)
        return req_json

    @classmethod
    def process_request(cls, req_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes the hotel search request.

        - Extracts login credentials.
        - Authenticates and creates a session.
        - Calls the fake hotel search API.

        Args:
            req_json (Dict[str, Any]): The request JSON.

        Returns:
            Dict[str, Any]: The raw API response.
        """
        search_req_data = req_json.get("data", {})
        config_data = search_req_data.pop("Configuration", {})

        # Extract login request parameters
        login_req: Dict[str, Any] = {}
        parameters = config_data.get("Parameters", {}).get("Parameter", [])
        if isinstance(parameters, list) and parameters:
            login_req = parameters[0]  # Assuming one configuration for now

        # Authenticate and create session
        search_req_data["session_id"] = HotelEngine().authenticate_and_create_session(login_req)

        # genrate num of hotels based on AvailDestinations fake concets
        num_hotels = len(search_req_data.get('AvailDestinations', [0]))

        # Call the hotel search API
        fake_api = FakeHotelAPI(num_hotels=num_hotels)
        return fake_api.process_request(search_req_data)

    @classmethod
    def process_response(cls, response_obj: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        """
        Processes and transforms the API response.
        - Validates the API response.
        - Converts the response to the required format.
        Args:
            response_obj (Dict[str, Any]): The raw API response.
        Returns:
            Tuple[Dict[str, Any], int]: The transformed response and status code.
        """
        HotelEngine.handle_response_service_error(response_obj, cls.query_type)

        # Convert response format
        converter = PricingResponseConverter(
            target_currency="EUR",
            exchange_rates={"USD": 1.0, "EUR": 0.85, "GBP": 1.17}
        )
        converted_response = converter.convert(response_obj)
        return converted_response
