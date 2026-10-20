"""PySide6 application with dynamo and unit-conversion tabs."""
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)
from dynamo import BRAKING_UNITS, UNITS, solve, solve_braking


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Calculator")
        self.resize(1040, 700)
        self.setMinimumSize(760, 520)

        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("header")
        header.setMinimumHeight(132)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(32, 24, 32, 24)
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
        self.tabs.addTab(self.dynamo_page, "다이나모")
        self.tabs.addTab(self.conversion_page, "단위환산")
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)

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
        heading = QLabel("다이나모 계산")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        instruction = QLabel("운동에너지·초기속도·등가관성중량 중 두 값을 입력하세요. 제동거리·감속도는 한 값만 입력하면 됩니다.")
        instruction.setWordWrap(True)
        layout.addWidget(instruction)
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
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        self.fields = {}
        self.unit_boxes = {}
        self.result_cells = {}
        self.quantity_names = {"energy": "운동에너지", "speed": "초기속도", "mass": "등가관성중량", "distance": "제동거리", "deceleration": "감속도"}
        for row, (key, name) in enumerate(self.quantity_names.items(), start=1):
            grid.addWidget(QLabel(name), row, 0)
            field = QLineEdit()
            field.setPlaceholderText("값 입력 또는 비워두기")
            field.setClearButtonEnabled(True)
            field.setAccessibleName(name)
            field.textChanged.connect(self.clear_result)
            field.returnPressed.connect(self.calculate)
            grid.addWidget(field, row, 1)
            self.fields[key] = field
            box = QComboBox()
            box.addItems(list((UNITS | BRAKING_UNITS)[key]))
            box.setAccessibleName(f"{name} 단위")
            box.currentTextChanged.connect(self.clear_result)
            grid.addWidget(box, row, 2)
            self.unit_boxes[key] = box
            result_cell = QLabel("—")
            result_cell.setObjectName("resultCell")
            result_cell.setAccessibleName(f"{name} 결과")
            result_cell.setWordWrap(True)
            result_cell.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(result_cell, row, 3)
            self.result_cells[key] = result_cell
        self.unit_boxes["speed"].setCurrentText("km/h")
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
        results = QHBoxLayout()
        results.setSpacing(16)
        self.result = QLabel()
        self.braking_result = QLabel()
        for label in (self.result, self.braking_result):
            label.setObjectName("result")
            label.setWordWrap(True)
            label.setMinimumWidth(0)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            results.addWidget(label, 1)
            label.hide()
        layout.addLayout(results)
        note = QLabel(
            "E = ½mv²  ·  a = v²/(2s)  ·  s = v²/(2a)\n"
            "초기속도를 함께 사용하며, 비워두면 운동에너지와 등가관성중량으로 계산한 속도를 사용합니다.\n"
            "등가관성중량은 질량, 감속도는 양의 크기입니다. 정지까지 일정 감속하며 반응거리는 제외합니다."
        )
        note.setObjectName("calculationNote")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()

    def clear_result(self, *_):
        for cell in self.result_cells.values():
            cell.setText("—")
        if hasattr(self, "result"):
            for label in (self.result, self.braking_result):
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
        calculated_speed = None
        try:
            values = self.read_values(UNITS)
            key, value = solve(values, units)
            self.result_cells[key].setText(f"{value:,.12g} {units[key]}")
            if key == "speed":
                calculated_speed = value
        except ValueError as error:
            self.result.setText(str(error))
            self.result.show()

        if not any(self.fields[k].text().strip() for k in ("distance", "deceleration")):
            return
        try:
            values = self.read_values(BRAKING_UNITS)
            if values["speed"] is None:
                values["speed"] = calculated_speed
            key, value = solve_braking(values, units)
            self.result_cells[key].setText(f"{value:,.12g} {units[key]}")
        except ValueError as error:
            self.braking_result.setText(str(error))
            self.braking_result.show()

    def reset_dynamo(self):
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
QFrame#inputCard { background: #faf8fd; border: 1px solid #e3daef; border-radius: 10px; }
QLineEdit, QComboBox { background: white; padding: 9px; border: 1px solid #d6c7e6; border-radius: 5px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #8750c4; }
QPushButton { padding: 10px 24px; background: #eee7f6; border: 1px solid #d6c7e6; border-radius: 6px; }
QPushButton:hover { background: #e5d9f2; }
QPushButton#primary { color: white; background: #7946b4; border: none; }
QPushButton#primary:hover { background: #61358f; }
QLabel#result { background: #eee7f6; border-radius: 8px; padding: 16px; font-size: 17px; color: #61358f; }
QLabel#resultCell { background: #eee7f6; border-radius: 5px; padding: 9px; color: #61358f; font-weight: bold; }
QLabel#calculationNote { color: #77618e; font-size: 12px; }
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
