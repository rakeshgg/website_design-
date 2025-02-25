from lxml import etree
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Type
from abc import ABC, abstractmethod
from collections import Counter, OrderedDict


class XmlProcessor(ABC):
    """
    Generic XML Processor for parsing, validating, and transforming XML requests.
    """

    # Default values for XML fields
    # this cn be fetced from configuration 
    DEFAULTS = {
        "languageCode": "en",
        "optionsQuota": 20,
        "Currency": "EUR",
        "Nationality": "US",
        "Market": "ES",
    }

    # Valid values for specific XML fields
    VALID_VALUES = {
        "languageCode": {"en", "fr", "de", "es"},
        "Currency": {"EUR", "USD", "GBP"},
        "Nationality": {"US", "GB", "CA"},
        "Market": {"US", "GB", "CA", "ES"},
    }

    def __init__(self, xml_string: str, schema: Optional[etree.XMLSchema] = None, encoding=None):
        """
        Initialize the XML processor.
        Args:
            xml_string (str): The XML string to process.
            schema (Optional[etree.XMLSchema]): The XML schema for validation (optional).
        Raises:
            ValueError: If the XML is malformed or fails schema validation.
        """
        self.data: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.xml_schema = schema
        if isinstance(xml_string, str):
            encoding = encoding or 'utf-8'
            xml_string = xml_string.encode(encoding)
        try:
            # Parse the XML string
            self.root = etree.XML(xml_string)
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Malformed XML: {e}")
        # Validate the XML against the schema (if provided)
        if self.xml_schema and not self.xml_schema.validate(self.root):
            error_log = self.xml_schema.error_log
            raise ValueError(f"XML validation failed:\n{error_log}")

    @abstractmethod
    def process(self) -> str:
        """
        Subclasses must implement this method to validate and transform data.
        Returns:
            str: JSON response after processing the XML.
        """
        pass

    def _get_validated_field(self, xpath: str, valid_values: set, default_key: str) -> str:
        """
        Get and validate a field from XML.

        Args:
            xpath (str): The XPath to locate the field in the XML.
            valid_values (set): Set of valid values for the field.
            default_key (str): Key to retrieve the default value from DEFAULTS.

        Returns:
            str: The validated field value or the default value.
        """
        value = self.root.findtext(xpath, self.DEFAULTS[default_key])
        return value if value in valid_values else self.DEFAULTS[default_key]

    def _parse_integer(self, xpath: str, default: Optional[int] = 0, max_value: Optional[int] = None) -> int:
        """
        Parse an integer value from XML, ensuring it falls within a valid range.

        Args:
            xpath (str): The XPath to locate the field in the XML.
            default (int): Default value if the field is missing or invalid.
            max_value (Optional[int]): Maximum allowed value for the field.

        Returns:
            int: The parsed integer value.
        """
        value = self.root.findtext(xpath)
        if value and value.isdigit():
            parsed_value = int(value)
            return min(parsed_value, max_value) if max_value else parsed_value
        return default

    def _parse_text_list(self, xpath: str):
        """Extracts a list of data from XML."""
        return [dest.text for dest in self.root.findall(xpath)]

    def _validate_dates(self, start_xpath: str, end_xpath: str):
        """
        Validate check-in and check-out dates.
        Args:
            start_xpath (str): XPath to locate the start date in the XML.
            end_xpath (str): XPath to locate the end date in the XML.
        """
        try:
            start_date_str = self.root.findtext(start_xpath)
            end_date_str = self.root.findtext(end_xpath)

            start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
            end_date = datetime.strptime(end_date_str, "%d/%m/%Y")
            # Validate start date
            if start_date < datetime.today() + timedelta(days=2):
                self.errors.append("StartDate must be at least 2 days after today.")
            # Validate stay duration
            if (end_date - start_date).days < 3:
                self.errors.append("Stay duration must be at least 3 nights.")
            # Add dates to processed data
            self.data["StartDate"] = start_date_str
            self.data["EndDate"] = end_date_str
        except ValueError:
            self.errors.append("Invalid date format, expected DD/MM/YYYY.")

    def _build_response(self) -> str:
        """
        Build and return a JSON response.
        Returns:
            str: JSON response containing status, errors (if any), and processed data.
        """
        if self.errors:
            response = {"status": "error", "errors": self.errors}
        else:
            response = {"status": "success", "data": self.data}

        return response

