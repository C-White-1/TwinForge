from pycomm3 import LogixDriver

with LogixDriver("125.215.255.49") as plc:
    print(plc.info)
