# Get Online Let's Play

Get Online Let's Play is a simple multiplayer 2D top‑down world where players can join, receive a random name, move around the world and chat with others. Messages appear above each player's avatar for a few seconds before fading, and movement is predicted client side to reduce network traffic.

This repository contains two independent implementations of the game:

- A **Python** version using `asyncio` and `websockets` for the server and `tkinter` for the client.
- A **Node.js** version (under the `js/` folder) using Express and Socket.IO for a browser‑based client.

## Requirements

### Python version

- Python 3.8 or higher
- [`websockets`](https://pypi.org/project/websockets/) library (install via `pip install websockets`)
- Tkinter (usually included with standard Python distributions)

### Node.js version

- Node.js 14+ and npm
- The `express` and `socket.io` packages (installed automatically via npm)

## Usage

### Running the Python server and client

1. Install dependencies (only required once):

    ```bash
    pip install websockets
    ```

2. Start the server from the project root:

    ```bash
    python server.py
    ```

    The server listens on `ws://localhost:8765` by default.

3. In separate terminals, start one or more clients:

    ```bash
    python client.py
    ```

    Each client opens a window with a top‑down view. Use **WASD** or the **arrow keys** to move. Press **Enter** to open the chat box, type a message and press **Enter** again to send. Messages appear above your avatar for five seconds.

### Running the Node.js server and web client

1. Change into the `js` folder and install dependencies:

    ```bash
    cd js
    npm install
    ```

2. Start the Node.js server:

    ```bash
    node server.js
    ```

    The server serves a browser client on port `3000`.

3. Open a browser and navigate to [http://localhost:3000](http://localhost:3000) in multiple tabs or windows to play. Controls are the same as above.

## Folder structure

- `server.py` – Python server implementing the websocket game logic.
- `client.py` – Python Tkinter client.
- `js/` – Contains the JavaScript implementation:
  - `server.js` – Node.js/Express server using Socket.IO.
  - `package.json` – Node.js package manifest.
  - `public/` – Browser client (`index.html` and `client.js`) served by the Node server.

## Contributing

Contributions are welcome! If you’d like to add features or fix bugs:

1. Fork the repository and create a new branch for your work.
2. Commit your changes with clear messages.
3. Open a pull request describing your changes.

Feel free to open issues to report problems or request enhancements.

## License

No license has been specified yet; please contact the project owners before using this code in your own projects.
