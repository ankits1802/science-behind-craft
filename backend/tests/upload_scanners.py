from __future__ import annotations

from dataclasses import dataclass, field

from app.services.malware_scan import DOWN, ScannerDown

__all__ = ["EICAR", "EICAR_SIGNATURE", "ScriptedScanner"]

EICAR = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + "EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
EICAR_SIGNATURE = "Eicar-Test-Signature"


@dataclass
class ScriptedScanner:
    down: bool = False
    scanned: list[bytes] = field(default_factory=list)

    async def scan(self, data: bytes) -> str | None:
        if self.down:
            raise ScannerDown(DOWN)
        self.scanned.append(data)
        return EICAR_SIGNATURE if EICAR.encode("ascii") in data else None
