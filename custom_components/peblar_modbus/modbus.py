"""Small asynchronous Modbus TCP client for Peblar chargers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import struct
from typing import Final

_READ_HOLDING_REGISTERS: Final = 3
_READ_INPUT_REGISTERS: Final = 4
_WRITE_SINGLE_REGISTER: Final = 6
_WRITE_MULTIPLE_REGISTERS: Final = 16


class PeblarModbusError(Exception):
    """Base exception for Peblar Modbus communication."""


class PeblarModbusConnectionError(PeblarModbusError):
    """Raised when the charger cannot be reached."""


class PeblarModbusResponseError(PeblarModbusError):
    """Raised when the charger sends an invalid or exception response."""


@dataclass(frozen=True, slots=True)
class PeblarInfo:
    """Static information read from a Peblar charger."""

    serial_number: str
    product_number: str
    firmware_version: str
    phase_count: int
    independent_relays: bool
    api_version: str


def decode_ascii(registers: list[int]) -> str:
    """Decode an ASCII string stored in big-endian registers."""
    return b"".join(value.to_bytes(2, "big") for value in registers).decode(
        "ascii", errors="replace"
    ).strip("\x00 ")


def decode_int32(registers: list[int]) -> int:
    """Decode a signed 32-bit big-endian register value."""
    return int.from_bytes(_register_bytes(registers), "big", signed=True)


def decode_uint32(registers: list[int]) -> int:
    """Decode an unsigned 32-bit big-endian register value."""
    return int.from_bytes(_register_bytes(registers), "big")


def decode_int64(registers: list[int]) -> int:
    """Decode a signed 64-bit big-endian register value."""
    return int.from_bytes(_register_bytes(registers), "big", signed=True)


def _register_bytes(registers: list[int]) -> bytes:
    return b"".join(value.to_bytes(2, "big") for value in registers)


class PeblarModbusClient:
    """Communicate with one Peblar charger over Modbus TCP."""

    def __init__(
        self,
        host: str,
        port: int = 502,
        unit_id: int = 1,
        timeout: float = 5,
    ) -> None:
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self._lock = asyncio.Lock()
        self._transaction_id = 0

    async def read_input_registers(self, address: int, count: int) -> list[int]:
        """Read input registers with Modbus function code 4."""
        return await self._read_registers(_READ_INPUT_REGISTERS, address, count)

    async def read_holding_registers(self, address: int, count: int) -> list[int]:
        """Read holding registers with Modbus function code 3."""
        return await self._read_registers(_READ_HOLDING_REGISTERS, address, count)

    async def write_holding_registers(
        self, address: int, values: list[int]
    ) -> None:
        """Write one or more holding registers with function code 16."""
        if not values:
            raise ValueError("At least one register value is required")
        if len(values) > 123:
            raise ValueError("Cannot write more than 123 registers")
        if any(not 0 <= value <= 0xFFFF for value in values):
            raise ValueError("Register values must be between 0 and 65535")
        payload = (
            struct.pack(">HHB", address, len(values), len(values) * 2)
            + b"".join(struct.pack(">H", value) for value in values)
        )
        response = await self._request(_WRITE_MULTIPLE_REGISTERS, payload)
        if response != struct.pack(">HH", address, len(values)):
            raise PeblarModbusResponseError("Unexpected write response")

    async def write_holding_register(self, address: int, value: int) -> None:
        """Write one holding register with function code 6."""
        if not 0 <= value <= 0xFFFF:
            raise ValueError("Register value must be between 0 and 65535")
        payload = struct.pack(">HH", address, value)
        response = await self._request(_WRITE_SINGLE_REGISTER, payload)
        if response != payload:
            raise PeblarModbusResponseError("Unexpected write response")

    async def read_information(self) -> PeblarInfo:
        """Read static charger information."""
        serial_number, product_number, firmware_version = await asyncio.gather(
            self.read_input_registers(30050, 12),
            self.read_input_registers(30062, 12),
            self.read_input_registers(30074, 12),
        )
        phase_count = (await self.read_input_registers(30092, 1))[0]
        independent_relays = (await self.read_input_registers(30093, 1))[0]
        if phase_count not in (1, 2, 3):
            raise PeblarModbusResponseError(
                f"Charger reported invalid phase count {phase_count}"
            )
        if independent_relays not in (0, 1):
            raise PeblarModbusResponseError(
                f"Charger reported invalid relay mode {independent_relays}"
            )
        try:
            api = await self.read_input_registers(30123, 2)
            api_version = f"{api[0]}.{api[1]}"
        except PeblarModbusResponseError:
            # API version registers are metadata and are absent on some
            # otherwise compatible firmware versions.
            api_version = "unknown"

        serial = decode_ascii(serial_number)
        if not serial:
            raise PeblarModbusResponseError("Charger returned an empty serial number")
        return PeblarInfo(
            serial_number=serial,
            product_number=decode_ascii(product_number),
            firmware_version=decode_ascii(firmware_version),
            phase_count=phase_count,
            independent_relays=independent_relays == 1,
            api_version=api_version,
        )

    async def read_data(self, phase_count: int) -> dict[str, object]:
        """Read dynamic charger data."""
        energy, total_power, diagnostics, status, ev, control = await asyncio.gather(
            self.read_input_registers(30000, 8),
            self.read_input_registers(30014, 2),
            self.read_input_registers(30086, 8),
            self.read_input_registers(30100, 10),
            self.read_input_registers(30110, 5),
            self.read_holding_registers(40000, 3),
        )

        data: dict[str, object] = {
            "energy_total": decode_int64(energy[0:4]),
            "energy_session": decode_int64(energy[4:8]),
            "power_total": decode_int32(total_power),
            "wlan_signal_strength": decode_int32(diagnostics[0:2]),
            "cellular_signal_strength": decode_int32(diagnostics[2:4]),
            "uptime": decode_uint32(diagnostics[4:6]),
            "warnings": tuple(value for value in status[0:5] if value),
            "errors": tuple(value for value in status[5:10] if value),
            "cp_state": decode_ascii(ev[0:1]),
            "lock_state": ev[1] == 1,
            "current_limit_source": ev[2],
            "current_limit_actual": decode_uint32(ev[3:5]) / 1000,
            "charge_current_limit": decode_uint32(control[0:2]) / 1000,
            "force_single_phase": control[2] == 1,
        }

        phase_registers = (
            ("power", 30008, 1),
            ("voltage", 30016, 1),
            ("current", 30022, 0.001),
        )
        for name, address, scale in phase_registers:
            registers = await self.read_input_registers(address, phase_count * 2)
            for phase in range(phase_count):
                start = phase * 2
                data[f"{name}_phase_{phase + 1}"] = (
                    decode_int32(registers[start : start + 2]) * scale
                )
        return data

    async def set_charge_current(self, amperes: float) -> None:
        """Set the Modbus current limit in amperes."""
        milliamperes = round(amperes * 1000)
        if milliamperes < 0 or milliamperes > 32000:
            raise ValueError("Charge current must be between 0 and 32 A")
        await self.write_holding_registers(
            40000, [(milliamperes >> 16) & 0xFFFF, milliamperes & 0xFFFF]
        )

    async def set_force_single_phase(self, enabled: bool) -> None:
        """Enable or disable forced single-phase charging."""
        await self.write_holding_register(40002, int(enabled))

    async def _read_registers(
        self, function_code: int, address: int, count: int
    ) -> list[int]:
        if not 1 <= count <= 125:
            raise ValueError("Register count must be between 1 and 125")
        response = await self._request(
            function_code, struct.pack(">HH", address, count)
        )
        if (
            not response
            or response[0] != count * 2
            or len(response) != count * 2 + 1
        ):
            raise PeblarModbusResponseError("Unexpected register response length")
        return list(struct.unpack(f">{count}H", response[1:]))

    async def _request(self, function_code: int, payload: bytes) -> bytes:
        async with self._lock:
            self._transaction_id = (self._transaction_id + 1) & 0xFFFF
            transaction_id = self._transaction_id
            pdu = bytes([function_code]) + payload
            request = struct.pack(
                ">HHHB", transaction_id, 0, len(pdu) + 1, self.unit_id
            ) + pdu
            writer: asyncio.StreamWriter | None = None
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), self.timeout
                )
                writer.write(request)
                await asyncio.wait_for(writer.drain(), self.timeout)
                header = await asyncio.wait_for(reader.readexactly(7), self.timeout)
                response_transaction, protocol, length, unit_id = struct.unpack(
                    ">HHHB", header
                )
                if not 2 <= length <= 254:
                    raise PeblarModbusResponseError(
                        f"Invalid Modbus TCP response length {length}"
                    )
                response_pdu = await asyncio.wait_for(
                    reader.readexactly(length - 1), self.timeout
                )
            except (OSError, TimeoutError, asyncio.IncompleteReadError) as err:
                raise PeblarModbusConnectionError(
                    f"Unable to communicate with {self.host}:{self.port}"
                ) from err
            finally:
                if writer is not None:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except OSError:
                        pass

            if (
                response_transaction != transaction_id
                or protocol != 0
                or unit_id != self.unit_id
                or not response_pdu
            ):
                raise PeblarModbusResponseError("Invalid Modbus TCP response header")
            response_function = response_pdu[0]
            if response_function == function_code | 0x80:
                code = response_pdu[1] if len(response_pdu) > 1 else -1
                raise PeblarModbusResponseError(
                    f"Modbus exception {code} for function {function_code}"
                )
            if response_function != function_code:
                raise PeblarModbusResponseError(
                    f"Unexpected Modbus function {response_function}"
                )
            return response_pdu[1:]
