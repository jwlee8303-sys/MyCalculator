"""PySide6 application with dynamo and unit-conversion tabs."""
import sys
import math
from decimal import Decimal, ROUND_HALF_UP, localcontext

from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QScrollArea, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)
from dynamo import BRAKING_UNITS, UNITS, TORQUE_UNITS, solve, solve_braking, solve_torque
from conversion import CONVERSION_UNITS, CONVERSION_NAMES, CONVERSION_DEFAULTS, convert_value


CALCULATION_ROUTES = {
    "energy": [(('mass', 'speed'), 'KE = ½ × m × v²')],
    "speed": [(('energy', 'mass'), 'v = √(2 × KE / m)')],
    "mass": [(('energy', 'speed'), 'm = 2 × KE / v²'),
             (('torque', 'deceleration', 'radius'), 'm = T / (a × r)')],
    "distance": [(('speed', 'deceleration'), 's = v² / (2 × a)')],
    "deceleration": [(('speed', 'distance'), 'a = v² / (2 × s)'),
                     (('torque', 'mass', 'radius'), 'a = T / (m × r)')],
    "radius": [(('torque', 'mass', 'deceleration'), 'r = T / (m × a)')],
    "torque": [(('mass', 'deceleration', 'radius'), 'T = m × a × r')],
}

DRUM_DIAMETER_METERS = 120 * 0.0254
DEFAULT_UNITS = {'energy': 'MJ', 'speed': 'ft/s', 'mass': 'lbs', 'distance': 'ft',
                 'deceleration': 'ft/s^2', 'radius': 'in', 'torque': 'lbf·in'}
DEFAULT_DECIMALS = {'energy': 0, 'speed': 2, 'mass': 0, 'distance': 0,
                    'deceleration': 2, 'radius': 1, 'torque': 0}


