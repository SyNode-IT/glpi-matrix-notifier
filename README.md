# GLPI Matrix Notifier

A Python-based project to monitor new tickets in GLPI and send notifications to a Matrix room.

## Features

- Monitors GLPI tickets in real-time.
- Sends notifications to Matrix chat rooms.
- Fully containerized with Docker and Docker Compose.

## Requirements

- Docker
- Docker Compose

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/SyNode-IT/glpi-matrix-notifier.git
cd glpi-matrix-notifier
```

### 2. Configure Environment Variables

Edit `docker-compose.yml` and set your 'container_name: NAME_CONTAINER'

Create a `.env` file in the project root with the following keys:

```
### Configuration GLPI
GLPI_API_URL="https://your-glpi-instance.tld/apirest.php"
GLPI_USERNAME="glpi_username"
GLPI_PASSWORD="glpi_password"
GLPI_APP_TOKEN="tokentokentokentokentoken"
### Configuration MATRIX
MATRIX_HOMESERVER="https://your-matrix-server.com"
MATRIX_TOKEN="tokentokentokentokentoken"
ROOM_ID="!your_room_id:your_matrix.tld"
### Message
MESSAGE="[CLIENT] 🆕 Ticket :"
```

### 3. Build and Run

To build the Docker image and start the service:

```bash
docker-compose up -d
```

### 4. Logs

View the application logs:

```bash
docker-compose logs -f
```

## License

This project is licensed under the MIT License.
