import subprocess
from pathlib import Path
from sys import platform
import json
import sys, os

# === Función universal para obtener rutas de recursos ===
def resource_path(relative_path):
    """Obtiene la ruta absoluta del recurso, compatible con PyInstaller."""
    try:
        base_path = sys._MEIPASS  # Carpeta temporal creada por PyInstaller
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# === Cargar archivo JSON con compatibilidad para ejecutables ===
guestOS_path = resource_path("staticConstant.json")
try:
    with open(guestOS_path, encoding="utf-8") as f:
        guestOS = json.load(f)
except FileNotFoundError:
    print(f"[Error] No se encontró el archivo: {guestOS_path}")
    guestOS = {}

# === Clase principal para VMware ===
class vmware(object):
    vmrunpath = None
    output = None

    def __init__(self, vmwarepath):
        if platform.lower() == "win32":
            vmwarepath = vmwarepath.replace('"', "").replace("'", "")
            self.vmrunpath = Path(vmwarepath).joinpath("vmrun.exe")
        else:
            self.vmrunpath = vmwarepath

    def updateOutput(self):
        output = subprocess.run([str(self.vmrunpath), "list"], stdout=subprocess.PIPE)
        output = output.stdout.decode("utf-8")
        if platform.lower() == "win32":
            output = output.split("\r\n")
        else:
            output = output.split("\n")
        # No confiar en que el último elemento está vacío
        self.output = [x for x in output if len(x)]

    def runCount(self):
        return len(self.output) - 1

    def isRunning(self):
        return self.runCount() > 0

    def getRunningVMPath(self, index=None):
        if not self.isRunning():
            return None
        elif index is not None:
            return self.output[index + 1]
        else:
            return self.output[1:]

    def getVMProperty(self, path, property):
        vmx = Path(path)
        value = None
        for line in vmx.read_text(encoding="utf-8").split("\n"):
            if property in line:
                value = line[len(property) + 4:][:-1]
                break
        return value

    def getRunningVMProperty(self, index, property):
        return self.getVMProperty(self.getRunningVMPath(index), property)

    def getGuestName(self, path):
        return self.getVMProperty(path, "displayName")

    def getRunningGuestName(self, index):
        return self.getRunningVMProperty(index, "displayName")

    def getGuestOS(self, path, raw=None):
        if raw:
            return self.getVMProperty(path, "guestOS")
        else:
            property = self.getVMProperty(path, "guestOS")
            return guestOS.get(property, "Unknown")

    def getRunningGuestOS(self, index, raw=None):
        if raw:
            return self.getRunningVMProperty(index, "guestOS")
        else:
            property = self.getRunningVMProperty(index, "guestOS")
            return guestOS.get(property, "Unknown")
