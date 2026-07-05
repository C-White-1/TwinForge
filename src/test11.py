from pycomm3 import CIPDriver

ip = "125.215.255.49"

with CIPDriver(ip) as plc:
    print(plc.generic_message(
        service=0x01,
        class_code=0x01,
        instance=1,
        attribute=1,
        route_path=[1,1]
    ))

 #def scan_debug(plc, max_slots=10):
 #   for slot in range(max_slots):
 #       resp = plc.generic_message(
 #           service=0x01,
 #          class_code=0x01,
 #           instance=1,
 #           attribute=1,
 #           route_path=f"1,{slot}"
 #       )

 #      print(slot, resp)  
