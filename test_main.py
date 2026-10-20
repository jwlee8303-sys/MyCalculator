"""Integration checks for shared initial speed and result-column behavior."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
import math
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from main import MainWindow, DEFAULT_UNITS, DEFAULT_DECIMALS, format_number


class IntegratedDynamoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.addCleanup(self.window.close)
        # Existing calculation scenarios explicitly use their original units.
        for key, unit in {'energy': 'J', 'speed': 'km/h', 'mass': 'kg', 'distance': 'm',
                          'deceleration': 'm/s²', 'radius': 'm', 'torque': 'N·m'}.items():
            self.window.unit_boxes[key].setCurrentText(unit)

    def fill(self, **values):
        for key, value in values.items():
            self.window.fields[key].setText(str(value))
        self.window.calculate()

    def test_shared_speed_and_both_result_directions(self):
        self.fill(speed=36, mass=1000, distance=10)
        self.assertTrue(self.window.result_cells["energy"].text() == "50,000 J")
        self.assertTrue(self.window.result_cells["deceleration"].text() == "5.00 m/s²")
        self.fill(distance="", deceleration=5)
        self.assertTrue(self.window.result_cells["distance"].text() == "10 m")

    def test_calculated_speed_used_for_braking(self):
        self.fill(energy=50000, mass=1000, distance=10)
        self.assertEqual(self.window.result_cells["speed"].text(), "36.00 km/h (62.66 RPM)")
        self.assertTrue(self.window.result_cells["deceleration"].text() == "5.00 m/s²")

    def test_independent_results_and_reset(self):
        self.fill(speed=36, distance=10)
        self.assertNotIn("=", self.window.result.text())
        self.assertTrue(self.window.result_cells["deceleration"].text() == "5.00 m/s²")
        self.window.unit_boxes["deceleration"].setCurrentText("g")
        self.assertNotIn("=", self.window.braking_result.text())
        self.window.calculate()
        self.assertEqual("0.51 g", self.window.result_cells["deceleration"].text())
        self.window.reset_dynamo()
        self.assertTrue(all(not f.text() for f in self.window.fields.values()))
        self.assertNotIn("=", self.window.braking_result.text())

    def test_invalid_braking_does_not_hide_energy(self):
        self.fill(speed=36, mass=1000, distance="bad")
        self.assertTrue(self.window.result_cells["energy"].text() == "50,000 J")
        self.assertNotIn("=", self.window.braking_result.text())

    def test_inputs_preserved_and_echoed_in_results(self):
        self.fill(speed="36.00", mass="1e3", distance="10.0")
        for key, original in {"speed": "36.00", "mass": "1e3", "distance": "10.0"}.items():
            self.assertEqual(self.window.fields[key].text(), original)
            unit = self.window.unit_boxes[key].currentText()
            suffix = ' (62.66 RPM)' if key == 'speed' else ''
            number = format_number(float(original), self.window.decimal_boxes[key].value())
            self.assertEqual(self.window.result_cells[key].text(), f"{number} {unit}{suffix}")
        self.assertEqual(self.window.fields["energy"].text(), "")
        self.assertEqual(self.window.fields["deceleration"].text(), "")
        self.assertEqual(self.window.result_cells["energy"].text(), "50,000 J")
        self.assertEqual(self.window.result_cells["deceleration"].text(), "5.00 m/s²")
        self.window.fields["speed"].setText("72")
        self.assertTrue(all(cell.text() == "—" for cell in self.window.result_cells.values()))
        self.window.calculate()
        self.assertEqual(self.window.result_cells["energy"].text(), "200,000 J")
        self.window.reset_dynamo()
        self.assertTrue(all(cell.text() == "—" for cell in self.window.result_cells.values()))

    def test_result_column_alignment(self):
        self.window.show()
        self.app.processEvents()
        for key in self.window.fields:
            cell = self.window.result_cells[key]
            unit = self.window.unit_boxes[key]
            self.assertGreater(cell.x(), unit.geometry().right())
            self.assertLessEqual(abs(cell.geometry().center().y() - unit.geometry().center().y()), 1)

    def test_torque_four_directions_without_purple_formula(self):
        reference = {"mass": 1000, "deceleration": 5, "radius": 0.3, "torque": 1500}
        for target in reference:
            with self.subTest(target=target):
                self.window.reset_dynamo()
                self.fill(**{k: v for k, v in reference.items() if k != target})
                self.assertEqual(self.window.fields[target].text(), "")
                unit = self.window.unit_boxes[target].currentText()
                number = format_number(reference[target], self.window.decimal_boxes[target].value())
                self.assertEqual(self.window.result_cells[target].text(), f"{number} {unit}")
                self.assertEqual('', self.window.torque_result.text())
                self.assertTrue(self.window.torque_result.isHidden())

    def test_torque_uses_calculated_deceleration_and_converts_units(self):
        self.window.decimal_boxes['torque'].setValue(9)
        self.window.unit_boxes["radius"].setCurrentText("mm")
        self.window.unit_boxes["torque"].setCurrentText("kgf·m")
        self.fill(speed=36, mass=1000, distance=10, radius=300)
        self.assertAlmostEqual(float(self.window.result_cells["torque"].text().split()[0]), 1500 / 9.80665)
        self.window.fields["radius"].setText("400")
        self.assertEqual(self.window.torque_result.text(), "")
        self.assertTrue(all(cell.text() == "—" for cell in self.window.result_cells.values()))

    def test_torque_mass_feeds_energy_and_invalid_radius_preserves_energy(self):
        self.fill(speed=36, deceleration=5, radius=0.3, torque=1500)
        self.assertEqual(self.window.result_cells["mass"].text(), "1,000 kg")
        self.assertEqual(self.window.result_cells["energy"].text(), "50,000 J")
        self.fill(mass=1000, radius="bad", torque="")
        self.assertEqual(self.window.result_cells["energy"].text(), "50,000 J")
        self.assertIn("올바른 숫자", self.window.torque_result.text())

    def test_torque_rejects_invalid_and_overdetermined_inputs(self):
        self.fill(mass=1000, deceleration=5, radius=0)
        self.assertEqual(self.window.result_cells["torque"].text(), "—")
        self.assertIn("양수", self.window.torque_result.text())
        self.fill(radius=0.3, torque=1500)
        self.assertIn("세 개만", self.window.torque_result.text())

    def test_units_recalculate_immediately(self):
        self.window.decimal_boxes['torque'].setValue(6)
        self.fill(speed=36, mass=1000, distance=10, radius=0.3)
        self.window.unit_boxes['energy'].setCurrentText('kJ')
        self.assertEqual(self.window.result_cells['energy'].text(), '50 kJ')
        self.window.unit_boxes['torque'].setCurrentText('kgf·m')
        self.assertIn('152.957', self.window.result_cells['torque'].text())
        self.window.unit_boxes['radius'].setCurrentText('cm')
        self.assertEqual(self.window.fields['radius'].text(), '0.3')
        self.assertIn('1.52957', self.window.result_cells['torque'].text())

    def test_drum_rpm_for_every_speed_unit_and_fixed_diameter(self):
        from dynamo import UNITS
        # One drum revolution per second must read 60 RPM for every speed unit.
        circumference = math.pi * 3.048
        for unit, factor in UNITS['speed'].items():
            with self.subTest(unit=unit):
                self.window.unit_boxes['speed'].setCurrentText(unit)
                self.fill(speed=circumference / factor, mass=1000, radius=0.1)
                self.assertTrue(self.window.result_cells['speed'].text().endswith(' (60.00 RPM)'))
        self.window.unit_boxes['radius'].setCurrentText('in')
        self.assertTrue(self.window.result_cells['speed'].text().endswith(' (60.00 RPM)'))
        self.window.unit_boxes['speed'].setCurrentText('km/h')
        self.fill(speed=36)
        self.assertEqual(self.window.result_cells['speed'].text(), '36.00 km/h (62.66 RPM)')
        self.window.unit_boxes['speed'].setCurrentText('m/s')
        self.assertEqual(self.window.result_cells['speed'].text(), '36.00 m/s (225.57 RPM)')

    def test_drum_rpm_zero_invalid_and_clear(self):
        self.fill(speed=0, mass=1000)
        self.assertEqual(self.window.result_cells['speed'].text(), '0.00 km/h (0.00 RPM)')
        for speed in ('bad', '-1', 'nan', 'inf'):
            self.fill(speed=speed)
            self.assertNotIn('RPM', self.window.result_cells['speed'].text())
        self.window.fields['speed'].setText('36')
        self.assertEqual(self.window.result_cells['speed'].text(), '—')
        self.window.reset_dynamo()
        self.assertEqual(self.window.result_cells['speed'].text(), '—')

    def test_click_guidance_blinks_and_dismisses(self):
        self.window.show()
        self.app.processEvents()
        QTest.mouseClick(self.window.result_cells['torque'], Qt.MouseButton.LeftButton)
        self.assertEqual(set(self.window.guide_dependencies), {'mass', 'deceleration', 'radius'})
        self.assertTrue(self.window.pulse_timer.isActive())
        self.assertIn('T = m × a × r', self.window.guide_formula.text())
        first = self.window.fields['mass'].property('requiredPulse')
        QTest.qWait(600)
        self.assertNotEqual(self.window.fields['mass'].property('requiredPulse'), first)
        QTest.mouseClick(self.window.result_cells['torque'], Qt.MouseButton.LeftButton)
        self.assertFalse(self.window.pulse_timer.isActive())
        self.assertEqual(self.window.fields['mass'].property('requiredPulse'), 0)
        self.assertTrue(self.window.guide_formula.isHidden())
        QTest.mouseClick(self.window.name_cells['energy'], Qt.MouseButton.LeftButton)
        self.assertEqual(set(self.window.guide_dependencies), {'mass', 'speed'})
        QTest.mouseClick(self.window.fields['distance'], Qt.MouseButton.LeftButton)
        self.assertIsNone(self.window.guide_target)
        self.assertFalse(self.window.pulse_timer.isActive())

    def test_guidance_chooses_torque_inverse_and_switches_target(self):
        self.fill(torque=1500, radius=0.3, deceleration=5)
        QTest.mouseClick(self.window.name_cells['mass'], Qt.MouseButton.LeftButton)
        self.assertEqual(set(self.window.guide_dependencies), {'torque', 'radius', 'deceleration'})
        QTest.mouseClick(self.window.result_cells['radius'], Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.guide_target, 'radius')
        self.assertEqual(self.window.fields['radius'].property('requiredPulse'), 0)
        self.window.reset_dynamo()
        self.assertIsNone(self.window.guide_target)

    def test_requested_defaults_and_spinbox_position(self):
        window = MainWindow()
        self.addCleanup(window.close)
        window.show()
        self.app.processEvents()
        for key in DEFAULT_UNITS:
            self.assertEqual(window.unit_boxes[key].currentText(), DEFAULT_UNITS[key])
            self.assertEqual(window.decimal_boxes[key].value(), DEFAULT_DECIMALS[key])
            self.assertGreater(window.decimal_boxes[key].x(), window.result_cells[key].geometry().right())
        window.fields['speed'].setText('10')
        window.fields['mass'].setText('1000')
        window.calculate()
        self.assertEqual(window.result_cells['speed'].text(), '10.00 ft/s (19.10 RPM)')
        self.assertEqual(window.result_cells['energy'].text(), '0 MJ')
        window.decimal_boxes['energy'].setValue(6)
        self.assertEqual(window.result_cells['energy'].text(), '0.002107 MJ')

    def test_half_up_precision_changes_keep_full_calculation_values(self):
        self.assertEqual(format_number(2.5, 0), '3')
        self.assertEqual(format_number(1.25, 1), '1.3')
        self.assertEqual(format_number(1.005, 2), '1.01')
        self.fill(mass=2.5, deceleration=1, radius=1)
        self.assertEqual(self.window.result_cells['mass'].text(), '3 kg')
        self.assertEqual(self.window.result_cells['torque'].text(), '3 N·m')
        self.window.decimal_boxes['torque'].setValue(2)
        self.assertEqual(self.window.result_cells['torque'].text(), '2.50 N·m')
        self.assertEqual(self.window.fields['mass'].text(), '2.5')
        self.window.decimal_boxes['mass'].setValue(1)
        self.assertEqual(self.window.result_cells['mass'].text(), '2.5 kg')
        self.assertEqual(self.window.result_cells['torque'].text(), '2.50 N·m')
        self.fill(speed=36, mass=1000)
        self.window.decimal_boxes['speed'].setValue(0)
        self.assertEqual(self.window.result_cells['speed'].text(), '36 km/h (63 RPM)')


if __name__ == "__main__":
    unittest.main()
