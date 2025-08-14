import asyncio
import json
import queue
import threading
import time
import math
import tkinter as tk

# Canvas
WIDTH, HEIGHT = 800, 600

# State
players = {}
projectiles = []
my_id = None

# Inter-thread comms
msg_queue = queue.Queue()
network_state = {"loop": None, "writer": None}

# Chat
CHAT_DURATION_MS = 5000
chat_mode = False
chat_text = ""

def start_network_thread(host="127.0.0.1", port=8765):
    def _runner():
        loop = asyncio.new_event_loop()
        network_state["loop"] = loop
        loop.run_until_complete(receiver(host, port))
    t = threading.Thread(target=_runner, daemon=True)
    t.start()

async def receiver(host="127.0.0.1", port=8765):
    try:
        reader, writer = await asyncio.open_connection(host, port)
        network_state["writer"] = writer
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("utf-8"))
                msg_queue.put(msg)
            except Exception:
                pass
    except Exception as e:
        msg_queue.put({"type": "error", "error": str(e)})

def process_messages():
    global my_id, projectiles
    while True:
        try:
            msg = msg_queue.get_nowait()
        except queue.Empty:
            break

        t = msg.get("type")
        if t == "currentPlayers":
            players.clear()
            players.update(msg.get("players", {}))
        elif t == "state":
            players.clear()
            players.update(msg.get("players", {}))
            projectiles = msg.get("projectiles", [])
        elif t == "newPlayer":
            p = msg.get("player")
            if p:
                players[p["id"]] = p
        elif t == "playerDisconnected":
            players.pop(msg.get("id"), None)
        elif t == "yourInfo":
            you = msg.get("you")
            if you:
                my_id = you.get("id")
        elif t == "chat":
            # Could handle client-side chat bubble timers here if desired
            pass

def send_obj(obj: dict):
    w = network_state.get("writer")
    loop = network_state.get("loop")
    if not w or not loop:
        return
    try:
        w.write((json.dumps(obj) + "\n").encode("utf-8"))
        asyncio.run_coroutine_threadsafe(w.drain(), loop)
    except Exception:
        pass

def send_move_event(kind, direction):
    send_obj({"type": kind, "dir": direction})

def send_shoot():
    send_obj({"type": "shoot"})

pressed = {"up": False, "down": False, "left": False, "right": False}

def on_key_press(event):
    global chat_mode, chat_text
    if chat_mode:
        if event.keysym == "Return":
            txt = chat_text.strip()
            if txt:
                send_obj({"type": "chat", "text": txt[:140]})
            chat_text = ""
            chat_mode = False
        elif event.keysym == "BackSpace":
            chat_text = chat_text[:-1]
        elif len(event.char) == 1:
            chat_text += event.char
        return

    if event.keysym == "Return":
        chat_mode = True
        chat_text = ""
        return

    if event.keysym.lower() == "x":
        send_shoot()
        return

    keymap = {
        "Up": "up", "w": "up",
        "Down": "down", "s": "down",
        "Left": "left", "a": "left",
        "Right": "right", "d": "right",
    }
    d = keymap.get(event.keysym) or keymap.get(event.keysym.lower())
    if d and not pressed[d]:
        pressed[d] = True
        send_move_event("moveStart", d)

def on_key_release(event):
    keymap = {
        "Up": "up", "w": "up",
        "Down": "down", "s": "down",
        "Left": "left", "a": "left",
        "Right": "right", "d": "right",
    }
    d = keymap.get(event.keysym) or keymap.get(event.keysym.lower())
    if d and pressed.get(d):
        pressed[d] = False
        send_move_event("moveStop", d)

# --- UI ---
root = tk.Tk()
root.title("Get Online Let's Play (Python)")
canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#222222")
canvas.pack()

root.bind("<KeyPress>", on_key_press)
root.bind("<KeyRelease>", on_key_release)

def render():
    canvas.delete("all")

    # Draw players
    for p in players.values():
        x = p.get("x", 100.0)
        y = p.get("y", 100.0)
        color = p.get("color", "#44aaff")

        # body
        canvas.create_rectangle(x-10, y-10, x+10, y+10, fill=color, outline="")

        # facing arrow (0 deg = right/east; +90 = down)
        ang = p.get("angle", 0.0)
        rad = math.radians(ang)
        x2 = x + 18 * math.cos(rad)
        y2 = y + 18 * math.sin(rad)
        canvas.create_line(x, y, x2, y2, width=2)

        # name
        canvas.create_text(x, y-18, text=p.get("name", ""), fill="#ffffff")

    # Draw projectiles
    for pr in projectiles:
        px = pr.get("x", 0.0)
        py = pr.get("y", 0.0)
        canvas.create_oval(px-3, py-3, px+3, py+3, outline="", fill="#ffffff")

    # If chatting, show input hint
    if chat_mode:
        canvas.create_text(WIDTH//2, HEIGHT-30,
                           text="Type message: " + chat_text,
                           fill="#00ffcc")

    process_messages()
    root.after(33, render)  # ~30 FPS

if __name__ == "__main__":
    # Change host here if your server runs elsewhere:
    start_network_thread(host="127.0.0.1", port=8765)
    root.after(33, render)
    root.mainloop()
