from dataclasses import dataclass
from .revision import Revision



@dataclass
class Identity:
    vendor: str = ""
    product_code: int = 0
    product_type: str = ""
    product_name: str = ""

    revision: Revision = Revision(0, 0)

    serial: str = ""

    status: bytes = b""
