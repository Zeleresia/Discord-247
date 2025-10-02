# Discord 247 Controller

An enhanced, modular Discord worker designed for **24/7 reliability** and managed via **Command Line Interface (CLI)**.

## Key Features

This project focuses on operational stability and provides key tools for real-time management directly through your terminal.

### Interactive CLI Management
The core user feature is the responsive TUI/CLI:
* **Real-time Monitoring:** View live **RAM, CPU usage, and Uptime** for the operation process.
* **Session Status:** Get instant feedback on the user's **Discord Gateway connection status**.
* **Voice Channel Toggling:** Easily **enable or disable** automatic voice channel joining.
* **Dynamic Presence:** Update the user's Discord **status** (online, idle, dnd) and **custom activity/status** on the fly.
* **Graceful Shutdown:** Securely log out and stop all background processes (`WebSocket`, `Heartbeat`, `Voice State`).

### Core Architecture (`core.py`)
The worker is built for robust, non-blocking operation:
* **Direct WebSocket Gateway:** Uses a direct WebSocket connection (`GATEWAY_URL`) for efficient communication with Discord.
* **Multi-threading:** Separates critical operations:
    * **Heartbeat Thread:** Ensures the connection remains alive by periodically sending heartbeats (`op: 1`).
    * **Gateway Loop:** Handles message reception (`op: 0` Dispatch) and reconnection logic.
* **Voice State Handling:** Manages joining and leaving voice channels using the `op: 4` **Voice State Update** payload.
* **Presence Updates:** Sends real-time presence changes (`op: 3`) for status and custom activities configured via the CLI.
* **Token Validation:** Built-in validation check using the `/users/@me` endpoint before connecting.

---

## Prerequisites

* **Python 3.10+** (Required)
* **Dependencies:** `websocket-client`, `psutil`, `requests`, and `python-dotenv`.
* **Virtual Environment** (Highly recommended for dependency isolation)

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/Zeleresia/Discord-247.git
    cd Discord_247
    ```
2.  Install the necessary dependencies. You'll need a `requirements.txt` containing the necessary libraries like `psutil`, `python-dotenv`, `requests`, and `websocket-client`.
    ```bash
    pip install -r requirements.txt
    ```


## Running program

Start the program by running the main entry point: 

    python main.py
    
## ⚠️ STRICT EDUCATIONAL NOTICE & DISCLAIMER

**THIS PROJECT IS INTENDED FOR EDUCATIONAL PURPOSES ONLY.**

This code demonstrates how to interact with the Discord Gateway using low-level **WebSockets** and **Multithreading** (in `core.py`) instead of standard high-level libraries. It serves as a learning tool to understand:

1.  Discord's **Heartbeat** and **Presence Update** protocols.
2.  How to send **Voice State Updates** directly.
3.  How to build a real-time, interactive **Command Line Interface (CLI)**.

### SECURITY WARNING

* **DO NOT** use this code structure in production without robust error handling, session management, and proper token security measures.
* **NEVER** share your Discord Token (`DISCORD_TOKEN`). Ensure your `.env` file is permanently excluded by **`.gitignore`** before committing.
