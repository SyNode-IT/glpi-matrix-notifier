#!/usr/bin/env python3
import os
import time
import requests
import asyncio
import logging
import aiohttp

# Configuration from environment variables GLPI
GLPI_API_URL = os.getenv("GLPI_API_URL")  # GLPI API base URL
GLPI_USERNAME = os.getenv("GLPI_USERNAME")  # GLPI username
GLPI_PASSWORD = os.getenv("GLPI_PASSWORD")  # GLPI password
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN")  # GLPI application token
# Configuration from environment variables MATRIX
MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER")  # Matrix homeserver URL
MATRIX_TOKEN = os.getenv("MATRIX_TOKEN")  # Matrix user access token
ROOM_ID = os.getenv("ROOM_ID")  # Matrix room ID for notifications
# Configuration from environment variable MESSAGE
MESSAGE = os.getenv("MESSAGE")  # Start of Message content

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize a GLPI session and get the session token
def init_glpi_session():
    try:
        headers = {
            "Content-Type": "application/json",
            "App-Token": GLPI_APP_TOKEN
        }
        response = requests.get(f"{GLPI_API_URL}/initSession", headers=headers, auth=(GLPI_USERNAME, GLPI_PASSWORD))
        if response.status_code == 200:
            session_token = response.json().get("session_token")
            logger.info("GLPI session initialized successfully")
            return session_token
        else:
            logger.error(f"Error initializing session: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error initializing session: {e}")
        return None

# Terminate a GLPI session
def kill_glpi_session(session_token):
    try:
        headers = {
            "Session-Token": session_token,
            "Content-Type": "application/json",
            "App-Token": GLPI_APP_TOKEN
        }
        response = requests.get(f"{GLPI_API_URL}/killSession", headers=headers)
        if response.status_code == 200:
            logger.info("GLPI session terminated successfully")
        else:
            logger.error(f"Error terminating session: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Error terminating session: {e}")

# Fetch tickets from GLPI
def fetch_glpi_tickets(session_token):
    try:
        headers = {
            "Session-Token": session_token,
            "Content-Type": "application/json",
            "App-Token": GLPI_APP_TOKEN
        }
        response = requests.get(f"{GLPI_API_URL}/Ticket", headers=headers)
        
        if response.status_code in (200, 206):
            # If the response is a list, return it directly
            if isinstance(response.json(), list):
                tickets = response.json()
            else:
                tickets = response.json().get("data", [])
                
            logger.info(f"Retrieved {len(tickets)} tickets from GLPI")
            return tickets
        else:
            logger.error(f"Error fetching tickets: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        return []

# Send a message to a Matrix room
async def send_matrix_message(message):
    try:
        async with aiohttp.ClientSession() as session:
            txn_id = int(time.time() * 1000)  # Transaction ID based on the timestamp
            url = f"{MATRIX_HOMESERVER}/_matrix/client/v3/rooms/{ROOM_ID}/send/m.room.message/{txn_id}"
            headers = {
                "Authorization": f"Bearer {MATRIX_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {
                "msgtype": "m.text",
                "body": message
            }
            
            async with session.put(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Message sent: {message}")
                    return True
                else:
                    error_response = await response.text()
                    logger.error(f"Failed to send message. Status: {response.status}, Response: {error_response}")
                    return False
    except Exception as e:
        logger.error(f"Error sending Matrix message: {e}")
        return False

# Monitor ticket changes
async def monitor_glpi_tickets():
    session_token = init_glpi_session()
    if not session_token:
        logger.error("Unable to initialize GLPI session. Stopping.")
        return

    previous_tickets = set()
    try:
        while True:
            tickets = fetch_glpi_tickets(session_token)
            if tickets:
                current_tickets = set(ticket['id'] for ticket in tickets)

                # Detect new tickets
                new_tickets = current_tickets - previous_tickets
                for ticket_id in new_tickets:
                    ticket_info = next((t for t in tickets if t['id'] == ticket_id), None)
                    if ticket_info:
                        message = f"{MESSAGE} {ticket_info.get('name', 'No name')} (ID: {ticket_id})"
                        await send_matrix_message(message)

                previous_tickets = current_tickets

            await asyncio.sleep(60)  # Check every minute
    except asyncio.CancelledError:
        logger.info("Ticket monitoring stopped.")
    finally:
        kill_glpi_session(session_token)

# Start monitoring tickets
async def main():
    try:
        await monitor_glpi_tickets()
    except KeyboardInterrupt:
        logger.info("Script stopped manually.")

if __name__ == "__main__":
    asyncio.run(main())
