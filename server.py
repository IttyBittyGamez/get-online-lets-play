import asyncio
import json
import random
import math

# Canvas dimensions (for initial spawn positions)
WIDTH, HEIGHT = 800, 600

# Store players keyed by unique string ids
players = {}

# Map writer objects to player ids
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
    return random.choice(ANIMALS) + str(random.randint(1000, 9999))

def random_color():
    # Return hex color with leading '#'
    return f"#{random.randint(0, 0xFFFFFF):06x}"

async def send_message(writer, message):
    try:
        writer.write((json.dumps(message) + "\n").encode())
        await writer.drain()
    except Exception:
        pass

async def broadcast(message):
    data = json.dumps(message) + "\n"
    for writer in list(connections.keys()):
        try:
            writer.write(data.encode())
        except Exception:
            continue
    # drain writers concurrently
    coros = [w.drain() for w in connections.keys()]
    if coros:
        await asyncio.gather(*coros, return_exceptions=True)

async def handle_client(reader, writer):
    global next_id
    peername = writer.get_extra_info("peername")
    pid = str(next_id)
    next_id += 1
    # Create new player state
    players[pid] = {
        "id": pid,
        "name": random_name(),
        "x": random.randint(50, WIDTH - 50),
        "y": random.randint(50, HEIGHT - 50),
        "angle": 0.0,
        "color": random_color(),
        "inputs": {"up": False, "down": False, "left": False, "right": False}
    }
    connections[writer] = pid
    print(f"Client {pid} connected from {peername}")
    # Send your info and current players list
    await send_message(writer, {"type": "yourInfo", "id": pid})
    await send_message(writer, {"type": "currentPlayers", "players": players})
    await broadcast({"type": "newPlayer", "player": players[pid]})

    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode().strip())
            except Exception:
                continue
            msg_type = msg.get("type")
            if msg_type == "moveStart":
                direction = msg.get("direction")
                if direction in players[pid]["inputs"]:
                    players[pid]["inputs"][direction] = True
            elif msg_type == "moveStop":
                direction = msg.get("direction")
                if direction in players[pid]["inputs"]:
                    players[pid]["inputs"][direction] = False
            elif msg_type == "chat":
                text = msg.get("text", "")
                await broadcast({"type": "chat", "id": pid, "text": text})
    except Exception:
        pass
    # Client disconnected
    if pid in players:
        players.pop(pid, None)
    connections.pop(writer, None)
    print(f"Client {pid} disconnected")
    await broadcast({"type": "playerDisconnected", "id": pid})
    try:
        writer.close()
        await writer.wait_closed()
    except Exception:
        pass

async def game_loop():
    SPEED = 3.0
    ROTATE_SPEED = 5.0  # degrees per tick
    TICK_RATE = 30.0
    while True:
        if players:
            for p in players.values():
                inputs = p["inputs"]
                # Handle rotation
                rot_dir = 0
                if inputs["left"]:
                    rot_dir -= 1
                if inputs["right"]:
                    rot_dir += 1
                p["angle"] = (p["angle"] + rot_dir * ROTATE_SPEED) % 360
                # Handle movement
                move = 0
                if inputs["up"]:
                    move += 1
                if inputs["down"]:
                    move -= 1
                if move != 0:
                    rad = math.radians(p["angle"])
                    p["x"] += move * SPEED * math.cos(rad)
                    p["y"] += move * SPEED * math.sin(rad)
            # Broadcast updated state
            await broadcast({"type": "state", "players": players})
        await asyncio.sleep(1.0 / TICK_RATE)

async def main():
    host = "0.0.0.0"
    port = 8765
    server = await asyncio.start_server(handle_client, host=host, port=port)
    addr = server.sockets[0].getsockname()
    print(f"Server started on {addr[0]}:{addr[1]}")
    async with server:
        await asyncio.gather(server.serve_forever(), game_loop())

if __name__ == "__main__":
    asyncio.run(main())
