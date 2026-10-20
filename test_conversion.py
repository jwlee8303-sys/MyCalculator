"""Reference conversions and integration checks for the conversion tab."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

import unittest
from PySide6.QtWidgets import QApplication
from conversion import CONVERSION_UNITS, convert_value
from main import MainWindow


class ConversionTests(unittest.TestCase):
    def test_reference_values(self):
        cases = [('speed', 36, 'km/h', 'm/s', 10),
                 ('pressure', 1, 'atm', 'Pa', 101325),
                 ('pressure', 1, 'bar', 'psi', 14.503773773),
                 ('pressure', 1, 'kgf/cm²', 'kPa', 98.0665),
                 ('mass', 1, 'lbs', 'kg', 0.45359237),
                 ('length', 1, 'in', 'mm', 25.4),
                 ('torque', 1, 'lbf·in', 'N·m', 0.1129848290276167),
                 ('energy', 1, 'kWh', 'J', 3600000),
                 ('temperature', 0, '°C', '°F', 32),
                 ('temperature', 212, '°F', '°C', 100),
                 ('temperature', -40, '°C', '°F', -40),
                 ('temperature', 0, 'K', '°C', -273.15),
                 ('temperature', 32, '°F', 'K', 273.15)]
        for category, value, source, target, expected in cases:
            with self.subTest(category=category, source=source, target=target):
                self.assertAlmostEqual(convert_value(category, value, source, target), expected)

    def test_every_unit_round_trip(self):
        for category, options in CONVERSION_UNITS.items():
            for source in options:
                for target in options:
                    with self.subTest(category=category, source=source, target=target):
                        converted = convert_value(category, 123.45, source, target)
                        self.assertAlmostEqual(convert_value(category, converted, target, source), 123.45)

    def test_invalid_values(self):
        for number in ('bad', 'nan', 'inf', '-inf'):
            with self.assertRaises(ValueError):
                convert_value('speed', number, 'km/h', 'm/s')
        for unit, value in [('K', -1), ('°C', -274), ('°F', -460)]:
            with self.assertRaises(ValueError):
                convert_value('temperature', value, unit, 'K')
        with self.assertRaises(ValueError):
            convert_value('pressure', 1e308, 'MPa', 'Pa')


class ConversionTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.addCleanup(self.window.close)

    def test_two_independent_rows_in_every_category(self):
        self.assertEqual(len(self.window.conversion_rows), 7)
        for category, rows in self.window.conversion_rows.items():
            self.assertEqual(len(rows), 2)
            rows[0]['input'].setText('10')
            self.assertTrue(rows[0]['result'].text())
            self.assertEqual(rows[1]['result'].text(), '')
            self.assertTrue(rows[0]['result'].isReadOnly())

    def test_units_and_global_precision_update_immediately(self):
        rows = self.window.conversion_rows
        length = rows['length'][0]
        length['input'].setText('1.25')
        self.assertEqual(length['result'].text(), '31.75')
        temperature = rows['temperature'][0]
        temperature['input'].setText('0')
        self.assertEqual(temperature['result'].text(), '32.00')
        for category, pairs in rows.items():
            for pair in pairs:
                pair['input'].setText('1.25')
        self.window.conversion_decimals.setValue(1)
        self.assertEqual(length['result'].text(), '31.8')
        for pairs in rows.values():
            for pair in pairs:
                self.assertEqual(len(pair['result'].text().split('.')[1]), 1)
        length['target'].setCurrentText('cm')
        self.assertEqual(length['result'].text(), '3.2')
        length['source'].setCurrentText('ft')
        self.assertEqual(length['result'].text(), '38.1')
        self.assertEqual(length['input'].text(), '1.25')
        self.assertEqual(self.window.decimal_boxes['speed'].value(), 2)

    def test_invalid_and_empty_clear_stale_result(self):
        row = self.window.conversion_rows['temperature'][0]
        row['input'].setText('0')
        self.assertEqual(row['result'].text(), '32.00')
        for value in ('bad', 'inf', '-274'):
            row['input'].setText(value)
            self.assertEqual(row['result'].text(), '')
            self.assertTrue(row['result'].toolTip())
        row['input'].clear()
        self.assertEqual(row['result'].text(), '')
        self.assertEqual(row['result'].toolTip(), '')
        row['input'].setText('100')
        self.assertEqual(row['result'].text(), '212.00')


if __name__ == '__main__':
    unittest.main()
