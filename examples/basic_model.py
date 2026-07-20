from twinforge.model import (
    Plant,
    Controller,
    Chassis,
    Module,
    Program,
    Routine,
    Identity,
    Revision,
    VendorIdentity,
)

plant = Plant(name="Demo Plant")

controller = Controller(
    name="JVBC",
    identity=Identity(
        vendor=VendorIdentity(
            id=1,
            name="Allen-Bradley / Rockwell Automation",
        ),
        product_name="1756-L61/B",
        product_code=54,
        product_type=14,
        product_type_name="Programmable Logic Controller",
        revision=Revision(20, 55),
        serial="008b26cc",
    )
)

chassis = Chassis(name="Local Chassis")

module = Module(
    slot=0,
    catalog="1756-L61/B",
    identity=controller.identity,
)

chassis.add_module(module)
controller.add_chassis(chassis)
plant.add_controller(controller)
program = Program(name="MainProgram")
controller.add_program(program)
routine = Routine(name="MainRoutine")
program.add_routine(routine)

assert module.parent is chassis
assert chassis.parent is controller
assert controller.parent is plant

assert controller.get_chassis("Local Chassis") is chassis
assert chassis.get_module(0) is module

print(plant)

for controller in plant.controllers:
    print(" ", controller)

    for chassis in controller.iter_chassis():
        print(chassis)
    
    for module in chassis.iter_modules():
        print(module)
