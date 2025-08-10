# 🏠 Smart Home Control System

Welcome to your personal smart home automation hub! This project lets you control all your smart devices through a simple MCP (Model Context Protocol) server. Whether you want to dim the lights, crank up the AC, or binge-watch your favorite Netflix series, this system has got you covered.

## What This Does

Think of this as your smart home's brain. It's an MCP server that connects to various devices around your house and lets you control them through natural language commands. You can control lights, fans, air conditioners, and even your smart TV - all from one place!

The system uses MQTT for real-time communication between devices and stores all your device states persistently, so your settings are remembered even after restarts.

## 🚀 Quick Setup

### Prerequisites
- Python 3.11 or higher
- ADB (Android Debug Bridge) installed for TV control
- Optional: MQTT broker running on localhost

### Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   uv sync
   ```

3. Create a `.env` file with your authentication credentials:
   ```env
   AUTH_TOKEN=your_secret_token_here
   MY_NUMBER=your_validation_number
   ```

4. Run the server:
   ```bash
   python smart_home_server.py
   ```

The server will start on `http://0.0.0.0:8002` and you're ready to go!

## 🏡 Supported Devices

### Standard Smart Devices
- **Lights** - Control power and brightness
- **Fans** - Adjust speed settings  
- **Air Conditioners** - Set temperature
- **Chimneys** - Change operation modes

### Smart TVs (Android TV/Google TV)
- Full remote control via ADB
- App launching (Netflix, YouTube)
- Content search and playback
- Volume and navigation control

## 🛠️ Available Tools

Here's everything you can do with this system:

### Basic Device Control

#### `turn_on_device(room, device_name)`
Powers on any device in your smart home. Works with lights, fans, ACs, you name it!

#### `turn_off_device(room, device_name)`
Turns off devices. Pretty straightforward - the opposite of turning them on.

#### `set_device_value(room, device_name, key, value)`
This is where the magic happens! Adjust specific settings like:
- Light brightness: `set_device_value("bedroom", "light1", "brightness", "80")`
- Fan speed: `set_device_value("livingroom", "fan1", "speed", "3")`
- AC temperature: `set_device_value("bedroom", "ac1", "temperature", "22")`

#### `get_device_state(room, device_name)`
Check what's going on with a specific device - is it on? What's the current brightness? Temperature?

#### `get_all_states()`
Get a complete overview of every device in your home. Perfect for checking everything at once.

### TV Control - Basic Functions

#### `tv_volume_up(room, device_name)` & `tv_volume_down(room, device_name)`
Adjust TV volume. The system tracks the current volume level too.

#### `tv_mute(room, device_name)`
Toggle mute on your TV. Hit it again to unmute.

#### `tv_open_app(room, device_name, app)`
Launch apps on your TV. Currently supports:
- `netflix` - Open Netflix
- `youtube` - Open YouTube  
- `home` - Go to home screen

#### `tv_navigate(room, device_name, direction)`
Navigate your TV interface:
- `back` - Go back one screen
- `home` - Return to home screen

#### `check_tv_connection(room, device_name)`
Test if your TV is connected and responding. Great for troubleshooting!

### TV Setup & Management

#### `add_tv_device(room, device_name, ip_address, port=5555)`
Add a new smart TV to your system. You'll need the TV's IP address (find it in your TV's network settings).

Example: `add_tv_device("livingroom", "main_tv", "192.168.1.100")`

#### `update_tv_config(room, device_name, ip_address, port=5555)`
Update an existing TV's network settings. Useful when your TV gets a new IP address.

#### `remove_tv_device(room, device_name)`
Remove a TV from your system completely.

#### `list_tv_devices()`
See all your configured TVs, their IP addresses, and connection status.

#### `load_tv_configs_from_file()`
Load TV configurations from a JSON file. You can manually edit `device_states/tv_config.json` to add multiple TVs at once.

### Advanced TV Content Control

#### `tv_search_and_play(room, device_name, query, app="netflix")`
The crown jewel! Search for content and automatically start playing it.

Examples:
- `tv_search_and_play("livingroom", "tv", "Breaking Bad", "netflix")`
- `tv_search_and_play("bedroom", "tv", "funny cat videos", "youtube")`

#### `tv_search_content(room, device_name, query, app="netflix")`
Search for content but don't auto-play. Let you browse the results first.

#### `play_netflix_show(room, device_name, show_name)`
Dedicated Netflix function with enhanced error handling and troubleshooting tips.

#### `play_youtube_video(room, device_name, search_query)`
YouTube-specific search with smart fallbacks when the interface is tricky.

#### `youtube_voice_search_workaround(room, device_name, search_query)`
Alternative YouTube search using voice search interface. Sometimes works better than regular search.

### TV Remote Control

#### `tv_send_text(room, device_name, text)`
Type text into TV search fields or any text input.

#### `tv_press_key(room, device_name, key)`
Press specific remote control buttons:
- Navigation: `up`, `down`, `left`, `right`, `enter`, `back`, `home`
- Media: `play`, `pause`, `search`, `menu`

#### `youtube_navigate_and_play(room, device_name, direction="down", steps=1)`
Navigate YouTube's interface manually. Useful when automatic search fails.

### Troubleshooting

#### `diagnose_tv_connection(room, device_name)`
Run comprehensive diagnostics on your TV connection:
- Network connectivity test
- ADB connection status
- Device responsiveness check
- App availability verification

Perfect for figuring out why your TV isn't responding!

## 🏠 Room Management

The system is smart about room names. You can use natural variations:
- "living room", "livingroom", "lounge", "hall" → all become "livingroom"
- "bed room", "bedroom", "master bedroom" → all become "bedroom"  
- "kitchen", "cook room" → both become "kitchen"

## 📁 Project Structure

```
hack/
├── smart_home_server.py    # Main MCP server with all the tools
├── devices.py             # Device classes (Light, Fan, AC, TV, etc.)
├── registry.py           # Initial device registry
├── device_states/        # Persistent storage
│   ├── devices.json      # Device states
│   └── tv_config.json    # TV configurations
└── main.py              # Entry point
```

## 🔧 Technical Details

- **MCP Server**: Runs on FastMCP with Bearer token authentication
- **TV Control**: Uses ADB (Android Debug Bridge) for smart TV interaction
- **MQTT Support**: Optional MQTT broker integration for real-time updates
- **Persistent Storage**: All device states are saved automatically
- **Error Handling**: Comprehensive error messages and connection diagnostics

## 🤔 Troubleshooting TV Setup

If your android TV isn't connecting:

1. **Enable Developer Options**: Go to Settings → About → Keep pressing on "Build" until developer mode activates
2. **Enable USB Debugging**: In Developer Options, turn on "USB Debugging" 
3. **Enable Network ADB**: Turn on "Network ADB" if available
4. **Check IP Address**: Make sure you have the correct IP (Settings → Network) and IP changes everytime you start the TV
5. **Same Network**: Ensure your TV and server are on the same WiFi network
6. **Use Diagnostics**: Run `diagnose_tv_connection()` for detailed troubleshooting

## 🎉 Getting Started

1. Start with basic devices like lights and fans
2. Add your TV using `add_tv_device()` 
3. Test the connection with `check_tv_connection()`
4. Try some basic TV controls like volume or opening apps
5. Experiment with content search and playback
6. Use `diagnose_tv_connection()` if you run into issues

That's it! You now have a full smart home control system that can handle everything from dimming lights to finding your next binge-watch series. Enjoy your automated home! 🏡✨
