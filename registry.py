
from devices import Light, Fan, AC, Chimney

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
    },
    "bedroom": {
        "ac1": AC("ac1", "bedroom"),
        "fan2": Fan("fan2", "bedroom"),
        "light76": Light("light76", "bedroom")
    }
}