def format_number(value, places):
    """Round halves up for display without rounding intermediate calculations."""
    number = Decimal(str(value))
    with localcontext() as context:
        context.prec = max(32, number.adjusted() + places + 3)
        rounded = number.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return f'{abs(rounded) if rounded == 0 else rounded:,.{places}f}'


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Calculator")
        self.resize(800, 826)
        self.setMinimumSize(760, 520)

        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(88)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(32, 12, 32, 12)
        header_layout.setSpacing(18)

        emblem = QLabel("＋")
        emblem.setObjectName("emblem")
        emblem.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emblem.setFixedSize(56, 56)
        header_layout.addWidget(emblem)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        title = QLabel("My Calculator")
        title.setObjectName("appTitle")
        title_layout.addWidget(title)
        subtitle = QLabel("다이나모 · 단위환산")
        subtitle.setObjectName("appSubtitle")
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        ornament = QLabel("÷  ×  −  +")
        ornament.setObjectName("ornament")
        header_layout.addWidget(ornament)
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.dynamo_page = QWidget()
        self.build_dynamo()
        self.conversion_page = QWidget()
        self.build_conversion()
        self.tabs.addTab(self.dynamo_page, "다이나모")
        self.tabs.addTab(self.conversion_page, "단위환산")
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)
        self.guide_target = None
        self.guide_dependencies = ()
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(550)
        self.pulse_timer.timeout.connect(self.pulse_highlight)
        self.pulse_on = False
        QApplication.instance().installEventFilter(self)
        self.window_size_label = QLabel()
        self.window_size_label.setAccessibleName('현재 창 크기')
        self.statusBar().addPermanentWidget(self.window_size_label)
        self.update_window_size()

    def update_window_size(self):
        self.window_size_label.setText(f'{self.width()} × {self.height()} px')

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'window_size_label'):
            self.update_window_size()

    def build_conversion(self):
        outer = QVBoxLayout(self.conversion_page)
        outer.setContentsMargins(28, 20, 28, 20)
        controls = QHBoxLayout()
        controls.addWidget(QLabel('소수점'))
        self.conversion_decimals = QSpinBox()
        self.conversion_decimals.setRange(0, 12)
        self.conversion_decimals.setValue(2)
        self.conversion_decimals.setAccessibleName('단위환산 전체 소수점')
        controls.addWidget(self.conversion_decimals)
        controls.addStretch()
        outer.addLayout(controls)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        sections = QVBoxLayout(content)
        sections.setContentsMargins(0, 0, 0, 0)
        sections.setSpacing(12)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        self.conversion_rows = {}
        for category, title in CONVERSION_NAMES.items():
            card = QFrame()
            card.setObjectName('inputCard')
            grid = QGridLayout(card)
            grid.setContentsMargins(16, 12, 16, 16)
            heading = QLabel(title)
            heading.setObjectName('conversionTitle')
            grid.addWidget(heading, 0, 0, 1, 5)
            grid.setColumnStretch(0, 1)
            grid.setColumnStretch(3, 1)
            self.conversion_rows[category] = []
            for index, (source_unit, target_unit) in enumerate(CONVERSION_DEFAULTS[category]):
                field = QLineEdit()
                field.setPlaceholderText('값 입력')
                field.setClearButtonEnabled(True)
                source = QComboBox()
                target = QComboBox()
                for box in (source, target):
                    box.addItems(list(CONVERSION_UNITS[category]))
                source.setCurrentText(source_unit)
                target.setCurrentText(target_unit)
                result = QLineEdit()
                result.setReadOnly(True)
                result.setObjectName('conversionResult')
                result.setPlaceholderText('결과')
                for widget, label in ((field, '입력값'), (source, '입력 단위'),
                                      (target, '결과 단위'), (result, '결과')):
                    widget.setAccessibleName(f'{title} 변환 {index + 1} {label}')
                row = {'input': field, 'source': source, 'target': target, 'result': result}
                self.conversion_rows[category].append(row)
                for column, widget in enumerate((field, source, QLabel('→'), result, target)):
                    grid.addWidget(widget, index + 1, column)
                update = lambda *_, c=category, r=row: self.update_conversion(c, r)
                field.textChanged.connect(update)
                source.currentTextChanged.connect(update)
                target.currentTextChanged.connect(update)
            sections.addWidget(card)
        sections.addStretch()
        self.conversion_decimals.valueChanged.connect(self.update_all_conversions)

    def update_conversion(self, category, row):
        text = row['input'].text().strip()
        result = row['result']
        result.clear()
        result.setToolTip('')
        result.setPlaceholderText('결과')
        if not text:
            return
        try:
            value = convert_value(category, text, row['source'].currentText(), row['target'].currentText())
        except ValueError as error:
            message = str(error) if not str(error).startswith('could not convert') else '올바른 숫자를 입력해 주세요.'
            result.setPlaceholderText('입력 확인')
            result.setToolTip(message)
            return
        result.setText(format_number(value, self.conversion_decimals.value()))

    def update_all_conversions(self, *_):
        for category, rows in self.conversion_rows.items():
            for row in rows:
                self.update_conversion(category, row)

    def build_dynamo(self):
        outer = QVBoxLayout(self.dynamo_page)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        card = QFrame()
        card.setObjectName("inputCard")
        grid = QGridLayout(card)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(14)
        grid.addWidget(QLabel("항목"), 0, 0)
        grid.addWidget(QLabel("입력값"), 0, 1)
        grid.addWidget(QLabel("단위"), 0, 2)
        grid.addWidget(QLabel("결과"), 0, 3)
        grid.addWidget(QLabel("소수점"), 0, 4)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        self.fields = {}
        self.unit_boxes = {}
        self.result_cells = {}
        self.name_cells = {}
        self.decimal_boxes = {}
        self.quantity_names = {"energy": "운동에너지(KE)", "speed": "초기속도(v)", "mass": "등가관성중량(m)", "distance": "제동거리(s)", "deceleration": "감속도(a)", "radius": "회전반경(r)", "torque": "제동토크(T)"}
        for row, (key, name) in enumerate(self.quantity_names.items(), start=1):
            name_cell = QLabel(name)
            name_cell.setProperty('calculationTarget', key)
            name_cell.setCursor(Qt.CursorShape.PointingHandCursor)
            name_cell.setToolTip('클릭하면 필요한 입력 항목과 수식을 표시합니다.')
            grid.addWidget(name_cell, row, 0)
            self.name_cells[key] = name_cell
            field = QLineEdit()
            field.setPlaceholderText("값 입력 또는 비워두기")
            field.setClearButtonEnabled(True)
            field.setAccessibleName(name)
            field.textChanged.connect(self.clear_result)
            field.returnPressed.connect(self.calculate)
            grid.addWidget(field, row, 1)
            self.fields[key] = field
            box = QComboBox()
            box.addItems(list((UNITS | BRAKING_UNITS | TORQUE_UNITS)[key]))
            box.setCurrentText(DEFAULT_UNITS[key])
            box.setAccessibleName(f"{name} 단위")
            grid.addWidget(box, row, 2)
            self.unit_boxes[key] = box
            result_cell = QLabel("—")
            result_cell.setObjectName("resultCell")
            result_cell.setAccessibleName(f"{name} 결과")
            result_cell.setWordWrap(True)
            result_cell.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            result_cell.setProperty('calculationTarget', key)
            result_cell.setCursor(Qt.CursorShape.PointingHandCursor)
            result_cell.setToolTip('클릭하면 필요한 입력 항목과 수식을 표시합니다.')
            grid.addWidget(result_cell, row, 3)
            self.result_cells[key] = result_cell
            decimals = QSpinBox()
            decimals.setRange(0, 12)
            decimals.setValue(DEFAULT_DECIMALS[key])
            decimals.setAccessibleName(f'{name} 소수점 자릿수')
            grid.addWidget(decimals, row, 4)
            self.decimal_boxes[key] = decimals
        layout.addWidget(card)
        actions = QHBoxLayout()
        calculate = QPushButton("계산하기")
        calculate.setObjectName("primary")
        calculate.clicked.connect(self.calculate)
        reset = QPushButton("초기화")
        reset.clicked.connect(self.reset_dynamo)
        actions.addWidget(calculate)
        actions.addWidget(reset)
        actions.addStretch()
        layout.addLayout(actions)
        self.guide_formula = QLabel()
        self.guide_formula.setObjectName('guideFormula')
        self.guide_formula.setWordWrap(True)
        self.guide_formula.hide()
        layout.addWidget(self.guide_formula)
        # Keep calculation diagnostics internal; no explanatory panels are displayed.
        self.result = QLabel(self)
        self.braking_result = QLabel(self)
        self.torque_result = QLabel(self)
        for label in (self.result, self.braking_result, self.torque_result):
            label.hide()
        layout.addStretch()
        for box in self.unit_boxes.values():
            box.currentTextChanged.connect(lambda _: self.calculate())
        for box in self.decimal_boxes.values():
            box.valueChanged.connect(lambda _: self.calculate())

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonPress and isinstance(watched, QWidget):
            if watched is self or self.isAncestorOf(watched):
                target = watched.property('calculationTarget')
                if target:
                    self.toggle_guide(target)
                    return True
                self.clear_guide()
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        self.clear_guide()
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)

    def toggle_guide(self, target):
        previous = self.guide_target
        self.clear_guide()
        if target == previous:
            return
        self.guide_target = target
        # Prefer the formula best supported by the current inputs or computed results.
        def available(key):
            return bool(self.fields[key].text().strip()) or self.result_cells[key].text() != '—'
        dependencies, formula = max(
            CALCULATION_ROUTES[target],
            key=lambda route: sum(available(k) for k in route[0]) / len(route[0]),
        )
        self.guide_dependencies = dependencies
        names = ' · '.join(self.quantity_names[k] for k in dependencies)
        self.guide_formula.setText(f'{self.quantity_names[target]} 계산: {formula}\n'
                                   f'필요한 항목: {names}\n'
                                   '수식 기준 단위: KE[J], m[kg], v[m/s], s·r[m], a[m/s²], T[N·m]. 선택 단위는 자동 환산합니다.')
        self.guide_formula.show()
        self.pulse_highlight()
        self.pulse_timer.start()

    def set_highlight(self, key, phase):
        for widget in (self.name_cells[key], self.fields[key], self.unit_boxes[key], self.result_cells[key]):
            widget.setProperty('requiredPulse', phase)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def pulse_highlight(self):
        self.pulse_on = not self.pulse_on
        for key in self.guide_dependencies:
            self.set_highlight(key, 1 if self.pulse_on else 2)

    def clear_guide(self):
        self.pulse_timer.stop()
        for key in self.guide_dependencies:
            self.set_highlight(key, 0)
        self.guide_target = None
        self.guide_dependencies = ()
        self.pulse_on = False
        self.guide_formula.clear()
        self.guide_formula.hide()

    def clear_result(self, *_):
        for cell in self.result_cells.values():
            cell.setText("—")
        if hasattr(self, "result"):
            for label in (self.result, self.braking_result, self.torque_result):
                label.clear()
                label.hide()

    def read_values(self, keys):
        values = {}
        for key in keys:
            text = self.fields[key].text().strip()
            try:
                values[key] = float(text) if text else None
            except ValueError:
                raise ValueError(f"{self.quantity_names[key]}에 올바른 숫자를 입력해 주세요.") from None
        return values

    def calculate(self):
        self.clear_result()
        units = {key: box.currentText() for key, box in self.unit_boxes.items()}
        for key, field in self.fields.items():
            if field.text().strip():
                self.result_cells[key].setText(f"{field.text()} {units[key]}")
        values = {}
        invalid = {}
        for key in self.fields:
            try:
                values.update(self.read_values((key,)))
            except ValueError as error:
                values[key] = None
                invalid[key] = str(error)
        torque_active = any(self.fields[k].text().strip() for k in ("radius", "torque"))
        braking_active = any(self.fields[k].text().strip() for k in ("distance", "deceleration"))
        groups = [(UNITS, solve, self.result, True),
                  (BRAKING_UNITS, solve_braking, self.braking_result, braking_active),
                  (TORQUE_UNITS, solve_torque, self.torque_result, torque_active)]
        # Resolve dependencies in either direction without changing the user's inputs.
        for _ in range(len(self.fields)):
            changed = False
            for options, solver, label, active in groups:
                if not active or any(k in invalid for k in options):
                    continue
                try:
                    key, value = solver(values, units)
                except ValueError:
                    continue
                if values[key] is not None:
                    continue
                values[key] = value
                self.result_cells[key].setText(f"{value:,.12g} {units[key]}")
                changed = True
            if not changed:
                break
        for options, solver, label, active in groups:
            if not active:
                continue
            error = next((invalid[k] for k in options if k in invalid), None)
            if solver is solve_torque and all(self.fields[k].text().strip() for k in options) and error is None:
                error = "제동토크·등가관성중량·감속도·회전반경 중 세 개만 입력하고, 계산할 항목은 비워 주세요."
            if error is None and all(values[k] is not None for k in options):
                continue
            if error is None:
                try:
                    solver(values, units)
                except ValueError as exc:
                    error = str(exc)
            if error:
                label.setText(error)
        for key, value in values.items():
            if value is not None and math.isfinite(value):
                places = self.decimal_boxes[key].value()
                text = f'{format_number(value, places)} {units[key]}'
                if key == 'speed':
                    speed_si = value * UNITS['speed'][units['speed']]
                    rpm = speed_si * (60 / (math.pi * DRUM_DIAMETER_METERS))
                    if math.isfinite(rpm) and rpm >= 0:
                        text += f' ({format_number(rpm, places)} RPM)'
                self.result_cells[key].setText(text)
        self.result_cells['speed'].setToolTip('클릭하면 필요한 입력 항목과 수식을 표시합니다.\nRPM은 지름 120인치(3.048 m) 드럼의 선속도 기준입니다.')

    def reset_dynamo(self):
        self.clear_guide()
        for field in self.fields.values():
            field.clear()
        self.clear_result()
        self.fields["energy"].setFocus()


