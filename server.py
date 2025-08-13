import asyncio
import json
import random
import time

# Store players keyed by unique string ids
players = {}
# Map id to writer objects for sending messages
connections = {}
next_id = 1

# List of animals for random names
ANIMALS = [
    "Aardvark", "Badger", "Cheetah", "Dolphin", "Eagle", "Fox", "Giraffe",
    "Hippo", "Iguana", "Jaguar", "Koala", "Lemur", "Meerkat", "Narwhal",
    "Otter", "Panda", "Quokka", "Raccoon", "Shark", "Tiger", "Urchin",
    "Vulture", "Walrus", "Xerus", "Yak", "Zebra"
]

def random_name():
    return random.choice(ANIMALS) + str(random.randint(100, 999))

def random_color():
    # Prefix with '#' for Tkinter compatibility
    return f"#{random.randint(0, 0xFFFFFF):06x}"

async def send_message(writer, message):
    """Send a JSON-serialisable message to a writer."""
    try:
        data = json.dumps(message) + "\n"
        writer.write(data.encode())
        await writer.drain()
    except Exception:
        # If sending fails ignore; connection will be cleaned up on next loop
        pass

async def broadcast(message, exclude=None):
    """Broadcast a message to all connected players except optional exclude id."""
    for pid, writer in list(connections.items()):
        if pid != exclude:
            try:
                await send_message(writer, message)
            except Exception:
                continue

async def handle_client(reader, writer):
    """Handle a new incoming TCP client."""
    global next_id
    pid = str(next_id)
    next_id += 1

    # Register new player
    name = random_name()
    x = random.randint(50, 750)
    y = random.randint(50, 550)
    color = random_color()
    players[pid] = {
        "id": pid,
        "name": name,
        "x": x,
        "y": y,
        "direction": "",
        "moving": False,
        "color": color,
        # chat messages for this player
        "messages": []
    }
    connections[pid] = writer

    # Send info about existing players and your player
    await send_message(writer, {"type": "yourInfo", "player": players[pid]})
    await send_message(writer, {"type": "currentPlayers", "players": players})
    await broadcast({"type": "newPlayer", "player": players[pid]}, exclude=pid)

    # Read loop
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                data = json.loads(line.decode().strip())
            except json.JSONDecodeError:
                continue
            mtype = data.get("type")
            if mtype in ("moveStart", "movestart"):
                direction = data.get("direction")
                if direction in ("up", "down", "left", "right"):
                    players[pid]["direction"] = direction
                    players[pid]["moving"] = True
            elif mtype in ("moveStop", "movestop"):
                direction = data.get("direction")
                # Stop moving if the direction matches
                if direction == players[pid]["direction"]:
                    players[pid]["moving"] = False
            elif mtype == "chat":
                text = data.get("text", "")
                if text:
                    # store message with timestamp for possible removal
                    players[pid]["messages"].append({"text": text, "time": time.time()})
                    # broadcast chat
                    await broadcast({"type": "chat", "id": pid, "text": text})
    except Exception:
        # Any exception will close connection
        pass
    finally:
        # Clean up
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        # Remove player
        if pid in players:
            players.pop(pid, None)
        if pid in connections:
            connections.pop(pid, None)
        await broadcast({"type": "playerDisconnected", "id": pid})

async def game_loop(tick_rate=30, speed=3):
    """Update player positions and broadcast state periodically."""
    while True:
        # update positions
        for p in list(players.values()):
            if p["moving"]:
                if p["direction"] == "up":
                    p["y"] -= speed
                elif p["direction"] == "down":
                    p["y"] += speed
                elif p["direction"] == "left":
                    p["x"] -= speed
                elif p["direction"] == "right":
                    p["x"] += speed
        # broadcast state
        if players:
            await broadcast({"type": "state", "players": players})
        await asyncio.sleep(1 / tick_rate)

async def main(host="0.0.0.0", port=8765):
    server = await asyncio.start_server(handle_client, host, port)
    # start game loop
    loop_task = asyncio.create_task(game_loop())
    print(f"Server started on {host}:{port}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
