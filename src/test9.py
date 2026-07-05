from pycomm3 import LogixDriver

with LogixDriver("125.215.255.49") as plc:
    tags = plc.tags

    if isinstance(tags, dict):
        for name, meta in tags.items():
            print(name, meta)

    elif isinstance(tags, list):
        for name in tags:
            print(name)

    else:
        print("Unknown tag structure:", type(tags))

