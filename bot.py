import os
import json
import time
from datetime import datetime
from neonize.client import NewClient
from neonize.events import MessageEv, ConnectedEv

# Configuración de administrador
ADMIN_NUMBERS = ["5218641062059"]

# Rutas de almacenamiento (usa /var/data si existe un disco en Render, si no usa la carpeta local)
DATA_DIR = "/var/data" if os.path.exists("/var/data") else "./"
DB_PATH = os.path.join(DATA_DIR, "sesion_clickandcut.db")
SALDOS_FILE = os.path.join(DATA_DIR, "saldos.json")
PEDIDOS_FILE = os.path.join(DATA_DIR, "pedidos.json")
CLIENTES_FILE = os.path.join(DATA_DIR, "clientes.json")

def cargar_datos(ruta):
    if not os.path.exists(ruta):
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
        return {}
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def guardar_datos(ruta, datos):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def registrar_o_actualizar_cliente(numero, nombre="Cliente"):
    clientes = cargar_datos(CLIENTES_FILE)
    saldos = cargar_datos(SALDOS_FILE)
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if numero not in clientes:
        clientes[numero] = {"nombre": nombre, "fecha_registro": ahora, "ultimo_mensaje": ahora}
    else:
        clientes[numero]["ultimo_mensaje"] = ahora

    guardar_datos(CLIENTES_FILE, clientes)

    if numero not in saldos:
        saldos[numero] = 0.0
        guardar_datos(SALDOS_FILE, saldos)

client = NewClient(DB_PATH)

@client.event(ConnectedEv)
def on_connected(_: NewClient, __: ConnectedEv):
    print("¡Bot Click&Cut Store conectado exitosamente a WhatsApp!")

@client.event(MessageEv)
def on_message(cl: NewClient, message: MessageEv):
    try:
        if message.Info.IsFromMe:
            return

        remitente = message.Info.Sender.User
        push_name = message.Info.PushName or "Cliente"
        texto = (message.Message.conversation or message.Message.extendedTextMessage.text or "").strip()

        if not texto:
            return

        registrar_o_actualizar_cliente(remitente, push_name)
        es_admin = remitente in ADMIN_NUMBERS

        # Comandos de Administrador
        if es_admin:
            if texto.startswith(".recargar"):
                partes = texto.split()
                if len(partes) == 3 and partes[2].replace('.', '', 1).isdigit():
                    destino = partes[1].replace("+", "").strip()
                    monto = float(partes[2])
                    saldos = cargar_datos(SALDOS_FILE)
                    saldos[destino] = saldos.get(destino, 0.0) + monto
                    guardar_datos(SALDOS_FILE, saldos)
                    cl.reply_message(message, f"✅ Saldo recargado a {destino}: ${monto:.2f}\nSaldo total:${saldos[destino]:.2f}")
                else:
                    cl.reply_message(message, "⚠️ Uso: `.recargar <numero> <monto>`")
                return

            elif texto == ".totalclientes":
                clientes = cargar_datos(CLIENTES_FILE)
                cl.reply_message(message, f"👥 Clientes registrados: {len(clientes)}")
                return

            elif texto == ".verpedidos":
                pedidos = cargar_datos(PEDIDOS_FILE)
                if not pedidos:
                    cl.reply_message(message, "📦 No hay pedidos registrados.")
                else:
                    resumen = "📦 *ÚLTIMOS PEDIDOS:*\n"
                    for item in list(pedidos.values())[-5:]:
                        resumen += f"- {item.get('fecha')}: {item.get('cliente')} -> {item.get('producto')}\n"
                    cl.reply_message(message, resumen)
                return

        # Comandos para Clientes
        if texto == ".menu":
            menu_msg = (
                "🛍️ *Bienvenido a Click&Cut Store*\n\n"
                "🔹 *.catalogo* - Ver productos disponibles\n"
                "🔹 *.saldo* - Ver crédito disponible\n"
                "🔹 *.comprar <producto>* - Realizar pedido\n"
                "🔹 *.soporte* - Contactar a un asesor"
            )
            cl.reply_message(message, menu_msg)

        elif texto == ".saldo":
            saldos = cargar_datos(SALDOS_FILE)
            cl.reply_message(message, f"💳 Tu saldo actual es de: *${saldos.get(remitente, 0.0):.2f}*")

        elif texto.startswith(".comprar"):
            partes = texto.split(maxsplit=1)
            if len(partes) < 2:
                cl.reply_message(message, "⚠️ Indica el producto. Ejemplo: `.comprar Netflix 1 Mes`")
                return
            producto = partes[1]
            pedidos = cargar_datos(PEDIDOS_FILE)
            id_pedido = str(len(pedidos) + 1)
            pedidos[id_pedido] = {
                "cliente": remitente,
                "producto": producto,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "estado": "Pendiente"
            }
            guardar_datos(PEDIDOS_FILE, pedidos)
            cl.reply_message(message, f"🛒 *Pedido #{id_pedido} recibido.*\nProducto: {producto}\nEstado: *Pendiente*")

    except Exception as e:
        print(f"Error procesando mensaje: {e}")

# Conexión y bucle de vida
client.connect()
print("Bot Click&Cut Store activo y escuchando eventos...")

while True:
    time.sleep(3600)
