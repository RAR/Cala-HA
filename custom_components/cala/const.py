"""Constants for the Cala Water Heater integration."""
from __future__ import annotations

import re
from typing import Final

DOMAIN: Final = "cala"

# AWS Configuration (discovered from decompiled app)
AWS_REGION: Final = "us-east-1"
AWS_USER_POOL_ID: Final = "us-east-1_bawUVpr9c"
AWS_CLIENT_ID: Final = "5pgmmkmv4huev9s11se9n1a3rd"
AWS_IDENTITY_POOL_ID: Final = "us-east-1:2e75dd3e-7711-4cbb-924f-267ace573c3c"
GRAPHQL_ENDPOINT: Final = "https://5mrdehpsojanvnvqcpeso2npiq.appsync-api.us-east-1.amazonaws.com/graphql"

# Default values
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
MIN_TEMP: Final = 35  # Celsius
MAX_TEMP: Final = 60  # Celsius

# Water heater modes
OPERATION_MODE_STANDARD: Final = "standard"
OPERATION_MODE_VACATION: Final = "vacation"
OPERATION_MODE_BOOST: Final = "boost"

# Sensor keys
SENSOR_TOP_TANK_TEMP: Final = "top_tank_temp"
SENSOR_OUTLET_TEMP: Final = "outlet_temp"
SENSOR_INLET_TEMP: Final = "inlet_temp"
SENSOR_AMBIENT_TEMP: Final = "ambient_temp"
SENSOR_WATER_USED: Final = "water_used"
SENSOR_ENERGY_USED: Final = "energy_used"
SENSOR_COP: Final = "cop"  # Coefficient of Performance

# GraphQL operation names (discovered from bundle)
GQL_LIST_WATER_HEATERS_BY_HOME_ID: Final = "listWaterHeatersByHomeId"
GQL_WATER_HEATERS_BY_IOT_ID: Final = "waterHeatersByIoT_id"
GQL_CREATE_WATER_HEATER: Final = "CreateWaterHeaterWithThingReturnType"

# Device info
MANUFACTURER: Final = "Cala Systems"
MODEL: Final = "Heat Pump Water Heater"


def sanitize_entity_id(entity_id: str) -> str:
    """Sanitize entity ID to be lowercase with underscores only.
    
    Home Assistant requires entity IDs to be lowercase and only contain
    letters, numbers, and underscores.
    """
    # Convert to lowercase
    entity_id = entity_id.lower()
    # Replace any non-alphanumeric characters (except underscores) with underscores
    entity_id = re.sub(r'[^a-z0-9_]', '_', entity_id)
    # Replace multiple consecutive underscores with a single underscore
    entity_id = re.sub(r'_+', '_', entity_id)
    # Remove leading/trailing underscores
    entity_id = entity_id.strip('_')
    return entity_id
