import asyncio
import json
import queue
import random
import threading
import time
import tkinter as tk

WIDTH, HEIGHT = 800, 600
# Store players data keyed by id
players = {}
my_id = None

# Message queue for network thread to communicate with GUI thread
msg_queue = queue.Queue()

# Network state to hold loop and writer
network_state = {
    "loop": None,
    "writer": None
}

# Chat bubbles store per-player lists of (text, expiry time)
chat_bubbles = {}
# Movement state
keys = {"up": False, "down": False, "left": False, "right": False}
# Chat mode flag
chat_mode = False


def run_network(host='localhost', port=8765):
    """Network thread entry point. Connects to the server and reads messages."""
    async def network_coroutine():
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except Exception as e:
            print(f"Unable to connect to server: {e}")
            return
        # Save loop and writer for sending
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


def send_message(message):
    """Send a message to the server from the GUI thread."""
    writer = network_state.get("writer")
    loop = network_state.get("loop")
    if writer and loop:
        try:
            data = json.dumps(message) + "\n"
            def write_and_drain():
                writer.write(data.encode())
                return asyncio.create_task(writer.drain())
            loop.call_soon_threadsafe(write_and_drain)
        except Exception:
            pass

# Tkinter setup
root = tk.Tk()
root.title("Get Online Let's Play (Python)")
canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg='white')
canvas.pack()
# Chat entry widget
chat_entry = tk.Entry(root)
chat_entry.place(x=10, y=HEIGHT - 30, width=200)
chat_entry.lower()  # hide initially


def process_messages():
    """Process network messages from the queue and update game state."""
    global my_id
    while not msg_queue.empty():
        msg = msg_queue.get()
        mtype = msg.get("type")
        if mtype == "yourInfo":
            p = msg.get("player")
            my_id = p["id"]
            players[p["id"]] = p
        elif mtype == "currentPlayers":
            players.update(msg.get("players", {}))
        elif mtype == "newPlayer":
            p = msg.get("player")
            players[p["id"]] = p
        elif mtype == "playerDisconnected":
            pid = msg.get("id")
            players.pop(pid, None)
            chat_bubbles.pop(pid, None)
        elif mtype == "state":
            state_players = msg.get("players", {})
            for pid, data in state_players.items():
                if pid in players:
                    players[pid].update({
                        "x": data["x"],
                        "y": data["y"],
                        "direction": data["direction"],
                        "moving": data["moving"],
                        "color": data["color"]
                    })
        elif mtype == "chat":
            pid = msg.get("id")
            text = msg.get("text", "")
            expiry = time.time() + 5.0
            chat_bubbles.setdefault(pid, []).append((text, expiry))
    render()
    root.after(50, process_messages)


def render():
    """Render all players and chat messages on the canvas."""
    canvas.delete("all")
    for pid, p in players.items():
        x, y = p.get("x", 0), p.get("y", 0)
        color = p.get("color", "#ff0000")
        if not color.startswith("#"):
            color = "#" + color
        size = 20
        canvas.create_rectangle(x, y, x + size, y + size, fill=color, outline='')
        canvas.create_text(x + size/2, y - 10, text=p.get("name", ""), fill="black", font=("Arial", 8))
        # Draw chat messages above
        messages = chat_bubbles.get(pid, [])
        new_msgs = []
        offset = -25
        for text, expiry in messages:
            if time.time() < expiry:
                canvas.create_text(x + size/2, y + offset, text=text, fill="black", font=("Arial", 8))
                offset -= 15
                new_msgs.append((text, expiry))
        chat_bubbles[pid] = new_msgs


def on_key_press(event):
    global chat_mode
    key = event.keysym.lower()
    if key == "return":
        # Toggle chat mode
        if not chat_mode:
            chat_mode = True
            chat_entry.delete(0, tk.END)
            chat_entry.lift()
            chat_entry.focus()
        else:
            text = chat_entry.get().strip()
            chat_entry.delete(0, tk.END)
            chat_entry.lower()
            chat_mode = False
            if text:
                send_message({"type": "chat", "text": text})
    elif not chat_mode:
        if key in ("w", "up"):
            if not keys["up"]:
                send_message({"type": "moveStart", "direction": "up"})
                keys["up"] = True
        elif key in ("s", "down"):
            if not keys["down"]:
                send_message({"type": "moveStart", "direction": "down"})
                keys["down"] = True
        elif key in ("a", "left"):
            if not keys["left"]:
                send_message({"type": "moveStart", "direction": "left"})
                keys["left"] = True
        elif key in ("d", "right"):
            if not keys["right"]:
                send_message({"type": "moveStart", "direction": "right"})
                keys["right"] = True


def on_key_release(event):
    key = event.keysym.lower()
    if not chat_mode:
        if key in ("w", "up"):
            if keys["up"]:
                send_message({"type": "moveStop", "direction": "up"})
                keys["up"] = False
        elif key in ("s", "down"):
            if keys["down"]:
                send_message({"type": "moveStop", "direction": "down"})
                keys["down"] = False
        elif key in ("a", "left"):
            if keys["left"]:
                send_message({"type": "moveStop", "direction": "left"})
                keys["left"] = False
        elif key in ("d", "right"):
            if keys["right"]:
                send_message({"type": "moveStop", "direction": "right"})
                keys["right"] = False

# Bind keyboard events
root.bind("<KeyPress>", on_key_press)
root.bind("<KeyRelease>", on_key_release)

# Start the network thread
threading.Thread(target=run_network, daemon=True).start()
# Start processing messages
after_id = root.after(50, process_messages)

root.mainloop()
