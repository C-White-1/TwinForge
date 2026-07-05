from pycomm3 import LogixDriver
import json

class CIPEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (bytes, bytearray)):
            return obj.hex()  # or obj.decode(errors="ignore")
        return super().default(obj)

def enumerate_chassis(ip, max_slots=20):
    chassis = {}

    with LogixDriver(f"{ip}/0") as plc:
        # Controller (slot 0)
        chassis["controller"] = plc.info

        slots = {}

        for slot in range(max_slots):
            path = f"{ip}/{slot}"

            try:
                with LogixDriver(path) as module:
                    info = module.info

                    slots[slot] = {
                        "product": info.get("product_name"),
                        "vendor": info.get("vendor"),
                        "revision": info.get("revision"),
                        "product_code": info.get("product_code"),
                    }

            except Exception:
                # No module in slot or not reachable
                continue

        chassis["slots"] = slots

    return chassis


if __name__ == "__main__":

    result = enumerate_chassis("125.215.255.49")
    print(json.dumps(result, indent=2, cls=CIPEncoder))
