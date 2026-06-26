# Railway Chat Server

Servidor publico de prueba para la app de mensajeria.

## Railway

Sube esta carpeta a Railway como servicio Python.

Comando de inicio:

```bash
python server.py
```

Railway asigna el puerto automaticamente con la variable `PORT`.

Cuando Railway te de una URL publica, usala en la app como:

```text
wss://TU-URL-DE-RAILWAY
```

La ruta `/health` sirve para verificar que el servidor esta vivo.
