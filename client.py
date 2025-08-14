import asyncio
import json
import queue
import random
import threading
import time
import math
import tkinter as tk

# Canvas dimensions
WIDTH, HEIGHT = 800, 600

# Store players keyed by id
players = {}
my_id = None

# Queue for communication between network thread and GUI thread
msg_queue = queue.Queue()

# Store network event loop and writer
network_state = {"loop": None, "writer": None}

# Chat bubbles {player_id: [(text, expiry_time), ...]}
chat_bubbles = {}

# Track key states to avoid duplicate messages
keys = {"up": False, "down": False, "left": False, "right": False}

# Chat mode flag
chat_mode = False

def run_network(host='localhost', port=8765):
    """Runs in a separate thread. Connects to the server and reads messages."""
    async def network_coroutine():
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except Exception as e:
            print(f"Unable to connect to server: {e}")
            return

        # Save loop and writer for send_message
        network_state["loop"] = asyncio.get_running_loop()
        network_state["writer"] = writer

        async def read_loop():
            while True:
                line = await reader.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode().strip())
                    msg_queue.put(data)
                except Exception:
                    continue
        await read_loop()

    asyncio.run(network_coroutine())

def send_message(message: dict):
    """Send a message to the server from the GUI thread."""
    loop = network_state.get("loop")
    writer = network_state.get("writer")
    if not loop or not writer:
        return
    async def _async_write():
        writer.write((json.dumps(message) + "\n").encode())
        await writer.drain()
    asyncio.run_coroutine_threadsafe(_async_write(), loop)

def process_messages():
    """Process messages from the network thread."""
    now = time.time()
    try:
        while True:
            data = msg_queue.get_nowait()
            handle_message(data)
    except queue.Empty:
        pass
    # Remove expired chat bubbles
    for pid in list(chat_bubbles.keys()):
        chat_bubbles[pid] = [(text, expiry) for text, expiry in chat_bubbles[pid] if expiry > now]
    root.after(30, process_messages)

def handle_message(data):
    """Handle a single message from the server."""
    global my_id
    t = data.get("type")
    if t == "yourInfo":
        my_id = data.get("id")
    elif t == "currentPlayers":
        players.clear()
        for pid, p in data.get("players", {}).items():
            players[pid] = p
            chat_bubbles.setdefault(pid, [])
    elif t == "newPlayer":
        p = data.get("player")
        if p:
            pid = p["id"]
            players[pid] = p
            chat_bubbles.setdefault(pid, [])
    elif t == "playerDisconnected":
        pid = data.get("id")
        if pid and pid in players:
            players.pop(pid, None)
            chat_bubbles.pop(pid, None)
    elif t == "state":
        for pid, p in data.get("players", {}).items():
            if pid in players:
                players[pid].update(p)
    elif t == "chat":
        pid = data.get("id")
        text = data.get("text", "")
        if pid:
            chat_bubbles.setdefault(pid, [])
            chat_bubbles[pid].insert(0, (text, time.time() + 5))
            if len(chat_bubbles[pid]) > 3:
                chat_bubbles[pid] = chat_bubbles[pid][:3]

def render():
    """Render players and chat bubbles on the canvas."""
    canvas.delete("all")
    for pid, p in players.items():
        x = p.get("x", 0)
        y = p.get("y", 0)
        angle = p.get("angle", 0)
        name = p.get("name", "")
        color = p.get("color", "#888888")
        if not isinstance(color, str):
            color = str(color)
        if not color.startswith("#"):
            color = "#" + color
        # Draw player square
        canvas.create_rectangle(x, y, x + 20, y + 20, fill=color, outline="")
        # Draw orientation arrow (adjust by -90 degrees so 0 degrees points up)
        rad = math.radians(angle - 90)
        cx = x + 10
        cy = y + 10
        length = 15
        ex = cx + length * math.cos(rad)
        ey = cy + length * math.sin(rad)
        canvas.create_line(cx, cy, ex, ey, fill="black", width=2)
        # Draw player name
        canvas.create_text(cx, y - 10, text=name, fill="black")
        # Draw chat bubbles
        if pid in chat_bubbles:
            offset = 0
            for text, expiry in chat_bubbles[pid]:
                canvas.create_text(cx, y - 30 - offset, text=text, fill="black", font=("Arial", 8))
                offset += 12
    root.after(33, render)

def on_key_press(event):
    """Handle key press events for movement and chat."""
    global chat_mode
    if event.keysym == "Return":
        if not chat_mode:
            chat_mode = True
            chat_entry.delete(0, tk.END)
            chat_entry.place(x=10, y=HEIGHT - 30, width=200)
            chat_entry.focus_set()
        else:
            msg = chat_entry.get().strip()
            chat_entry.place_forget()
            root.focus_set()
            chat_mode = False
            if msg:
                send_message({"type": "chat", "text": msg})
        return

    if chat_mode:
        return

    keymap = {
        "Up": "up",
        "Down": "down",
        "Left": "left",
        "Right": "right",
        "w": "up",
        "s": "down",
        "a": "left",
        "d": "right",
    }
    direction = keymap.get(event.keysym)
    if direction and not keys[direction]:
        keys[direction] = True
        send_message({"type": "moveStart", "direction": direction})

def on_key_release(event):
    """Handle key release events."""
    if chat_mode:
        return
    keymap = {
        "Up": "up",
        "Down": "down",
        "Left": "left",
        "Right": "right",
        "w": "up",
        "s": "down",
        "a": "left",
        "d": "right",
    }
    direction = keymap.get(event.keysym)
    if direction and keys[direction]:
        keys[direction] = False
        send_message({"type": "moveStop", "direction": direction})

# Start network thread
threading.Thread(target=run_network, kwargs={"host": "localhost", "port": 8765}, daemon=True).start()

# Setup GUI
root = tk.Tk()
root.title("Get Online Let's Play")
canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="white")
canvas.pack()
chat_entry = tk.Entry(root)
chat_entry.place_forget()

# Bind events
root.bind("<KeyPress>", on_key_press)
root.bind("<KeyRelease>", on_key_release)

# Start loops
root.after(30, process_messages)
root.after(33, render)

root.mainloop()
