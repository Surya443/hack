import os
import json
import paho.mqtt.client as mqtt
from typing import List
from registry import DEVICES
from mcp.server.fastmcp import FastMCP

BROKER = "localhost"
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

# Only connect if MQTT broker is available
try:
    client.connect(BROKER, timeout=1)
    mqtt_enabled = True
    print("MQTT broker connected successfully")
except Exception as e:
    mqtt_enabled = False
    print(f"MQTT broker not available: {e}. Running without MQTT.")

mcp = FastMCP("smart_home", port=8002)

STATE_DIR = "device_states"
os.makedirs(STATE_DIR, exist_ok=True)

def save_state():
    file_path = os.path.join(STATE_DIR, "devices.json")
    state_dict = {
        room: {name: dev.to_dict() for name, dev in devices.items()}
        for room, devices in DEVICES.items()
    }
    with open(file_path, "w") as f:
        json.dump(state_dict, f, indent=2)

@mcp.tool()
def turn_on_device(room: str, device_name: str) -> str:
    """Turn ON a device in a given room."""
    if room in DEVICES and device_name in DEVICES[room]:
        dev = DEVICES[room][device_name]
        dev.turn_on()
        if mqtt_enabled:
            topic = f"home/{room}/{device_name}/set"
            client.publish(topic, "ON")
        save_state()
        return f"{device_name} in {room} is now ON."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def turn_off_device(room: str, device_name: str) -> str:
    """Turn OFF a device in a given room."""
    if room in DEVICES and device_name in DEVICES[room]:
        dev = DEVICES[room][device_name]
        dev.turn_off()
        if mqtt_enabled:
            topic = f"home/{room}/{device_name}/set"
            client.publish(topic, "OFF")
        save_state()
        return f"{device_name} in {room} is now OFF."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def set_device_value(room: str, device_name: str, key: str, value: str) -> str:
    """
    Set a specific parameter for a device.
    Example: brightness for light, speed for fan, temperature for AC.
    """
    if room in DEVICES and device_name in DEVICES[room]:
        dev = DEVICES[room][device_name]
        if hasattr(dev, f"set_{key}"):
            getattr(dev, f"set_{key}")(value)
            if mqtt_enabled:
                topic = f"home/{room}/{device_name}/set"
                client.publish(topic, f"{key.upper()}:{value}")
            save_state()
            return f"{key} for {device_name} in {room} set to {value}."
        return f"Device {device_name} does not support {key}."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def get_device_state(room: str, device_name: str) -> str:
    """Get the current state of a specific device."""
    if room in DEVICES and device_name in DEVICES[room]:
        return json.dumps(DEVICES[room][device_name].to_dict(), indent=2)
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def get_all_states() -> str:
    """Get the state of all devices in the smart home."""
    state_dict = {
        room: {name: dev.to_dict() for name, dev in devices.items()}
        for room, devices in DEVICES.items()
    }
    return json.dumps(state_dict, indent=2)
if __name__ == "__main__":
    mcp.run(transport='sse')