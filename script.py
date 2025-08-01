#!/usr/bin/env python3
import os
import time
import requests
import asyncio
import logging
import aiohttp
import signal
import sys

# Configuration from environment variables GLPI
GLPI_API_URL = os.getenv("GLPI_API_URL")
GLPI_USERNAME = os.getenv("GLPI_USERNAME")
GLPI_PASSWORD = os.getenv("GLPI_PASSWORD")
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN")
# MATRIX
MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER")
MATRIX_TOKEN = os.getenv("MATRIX_TOKEN")
ROOM_ID = os.getenv("ROOM_ID")
MESSAGE = os.getenv("MESSAGE")

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_env():
    missing = []
    for var in [
        "GLPI_API_URL", "GLPI_USERNAME", "GLPI_PASSWORD", "GLPI_APP_TOKEN",
        "MATRIX_HOMESERVER", "MATRIX_TOKEN", "ROOM_ID", "MESSAGE"
    ]:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

# Initialize a GLPI session and get the session token
def init_glpi_session():
    try:
        headers = {
            "Content-Type": "application/json",
            "App-Token": GLPI_APP_TOKEN
        }
        resp = requests.get(f"{GLPI_API_URL}/initSession", headers=headers, auth=(GLPI_USERNAME, GLPI_PASSWORD), timeout=10)
        if resp.status_code == 200:
            session_token = resp.json().get("session_token")
            logger.info("GLPI session initialized successfully")
            return session_token
        else:
            logger.error(f"Error initializing session: {resp.status_code}, {resp.text}")
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
        requests.get(f"{GLPI_API_URL}/killSession", headers=headers, timeout=5)
        logger.info("GLPI session terminated successfully")
    except Exception as e:
        logger.error(f"Error terminating session: {e}")

async def fetch_glpi_tickets(session_token):
    try:
        headers = {
            "Session-Token": session_token,
            "Content-Type": "application/json",
            "App-Token": GLPI_APP_TOKEN,
        }
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            async with session.get(f"{GLPI_API_URL}/Ticket", headers=headers) as response:
                if response.status in (200, 206):
                    data = await response.json()
                    if isinstance(data, list):
                        tickets = data
                    else:
                        tickets = data.get("data", [])
                    logger.info(f"Retrieved {len(tickets)} tickets from GLPI")
                    return tickets
                elif response.status == 401:  # Session expired/invalid
                    logger.warning("GLPI session expired, need to re-authenticate")
                    return None
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Error fetching tickets: {response.status}, {error_text}"
                    )
                    return []
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        return []

async def send_matrix_message(message):
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
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
                if response.status in (200, 201):
                    logger.info(f"Message sent: {message}")
                    return True
                else:
                    error_response = await response.text()
                    logger.error(f"Failed to send message. Status: {response.status}, Response: {error_response}")
                    return False
    except Exception as e:
        logger.error(f"Error sending Matrix message: {e}")
        return False

async def monitor_glpi_tickets():
    session_token = init_glpi_session()
    if not session_token:
        logger.error("Unable to initialize GLPI session. Stopping.")
        return

    previous_tickets = set()
    error_count = 0
    max_errors = 5

    while True:
        try:
            tickets = await fetch_glpi_tickets(session_token)
            if tickets is None:
                # Session probably expired, try to re-authenticate
                logger.info("Re-initializing GLPI session.")
                kill_glpi_session(session_token)
                session_token = init_glpi_session()
                if not session_token:
                    logger.error("Failed to re-initialize session. Stopping.")
                    break
                continue
            if tickets:
                # Normalize ticket IDs as string
                current_tickets = set(str(ticket['id']) for ticket in tickets if 'id' in ticket)
                new_tickets = current_tickets - previous_tickets
                for ticket_id in new_tickets:
                    ticket_info = next((t for t in tickets if str(t.get('id')) == ticket_id), None)
                    if ticket_info:
                        message = f"{MESSAGE} {ticket_info.get('name', 'No name')} (ID: {ticket_id})"
                        await send_matrix_message(message)
                previous_tickets = current_tickets
            error_count = 0  # Reset error count on success
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            logger.info("Ticket monitoring stopped.")
            break
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            error_count += 1
            if error_count >= max_errors:
                logger.error("Too many consecutive errors, stopping monitor.")
                break
            await asyncio.sleep(20)  # Wait longer after an error
    kill_glpi_session(session_token)

def handle_exit(signum, frame):
    logger.info("Received exit signal, shutting down...")
    sys.exit(0)

async def main():
    check_env()
    # Handle signals for graceful shutdown
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    try:
        await monitor_glpi_tickets()
    except KeyboardInterrupt:
        logger.info("Script stopped manually.")

if __name__ == "__main__":
    asyncio.run(main())
