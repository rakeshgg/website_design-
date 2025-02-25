# __define_ocg__
import sys
import json
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.services.services import HotelEngine

xml_input = """
<AvailRQ>
    <timeoutMilliseconds>25000</timeoutMilliseconds>
    <source>
        <languageCode>en</languageCode>
    </source>
    <optionsQuota>25</optionsQuota>
    <Configuration>
        <Parameters>
            <Parameter password="pass123" username="user123" CompanyID="123"/>
            <Parameter password="pass123" username="user123" CompanyID="123"/>
        </Parameters>
    </Configuration>
    <SearchType>Multiple</SearchType>
    <AvailDestinations>
        <Destination>New York</Destination>
        <Destination>London</Destination>
    </AvailDestinations>
    <StartDate>15/10/2025</StartDate>
    <EndDate>18/10/2025</EndDate>
    <Currency>USD</Currency>
    <Nationality>US</Nationality>
    <Market>ES</Market>
    <Paxes>
        <Pax type="Adult"/>
        <Pax type="Child" age="5"/>
    </Paxes>
    <Paxes>
        <Pax type="Adult"/>
    </Paxes>
</AvailRQ>
"""


# Define the secret handshake variable
var_ocg = "OCG_Secret_Handshake"


def main():
    """
    Hotel Processing System Entry Point.
    """
    print("🔹 Hotel Processing System v1.0 🔹")

    try:
        print("Processing XML with:", var_ocg)
        engine = HotelEngine()
        # Process request and handle response
        result = engine.process(xml_input)
        # Output result in formatted JSON
        print("\n✅ Processed Response:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        error_response = {"status": 500, "error": str(e)}
        print("\n❌ Error:")
        print(json.dumps(error_response, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
    sys.exit(0)