STYLE = """
QWidget { font-family: 'Malgun Gothic'; font-size: 14px; color: #35274b; }
QMainWindow, QWidget#root, QTabWidget { background: #f5f2fa; }
QFrame#header {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #432176, stop: 0.55 #7040af, stop: 1 #9863d5);
    border-bottom: 1px solid #aa80d9;
}
QLabel#emblem {
    color: white; font-size: 36px; font-weight: bold;
    background: rgba(255, 255, 255, 24);
    border: 1px solid rgba(255, 255, 255, 65); border-radius: 16px;
}
QLabel#appTitle {
    color: white; background: transparent; font-size: 30px; font-weight: bold;
}
QLabel#appSubtitle { color: #e4d6f5; background: transparent; font-size: 13px; }
QLabel#ornament { color: #ddc8f5; background: transparent; font-size: 28px; }
QTabWidget::pane { border: 1px solid #e3daef; background: white; }
QTabBar::tab {
    background: #eee7f6; color: #77618e;
    padding: 15px 32px; margin-right: 2px;
    border-bottom: 3px solid transparent;
}
QTabBar::tab:selected {
    background: white; color: #7341ae; font-weight: bold;
    border-bottom: 3px solid #8750c4;
}
QTabBar::tab:hover:!selected { background: #e5d9f2; color: #61358f; }
QLabel#sectionTitle { font-size: 22px; font-weight: bold; color: #61358f; }
QLabel#conversionTitle { font-size: 16px; font-weight: bold; color: #61358f; }
QLineEdit#conversionResult { background: #eee7f6; font-weight: bold; }
QFrame#inputCard { background: #faf8fd; border: 1px solid #e3daef; border-radius: 10px; }
QLineEdit, QComboBox, QSpinBox { background: white; padding: 9px; border: 1px solid #d6c7e6; border-radius: 5px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #8750c4; }
QPushButton { padding: 10px 24px; background: #eee7f6; border: 1px solid #d6c7e6; border-radius: 6px; }
QPushButton:hover { background: #e5d9f2; }
QPushButton#primary { color: white; background: #7946b4; border: none; }
QPushButton#primary:hover { background: #61358f; }
QLabel#result { background: #eee7f6; border-radius: 8px; padding: 16px; font-size: 17px; color: #61358f; }
QLabel#resultCell { background: #eee7f6; border-radius: 5px; padding: 9px; color: #61358f; font-weight: bold; }
QLabel#calculationNote { color: #77618e; font-size: 12px; }
QLabel#guideFormula { background: #edf6ff; color: #214f7b; border: 1px solid #bddcf5; border-radius: 8px; padding: 12px; }
QLabel[requiredPulse="1"], QLabel#resultCell[requiredPulse="1"], QLineEdit[requiredPulse="1"], QComboBox[requiredPulse="1"] { background: #d7ecff; color: #214f7b; }
QLabel[requiredPulse="2"], QLabel#resultCell[requiredPulse="2"], QLineEdit[requiredPulse="2"], QComboBox[requiredPulse="2"] { background: #f0f8ff; color: #214f7b; }
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("My Calculator")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
