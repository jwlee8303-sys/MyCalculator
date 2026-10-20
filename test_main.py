"""Integration checks for shared initial speed and result-column behavior."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
from PySide6.QtWidgets import QApplication
from main import MainWindow


class IntegratedDynamoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = MainWindow()
        self.addCleanup(self.window.close)

    def fill(self, **values):
        for key, value in values.items():
            self.window.fields[key].setText(str(value))
        self.window.calculate()

    def test_shared_speed_and_both_result_directions(self):
        self.fill(speed=36, mass=1000, distance=10)
        self.assertTrue(self.window.result_cells["energy"].text() == "50,000 J")
        self.assertTrue(self.window.result_cells["deceleration"].text() == "5 m/s²")
        self.fill(distance="", deceleration=5)
        self.assertTrue(self.window.result_cells["distance"].text() == "10 m")

    def test_calculated_speed_used_for_braking(self):
        self.fill(energy=50000, mass=1000, distance=10)
        self.assertTrue(self.window.result_cells["speed"].text() == "36 km/h")
        self.assertTrue(self.window.result_cells["deceleration"].text() == "5 m/s²")

    def test_independent_results_and_reset(self):
        self.fill(speed=36, distance=10)
        self.assertNotIn("=", self.window.result.text())
        self.assertTrue(self.window.result_cells["deceleration"].text() == "5 m/s²")
        self.window.unit_boxes["deceleration"].setCurrentText("g")
        self.assertNotIn("=", self.window.braking_result.text())
        self.window.calculate()
        self.assertIn("0.509858", self.window.result_cells["deceleration"].text())
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
            self.assertEqual(self.window.result_cells[key].text(), f"{original} {unit}")
        self.assertEqual(self.window.fields["energy"].text(), "")
        self.assertEqual(self.window.fields["deceleration"].text(), "")
        self.assertEqual(self.window.result_cells["energy"].text(), "50,000 J")
        self.assertEqual(self.window.result_cells["deceleration"].text(), "5 m/s²")
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
            self.assertEqual(cell.geometry().center().y(), unit.geometry().center().y())


if __name__ == "__main__":
    unittest.main()
