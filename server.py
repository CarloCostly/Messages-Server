import json
import os

from aiohttp import web


clients = {}


def build_message(message_type, **payload):
    data = {"type": message_type}
    data.update(payload)
    return json.dumps(data)


async def send_json(ws, message_type, **payload):
    if not ws.closed:
        await ws.send_str(build_message(message_type, **payload))


async def broadcast(message_type, exclude=None, **payload):
    for client in list(clients.keys()):
        if client is exclude or client.closed:
            continue

        await send_json(client, message_type, **payload)


def clean_name(name):
    name = str(name or "").strip()
    return name[:30] if name else "Usuario"


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    can_prepare = ws.can_prepare(request)

    if not can_prepare.ok:
        return web.Response(
            text="Chat server is running. Connect with WebSocket at this URL.",
            content_type="text/plain",
        )

    await ws.prepare(request)
    clients[ws] = "Usuario"
    print("Cliente conectado")

    try:
        async for message in ws:
            if message.type != web.WSMsgType.TEXT:
                continue

            try:
                data = json.loads(message.data)
            except json.JSONDecodeError:
                data = {"type": "chat", "text": message.data}

            message_type = data.get("type")

            if message_type == "join":
                name = clean_name(data.get("name"))
                clients[ws] = name

                await send_json(ws, "system", text=f"Te conectaste como {name}.")
                await broadcast("system", exclude=ws, text=f"{name} se unio al chat.")
                print(f"{name} se unio al chat")

            elif message_type == "chat":
                sender = clients.get(ws, "Usuario")
                text = str(data.get("text", "")).strip()

                if not text:
                    continue

                print(f"{sender}: {text}")
                await broadcast("chat", exclude=ws, sender=sender, text=text)

    finally:
        name = clients.pop(ws, "Usuario")
        await broadcast("system", text=f"{name} salio del chat.")
        print(f"{name} desconectado")

    return ws


async def health(request):
    return web.json_response({"status": "ok", "clients": len(clients)})


app = web.Application()
app.router.add_get("/", websocket_handler)
app.router.add_get("/health", health)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