class XmltoDictProcessor(XmlProcessor):

    def __init__(self, xml_string: str, schema: Optional[etree.XMLSchema] = None, encoding=None):
        super().__init__(xml_string, schema, encoding)
        # if requierd this can be make dynamic
        self.attr_prefix = '@'
        self.dict = OrderedDict
        self.list = list

    @staticmethod
    def _fromstring(value):
        """Converts XML string values to appropriate types"""
        if not value:
            return ""
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    def _element_to_dict(self, root):
        """
        Convert an `etree.Element` into a dictionary.
        Args:
            root (etree.Element): The root XML element to convert.
        Returns:
            dict: A dictionary representation of the XML element.
        """
        result = self.dict()
        # Add attributes to the result dictionary
        for attr, attrval in root.attrib.items():
            attr_key = attr if self.attr_prefix is None else self.attr_prefix + attr
            result[attr_key] = self._fromstring(attrval)
        # Filter child elements (ignore non-element nodes like comments)
        children = [node for node in root if isinstance(node.tag, str)]
        # If no children, return the text content (if any) or the attributes
        if not children:
            if root.text and root.text.strip():
                return self._fromstring(root.text.strip())
            return result
        # Count occurrences of each child tag
        tag_count = Counter(child.tag for child in children)
        # Process child elements
        for child in children:
            if tag_count[child.tag] == 1:
                result[child.tag] = self._element_to_dict(child)
            else:
                # If multiple children with the same tag, store them in a list
                result.setdefault(child.tag, []).append(self._element_to_dict(child))
        return result

    def process(self) -> str:
        """
        Parses an XML string into a JSON-compatible dictionary.
        """
        self.data = self._element_to_dict(self.root)
        return self._build_response()

