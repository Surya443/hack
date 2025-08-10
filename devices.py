# devices.py
class Device:
    def __init__(self, name, device_type, room):
        self.name = name
        self.type = device_type
        self.room = room
        self.state = {"power": "OFF"}

    def turn_on(self):
        self.state["power"] = "ON"

    def turn_off(self):
        self.state["power"] = "OFF"

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "room": self.room,
            "state": self.state
        }

class Light(Device):
    def __init__(self, name, room):
        super().__init__(name, "light", room)
        self.state["brightness"] = 0

    def set_brightness(self, value):
        self.state["brightness"] = value

class Fan(Device):
    def __init__(self, name, room):
        super().__init__(name, "fan", room)
        self.state["speed"] = 0

    def set_speed(self, value):
        self.state["speed"] = value

class AC(Device):
    def __init__(self, name, room):
        super().__init__(name, "ac", room)
        self.state["temperature"] = 24

    def set_temperature(self, value):
        self.state["temperature"] = value

class Chimney(Device):
    def __init__(self, name, room):
        super().__init__(name, "chimney", room)
        self.state["mode"] = "OFF"

    def set_mode(self, mode):
        self.state["mode"] = mode

# Add this to your devices.py file - Enhanced TV class methods

import time
import subprocess
import re

class TV:
    def __init__(self, name, room, ip_address, port=5555):
        self.name = name
        self.room = room
        self.ip_address = ip_address
        self.port = port
        self.state = {
            "power": "off",
            "volume": 50,
            "muted": False,
            "current_app": "home"
        }
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize ADB connection to TV"""
        try:
            # Connect to the device
            connect_cmd = f"adb connect {self.ip_address}:{self.port}"
            subprocess.run(connect_cmd, shell=True, capture_output=True, timeout=10)
        except Exception as e:
            print(f"Failed to initialize TV connection: {e}")
    
    def _send_adb_command(self, command: str) -> bool:
        """Helper method to send ADB commands to TV"""
        try:
            # First ensure connection
            connect_cmd = f"adb connect {self.ip_address}:{self.port}"
            subprocess.run(connect_cmd, shell=True, capture_output=True, timeout=5)
            
            # Send the actual command
            full_command = f"adb -s {self.ip_address}:{self.port} shell {command}"
            result = subprocess.run(full_command, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                return True
            else:
                print(f"ADB command failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("ADB command timed out")
            return False
        except Exception as e:
            print(f"ADB command error: {e}")
            return False
    
    def check_connection(self) -> bool:
        """Check if TV is connected and responsive"""
        try:
            # Try a simple command to test connection
            return self._send_adb_command("echo 'test'")
        except:
            return False
    
    def turn_on(self):
        """Turn on TV"""
        success = self._send_adb_command("input keyevent KEYCODE_POWER")
        if success:
            self.state["power"] = "on"
        return success
    
    def turn_off(self):
        """Turn off TV"""  
        success = self._send_adb_command("input keyevent KEYCODE_POWER")
        if success:
            self.state["power"] = "off"
        return success
    
    def volume_up(self) -> bool:
        """Increase volume"""
        success = self._send_adb_command("input keyevent KEYCODE_VOLUME_UP")
        if success:
            self.state["volume"] = min(100, self.state["volume"] + 5)
        return success
    
    def volume_down(self) -> bool:
        """Decrease volume"""
        success = self._send_adb_command("input keyevent KEYCODE_VOLUME_DOWN") 
        if success:
            self.state["volume"] = max(0, self.state["volume"] - 5)
        return success
    
    def mute(self) -> bool:
        """Toggle mute"""
        success = self._send_adb_command("input keyevent KEYCODE_VOLUME_MUTE")
        if success:
            self.state["muted"] = not self.state["muted"]
        return success
    
    def home(self) -> bool:
        """Go to home screen"""
        success = self._send_adb_command("input keyevent KEYCODE_HOME")
        if success:
            self.state["current_app"] = "home"
        return success
    
    def back(self) -> bool:
        """Go back"""
        return self._send_adb_command("input keyevent KEYCODE_BACK")
    
    def open_netflix(self) -> bool:
        """Open Netflix app"""
        success = self._send_adb_command("monkey -p com.netflix.ninja 1")
        if not success:
            # Alternative method - try using activity manager
            success = self._send_adb_command("am start -n com.netflix.ninja/.MainActivity")
        
        if success:
            self.state["current_app"] = "netflix"
            time.sleep(3)  # Give Netflix time to load
        return success
    
    def open_youtube(self) -> bool:
        """Open YouTube app"""
        success = self._send_adb_command("monkey -p com.google.android.youtube.tv 1")
        if not success:
            # Alternative method
            success = self._send_adb_command("am start -n com.google.android.youtube.tv/.MainActivity")
        
        if success:
            self.state["current_app"] = "youtube" 
            time.sleep(3)  # Give YouTube time to load
        return success
    
    def search_and_play(self, query: str, app: str = "netflix") -> bool:
        """Search for and play content on streaming apps"""
        try:
            print(f"Searching for '{query}' on {app}...")
            
            # Ensure the app is open first
            if app == "netflix":
                if not self.open_netflix():
                    print("Failed to open Netflix")
                    return False
                time.sleep(4)  # Extra time for Netflix to fully load
            elif app == "youtube":
                if not self.open_youtube():
                    print("Failed to open YouTube") 
                    return False
                time.sleep(4)
            
            # Try to open search interface
            search_success = False
            
            # Method 1: Try search key
            if self._send_adb_command("input keyevent KEYCODE_SEARCH"):
                search_success = True
                time.sleep(2)
            
            # Method 2: If search key doesn't work, try navigation to search
            if not search_success and app == "netflix":
                # Navigate to search in Netflix (usually top of interface)
                self._send_adb_command("input keyevent KEYCODE_DPAD_UP")
                time.sleep(1)
                self._send_adb_command("input keyevent KEYCODE_DPAD_UP") 
                time.sleep(1)
                self._send_adb_command("input keyevent KEYCODE_ENTER")
                time.sleep(2)
                search_success = True
            
            if search_success:
                # Send the search query
                if self.send_text(query):
                    time.sleep(2)
                    # Press enter to search
                    self._send_adb_command("input keyevent KEYCODE_ENTER")
                    time.sleep(3)
                    # Select and play first result
                    self._send_adb_command("input keyevent KEYCODE_ENTER")
                    print(f"Successfully initiated search and play for '{query}'")
                    return True
                else:
                    print("Failed to send search text")
            else:
                print("Failed to open search interface")
                
            return False
            
        except Exception as e:
            print(f"Error in search_and_play: {e}")
            return False
    
    def search_content(self, query: str, app: str = "netflix") -> bool:
        """Search for content without automatically playing"""
        try:
            # Ensure the app is open
            if app == "netflix":
                if not self.open_netflix():
                    return False
                time.sleep(4)
            elif app == "youtube":
                if not self.open_youtube():
                    return False 
                time.sleep(4)
            
            # Open search interface
            if self._send_adb_command("input keyevent KEYCODE_SEARCH"):
                time.sleep(2)
                # Send the search text
                if self.send_text(query):
                    time.sleep(2)
                    # Press enter to search (but don't auto-play)
                    self._send_adb_command("input keyevent KEYCODE_ENTER")
                    return True
            return False
        except Exception as e:
            print(f"Error in search_content: {e}")
            return False
    
    def send_text(self, text: str) -> bool:
        """Send text to TV input field"""
        try:
            # Clean the text for ADB input
            # Replace spaces with %s for ADB text input
            cleaned_text = text.replace(" ", "%s")
            # Escape special characters
            cleaned_text = re.sub(r'[^\w%s]', '', cleaned_text)
            
            success = self._send_adb_command(f"input text '{cleaned_text}'")
            if success:
                print(f"Successfully sent text: '{text}'")
            else:
                print(f"Failed to send text: '{text}'")
            return success
        except Exception as e:
            print(f"Error sending text: {e}")
            return False
    
    def press_key(self, key: str) -> bool:
        """Press specific keys on TV remote"""
        key_codes = {
            "enter": "KEYCODE_ENTER",
            "back": "KEYCODE_BACK",
            "home": "KEYCODE_HOME", 
            "up": "KEYCODE_DPAD_UP",
            "down": "KEYCODE_DPAD_DOWN",
            "left": "KEYCODE_DPAD_LEFT", 
            "right": "KEYCODE_DPAD_RIGHT",
            "menu": "KEYCODE_MENU",
            "play": "KEYCODE_MEDIA_PLAY",
            "pause": "KEYCODE_MEDIA_PAUSE",
            "search": "KEYCODE_SEARCH",
            "ok": "KEYCODE_ENTER",
            "select": "KEYCODE_ENTER"
        }
        
        if key.lower() in key_codes:
            return self._send_adb_command(f"input keyevent {key_codes[key.lower()]}")
        else:
            print(f"Unknown key: {key}. Available keys: {list(key_codes.keys())}")
            return False
    
    def update_connection_settings(self, ip_address: str, port: int):
        """Update IP and port for existing TV connection"""
        self.ip_address = ip_address
        self.port = port
        self._initialize_connection()
    
    def to_dict(self):
        """Convert TV state to dictionary"""
        return {
            "name": self.name,
            "room": self.room,
            "type": "tv",
            "ip_address": self.ip_address,
            "port": self.port,
            "state": self.state
        }
    
    # Updated TV class methods - replace the existing search methods in your TV class

def search_and_play(self, query: str, app: str = "netflix") -> bool:
    """Search for and play content on streaming apps"""
    try:
        print(f"Searching for '{query}' on {app}...")
        
        # Ensure the app is open first
        if app == "netflix":
            if not self.open_netflix():
                print("Failed to open Netflix")
                return False
            time.sleep(4)  # Extra time for Netflix to fully load
            return self._netflix_search_and_play(query)
            
        elif app == "youtube":
            if not self.open_youtube():
                print("Failed to open YouTube") 
                return False
            time.sleep(4)
            return self._youtube_search_and_play(query)
            
        return False
        
    except Exception as e:
        print(f"Error in search_and_play: {e}")
        return False

def search_content(self, query: str, app: str = "netflix") -> bool:
    """Search for content without automatically playing"""
    try:
        # Ensure the app is open
        if app == "netflix":
            if not self.open_netflix():
                return False
            time.sleep(4)
            return self._netflix_search_only(query)
            
        elif app == "youtube":
            if not self.open_youtube():
                return False 
            time.sleep(4)
            return self._youtube_search_only(query)
            
        return False
    except Exception as e:
        print(f"Error in search_content: {e}")
        return False

def _netflix_search_and_play(self, query: str) -> bool:
    """Netflix-specific search and play"""
    try:
        # Method 1: Try search key
        search_success = False
        if self._send_adb_command("input keyevent KEYCODE_SEARCH"):
            search_success = True
            time.sleep(2)
        
        # Method 2: Navigate to search manually
        if not search_success:
            # Navigate to search in Netflix (usually at top)
            for _ in range(3):  # Try going up multiple times
                self._send_adb_command("input keyevent KEYCODE_DPAD_UP")
                time.sleep(0.5)
            
            # Look for search icon and press enter
            self._send_adb_command("input keyevent KEYCODE_ENTER")
            time.sleep(2)
            search_success = True
        
        if search_success:
            # Send the search query
            if self.send_text(query):
                time.sleep(2)
                # Press enter to search
                self._send_adb_command("input keyevent KEYCODE_ENTER")
                time.sleep(3)
                # Select and play first result
                self._send_adb_command("input keyevent KEYCODE_ENTER")
                return True
        
        return False
    except Exception as e:
        print(f"Netflix search error: {e}")
        return False

def _netflix_search_only(self, query: str) -> bool:
    """Netflix-specific search without auto-play"""
    try:
        if self._send_adb_command("input keyevent KEYCODE_SEARCH"):
            time.sleep(2)
            if self.send_text(query):
                time.sleep(2)
                self._send_adb_command("input keyevent KEYCODE_ENTER")
                return True
        return False
    except Exception as e:
        print(f"Netflix search error: {e}")
        return False

def _youtube_search_and_play(self, query: str) -> bool:
    """YouTube TV-specific search and play method"""
    try:
        print("Navigating to YouTube search...")
        
        # Method 1: Navigate to search icon manually
        # In YouTube TV, search is usually in the left sidebar
        
        # First, go to the home/main screen
        self._send_adb_command("input keyevent KEYCODE_HOME")
        time.sleep(1)
        
        # Navigate left to access the sidebar
        for _ in range(3):
            self._send_adb_command("input keyevent KEYCODE_DPAD_LEFT")
            time.sleep(0.5)
        
        # Navigate up/down to find search (usually near the top)
        for _ in range(2):
            self._send_adb_command("input keyevent KEYCODE_DPAD_UP") 
            time.sleep(0.5)
        
        # Try to find and select search
        self._send_adb_command("input keyevent KEYCODE_ENTER")
        time.sleep(3)
        
        # Alternative method: Try using keyboard search
        success = False
        
        # Method 2: Use text input directly (some YouTube TV versions support this)
        if self.send_text(query):
            time.sleep(2)
            self._send_adb_command("input keyevent KEYCODE_ENTER")
            time.sleep(3)
            # Select first result
            self._send_adb_command("input keyevent KEYCODE_ENTER")
            success = True
        
        # Method 3: If text input didn't work, try voice search workaround
        if not success:
            print("Attempting voice search method...")
            # Trigger voice search but immediately cancel it, then try manual navigation
            self._send_adb_command("input keyevent KEYCODE_SEARCH")
            time.sleep(1)
            # Press back to cancel voice search
            self._send_adb_command("input keyevent KEYCODE_BACK")
            time.sleep(1)
            
            # Try navigating to search results or trending
            for _ in range(5):
                self._send_adb_command("input keyevent KEYCODE_DPAD_DOWN")
                time.sleep(0.3)
            
            # Try to play something
            self._send_adb_command("input keyevent KEYCODE_ENTER")
            success = True
        
        return success
        
    except Exception as e:
        print(f"YouTube search error: {e}")
        return False

def _youtube_search_only(self, query: str) -> bool:
    """YouTube TV-specific search without auto-play"""
    try:
        # Navigate to search
        for _ in range(3):
            self._send_adb_command("input keyevent KEYCODE_DPAD_LEFT")
            time.sleep(0.5)
        
        for _ in range(2):
            self._send_adb_command("input keyevent KEYCODE_DPAD_UP")
            time.sleep(0.5)
        
        self._send_adb_command("input keyevent KEYCODE_ENTER")
        time.sleep(2)
        
        if self.send_text(query):
            time.sleep(2)
            self._send_adb_command("input keyevent KEYCODE_ENTER")
            return True
            
        return False
    except Exception as e:
        print(f"YouTube search error: {e}")
        return False

# Also add a specific YouTube play function
def open_youtube_and_search(self, query: str) -> bool:
    """Open YouTube and search for content with multiple fallback methods"""
    try:
        print(f"Opening YouTube and searching for: {query}")
        
        # Open YouTube
        if not self.open_youtube():
            return False
        time.sleep(5)  # Give YouTube more time to fully load
        
        # Method 1: Try direct search navigation
        success = self._youtube_navigate_to_search(query)
        if success:
            return True
        
        # Method 2: Use YouTube deep link (if supported)
        youtube_search_intent = f'am start -a android.intent.action.SEARCH -e query "{query}" com.google.android.youtube.tv'
        if self._send_adb_command(youtube_search_intent):
            time.sleep(3)
            return True
        
        # Method 3: Fallback to manual instructions
        print("Automatic search failed. YouTube is open for manual search.")
        return False
        
    except Exception as e:
        print(f"YouTube open and search error: {e}")
        return False

def _youtube_navigate_to_search(self, query: str) -> bool:
    """Navigate to YouTube search interface"""
    try:
        # Try multiple navigation patterns for different YouTube TV layouts
        
        # Pattern 1: Search in left sidebar
        self._send_adb_command("input keyevent KEYCODE_DPAD_LEFT")
        time.sleep(1)
        self._send_adb_command("input keyevent KEYCODE_DPAD_LEFT") 
        time.sleep(1)
        
        # Look for search option (try multiple positions)
        for i in range(4):
            self._send_adb_command("input keyevent KEYCODE_DPAD_UP")
            time.sleep(0.5)
        
        # Try to activate search
        self._send_adb_command("input keyevent KEYCODE_ENTER")
        time.sleep(2)
        
        # Send search text
        if self.send_text(query):
            time.sleep(2)
            self._send_adb_command("input keyevent KEYCODE_ENTER")
            time.sleep(2)
            # Select first result
            self._send_adb_command("input keyevent KEYCODE_ENTER")
            return True
        
        return False
        
    except Exception as e:
        print(f"YouTube navigation error: {e}")
        return False