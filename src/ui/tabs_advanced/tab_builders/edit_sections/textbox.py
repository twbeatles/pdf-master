from __future__ import annotations

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from ....fluent_widgets import PrimaryButton, PushButton, QCheckBox, QComboBox, QDoubleSpinBox, QSpinBox, QTextEdit, WarningButton

from .....core.i18n import tm
from ....widgets import FileSelectorWidget
from ....form_rows import pair_grid


def build_textbox(self, layout) -> None:
    """v4.5: 텍스트 상자/선택 위치 워터마크 삽입"""
    # v4.5: 텍스트 상자/선택 위치 워터마크 삽입
    grp_textbox = QGroupBox(tm.get("grp_insert_textbox"))
    l_textbox = QVBoxLayout(grp_textbox)
    self.sel_textbox = FileSelectorWidget()
    self.sel_textbox.pathChanged.connect(self._update_preview)
    l_textbox.addWidget(self.sel_textbox)

    # 1) 넣을 글
    l_textbox.addWidget(QLabel(tm.get("lbl_textbox_content")))
    self.txt_textbox_content = QTextEdit()
    self.txt_textbox_content.setPlaceholderText(tm.get("ph_textbox_content"))
    self.txt_textbox_content.setAcceptRichText(False)
    self.txt_textbox_content.setMaximumHeight(96)
    self.txt_textbox_content.setTabChangesFocus(True)
    l_textbox.addWidget(self.txt_textbox_content)

    # 2) 글꼴, 크기, 색
    self.cmb_tb_font = QComboBox()
    tb_fonts = [
        (tm.get("font_cjk"), "cjk"),
        (tm.get("font_helvetica"), "helv"),
        (tm.get("font_courier"), "cour"),
        (tm.get("font_times"), "tiro"),
    ]
    for label, val in tb_fonts:
        self.cmb_tb_font.addItem(label, userData=val)

    self.spn_tb_fontsize = QSpinBox()
    self.spn_tb_fontsize.setRange(6, 144)
    self.spn_tb_fontsize.setValue(14)

    self.cmb_tb_color = QComboBox()
    tb_colors = [
        (tm.get("color_black"), (0, 0, 0)),
        (tm.get("color_blue"), (0, 0, 1)),
        (tm.get("color_red"), (1, 0, 0)),
        (tm.get("color_green"), (0, 0.5, 0)),
        (tm.get("color_white"), (1, 1, 1)),
        (tm.get("color_gray"), (0.5, 0.5, 0.5)),
    ]
    for label, value in tb_colors:
        self.cmb_tb_color.addItem(label, userData=value)

    self.cmb_tb_align = QComboBox()
    self.cmb_tb_align.addItem(tm.get("align_left"), userData=0)
    self.cmb_tb_align.addItem(tm.get("align_center"), userData=1)
    self.cmb_tb_align.addItem(tm.get("align_right"), userData=2)

    l_textbox.addLayout(
        pair_grid(
            [
                (tm.get("lbl_textbox_font"), self.cmb_tb_font),
                (tm.get("lbl_textbox_fontsize"), self.spn_tb_fontsize),
                (tm.get("lbl_textbox_color"), self.cmb_tb_color),
                (tm.get("lbl_textbox_align"), self.cmb_tb_align),
            ]
        )
    )

    # 3) 위치: 미리보기에서 잡거나, 자주 쓰는 위치를 고르거나, 숫자로 직접 입력
    tb_drag_layout = QHBoxLayout()
    self.b_tb_drag = PushButton(tm.get("btn_textbox_drag_select"))
    self.b_tb_drag.setObjectName("secondaryBtn")
    self.b_tb_drag.setToolTip(tm.get("tooltip_textbox_drag_select"))
    self.b_tb_drag.clicked.connect(self.action_start_textbox_region_select)
    tb_drag_layout.addWidget(self.b_tb_drag)
    self.lbl_tb_drag_hint = QLabel(tm.get("hint_textbox_drag_idle"))
    self.lbl_tb_drag_hint.setObjectName("desc")
    self.lbl_tb_drag_hint.setWordWrap(True)
    tb_drag_layout.addWidget(self.lbl_tb_drag_hint, 1)
    l_textbox.addLayout(tb_drag_layout)

    tb_preset_layout = QHBoxLayout()
    tb_preset_layout.addWidget(QLabel(tm.get("lbl_textbox_preset")))
    self.cmb_tb_preset = QComboBox()
    tb_presets = [
        (tm.get("pos_preset_custom"), "custom"),
        (tm.get("pos_top_left"), "top-left"),
        (tm.get("pos_top_center"), "top-center"),
        (tm.get("pos_top_right"), "top-right"),
        (tm.get("pos_center_left"), "center-left"),
        (tm.get("pos_center"), "center"),
        (tm.get("pos_center_right"), "center-right"),
        (tm.get("pos_bottom_left"), "bottom-left"),
        (tm.get("pos_bottom_center"), "bottom-center"),
        (tm.get("pos_bottom_right"), "bottom-right"),
    ]
    for label, val in tb_presets:
        self.cmb_tb_preset.addItem(label, userData=val)
    self.cmb_tb_preset.setToolTip(tm.get("tooltip_textbox_preset"))
    self.cmb_tb_preset.currentIndexChanged.connect(self.action_apply_textbox_preset)
    tb_preset_layout.addWidget(self.cmb_tb_preset, 1)
    l_textbox.addLayout(tb_preset_layout)

    # 페이지 & 위치 좌표 (X, Y, W, H) — 소수점 1자리로 정밀 배치
    self.spn_tb_page = QSpinBox()
    self.spn_tb_page.setRange(1, 9999)
    self.spn_tb_page.setValue(1)

    self.spn_tb_x = QDoubleSpinBox()
    self.spn_tb_x.setRange(0.0, 20000.0)
    self.spn_tb_x.setDecimals(1)
    self.spn_tb_x.setSingleStep(1.0)
    self.spn_tb_x.setValue(36.0)  # A4 좌상단 여백 기본

    self.spn_tb_y = QDoubleSpinBox()
    self.spn_tb_y.setRange(0.0, 20000.0)
    self.spn_tb_y.setDecimals(1)
    self.spn_tb_y.setSingleStep(1.0)
    self.spn_tb_y.setValue(36.0)

    self.spn_tb_w = QDoubleSpinBox()
    self.spn_tb_w.setRange(20.0, 20000.0)
    self.spn_tb_w.setDecimals(1)
    self.spn_tb_w.setSingleStep(1.0)
    self.spn_tb_w.setValue(220.0)

    self.spn_tb_h = QDoubleSpinBox()
    self.spn_tb_h.setRange(14.0, 20000.0)
    self.spn_tb_h.setDecimals(1)
    self.spn_tb_h.setSingleStep(1.0)
    self.spn_tb_h.setValue(40.0)

    # 투명도, 회전각(90° 배수), 레이어
    self.spn_tb_opacity = QSpinBox()
    self.spn_tb_opacity.setRange(10, 100)
    self.spn_tb_opacity.setValue(100)
    self.spn_tb_opacity.setSuffix("%")

    self.spn_tb_rotation = QSpinBox()
    self.spn_tb_rotation.setRange(0, 270)
    self.spn_tb_rotation.setSingleStep(90)
    self.spn_tb_rotation.setValue(0)
    self.spn_tb_rotation.setSuffix("°")

    self.cmb_tb_layer = QComboBox()
    self.cmb_tb_layer.addItem(tm.get("msg_layer_foreground"), userData="foreground")
    self.cmb_tb_layer.addItem(tm.get("msg_layer_background"), userData="background")

    l_textbox.addLayout(
        pair_grid(
            [
                (tm.get("lbl_page"), self.spn_tb_page),
                (tm.get("lbl_textbox_layer"), self.cmb_tb_layer),
                (tm.get("lbl_textbox_x"), self.spn_tb_x),
                (tm.get("lbl_textbox_y"), self.spn_tb_y),
                (tm.get("lbl_textbox_w"), self.spn_tb_w),
                (tm.get("lbl_textbox_h"), self.spn_tb_h),
                (tm.get("lbl_textbox_opacity"), self.spn_tb_opacity),
                (tm.get("lbl_textbox_rotation"), self.spn_tb_rotation),
            ]
        )
    )

    # 미리보기 배치 중 텍스트/스타일 변경 시 오버레이 동기화
    self.txt_textbox_content.textChanged.connect(self._sync_textbox_placement_overlay)
    self.spn_tb_fontsize.valueChanged.connect(self._sync_textbox_placement_overlay)
    self.cmb_tb_color.currentIndexChanged.connect(self._sync_textbox_placement_overlay)
    self.cmb_tb_align.currentIndexChanged.connect(self._sync_textbox_placement_overlay)
    self.spn_tb_opacity.valueChanged.connect(self._sync_textbox_placement_overlay)
    self.spn_tb_x.valueChanged.connect(self._sync_textbox_placement_overlay)
    self.spn_tb_y.valueChanged.connect(self._sync_textbox_placement_overlay)
    self.spn_tb_w.valueChanged.connect(self._sync_textbox_placement_overlay)
    self.spn_tb_h.valueChanged.connect(self._sync_textbox_placement_overlay)

    # 4) 저장 방식 옵션 + 실행
    self.chk_tb_same_path = QCheckBox(tm.get("chk_textbox_same_path"))
    self.chk_tb_same_path.setToolTip(tm.get("tooltip_textbox_same_path"))
    self.chk_tb_same_path.setChecked(False)
    l_textbox.addWidget(self.chk_tb_same_path)
    self.chk_tb_keep_placing = QCheckBox(tm.get("chk_textbox_keep_placing"))
    self.chk_tb_keep_placing.setToolTip(tm.get("tooltip_textbox_keep_placing"))
    self.chk_tb_keep_placing.setChecked(False)
    l_textbox.addWidget(self.chk_tb_keep_placing)

    tb_actions = QHBoxLayout()
    b_textbox = PrimaryButton(tm.get("btn_insert_textbox"))
    b_textbox.setObjectName("actionBtn")
    b_textbox.clicked.connect(self.action_insert_textbox)
    tb_actions.addWidget(b_textbox, 1)
    b_tb_focus = PushButton(tm.get("btn_preview_focus_enter"))
    b_tb_focus.setObjectName("secondaryBtn")
    b_tb_focus.setToolTip(tm.get("tooltip_preview_focus_enter"))
    b_tb_focus.clicked.connect(self._toggle_preview_focus_mode)
    tb_actions.addWidget(b_tb_focus)
    l_textbox.addLayout(tb_actions)

    # 5) 여러 개를 담아 두었다가 한꺼번에 넣기
    self.lbl_tb_queue_count = QLabel(tm.get("hint_textbox_queue_count", 0))
    self.lbl_tb_queue_count.setObjectName("desc")
    l_textbox.addWidget(self.lbl_tb_queue_count)
    self.lst_tb_queue = QListWidget()
    self.lst_tb_queue.setMaximumHeight(80)
    l_textbox.addWidget(self.lst_tb_queue)
    tb_queue_btns = QHBoxLayout()
    b_q_add = PushButton(tm.get("btn_textbox_queue_add"))
    b_q_add.setObjectName("secondaryBtn")
    b_q_add.clicked.connect(self.action_textbox_queue_add)
    tb_queue_btns.addWidget(b_q_add)
    b_q_clear = PushButton(tm.get("btn_textbox_queue_clear"))
    b_q_clear.setObjectName("secondaryBtn")
    b_q_clear.clicked.connect(self.action_textbox_queue_clear)
    tb_queue_btns.addWidget(b_q_clear)
    tb_queue_btns.addStretch()
    l_textbox.addLayout(tb_queue_btns)
    b_q_commit = PrimaryButton(tm.get("btn_textbox_queue_commit"))
    b_q_commit.setObjectName("actionBtn")
    b_q_commit.clicked.connect(self.action_textbox_queue_commit)
    l_textbox.addWidget(b_q_commit)

    # 실험: 영역 텍스트 교체
    tb_replace = QHBoxLayout()
    b_rep_region = PushButton(tm.get("btn_textbox_replace_region"))
    b_rep_region.setObjectName("secondaryBtn")
    b_rep_region.setToolTip(tm.get("tooltip_textbox_replace_region"))
    b_rep_region.clicked.connect(self.action_start_textbox_replace_region)
    tb_replace.addWidget(b_rep_region)
    b_rep_apply = WarningButton(tm.get("btn_textbox_replace_apply"))
    b_rep_apply.setObjectName("warningBtn")
    b_rep_apply.setToolTip(tm.get("tooltip_textbox_replace_apply"))
    b_rep_apply.clicked.connect(self.action_replace_text_in_rect)
    tb_replace.addWidget(b_rep_apply)
    tb_replace.addStretch()
    l_textbox.addLayout(tb_replace)
    layout.addWidget(grp_textbox)

    self._textbox_queue = []

