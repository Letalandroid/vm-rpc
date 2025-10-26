import sys
import threading
import time
import subprocess
import os
import psutil
from pystray import Icon, Menu, MenuItem
from PIL import Image
from pathlib import Path

# --- Bloqueo para evitar múltiples instancias ---
def ya_ejecutandose():
    actual = psutil.Process().pid
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['pid'] != actual and proc.info['name'] == os.path.basename(sys.executable):
            return True
    return False

if ya_ejecutandose():
    sys.exit(0)

# --- Ruta al main.py ---
MAIN_PATH = Path(__file__).parent.joinpath("main.py")

# --- Variables globales ---
ejecutando = True
proceso_main = None

# --- Función para ejecutar main.py ---
def ejecutar_main():
    global proceso_main
    proceso_main = subprocess.Popen(
        [sys.executable, str(MAIN_PATH)],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    )

# --- Funcionalidad principal del tray ---
def tarea_en_segundo_plano():
    ejecutar_main()
    while ejecutando:
        # Puedes añadir logs, monitoreo, etc.
        time.sleep(5)

# --- Función para salir ---
def salir(icon, item):
    global ejecutando, proceso_main
    ejecutando = False

    # Detener main.py si sigue corriendo
    if proceso_main and proceso_main.poll() is None:
        try:
            proceso_main.terminate()
            proceso_main.wait(timeout=3)
        except Exception:
            proceso_main.kill()

    icon.stop()

# --- Crear icono (usa un cuadrado verde simple) ---
def crear_icono():
    imagen = Image.new('RGB', (64, 64), color=(0, 128, 0))
    menu = Menu(MenuItem('Salir', salir))
    icon = Icon("VMRichPresence", imagen, "VMRichPresence", menu)
    return icon

# --- Ejecutar ---
if __name__ == "__main__":
    hilo = threading.Thread(target=tarea_en_segundo_plano, daemon=True)
    hilo.start()
    icono = crear_icono()
    icono.run()
