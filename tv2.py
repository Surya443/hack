from ppadb.client import Client as AdbClient

# ---- Config ----
ADB_HOST = "127.0.0.1"
ADB_PORT = 5037
TV_IP = "192.168.1.14"  # Your TV IP
TV_PORT = 5555         # Default ADB port

# ---- Connect to ADB Server ----
client = AdbClient(host=ADB_HOST, port=ADB_PORT)
device = client.device(f"{TV_IP}:{TV_PORT}")

if not device:
    print("❌ Could not connect to Mi TV. Make sure 'adb connect' works first.")
    exit()

print("✅ Connected to Mi TV!")

# ---- Command Functions ----
def volume_up():
    device.shell("input keyevent 24")  # Volume Up
    print("🔊 Volume Up")

def volume_down():
    device.shell("input keyevent 25")  # Volume Down
    print("🔉 Volume Down")

def mute():
    device.shell("input keyevent 164") # Mute
    print("🔇 Mute")

def open_netflix():
    device.shell("monkey -p com.netflix.ninja -c android.intent.category.LAUNCHER 1")
    print("📺 Netflix Opened")

def open_youtube():
    device.shell("monkey -p com.google.android.youtube.tv -c android.intent.category.LAUNCHER 1")
    print("▶️ YouTube Opened")

# ---- Menu ----
while True:
    print("\n--- Mi TV Control ---")
    print("1. Volume Up")
    print("2. Volume Down")
    print("3. Mute")
    print("4. Open Netflix")
    print("5. Open YouTube")
    print("6. Exit")

    choice = input("Choose: ").strip()

    if choice == "1":
        volume_up()
    elif choice == "2":
        volume_down()
    elif choice == "3":
        mute()
    elif choice == "4":
        open_netflix()
    elif choice == "5":
        open_youtube()
    elif choice == "6":
        print("Bye!")
        break
    else:
        print("Invalid choice.")
