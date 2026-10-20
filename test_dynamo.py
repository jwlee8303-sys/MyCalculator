import math
import unittest

from dynamo import BRAKING_UNITS, UNITS, TORQUE_UNITS, solve, solve_braking, solve_torque


class DynamoTests(unittest.TestCase):
    def test_all_targets_and_units(self):
        reference = {"energy": 50000.0, "speed": 10.0, "mass": 1000.0}
        for target in reference:
            for key in UNITS:
                for unit in UNITS[key]:
                    units = {k: next(iter(UNITS[k])) for k in UNITS}
                    units[key] = unit
                    values = {k: v / UNITS[k][units[k]] for k, v in reference.items()}
                    values[target] = None
                    result_key, result = solve(values, units)
                    self.assertEqual(result_key, target)
                    self.assertTrue(math.isclose(result * UNITS[target][units[target]], reference[target]))

    def test_known_conversion(self):
        _, result = solve({"energy": None, "speed": 36, "mass": 1},
                          {"energy": "kJ", "speed": "km/h", "mass": "t"})
        self.assertAlmostEqual(result, 50)

    def test_foot_pound_energy(self):
        units = {"energy": "ft-lbf", "speed": "m/s", "mass": "kg"}
        _, result = solve({"speed": 1, "mass": 2 * 1.3558179483314004}, units)
        self.assertAlmostEqual(result, 1)
        _, speed = solve({"energy": 1, "mass": 2 * 1.3558179483314004}, units)
        self.assertAlmostEqual(speed, 1)

    def test_invalid_and_ambiguous_inputs(self):
        units = {k: next(iter(UNITS[k])) for k in UNITS}
        for values in (
            {}, {"energy": 1, "speed": 1, "mass": 1},
            {"speed": -1, "mass": 1}, {"speed": float("nan"), "mass": 1},
            {"speed": float("inf"), "mass": 1},
            {"energy": 0, "mass": 0}, {"energy": 1, "speed": 0},
            {"speed": 1e308, "mass": 1e308},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                solve(values, units)

    def test_zero_energy(self):
        units = {k: next(iter(UNITS[k])) for k in UNITS}
        self.assertEqual(solve({"energy": 0, "mass": 10}, units), ("speed", 0))


class BrakingTests(unittest.TestCase):
    def test_both_directions_and_all_units(self):
        reference = {"speed": 10.0, "distance": 10.0, "deceleration": 5.0}
        for target in ("distance", "deceleration"):
            for quantity, options in BRAKING_UNITS.items():
                for unit in options:
                    units = {k: next(iter(v)) for k, v in BRAKING_UNITS.items()}
                    units[quantity] = unit
                    values = {k: v / BRAKING_UNITS[k][units[k]] for k, v in reference.items()}
                    values[target] = None
                    key, result = solve_braking(values, units)
                    self.assertEqual(key, target)
                    self.assertAlmostEqual(result * BRAKING_UNITS[target][units[target]], reference[target])

    def test_gravity_unit(self):
        _, value = solve_braking({"speed": 36, "distance": 10},
                                 {"speed": "km/h", "distance": "m", "deceleration": "g"})
        self.assertAlmostEqual(value, 5 / 9.80665)

    def test_invalid_inputs(self):
        units = {k: next(iter(v)) for k, v in BRAKING_UNITS.items()}
        for values in ({}, {"speed": 10}, {"speed": 10, "distance": 10, "deceleration": 5},
                       {"speed": 0, "distance": 10}, {"speed": -10, "distance": 10},
                       {"speed": 10, "distance": 0}, {"speed": 10, "deceleration": -1},
                       {"speed": float("nan"), "distance": 10},
                       {"speed": 10, "distance": float("inf")},
                       {"speed": 1e308, "distance": 10}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                solve_braking(values, units)


class TorqueTests(unittest.TestCase):
    def test_all_targets_and_units(self):
        reference = {"mass": 1000.0, "deceleration": 5.0, "radius": 0.3, "torque": 1500.0}
        for target in reference:
            for quantity, options in TORQUE_UNITS.items():
                for unit in options:
                    with self.subTest(target=target, quantity=quantity, unit=unit):
                        units = {k: next(iter(v)) for k, v in TORQUE_UNITS.items()}
                        units[quantity] = unit
                        values = {k: v / TORQUE_UNITS[k][units[k]] for k, v in reference.items()}
                        values[target] = None
                        key, result = solve_torque(values, units)
                        self.assertEqual(key, target)
                        self.assertAlmostEqual(result * TORQUE_UNITS[target][units[target]], reference[target])

    def test_kgf_torque_and_gravity_acceleration(self):
        units = {"mass": "kg", "deceleration": "g", "radius": "mm", "torque": "kgf·m"}
        self.assertAlmostEqual(solve_torque({"mass": 1000, "deceleration": 1, "radius": 300}, units)[1], 300)

    def test_invalid_inputs(self):
        units = {k: next(iter(v)) for k, v in TORQUE_UNITS.items()}
        for values in ({}, {"mass": 1000, "radius": 0.3},
                       {"mass": 1000, "deceleration": 5, "radius": 0.3, "torque": 1500},
                       {"mass": 0, "deceleration": 5, "radius": 0.3},
                       {"mass": 1000, "deceleration": -5, "radius": 0.3},
                       {"mass": 1000, "deceleration": 5, "radius": float("nan")},
                       {"mass": 1e308, "deceleration": 5, "radius": 1e308},
                       {"torque": 1500, "mass": 1e-300, "radius": 1e-300}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                solve_torque(values, units)


if __name__ == "__main__":
    unittest.main()
