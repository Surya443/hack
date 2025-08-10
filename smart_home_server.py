import os
import json
import paho.mqtt.client as mqtt
from typing import List
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp import ErrorData, McpError
from mcp.server.auth.provider import AccessToken
from mcp.types import TextContent, ImageContent, INVALID_PARAMS, INTERNAL_ERROR
import time
from registry import DEVICES
from devices import TV
import subprocess
import re
import asyncio

load_dotenv()

TOKEN = os.environ.get("AUTH_TOKEN")
MY_NUMBER = os.environ.get("MY_NUMBER")

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# --- Auth Provider ---
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="smart-home-client",
                scopes=["*"],
                expires_at=None,
            )
        return None

BROKER = "localhost"
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)


try:
    client.connect(BROKER, timeout=1)
    mqtt_enabled = True
    print("MQTT broker connected successfully")
except Exception as e:
    mqtt_enabled = False
    print(f"MQTT broker not available: {e}. Running without MQTT.")

mcp = FastMCP(
    "Smart Home MCP Server",
    auth=SimpleBearerAuthProvider(TOKEN),
)

STATE_DIR = "device_states"
os.makedirs(STATE_DIR, exist_ok=True)

# --- Configuration Loading ---
CONFIG_FILE = os.path.join(STATE_DIR, "tv_config.json")

