import json
import os
import uuid

from aiohttp import web


MAX_TEXT_LENGTH = 2000
MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024

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


async def broadcast_user_list():
    users = [
        {
            "id": info["id"],
            "name": info["name"],
            "profile_photo": info.get("profile_photo", ""),
        }
        for info in clients.values()
    ]
    await broadcast("users", users=users)


def clean_name(name):
    name = str(name or "").strip()
    return name[:5] if name else "Usuario"


def clean_text(text):
    return str(text or "").strip()[:MAX_TEXT_LENGTH]


def clean_attachment(data):
    attachment = data.get("attachment") or {}
    filename = str(attachment.get("filename") or "archivo").strip()[:120]
    mime = str(attachment.get("mime") or "application/octet-stream").strip()[:120]
    content = str(attachment.get("data") or "")
    size = int(attachment.get("size") or 0)

    if not content:
        return None

    if size > MAX_ATTACHMENT_BYTES:
        return {"error": "El archivo es demasiado grande. Maximo: 2 MB."}

    return {
        "filename": filename,
        "mime": mime,
        "data": content,
        "size": size,
    }


async def websocket_handler(request):
    ws = web.WebSocketResponse(max_msg_size=MAX_ATTACHMENT_BYTES + 256 * 1024)
    can_prepare = ws.can_prepare(request)

    if not can_prepare.ok:
        return web.Response(
            text="Chat server is running. Connect with WebSocket at this URL.",
            content_type="text/plain",
        )

    await ws.prepare(request)
    clients[ws] = {
        "id": str(uuid.uuid4()),
        "name": "Usuario",
        "profile_photo": "",
    }
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
            sender_info = clients.get(ws)

            if not sender_info:
                continue

            if message_type == "join":
                sender_info["name"] = clean_name(data.get("name"))
                sender_info["profile_photo"] = str(data.get("profile_photo") or "")

                await send_json(
                    ws,
                    "system",
                    text=f"Te conectaste como {sender_info['name']}.",
                )
                await broadcast(
                    "system",
                    exclude=ws,
                    text=f"{sender_info['name']} se unio al chat.",
                )
                await broadcast_user_list()
                print(f"{sender_info['name']} se unio al chat")

            elif message_type == "chat":
                text = clean_text(data.get("text"))
                attachment = clean_attachment(data)

                if isinstance(attachment, dict) and attachment.get("error"):
                    await send_json(ws, "system", text=attachment["error"])
                    continue

                if not text and not attachment:
                    continue

                print(f"{sender_info['name']}: {text or '[archivo]'}")
                await broadcast(
                    "chat",
                    exclude=ws,
                    sender_id=sender_info["id"],
                    sender=sender_info["name"],
                    profile_photo=sender_info.get("profile_photo", ""),
                    text=text,
                    attachment=attachment,
                )

    finally:
        info = clients.pop(ws, {"name": "Usuario"})
        await broadcast("system", text=f"{info['name']} salio del chat.")
        await broadcast_user_list()
        print(f"{info['name']} desconectado")

    return ws


async def health(request):
    return web.json_response({"status": "ok", "clients": len(clients)})


app = web.Application()
app.router.add_get("/", websocket_handler)
app.router.add_get("/health", health)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
