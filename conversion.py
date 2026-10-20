"""Unit conversions, using SI factors and explicit temperature offsets."""
import math

from dynamo import UNITS, BRAKING_UNITS, TORQUE_UNITS


CONVERSION_UNITS = {
    'speed': UNITS['speed'],
    'pressure': {'Pa': 1.0, 'kPa': 1000.0, 'MPa': 1e6, 'bar': 1e5, 'mbar': 100.0,
                 'psi': 6894.757293168, 'atm': 101325.0, 'kgf/cm²': 98066.5,
                 'Torr': 101325 / 760},
    'mass': UNITS['mass'],
    'length': BRAKING_UNITS['distance'],
    'torque': TORQUE_UNITS['torque'],
    'energy': UNITS['energy'],
    'temperature': {'°C': None, '°F': None, 'K': None},
}

CONVERSION_NAMES = {'speed': '속도', 'pressure': '압력', 'mass': '질량',
                    'length': '길이', 'torque': '토크', 'energy': '에너지', 'temperature': '온도'}

CONVERSION_DEFAULTS = {
    'speed': [('km/h', 'm/s'), ('ft/s', 'mph')],
    'pressure': [('MPa', 'psi'), ('bar', 'kgf/cm²')],
    'mass': [('kg', 'lbs'), ('g', 'kg')],
    'length': [('in', 'mm'), ('ft', 'm')],
    'torque': [('N·m', 'lbf·in'), ('kgf·m', 'N·m')],
    'energy': [('J', 'MJ'), ('kWh', 'kJ')],
    'temperature': [('°C', '°F'), ('°C', 'K')],
}


def convert_value(category, value, source, target):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('유한한 숫자를 입력해 주세요.')
    if category == 'temperature':
        if source == '°C':
            celsius = number
        elif source == '°F':
            celsius = (number - 32) / 1.8
        else:
            celsius = number - 273.15
        if celsius < -273.15 - 1e-10:
            raise ValueError('절대영도보다 낮은 온도입니다.')
        celsius = max(celsius, -273.15)
        if target == '°C':
            result = celsius
        elif target == '°F':
            result = celsius * 1.8 + 32
        else:
            result = celsius + 273.15
    else:
        factors = CONVERSION_UNITS[category]
        result = number * (factors[source] / factors[target])
    if not math.isfinite(result):
        raise ValueError('계산 가능한 숫자 범위를 벗어났습니다.')
    return result
