import unittest

from btle2opcua.inkbird import parse_inkbird


class ParseInkbirdTests(unittest.TestCase):
    def test_parses_sps_reading(self) -> None:
        reading = parse_inkbird(
            {0x089C: bytes.fromhex("f41000ba4e6408")},
            name="sps",
        )

        self.assertIsNotNone(reading)
        assert reading is not None
        self.assertEqual(reading.temperature, 22.04)
        self.assertEqual(reading.humidity, 43.4)
        self.assertEqual(reading.battery_percent, 100)

    def test_ignores_other_names_and_malformed_data(self) -> None:
        payload = {0x089C: bytes.fromhex("f41000ba4e6408")}
        self.assertIsNone(parse_inkbird(payload, name="other"))
        self.assertIsNone(parse_inkbird({0x089C: b"short"}, name="sps"))


if __name__ == "__main__":
    unittest.main()