class HotelRequestProcessor(XmlProcessor):
    """
    Processor for Hotel Requests (validates & generates JSON).
    This class extends `XmlProcessor` to handle hotel-specific XML requests,
    including validation of search criteria, dates, and room details.
    """

    def __init__(self, xml_string: str, schema: Optional[etree.XMLSchema] = None, encoding=None):
        super().__init__(xml_string, schema, encoding)
        # if requierd this can be fetched from configuration flow
        self.allowed_room_count = 5
        self.allowed_room_guest_count = 4
        self.allowed_child_count_per_room = 2

    def process(self) -> str:
        """
        Process the hotel request XML, validate its contents, and generate a JSON response.
        Returns:
            str: A JSON response containing the processed data or validation errors.
        """
        # Set service type
        self.data["ServiceType"] = "HotelSearchRequest"
        # get timeoutMilliseconds
        self.data["timeoutMilliseconds"] = self._parse_integer(".//timeoutMilliseconds")
        # Validate language code
        self.data["languageCode"] = self._get_validated_field(
            ".//languageCode", self.VALID_VALUES["languageCode"], "languageCode"
        )

        # Validate options quota
        self.data["optionsQuota"] = self._parse_integer(".//optionsQuota", 20, 50)

        # Validate required parameters
        self._validate_required_parameters()

        # Validate search type and destinations
        self._validate_search_type_and_destinations()

        # Validate dates
        self._validate_dates(".//StartDate", ".//EndDate")

        # Validate currency, nationality, and market
        self._validate_search_criteria()

        # Validate rooms and passengers
        self._validate_rooms(".//Paxes", ".//Pax")

        # Build and return the JSON response
        return self._build_response()

    def _validate_required_parameters(self):
        """
        Validate required parameters: password, username, and CompanyID.
        """
        self.data["Configuration"] = {"Parameters": {"Parameter": []}}
        parameters = self.root.findall(".//Configuration/Parameters/Parameter")
        if not parameters:
            self.errors.append("Missing required parameters in Configuration.")
            return
        required_fields = ["password", "username", "CompanyID"]
        param_list = []
        for param in parameters:
            param_data = {field: param.attrib.get(field) for field in required_fields}
            # Collect missing fields
            missing_fields = [field for field in required_fields if not param_data[field]]
            if "CompanyID" in param_data and (not param_data["CompanyID"] or not param_data["CompanyID"].isdigit()):
                missing_fields.append("CompanyID (invalid format)")
            if missing_fields:
                self.errors.append(f"Missing or invalid required parameters: {', '.join(missing_fields)}")
            param_list.append(param_data)
        self.data["Configuration"]["Parameters"]["Parameter"] = param_list


    def _validate_search_type_and_destinations(self):
        """
        Validate search type and destinations based on the rules.
        """
        search_type = self.root.findtext(".//SearchType")
        if search_type not in {"Single", "Multiple"}:
            self.errors.append("Invalid SearchType. Must be 'Single' or 'Multiple'.")
            return
        self.data["SearchType"] = search_type
        destinations = self._parse_text_list(".//AvailDestinations/Destination")
        if search_type == "Single" and len(destinations) != 1:
            self.errors.append("Single SearchType must have exactly one destination.")
        elif search_type == "Multiple" and len(destinations) > self.allowed_room_count:
            self.errors.append(f"Multiple SearchType can have at most {self.allowed_room_count} destinations.")
        self.data["AvailDestinations"] = destinations

    def _validate_search_criteria(self):
        """
        Validate common search criteria fields: Currency, Nationality, Market.

        Updates `self.data` with validated values.
        """
        for field, valid_values in self.VALID_VALUES.items():
            self.data[field] = self._get_validated_field(f".//{field}", valid_values, field)

    def _validate_rooms(self, rooms_xpath: str, pax_xpath: str):
        """
        Validate room details, including the number of adults and children.
        Args:
            rooms_xpath (str): XPath to locate room elements.
            pax_xpath (str): XPath to locate passenger elements within a room.
        """
        rooms = self.root.findall(rooms_xpath)
        if len(rooms) > self.allowed_room_count:
            self.errors.append(f"Maximum allowed rooms: {self.allowed_room_count}.")
            return

        room_list = []
        for room in rooms:
            room_data = {"Adults": 0, "Children" : 0, "childrenAges": []}

            # Process each passenger in the room
            pax_elements = room.findall(pax_xpath)
            if len(pax_elements) > self.allowed_room_guest_count:
                self.errors.append(f"Maximum allowed guests per room: {self.allowed_room_guest_count}.")
                continue

            for pax in pax_elements:
                pax_type = pax.attrib.get("type")
                if pax_type == "Adult":
                    room_data["Adults"] += 1
                elif pax_type == "Child":
                    age = pax.attrib.get("age", "0")
                    room_data["Children"] += 1
                    room_data["childrenAges"].append(int(age))

            # Validate room rules
            if room_data["Children"] and room_data["Adults"] == 0:
                self.errors.append("Each room must have at least one Adult if Children are present.")
            if room_data["Children"] > self.allowed_child_count_per_room:
                self.errors.append(f"Maximum allowed children per room: {self.allowed_child_count_per_room}.")
            room_list.append(room_data)

        # Add room details to processed data
        self.data["Rooms"] = room_list


# Mapper for request types to processors
# XmltoDictProcessor is genric class to convert xml to json dict
HOTEL_REQUEST_PROCESSORS: Dict[str, Type[XmlProcessor]] = {
    "search_req": HotelRequestProcessor,
    "xml_to_json" : XmltoDictProcessor
}

# client code
def parse_xml(xml_string, request_type, schema=None, encoding=None):
    try:
        processor_class = HOTEL_REQUEST_PROCESSORS.get(request_type)
        if not processor_class:
            raise ValueError(f"Invalid request type: {request_type}")
        return processor_class(xml_string, schema, encoding).process()
    except Exception as ex:
        return {"status": "error", "errors" : [str(ex)]}