import struct
from pycomm3 import CIPDriver, Services, ClassCode

with CIPDriver("166.152.88.41") as plc:
    reply = plc.generic_message(
        service=Services.get_attributes_all,
        class_code=ClassCode.identity_object,
        instance=1
    )
    raw = reply.value
    
    vendor, device_type, product_code = struct.unpack_from("<HHH", raw, 0)

    major = raw[6]
    minor = raw[7]

    status = struct.unpack_from("<H", raw, 8)[0]

    serial = struct.unpack_from("<I", raw, 10)[0]

    name_len = raw[14]
    name = raw[15:15 + name_len].decode("ascii")

    print(f"Vendor ID    : {vendor}")
    print(f"Device Type  : {device_type}")
    print(f"Product Code : {product_code}")
    print(f"Revision     : {major}.{minor}")
    print(f"Status       : 0x{status:04X}")
    print(f"Serial       : {serial:08X}")
    print(f"Product Name : {name}")    
