from pycomm3 import CIPDriver

with CIPDriver("166.152.88.41:44818") as plc:
    print("Connected")
