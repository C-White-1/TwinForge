from twinforge.services.digital_twin import DigitalTwinBuilder

builder = DigitalTwinBuilder("125.215.255.49")

plant = builder.build()

plant.to_json("plant.json")
plant.to_graphviz("plant.dot")
plant.to_automationml("plant.aml")
