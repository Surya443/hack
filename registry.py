
from devices import Light, Fan, AC, Chimney, TV

DEVICES = {
    "kitchen": {
        "light1": Light("light1", "kitchen"),
        "light2": Light("light2", "kitchen"),
        "chimney": Chimney("chimney", "kitchen")
    },
    "livingroom": {
        "light3": Light("light3", "livingroom"),
        "light4": Light("light4", "livingroom"),
        "light5": Light("light5", "livingroom"),
        "fan1": Fan("fan1", "livingroom")
        # TV removed - users should configure using add_tv_device() or tv_config.json
    },
    "bedroom": {
        "ac1": AC("ac1", "bedroom"),
        "fan2": Fan("fan2", "bedroom"),
        "light76": Light("light76", "bedroom")
    }
}
