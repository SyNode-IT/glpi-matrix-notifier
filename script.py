#!/usr/bin/env python3
import os
import time
import requests
import asyncio
import logging
import aiohttp

# Configuration from environment variables
GLPI_API_URL = os.getenv("GLPI_API_URL")  # GLPI API base URL
GLPI_USERNAME = os.getenv("GLPI_USERNAME")  # GLPI username
GLPI_PASSWORD = os.getenv("GLPI_PASSWORD")  # GLPI password
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN")  # GLPI application token

MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER")  # Matrix homeserver URL
MATRIX_TOKEN = os.getenv("MATRIX_TOKEN")  # Matrix user access token
ROOM_ID = os.getenv("ROOM_ID")  # Matrix room ID for notifications

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to initialize a GLPI session and retrieve the session token
def init_glpi_session():
    try:
        headers = {
            "Content-Type": "application/json",
            "App-Token": GLPI_APP_TOKEN
        }
        response = requests.get(f"{GLPI_API_URL}/initSession", headers=headers, auth=(GLPI_USERNAME, GLPI_PASSWORD))
        if response.status_code == 200:
            session_token = response.json().get("session_token")
            logger.info("Successfully initialized GLPI session.")
            return session_token
        else:
            logger.error(f"Failed to initialize GLPI session: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        logger.error(f"Error initializing GLPI session: {e}")
        return None

# Function to terminate a GLPI session
def kill_glpi_session(session_token):
    try:
        headers = {
            "Session-Token": session_token,
            "Content-Type": "application/json",
            "App-Token": GLPI_APP_TOKEN
        }
        response = requests.get(f"{GLPI_API_URL}/killSession", headers=headers)
        if response.status_code == 200:
            logger.info("Successfully terminated GLPI session.")
        else:
            logger.error(f"Failed to terminate GLPI session: {response.status_code}, {response.text}")
    except Exception as e:
        logger.error(f"Error terminating GLPI session: {e}")

# Function to fetch tickets from GLPI
def fetch_glpi_tickets(session_token):
    try:
        headers = {
            "Session-Token": session_token,
            "Content-Type": "application/json",
            "App-Token": GLPI_APP_TOKEN
        }
        response = requests.get(f"{GLPI_API_URL}/Ticket", headers=headers)
        if response.status_code == 200:
            tickets = response.json().get("data", [])
            logger.info(f"Retrieved {len(tickets)} tickets from GLPI.")
            return tickets
        else:
            logger.error(f"Failed to retrieve tickets: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        return []

# Function to send a message to a Matrix room
async def send_matrix_message(message):
    try:
        async with aiohttp.ClientSession() as session:
            # Generate a unique transaction ID based on the current timestamp
            txn_id = int(time.time() * 1000)
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

# Function to monitor new GLPI tickets and send notifications to a Matrix room
async def monitor_glpi_tickets():
    # Initialize GLPI session
    session_token = init_glpi_session()
    if not session_token:
        logger.error("Failed to initialize GLPI session. Exiting.")
        return

    previous_tickets = set()
    try:
        while True:
            tickets = fetch_glpi_tickets(session_token)
            if tickets:
                # Extract current ticket IDs
                current_tickets = set(ticket['id'] for ticket in tickets)

                # Identify new tickets
                new_tickets = current_tickets - previous_tickets
                for ticket_id in new_tickets:
                    # Get information for the new ticket
                    ticket_info = next((t for t in tickets if t['id'] == ticket_id), None)
                    if ticket_info:
                        message = f"🆕 New ticket created: {ticket_info.get('name', 'No name')} (ID: {ticket_id})"
                        await send_matrix_message(message)

                # Update the list of previously seen tickets
                previous_tickets = current_tickets

            # Wait for 60 seconds before checking again
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        logger.info("Ticket monitoring stopped.")
    finally:
        # Ensure the session is terminated
        kill_glpi_session(session_token)

# Main function to start the monitoring
async def main():
    try:
        await monitor_glpi_tickets()
    except KeyboardInterrupt:
        logger.info("Script stopped manually.")

if __name__ == "__main__":
    asyncio.run(main())
