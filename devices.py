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
