from pycomm3 import CIPDriver, Services, ClassCode

with CIPDriver("166.152.88.41") as plc:
    reply = plc.generic_message(
        service=Services.get_attributes_all,
        class_code=ClassCode.identity_object,
        instance=1
    )
    print(reply)
