from twinforge.parsers import L5XParser

parser = L5XParser()

plant = parser.parse("tests/data/basic/BoosterCompressor_20260128.l5x")

print(plant)


# for controller in plant

for controller in plant.iter_controllers():
    print(controller)

    for chassis in controller.iter_chassis():
        print(chassis)

        for module in chassis.iter_modules():
            print(module)

    for program in controller.iter_programs():
        print(program)

        for routine in program.iter_routines():
            print(routine)