def load_tv_config():
    """Load TV configurations from JSON file if it exists"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load TV config: {e}")
    return {}

def save_tv_config():
    """Save TV configurations to JSON file"""
    tv_configs = {}
    for room, devices in DEVICES.items():
        for device_name, device in devices.items():
            if hasattr(device, 'ip_address'):  # TV device
                if room not in tv_configs:
                    tv_configs[room] = {}
                tv_configs[room][device_name] = {
                    "ip_address": device.ip_address,
                    "port": device.port
                }
    
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(tv_configs, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save TV config: {e}")

def save_state():
    file_path = os.path.join(STATE_DIR, "devices.json")
    state_dict = {
        room: {name: dev.to_dict() for name, dev in devices.items()}
        for room, devices in DEVICES.items()
    }
    with open(file_path, "w") as f:
        json.dump(state_dict, f, indent=2)
    
    save_tv_config()

ROOM_ALIASES = {
    "living room": "livingroom",
    "living_room": "livingroom", 
    "lounge": "livingroom",
    "hall": "livingroom",
    "bed room": "bedroom",
    "bed_room": "bedroom",
    "master bedroom": "bedroom",
    "kitchen": "kitchen",
    "cook room": "kitchen"
}

def normalize_room_name(room: str) -> str:
    """Convert room name variations to the standardized room name."""
    room_lower = room.lower().strip()
    return ROOM_ALIASES.get(room_lower, room_lower)

def initialize_tv_configs():
    """Load TV configurations from file on server startup"""
    configs = load_tv_config()
    if configs:
        print("Loading TV configurations from file...")
        
        for room, devices in configs.items():
            normalized_room = normalize_room_name(room)
            
            if normalized_room not in DEVICES:
                DEVICES[normalized_room] = {}
            
            for device_name, config in devices.items():
                try:
                    ip_address = config["ip_address"]
                    port = config.get("port", 5555)
                    
                    if device_name not in DEVICES[normalized_room]:
                        new_tv = TV(device_name, normalized_room, ip_address, port)
                        DEVICES[normalized_room][device_name] = new_tv
                        print(f"Loaded TV: {device_name} in {room} ({ip_address}:{port})")
                        
                except Exception as e:
                    print(f"Error loading TV {device_name} in {room}: {e}")
    else:
        print("No TV configuration file found. Use add_tv_device() to configure TVs.")

initialize_tv_configs()

# --- Tool: validate (required by Puch) ---
@mcp.tool
async def validate() -> str:
    """Validation tool required by Puch for authentication."""
    return MY_NUMBER

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
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if hasattr(dev, f"set_{key}"):
            getattr(dev, f"set_{key}")(value)
            if mqtt_enabled:
                topic = f"home/{normalized_room}/{device_name}/set"
                client.publish(topic, f"{key.upper()}:{value}")
            save_state()
            return f"{key} for {device_name} in {room} set to {value}."
        return f"Device {device_name} does not support {key}."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def get_device_state(room: str, device_name: str) -> str:
    """Get the current state of a specific device."""
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        return json.dumps(DEVICES[normalized_room][device_name].to_dict(), indent=2)
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def get_all_states() -> str:
    """Get the state of all devices in the smart home."""
    state_dict = {
        room: {name: dev.to_dict() for name, dev in devices.items()}
        for room, devices in DEVICES.items()
    }
    return json.dumps(state_dict, indent=2)

# --- TV Control Tools ---
@mcp.tool()
def tv_volume_up(room: str, device_name: str) -> str:
    """Increase TV volume."""
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if hasattr(dev, 'volume_up'):
            success = dev.volume_up()
            if success:
                save_state()
                return f"TV volume increased. Current volume: {dev.state['volume']}"
            else:
                return f"Failed to increase TV volume. Connection issue."
        return f"Device {device_name} is not a TV."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def tv_volume_down(room: str, device_name: str) -> str:
    """Decrease TV volume."""
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if hasattr(dev, 'volume_down'):
            success = dev.volume_down()
            if success:
                save_state()
                return f"TV volume decreased. Current volume: {dev.state['volume']}"
            else:
                return f"Failed to decrease TV volume. Connection issue."
        return f"Device {device_name} is not a TV."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def tv_mute(room: str, device_name: str) -> str:
    """Mute/unmute TV."""
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if hasattr(dev, 'mute'):
            success = dev.mute()
            if success:
                save_state()
                mute_status = "muted" if dev.state['muted'] else "unmuted"
                return f"TV is now {mute_status}."
            else:
                return f"Failed to mute/unmute TV. Connection issue."
        return f"Device {device_name} is not a TV."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def tv_open_app(room: str, device_name: str, app: str) -> str:
    """Open an app on TV (netflix, youtube, home)."""
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if app.lower() == 'netflix' and hasattr(dev, 'open_netflix'):
            success = dev.open_netflix()
            app_emoji = "📺"
        elif app.lower() == 'youtube' and hasattr(dev, 'open_youtube'):
            success = dev.open_youtube()
            app_emoji = "▶️"
        elif app.lower() == 'home' and hasattr(dev, 'home'):
            success = dev.home()
            app_emoji = "🏠"
        else:
            return f"App '{app}' not supported. Available: netflix, youtube, home"
        
        if success:
            save_state()
            return f"{app_emoji} Opened {app} on TV."
        else:
            return f"Failed to open {app} on TV. Connection issue."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def tv_navigate(room: str, device_name: str, direction: str) -> str:
    """Navigate TV (back, home)."""
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if direction.lower() == 'back' and hasattr(dev, 'back'):
            success = dev.back()
        elif direction.lower() == 'home' and hasattr(dev, 'home'):
            success = dev.home()
        else:
            return f"Navigation command '{direction}' not supported. Available: back, home"
        
        if success:
            save_state()
            return f"TV navigation: {direction} command sent."
        else:
            return f"Failed to send {direction} command to TV."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def check_tv_connection(room: str, device_name: str) -> str:
    """Check if TV is connected and available."""
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if hasattr(dev, 'check_connection'):
            is_connected = dev.check_connection()
            if is_connected:
                return f"TV connection is active. Status: {json.dumps(dev.state, indent=2)}"
            else:
                return f"TV is not connected. Make sure TV is on, ADB is enabled, and IP is correct."
        return f"Device {device_name} is not a TV."
    return f"Device {device_name} not found in {room}."

# --- TV Configuration Tools ---
@mcp.tool()
def add_tv_device(room: str, device_name: str, ip_address: str, port: int = 5555) -> str:
    """
    Add a new TV device with specified IP address and port.
    This allows users to configure their own TV connections.
    """
    normalized_room = normalize_room_name(room)
    
    
    ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    if not re.match(ip_pattern, ip_address):
        return f"Invalid IP address format: {ip_address}"
    
    if not (1 <= port <= 65535):
        return f"Invalid port number: {port}. Must be between 1-65535"
    
    if normalized_room not in DEVICES:
        DEVICES[normalized_room] = {}
    
    if device_name in DEVICES[normalized_room]:
        return f"Device {device_name} already exists in {room}. Use update_tv_config to modify it."
    
    try:
        new_tv = TV(device_name, normalized_room, ip_address, port)
        DEVICES[normalized_room][device_name] = new_tv
        save_state()
        
        connection_status = "Connected" if new_tv.check_connection() else "Not connected"
        
        return f"TV '{device_name}' added to {room} with IP {ip_address}:{port}. Status: {connection_status}"
    except Exception as e:
        return f"Failed to add TV device: {str(e)}"

@mcp.tool()
def update_tv_config(room: str, device_name: str, ip_address: str, port: int = 5555) -> str:
    """
    Update the IP address and port for an existing TV device.
    This allows users to reconfigure TV connections.
    """
    normalized_room = normalize_room_name(room)
    
    if normalized_room not in DEVICES or device_name not in DEVICES[normalized_room]:
        return f"TV device {device_name} not found in {room}. Use add_tv_device to create it first."
    
    
    ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    if not re.match(ip_pattern, ip_address):
        return f"Invalid IP address format: {ip_address}"
    
    if not (1 <= port <= 65535):
        return f"Invalid port number: {port}. Must be between 1-65535"
    
    try:
        existing_tv = DEVICES[normalized_room][device_name]
        if not hasattr(existing_tv, 'ip_address'):
            return f"Device {device_name} is not a TV device."
        
        old_config = f"{existing_tv.ip_address}:{existing_tv.port}"
        existing_tv.ip_address = ip_address
        existing_tv.port = port
        
        existing_tv._initialize_connection()
        save_state()
        
        connection_status = "Connected" if existing_tv.check_connection() else "Not connected"
        
        return f"TV '{device_name}' updated from {old_config} to {ip_address}:{port}. Status: {connection_status}"
    except Exception as e:
        return f"Failed to update TV configuration: {str(e)}"

@mcp.tool()
def remove_tv_device(room: str, device_name: str) -> str:
    """
    Remove a TV device from the smart home system.
    """
    normalized_room = normalize_room_name(room)
    
    if normalized_room not in DEVICES or device_name not in DEVICES[normalized_room]:
        return f"TV device {device_name} not found in {room}."
    
    device = DEVICES[normalized_room][device_name]
    if not hasattr(device, 'ip_address'):
        return f"Device {device_name} is not a TV device."
    
    try:
        del DEVICES[normalized_room][device_name]
        save_state()
        return f"TV device '{device_name}' removed from {room}."
    except Exception as e:
        return f"Failed to remove TV device: {str(e)}"

@mcp.tool()
def list_tv_devices() -> str:
    """
    List all TV devices with their configurations and connection status.
    """
    tv_devices = []
    
    for room, devices in DEVICES.items():
        for device_name, device in devices.items():
            if hasattr(device, 'ip_address'):  # TV device
                connection_status = "Connected" if device.check_connection() else "Not connected"
                tv_info = {
                    "room": room,
                    "name": device_name,
                    "ip_address": device.ip_address,
                    "port": device.port,
                    "status": connection_status,
                    "current_app": device.state.get("current_app", "unknown"),
                    "volume": device.state.get("volume", 0),
                    "muted": device.state.get("muted", False)
                }
                tv_devices.append(tv_info)
    
    if not tv_devices:
        return "No TV devices configured. Use add_tv_device to add one."
    
    
    return f"TV Devices:\n{json.dumps(tv_devices, indent=2)}"

@mcp.tool()
def load_tv_configs_from_file() -> str:
    """
    Load TV configurations from the tv_config.json file.
    Users can manually edit this file to configure multiple TVs at once.
    
    Expected format:
    {
        "livingroom": {
            "tv": {"ip_address": "192.168.1.14", "port": 5555}
        },
        "bedroom": {
            "tv2": {"ip_address": "192.168.1.15", "port": 5555}
        }
    }
    """
    try:
        configs = load_tv_config()
        if not configs:
            return f"No TV configuration file found at {CONFIG_FILE}. Use add_tv_device to create TVs or manually create the config file."
        
        added_count = 0
        updated_count = 0
        errors = []
        
        for room, devices in configs.items():
            normalized_room = normalize_room_name(room)
            
            if normalized_room not in DEVICES:
                DEVICES[normalized_room] = {}
            
            for device_name, config in devices.items():
                try:
                    ip_address = config["ip_address"]
                    port = config.get("port", 5555)
                    
                    if device_name in DEVICES[normalized_room]:
                        existing_tv = DEVICES[normalized_room][device_name]
                        if hasattr(existing_tv, 'ip_address'):
                            existing_tv.update_connection_settings(ip_address, port)
                            updated_count += 1
                        else:
                            errors.append(f"Device {device_name} in {room} is not a TV")
                    else:
                        new_tv = TV(device_name, normalized_room, ip_address, port)
                        DEVICES[normalized_room][device_name] = new_tv
                        added_count += 1
                        
                except Exception as e:
                    errors.append(f"Error configuring {device_name} in {room}: {str(e)}")
        
        save_state()
        
        result = f"TV Configuration loaded:\n"
        result += f"Added: {added_count} devices\n"
        result += f"Updated: {updated_count} devices\n"
        
        if errors:
            result += f"Errors:\n" + "\n".join(f"  - {error}" for error in errors)
        
        return result
        
    except Exception as e:
        return f"Failed to load TV configurations: {str(e)}"
@mcp.tool()
def tv_search_and_play(room: str, device_name: str, query: str, app: str = "netflix") -> str:
    """
    Search for and play content on TV streaming apps.
    Supports Netflix, YouTube, and other apps.
    Examples: "Young Sheldon", "Brooklyn Nine Nine", "comedy shows"
    """
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if hasattr(dev, 'search_and_play'):
            success = dev.search_and_play(query, app.lower())
            if success:
                save_state()
                return f"Searching and playing '{query}' on {app.title()}..."
            else:
                return f"Failed to search and play '{query}' on {app}. Connection issue."
        return f"Device {device_name} does not support search and play functionality."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def tv_search_content(room: str, device_name: str, query: str, app: str = "netflix") -> str:
    """
    Search for content on streaming apps without automatically playing.
    This allows browsing search results before selecting what to play.
    """
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if hasattr(dev, 'search_content'):
            success = dev.search_content(query, app.lower())
            if success:
                save_state()
                return f"Searching for '{query}' on {app.title()}. Use TV remote to select what to play."
            else:
                return f"Failed to search for '{query}' on {app}. Connection issue."
        return f"Device {device_name} does not support search functionality."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def tv_send_text(room: str, device_name: str, text: str) -> str:
    """
    Send text input to TV (useful for search fields).
    This can be used when the TV is in a search interface.
    """
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if hasattr(dev, 'send_text'):
            success = dev.send_text(text)
            if success:
                save_state()
                return f"Sent text '{text}' to TV."
            else:
                return f"Failed to send text to TV. Connection issue."
        return f"Device {device_name} does not support text input."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def tv_press_key(room: str, device_name: str, key: str) -> str:
    """
    Press specific keys on TV remote.
    Available keys: enter, back, home, up, down, left, right, menu, play, pause, search
    """
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        if hasattr(dev, 'press_key'):
            success = dev.press_key(key.lower())
            if success:
                save_state()
                return f"Pressed '{key}' key on TV remote."
            else:
                return f"Failed to press '{key}' key. Connection issue."
        return f"Device {device_name} does not support key press functionality."
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def play_youtube_video(room: str, device_name: str, search_query: str) -> str:
    """
    Search and play videos on YouTube TV with improved navigation.
    """
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        
        if not hasattr(dev, 'ip_address'):
            return f"Device {device_name} is not a TV device."
        
        if not dev.check_connection():
            return f"Cannot connect to TV {device_name}. Please check connection."
        
        try:
            # improved YouTube search method
            if hasattr(dev, 'open_youtube_and_search'):
                success = dev.open_youtube_and_search(search_query)
                if success:
                    save_state()
                    return f"Successfully searched for '{search_query}' on YouTube!"
                else:
                    # Fallback
                    save_state()
                    return f"YouTube is now open. The search for '{search_query}' may need manual selection due to YouTube TV interface limitations. Try:\n" \
                           f"1. Use your remote to navigate to the search icon (🔍) in the left sidebar\n" \
                           f"2. Type '{search_query}' using the on-screen keyboard\n" \
                           f"3. Select a video to play"
            else:
                # basic method
                youtube_success = dev.open_youtube()
                if youtube_success:
                    return f"YouTube opened. Please manually search for '{search_query}' using your TV remote."
                else:
                    return f"Failed to open YouTube. Make sure YouTube app is installed."
                    
        except Exception as e:
            return f"Error playing YouTube video: {str(e)}"
    
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def youtube_voice_search_workaround(room: str, device_name: str, search_query: str) -> str:
    """
    Alternative YouTube search that uses voice search interface.
    This can work when regular text search fails.
    """
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        
        if not hasattr(dev, 'ip_address'):
            return f"Device {device_name} is not a TV device."
        
        try:
            if not dev.open_youtube():
                return f"Failed to open YouTube."
            
            time.sleep(4)
            
            dev._send_adb_command("input keyevent KEYCODE_SEARCH")
            
            return f"Voice search activated on YouTube! Please say '{search_query}' into your TV remote or use the on-screen keyboard that should appear."
            
        except Exception as e:
            return f"Error with voice search: {str(e)}"
    
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def youtube_navigate_and_play(room: str, device_name: str, direction: str = "down", steps: int = 1) -> str:
    """
    Navigate YouTube interface and play content.
    Directions: up, down, left, right, enter, back
    Use this for manual navigation when search doesn't work.
    """
    normalized_room = normalize_room_name(room)
    if normalized_room in DEVICES and device_name in DEVICES[normalized_room]:
        dev = DEVICES[normalized_room][device_name]
        
        if not hasattr(dev, 'ip_address'):
            return f"Device {device_name} is not a TV device."
        
        try:
            direction_map = {
                "up": "KEYCODE_DPAD_UP",
                "down": "KEYCODE_DPAD_DOWN", 
                "left": "KEYCODE_DPAD_LEFT",
                "right": "KEYCODE_DPAD_RIGHT",
                "enter": "KEYCODE_ENTER",
                "select": "KEYCODE_ENTER",
                "back": "KEYCODE_BACK",
                "ok": "KEYCODE_ENTER"
            }
            
            if direction.lower() not in direction_map:
                return f"Invalid direction. Use: {list(direction_map.keys())}"
            
            success_count = 0
            for i in range(steps):
                if dev._send_adb_command(f"input keyevent {direction_map[direction.lower()]}"):
                    success_count += 1
                    time.sleep(0.5)  # delay between commands
            
            return f"Successfully sent {success_count}/{steps} '{direction}' commands to YouTube."
            
        except Exception as e:
            return f"Navigation error: {str(e)}"
    
    return f"Device {device_name} not found in {room}."

@mcp.tool()
def play_netflix_show(room: str, device_name: str, show_name: str) -> str:
    """
    Play a specific show or movie on Netflix.
    This function will open Netflix and attempt to search and play the content.
    """
    normalized_room = normalize_room_name(room)
    
    if normalized_room not in DEVICES or device_name not in DEVICES[normalized_room]:
        return f"Device {device_name} not found in {room}. Available devices: {list(DEVICES.get(normalized_room, {}).keys())}"
    
    dev = DEVICES[normalized_room][device_name]
    
    if not hasattr(dev, 'ip_address'):
        return f"Device {device_name} is not a TV device."
    
    if not dev.check_connection():
        return f"Cannot connect to TV {device_name}. Please check:\n" \
               f"• TV is powered on\n" \
               f"• Developer options enabled\n" \
               f"• USB debugging enabled\n" \
               f"• IP address is correct: {dev.ip_address}:{dev.port}\n" \
               f"• TV and server are on same network"
    
    try:
        print(f"Attempting to play '{show_name}' on Netflix...")
        
        
        print("Opening Netflix...")
        netflix_success = dev.open_netflix()
        if not netflix_success:
            return f"Failed to open Netflix on {device_name}. Make sure Netflix app is installed."
        
        # Search and play
        print(f"Searching for '{show_name}'...")
        if hasattr(dev, 'search_and_play'):
            search_success = dev.search_and_play(show_name, "netflix")
            if search_success:
                save_state()
                return f"Successfully initiated playback of '{show_name}' on Netflix! The show should start playing shortly."
            else:
                # Fallback
                save_state()
                return f"Netflix is now open on {device_name}. I attempted to search for '{show_name}' but it may need manual selection. Try using your TV remote to:\n" \
                       f"1. Navigate to the search icon (🔍)\n" \
                       f"2. Type '{show_name}'\n" \
                       f"3. Select the show to play"
        else:
            save_state() 
            return f"Netflix opened on {device_name}. Your TV doesn't support automatic search yet. Please manually search for '{show_name}' using your remote."
            
    except Exception as e:
        return f"Unexpected error while trying to play '{show_name}': {str(e)}"

@mcp.tool()
def diagnose_tv_connection(room: str, device_name: str) -> str:
    """
    Run diagnostics on TV connection to help troubleshoot issues.
    """
    normalized_room = normalize_room_name(room)
    
    if normalized_room not in DEVICES or device_name not in DEVICES[normalized_room]:
        return f"Device {device_name} not found in {room}."
    
    dev = DEVICES[normalized_room][device_name]
    
    if not hasattr(dev, 'ip_address'):
        return f"Device {device_name} is not a TV device."
    
    results = []
    results.append(f"Diagnosing TV: {device_name} in {room}")
    results.append(f"IP Address: {dev.ip_address}:{dev.port}")
    
    try:
        ping_result = subprocess.run(f"ping -c 1 -W 3 {dev.ip_address}", 
                                   shell=True, capture_output=True, timeout=5)
        if ping_result.returncode == 0:
            results.append("Network connectivity: OK")
        else:
            results.append("Network connectivity: FAILED - TV not reachable")
            return "\n".join(results)
    except:
        results.append("Network connectivity: Could not test")
    
    try:
        adb_result = subprocess.run(f"adb connect {dev.ip_address}:{dev.port}", 
                                  shell=True, capture_output=True, timeout=10)
        if "connected" in adb_result.stdout.decode().lower():
            results.append("ADB connection: OK") 
        else:
            results.append(f"ADB connection: FAILED - {adb_result.stdout.decode().strip()}")
    except:
        results.append("ADB connection: ERROR - ADB not installed or accessible")
    
    if dev.check_connection():
        results.append("Device responsiveness: OK")
    else:
        results.append("Device responsiveness: FAILED")
    
    try:
        netflix_test = subprocess.run(f"adb -s {dev.ip_address}:{dev.port} shell pm list packages | grep netflix", 
                                    shell=True, capture_output=True, timeout=10)
        if netflix_test.returncode == 0 and netflix_test.stdout:
            results.append("Netflix app: Installed")
        else:
            results.append("Netflix app: Not found or not accessible")
    except:
        results.append("Netflix app: Could not verify")
    
    return "\n".join(results)

# --- Run MCP Server ---
async def main():
    print(f"Starting Smart Home MCP server on http://0.0.0.0:8002")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8002)

if __name__ == "__main__":
    
    asyncio.run(main())