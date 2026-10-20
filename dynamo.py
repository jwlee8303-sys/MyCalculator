"""Kinetic energy calculations; unit factors convert to J, m/s and kg."""
import math

UNITS = {
    "energy": {"J": 1.0, "kJ": 1000.0, "MJ": 1e6, "Wh": 3600.0,
               "kWh": 3.6e6, "ft-lbf": 1.3558179483314004,
               "cal (열화학)": 4.184, "kcal (열화학)": 4184.0},
    "speed": {"m/s": 1.0, "km/h": 1 / 3.6, "mph": 0.44704,
              "ft/s": 0.3048, "kn": 1852 / 3600},
    "mass": {"kg": 1.0, "g": 0.001, "t": 1000.0, "lb": 0.45359237},
}

BRAKING_UNITS = {
    "speed": UNITS["speed"],
    "distance": {"m": 1.0, "cm": 0.01, "mm": 0.001, "km": 1000.0,
                 "ft": 0.3048, "in": 0.0254, "yd": 0.9144},
    "deceleration": {"m/s²": 1.0, "g": 9.80665, "km/h/s": 1 / 3.6,
                     "ft/s²": 0.3048, "mph/s": 0.44704, "cm/s²": 0.01},
}


def solve_braking(values, units):
    """Constant deceleration from a positive initial speed to rest, no reaction time."""
    if values.get("speed") is None:
        raise ValueError("초기속도를 입력해 주세요.")
    missing = [key for key in ("distance", "deceleration") if values.get(key) is None]
    if len(missing) != 1:
        raise ValueError("제동거리와 감속도 중 한 개만 입력하고, 계산할 항목은 비워 주세요.")
    si = {}
    for key in BRAKING_UNITS:
        if values.get(key) is None:
            continue
        number = float(values[key]) * BRAKING_UNITS[key][units[key]]
        if not math.isfinite(number) or number <= 0:
            raise ValueError("초기속도, 제동거리, 감속도는 유한한 양수로 입력해 주세요.")
        si[key] = number
    target = missing[0]
    known = "deceleration" if target == "distance" else "distance"
    try:
        result = si["speed"] ** 2 / (2 * si[known])
        result /= BRAKING_UNITS[target][units[target]]
    except (OverflowError, ZeroDivisionError):
        raise ValueError("계산 가능한 숫자 범위를 벗어났습니다.") from None
    if not math.isfinite(result) or result <= 0:
        raise ValueError("계산 가능한 숫자 범위를 벗어났습니다.")
    return target, result


def solve(values, units):
    """Return (missing quantity, result in its selected unit)."""
    missing = [key for key in UNITS if values.get(key) is None]
    if len(missing) != 1:
        raise ValueError("세 항목 중 두 개만 입력하고, 계산할 항목은 비워 주세요.")
    si = {}
    for key in UNITS:
        if values.get(key) is None:
            continue
        value = float(values[key]) * UNITS[key][units[key]]
        if not math.isfinite(value) or value < 0:
            raise ValueError("유한한 0 이상의 숫자를 입력해 주세요.")
        si[key] = value
    target = missing[0]
    try:
        if target == "energy":
            result = 0.5 * si["mass"] * si["speed"] ** 2
        elif target == "speed":
            if si["mass"] == 0:
                raise ValueError("속도를 계산하려면 등가관성중량이 0보다 커야 합니다.")
            result = math.sqrt(2 * si["energy"] / si["mass"])
        else:
            if si["speed"] == 0:
                raise ValueError("등가관성중량을 계산하려면 속도가 0보다 커야 합니다.")
            result = 2 * si["energy"] / si["speed"] ** 2
        result /= UNITS[target][units[target]]
    except (OverflowError, ZeroDivisionError):
        raise ValueError("계산 가능한 숫자 범위를 벗어났습니다.") from None
    if not math.isfinite(result) or (result == 0 and all(v > 0 for v in si.values())):
        raise ValueError("계산 가능한 숫자 범위를 벗어났습니다.")
    return target, result
