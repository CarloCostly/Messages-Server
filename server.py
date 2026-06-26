import os

from aiohttp import web


clients = set()


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    can_prepare = ws.can_prepare(request)

    if not can_prepare.ok:
        return web.Response(
            text="Chat server is running. Connect with WebSocket at this URL.",
            content_type="text/plain",
        )

    await ws.prepare(request)
    clients.add(ws)
    print("Cliente conectado")

    try:
        async for message in ws:
            if message.type == web.WSMsgType.TEXT:
                print(f"Mensaje recibido: {message.data}")

                for client in clients.copy():
                    if client is not ws and not client.closed:
                        await client.send_str(message.data)

            elif message.type == web.WSMsgType.ERROR:
                print(f"Error WebSocket: {ws.exception()}")

    finally:
        clients.discard(ws)
        print("Cliente desconectado")

    return ws


async def health(request):
    return web.json_response({"status": "ok"})


app = web.Application()
app.router.add_get("/", websocket_handler)
app.router.add_get("/health", health)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    web.run_app(app, host="0.0.0.0", port=port)
