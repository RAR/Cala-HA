"""Constants for the Cala Water Heater integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "cala"

# AWS Configuration (discovered from decompiled app)
AWS_REGION: Final = "us-east-1"
AWS_USER_POOL_ID: Final = "us-east-1_bawUVpr9"
AWS_CLIENT_ID: Final = "5d8a356c1c297bfad33cb108cd"
GRAPHQL_ENDPOINT: Final = "https://5mrdehpsojanvnvqcpeso2npiq.appsync-api.us-east-1.amazonaws.com/graphql"

# Default values
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
MIN_TEMP: Final = 95  # Fahrenheit
MAX_TEMP: Final = 140  # Fahrenheit

# Water heater modes
OPERATION_MODE_STANDARD: Final = "standard"
OPERATION_MODE_ECO: Final = "eco"
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
