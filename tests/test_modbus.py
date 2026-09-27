"""Tests for the Peblar Modbus protocol client."""

import asyncio
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "peblar_modbus"
    / "modbus.py"
)
SPEC = importlib.util.spec_from_file_location("peblar_modbus_protocol", MODULE_PATH)
assert SPEC and SPEC.loader
modbus = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = modbus
SPEC.loader.exec_module(modbus)


class DecoderTests(unittest.TestCase):
    """Verify Peblar register decoding."""

    def test_decoders_use_big_endian_words(self) -> None:
        self.assertEqual(modbus.decode_uint32([0x0001, 0x86A0]), 100000)
        self.assertEqual(modbus.decode_int32([0xFFFF, 0xFC18]), -1000)
        self.assertEqual(modbus.decode_int64([0, 0, 0, 1000]), 1000)
        self.assertEqual(modbus.decode_ascii([0x5042, 0x4C52, 0]), "PBLR")


class ClientTests(unittest.IsolatedAsyncioTestCase):
    """Verify Modbus TCP framing against a small fake charger."""

    async def asyncSetUp(self) -> None:
        self.requests: list[tuple[int, int, bytes]] = []
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        socket = self.server.sockets[0]
        self.client = modbus.PeblarModbusClient(
            "127.0.0.1", socket.getsockname()[1], unit_id=255
        )

    async def asyncTearDown(self) -> None:
        self.server.close()
        await self.server.wait_closed()

    async def _handle(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        header = await reader.readexactly(7)
        transaction, protocol, length, unit = struct.unpack(">HHHB", header)
        pdu = await reader.readexactly(length - 1)
        function, payload = pdu[0], pdu[1:]
        self.requests.append((unit, function, payload))
        if function in (3, 4):
            _address, count = struct.unpack(">HH", payload)
            values = list(range(1, count + 1))
            body = bytes([function, count * 2]) + struct.pack(
                f">{count}H", *values
            )
        else:
            address, count = struct.unpack(">HH", payload[:4])
            body = bytes([function]) + struct.pack(">HH", address, count)
        writer.write(
            struct.pack(">HHHB", transaction, protocol, len(body) + 1, unit)
            + body
        )
        await writer.drain()
        writer.close()

    async def test_read_input_registers(self) -> None:
        result = await self.client.read_input_registers(30000, 2)
        self.assertEqual(result, [1, 2])
        self.assertEqual(
            self.requests, [(255, 4, struct.pack(">HH", 30000, 2))]
        )

    async def test_write_current(self) -> None:
        await self.client.set_charge_current(16)
        self.assertEqual(
            self.requests,
            [
                (
                    255,
                    16,
                    struct.pack(">HHBHH", 40000, 2, 4, 0, 16000),
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
