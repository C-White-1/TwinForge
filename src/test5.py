from pycomm3 import SLCDriver

plc = SLCDriver("166.152.88.41")

print(plc.open())
print(plc)
print(plc.connected)
print(plc.read("S:1"))
