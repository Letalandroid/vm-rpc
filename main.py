from pypresence import Presence, InvalidPipe
from datetime import datetime
from time import sleep
from pathlib import Path
from vmware import vmware
from hyperv import hyperv
from virtualbox import virtualbox
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

# === Limpieza de presencia ===
def clear() -> bool:
    global epoch_time, STATUS, LASTSTATUS, running
    epoch_time = 0
    RPC.clear()
    STATUS = None
    LASTSTATUS = None
    if running:
        print("Stopped running VMs.")
        running = False
    return running

running = False

# === Cargar settings.json ===
settings_path = Path(resource_path("settings.json"))
if settings_path.is_file() and settings_path.stat().st_size != 0:
    with open(settings_path, encoding="utf-8") as f:
        settings = json.load(f)
else:
    settings = {}

# === Obtener client ID ===
if settings.get("clientID"):
    clientID = settings["clientID"]
elif Path(resource_path("clientID.txt")).is_file():
    clientID = Path(resource_path("clientID.txt")).read_text(encoding="utf-8").strip()
else:
    clientID = input("Enter client ID: ")
    settings["clientID"] = clientID

# === Obtener hipervisores habilitados ===
hypervisors = []
for name in ["vmware", "hyper-v", "virtualbox"]:
    if settings.get(name, {}).get("enabled", True):
        hypervisors.append(name)
        settings.setdefault(name, {"enabled": True})

if not hypervisors:
    if Path(resource_path("hypervisors.txt")).is_file():
        hypervisors = Path(resource_path("hypervisors.txt")).read_text(encoding="utf-8").casefold().split("\n")
    else:
        hypervisors = ["vmware", "hyper-v", "virtualbox"]
        settings.update({
            "vmware": {"enabled": True},
            "hyper-v": {"enabled": True},
            "virtualbox": {"enabled": True}
        })

# === Obtener paths de hipervisores ===
if "vmware" in hypervisors:
    if platform.lower() == "win32":
        if settings["vmware"].get("path"):
            vmwarepath = settings["vmware"]["path"]
        elif Path("C:/Program Files (x86)/VMware/VMware Workstation/vmrun.exe").is_file():
            print("Using C:/Program Files (x86)/VMware/VMware Workstation")
            vmwarepath = "C:/Program Files (x86)/VMware/VMware Workstation"
        elif Path("C:/Program Files/VMware/VMware Workstation/vmrun.exe").is_file():
            print("Using C:/Program Files/VMware/VMware Workstation")
            vmwarepath = "C:/Program Files/VMware/VMware Workstation"
        else:
            vmwarepath = input("Enter path to VMware Workstation folder: ")
        settings["vmware"]["path"] = vmwarepath
    else:
        vmwarepath = "vmrun"

if "virtualbox" in hypervisors:
    if platform.lower() == "win32":
        if settings["virtualbox"].get("path"):
            virtualboxpath = settings["virtualbox"]["path"]
        elif Path("C:/Program Files (x86)/Oracle/VirtualBox/VBoxManage.exe").is_file():
            print("Using C:/Program Files (x86)/Oracle/VirtualBox/")
            virtualboxpath = "C:/Program Files (x86)/Oracle/VirtualBox"
        elif Path("C:/Program Files/Oracle/VirtualBox/VBoxManage.exe").is_file():
            print("Using C:/Program Files/Oracle/VirtualBox/")
            virtualboxpath = "C:/Program Files/Oracle/VirtualBox"
        else:
            virtualboxpath = input("Enter path to VirtualBox folder: ")
        settings["virtualbox"]["path"] = virtualboxpath
    else:
        virtualboxpath = "vboxmanage"

# === Obtener imágenes ===
largeimage = settings.get("largeImage") or (
    Path(resource_path("largeImage.txt")).read_text(encoding="utf-8").strip()
    if Path(resource_path("largeImage.txt")).is_file() else None
)
smallimage = settings.get("smallImage")

# === Guardar settings.json fuera de _MEIPASS ===
save_path = Path(os.getcwd()) / "settings.json"
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(settings, f, indent=4)

# === Inicializar hipervisores ===
if "vmware" in hypervisors:
    vmware = vmware(vmwarepath)
if "hyper-v" in hypervisors:
    hyperv = hyperv()
if "virtualbox" in hypervisors:
    virtualbox = virtualbox(virtualboxpath)

# === Configurar RPC ===
RPC = Presence(clientID)
try:
    RPC.connect()
except InvalidPipe:
    print("Waiting for Discord...")
    while True:
        try:
            RPC.connect()
            print("Connected to RPC.")
            break
        except InvalidPipe:
            sleep(5)
else:
    print("Connected to RPC.")

LASTSTATUS = None
STATUS = None
epoch_time = 0

print("Please note that Discord has a 15 second rate limit on Rich Presence updates.")

# === Bucle principal ===
while True:
    STATUS = None
    HYPERVISOR = None

    if "vmware" in hypervisors:
        vmware.updateOutput()
        if not vmware.isRunning():
            clear()
        elif vmware.runCount() > 1:
            running = True
            STATUS = "Running VMs"
            vmcount = [vmware.runCount(), vmware.runCount()]
            HYPERVISOR = "VMware"
        else:
            running = True
            displayName = vmware.getRunningGuestName(0)
            STATUS = "Virtualizing " + displayName
            vmcount = None
            HYPERVISOR = "VMware"

    if "hyper-v" in hypervisors:
        if not hyperv.isFound():
            print("Hyper-V not supported on this machine. Disabling for this session.")
            hypervisors.remove("hyper-v")
            continue
        hyperv.updateRunningVMs()
        if not hyperv.isRunning():
            clear()
        elif hyperv.runCount() > 1:
            running = True
            STATUS = "Running VMs"
            vmcount = [hyperv.runCount(), hyperv.runCount()]
            HYPERVISOR = "Hyper-V"
        else:
            running = True
            displayName = hyperv.getRunningGuestName(0)
            STATUS = "Virtualizing " + displayName
            vmcount = None
            HYPERVISOR = "Hyper-V"

    if STATUS != LASTSTATUS and STATUS:
        print(f"Rich presence updated locally: {STATUS} ({HYPERVISOR})")
        if "virtualbox" in hypervisors and virtualbox.isRunning() and virtualbox.runCount() == 1:
            epoch_time = virtualbox.getVMuptime(0)
        elif epoch_time == 0:
            now = datetime.utcnow()
            epoch_time = int((now - datetime(1970, 1, 1)).total_seconds())
        largetext = "Check out vm-rpc by DhinakG on GitHub!" if largeimage else None
        RPC.update(
            state=STATUS,
            details=f"Running {HYPERVISOR}",
            small_image=smallimage,
            large_image=largeimage,
            small_text=HYPERVISOR,
            large_text=largetext,
            start=epoch_time,
            party_size=vmcount
        )
        LASTSTATUS = STATUS

    sleep(1)
