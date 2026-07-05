from pycomm3 import CIPDriver

ip = "125.215.255.49"

with CIPDriver(ip) as plc:
    for slot in range(16):
        try:
            info = plc.get_module_info(slot)
            print(slot, info)
        except Exception:
            pass
