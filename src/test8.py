from pycomm3 import LogixDriver
import json


def enumerate_chassis(ip, max_slots=20):
    result = {
        "controller": None,
        "slots": {}
    }

    # Controller (slot 0)
    with LogixDriver(f"{ip}/0") as ctrl:
        result["controller"] = ctrl.info

    # True slot enumeration (authoritative only)
    for slot in range(max_slots):
        try:
            with LogixDriver(f"{ip}/{slot}") as dev:
                info = dev.info

                result["slots"][slot] = {
                    "vendor": info.get("vendor"),
                    "product_type": info.get("product_type"),
                    "product_code": info.get("product_code"),
                    "revision": info.get("revision"),
                    "serial": info.get("serial"),
                    "product_name": info.get("product_name"),
                }

        except Exception:
            continue

    return result

def sanitize(obj):
    if isinstance(obj, (bytes, bytearray)):
        return obj.hex()

    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [sanitize(v) for v in obj]

    return obj

if __name__ == "__main__":

    result = enumerate_chassis("125.215.255.49")
    print(json.dumps(sanitize(result), indent=2))



