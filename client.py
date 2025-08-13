import tkinter as tk
import asyncio
import websockets
import threading
import json
import random
import queue

# Canvas size
WIDTH, HEIGHT = 800, 600

# Store players keyed by id
players = {}
# Your own player id
my_id = None

# Queue for incoming messages from network thread
msg_queue = queue.Queue()

# Global event loop and websocket connection for sending messages
loop = None
ws = None

async def receiver(uri='ws://localhost:8765'):
    """Connect to the server and enqueue incoming messages."""
    global ws
    async with websockets.connect(uri) as websocket:
        ws = websocket
        async for message in websocket:
            data = json.loads(message)
            msg_queue.put(data)

def network_thread():
    """Run the asyncio event loop for networking in a background thread."""
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(receiver())

def send_message(msg: dict):
    """Send a JSON message to the server from the GUI thread."""
    global ws, loop
    if ws and loop:
        asyncio.run_coroutine_threadsafe(ws.send(json.dumps(msg)), loop)

# GUI update and rendering

def remove_message(pid, text):
    """Remove a chat message from a player's message list."""
    if pid in players:
        msgs = players[pid].get('messages', [])
        if text in msgs:
            msgs.remove(text)

def process_messages():
    """Process all messages from the network and update local state."""
    global my_id
    try:
        while True:
            data = msg_queue.get_nowait()
            mtype = data.get('type')
            if mtype == 'currentPlayers':
                players.clear()
                players.update(data['players'])
            elif mtype == 'yourInfo':
                my_id = data['id']
                # update our name/color in players if present
                for p in players.values():
                    if p['id'] == my_id:
                        p['name'] = data.get('name')
                        p['color'] = data.get('color')
            elif mtype == 'newPlayer':
                p = data['player']
                players[p['id']] = p
            elif mtype == 'playerDisconnected':
                pid = data['id']
                if pid in players:
                    del players[pid]
            elif mtype == 'state':
                for pid, p in data['players'].items():
                    if pid in players:
                        players[pid]['x'] = p['x']
                        players[pid]['y'] = p['y']
            elif mtype == 'chat':
                pid = data['id']
                text = data['text']
                if pid in players:
                    msgs = players[pid].setdefault('messages', [])
                    msgs.append(text)
                    if len(msgs) > 2:
                        msgs.pop(0)
                    # schedule removal after 5 seconds
                    root.after(5000, lambda pid=pid, text=text: remove_message(pid, text))
    except queue.Empty:
        pass
    render()
    root.after(33, process_messages)

def render():
    """Redraw the game canvas."""
    canvas.delete('all')
    for pid, p in players.items():
        x = p.get('x', 0)
        y = p.get('y', 0)
        color = p.get('color', '#4444ff')
        name = p.get('name', pid)
        # draw square
        canvas.create_rectangle(x, y, x + 20, y + 20, fill=color, outline='')
        # draw name below
        canvas.create_text(x, y, text=name, anchor='s', fill='black', font=('Arial', 10))
        # draw chat messages above (most recent on top)
        msgs = p.get('messages', [])
        for i, text in enumerate(reversed(msgs)):
            canvas.create_text(x, y - 10 - i * 14, text=text, anchor='s', fill='black', font=('Arial', 10))

# Keyboard handling
chat_mode = False
keys = {'up': False, 'down': False, 'left': False, 'right': False}

def on_key_press(event):
    global chat_mode
    if event.keysym == 'Return':
        if not chat_mode:
            chat_mode = True
            chat_entry.delete(0, tk.END)
            chat_entry.place(relx=0.5, rely=1.0, x=0, y=-20, anchor='s')
            chat_entry.focus_set()
        else:
            text = chat_entry.get().strip()
            chat_entry.place_forget()
            chat_mode = False
            if text:
                send_message({'type': 'chat', 'text': text})
                # also show locally on our own player
                if my_id is not None:
                    msgs = players.setdefault(my_id, {}).setdefault('messages', [])
                    msgs.append(text)
                    if len(msgs) > 2:
                        msgs.pop(0)
                    root.after(5000, lambda pid=my_id, text=text: remove_message(pid, text))
    else:
        if chat_mode:
            return
        if event.keysym in ('Up', 'w', 'W'):
            if not keys['up']:
                keys['up'] = True
                send_message({'type': 'moveStart', 'dir': 'up'})
        elif event.keysym in ('Down', 's', 'S'):
            if not keys['down']:
                keys['down'] = True
                send_message({'type': 'moveStart', 'dir': 'down'})
        elif event.keysym in ('Left', 'a', 'A'):
            if not keys['left']:
                keys['left'] = True
                send_message({'type': 'moveStart', 'dir': 'left'})
        elif event.keysym in ('Right', 'd', 'D'):
            if not keys['right']:
                keys['right'] = True
                send_message({'type': 'moveStart', 'dir': 'right'})

def on_key_release(event):
    if chat_mode:
        return
    if event.keysym in ('Up', 'w', 'W'):
        if keys['up']:
            keys['up'] = False
            send_message({'type': 'moveStop'})
    elif event.keysym in ('Down', 's', 'S'):
        if keys['down']:
            keys['down'] = False
            send_message({'type': 'moveStop'})
    elif event.keysym in ('Left', 'a', 'A'):
        if keys['left']:
            keys['left'] = False
            send_message({'type': 'moveStop'})
    elif event.keysym in ('Right', 'd', 'D'):
        if keys['right']:
            keys['right'] = False
            send_message({'type': 'moveStop'})

# Setup Tkinter GUI
root = tk.Tk()
root.title("Get Online Let's Play (Python)")
canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg='light grey')
canvas.pack()
chat_entry = tk.Entry(root)
chat_entry.place_forget()

# Start network thread
threading.Thread(target=network_thread, daemon=True).start()

# Bind keyboard events and start message processing
root.bind('<KeyPress>', on_key_press)
root.bind('<KeyRelease>', on_key_release)
root.after(100, process_messages)

root.mainloop()
