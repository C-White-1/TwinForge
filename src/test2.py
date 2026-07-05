from pycomm3 import CIPDriver, Services, ClassCode

with CIPDriver("166.152.88.41") as plc:
    reply = plc.generic_message(
        service=Services.get_attribute_single,
        class_code=ClassCode.identity_object,
        instance=1,
        attribute=7
    )

    raw = reply.value

    length = raw[0]
    name = raw[1:1+length].decode("ascii")

    print(length)
    print(name)
