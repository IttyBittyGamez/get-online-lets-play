import asyncio
import json
import random
import time
import math

# Store players keyed by unique string ids
players = {}
# Map id to writer objects
connections = {}
next_id = 1

# Animal names for random name generation
ANIMALS = [
    "Aardvark", "Badger", "Cheetah", "Dolphin", "Eagle", "Fox", "Giraffe",
    "Hippo", "Iguana", "Jaguar", "Koala", "Lemur", "Meerkat", "Narwhal",
    "Otter", "Panda", "Quokka", "Raccoon", "Shark", "Tiger", "Urchin",
    "Vulture", "Walrus", "Xerus", "Yak", "Zebra"
]

def random_name():
    return random.choice(ANIMALS) + str(random.randint(100, 999))

def random_color():
    return f"#{random.randint(0, 0xFFFFFF):06x}"

async def send_message(writer, message):
    """Send a JSON message over the given writer."""
    try:
        data = json.dumps(message) + "\n"
        writer.write(data.encode())
        await writer.drain()
    except Exception:
        pass

async def broadcast(message, exclude=None):
    """Broadcast a message to all connected players except an optional exclude id."""
    for pid, writer in list(connections.items()):
        if pid != exclude:
            try:
                await send_message(writer, message)
            except Exception:
                continue

async def handle_client(reader, writer):
    """Handle a newly connected client."""
    global next_id
    pid = str(next_id)
    next_id += 1

    # Initialize player with position and random orientation
    name = random_name()
    x = random.randint(50, 750)
    y = random.randint(50, 550)
    color = random_color()
    angle = random.randint(0, 359)
    players[pid] = {
        "id": pid,
        "name": name,
        "x": x,
        "y": y,
        "angle": angle,
        "direction": "",
        "moving": False,
        "color": color,
        "messages": []
    }
    connections[pid] = writer

    # Send player data to new client and broadcast to others
    await send_message(writer, {"type": "yourInfo", "player": players[pid]})
    await send_message(writer, {"type": "currentPlayers", "players": players})
    await broadcast({"type": "newPlayer", "player": players[pid]}, exclude=pid)

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
                if direction == players[pid]["direction"]:
                    players[pid]["moving"] = False
            elif mtype == "chat":
                text = data.get("text", "")
                if text:
                    players[pid]["messages"].append({"text": text, "time": time.time()})
                    await broadcast({"type": "chat", "id": pid, "text": text})
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        if pid in players:
            players.pop(pid, None)
        if pid in connections:
            connections.pop(pid, None)
        await broadcast({"type": "playerDisconnected", "id": pid})

async def game_loop(tick_rate=30, speed=3, rot_speed=5):
    """Update player positions and orientations and broadcast state."""
    while True:
        for p in list(players.values()):
            if p["moving"]:
                d = p["direction"]
                if d == "up":
                    rad = math.radians(p["angle"])
                    p["x"] += math.sin(rad) * speed
                    p["y"] -= math.cos(rad) * speed
                elif d == "down":
                    rad = math.radians(p["angle"])
                    p["x"] -= math.sin(rad) * speed
                    p["y"] += math.cos(rad) * speed
                elif d == "left":
                    p["angle"] = (p["angle"] - rot_speed) % 360
                elif d == "right":
                    p["angle"] = (p["angle"] + rot_speed) % 360
        if players:
            await broadcast({"type": "state", "players": players})
        await asyncio.sleep(1 / tick_rate)

async def main(host="0.0.0.0", port=8765):
    server = await asyncio.start_server(handle_client, host, port)
    loop_task = asyncio.create_task(game_loop())
    print(f"Server started on {host}:{port}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
