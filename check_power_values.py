#!/usr/bin/env python3
"""Check what the power values actually look like."""
import asyncio
import json
from pathlib import Path
import aiohttp
from pycognito import Cognito

# AWS Configuration
AWS_USER_POOL_ID = "us-east-1_bawUVpr9c"
AWS_CLIENT_ID = "5pgmmkmv4huev9s11se9n1a3rd"
GRAPHQL_ENDPOINT = "https://5mrdehpsojanvnvqcpeso2npiq.appsync-api.us-east-1.amazonaws.com/graphql"
SESSION_FILE = Path.home() / ".cala_session.json"


async def check_power_values():
    """Check actual power values from API."""
    # Authenticate
    session_data = json.loads(SESSION_FILE.read_text())
    cognito = Cognito(
        AWS_USER_POOL_ID,
        AWS_CLIENT_ID,
        username=session_data.get("username"),
        access_token=session_data.get("access_token"),
        refresh_token=session_data.get("refresh_token"),
        id_token=session_data.get("id_token"),
    )
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, cognito.renew_access_token)
    access_token = cognito.access_token
    
    # Get device ID
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": access_token,
            "Content-Type": "application/json",
        }
        
        # Get homes
        query = """query { listHomes { items { id } } }"""
        async with session.post(
            GRAPHQL_ENDPOINT, json={"query": query}, headers=headers
        ) as resp:
            result = await resp.json()
            homes = result.get("data", {}).get("listHomes", {}).get("items", [])
        
        # Get heaters
        query = """
        query($homeId: ID!) {
            listWaterHeaterByHomeId(homeId: $homeId) {
                items { id IoT_id name }
            }
        }
        """
        async with session.post(
            GRAPHQL_ENDPOINT, 
            json={"query": query, "variables": {"homeId": homes[0]["id"]}},
            headers=headers
        ) as resp:
            result = await resp.json()
            heaters = result.get("data", {}).get("listWaterHeaterByHomeId", {}).get("items", [])
            device_id = heaters[0].get("IoT_id")
            print(f"Heater: {heaters[0].get('name')} (IoT: {device_id})")
        
        # Get sensor data with power fields
        query = """
        query($deviceId: String!) {
            listSensorDataByDeviceIdAndTimestamp(
                deviceId: $deviceId, sortDirection: DESC, limit: 5
            ) {
                items {
                    timestamp
                    compRunning
                    fanPwr
                    compPwr
                    upperElementPwr
                    lowerElementPwr
                }
            }
        }
        """
        async with session.post(
            GRAPHQL_ENDPOINT,
            json={"query": query, "variables": {"deviceId": device_id}},
            headers=headers
        ) as resp:
            result = await resp.json()
            
        print("\n" + "="*60)
        print("POWER VALUES FROM API (last 5 readings)")
        print("="*60)
        
        items = result.get("data", {}).get("listSensorDataByDeviceIdAndTimestamp", {}).get("items", [])
        for i, item in enumerate(items, 1):
            print(f"\nReading {i}:")
            print(f"  compRunning: {item.get('compRunning')} (type: {type(item.get('compRunning')).__name__})")
            print(f"  fanPwr: {item.get('fanPwr')} (type: {type(item.get('fanPwr')).__name__})")
            print(f"  compPwr: {item.get('compPwr')} (type: {type(item.get('compPwr')).__name__})")
            print(f"  upperElementPwr: {item.get('upperElementPwr')} (type: {type(item.get('upperElementPwr')).__name__})")
            print(f"  lowerElementPwr: {item.get('lowerElementPwr')} (type: {type(item.get('lowerElementPwr')).__name__})")

if __name__ == "__main__":
    asyncio.run(check_power_values())
