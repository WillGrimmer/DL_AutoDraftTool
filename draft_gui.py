"""
Desktop GUI for the draft (PyQt6). Run with: python draft_gui.py
Requires: pip install PyQt6
Portraits: HeroPortraits/id<hero_id>.png
"""
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QGridLayout,
    QMessageBox,
    QStackedWidget,
    QTextEdit,
    QSizePolicy,
)

from data_loader import full_hero_pool
from hero_mappings import HERO_ID_MAPPINGS
from minimax import TURN_ORDER, TEAM_A, TEAM_B, NUM_PICKS, computer_pick, computer_ban
from evaluator import evaluate


PORTRAIT_DIR = Path(__file__).resolve().parent / "HeroPortraits"
PORTRAIT_SIZE = 72


def hero_name(hero_id):
    return HERO_ID_MAPPINGS.get(hero_id, str(hero_id))


def portrait_path(hero_id):
    return PORTRAIT_DIR / f"id{hero_id}.png"


class HeroPortraitLabel(QWidget):
    """Clickable portrait (image + name); greys out when disabled."""
    hero_clicked = pyqtSignal(int)  # hero_id

    def __init__(self, hero_id, parent=None):
        super().__init__(parent)
        self.hero_id = hero_id
        self._pixmap = None
        self._grey_pixmap = None
        self.setFixedSize(PORTRAIT_SIZE + 8, PORTRAIT_SIZE + 28)
        self.setStyleSheet(
            "HeroPortraitLabel { border: 2px solid transparent; border-radius: 4px; }"
            "HeroPortraitLabel:hover:!disabled { border-color: #4a9eff; background: rgba(74,158,255,0.15); }"
            "HeroPortraitLabel:disabled { background: #2a2a2a; }"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(hero_name(hero_id))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self._img_label = QLabel()
        self._img_label.setFixedSize(PORTRAIT_SIZE, PORTRAIT_SIZE)
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_label.setScaledContents(False)
        layout.addWidget(self._img_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self._name_label = QLabel(hero_name(hero_id))
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        f = QFont()
        f.setPointSize(8)
        self._name_label.setFont(f)
        self._name_label.setWordWrap(True)
        layout.addWidget(self._name_label)
        self._load_pixmaps()

    def _load_pixmaps(self):
        path = portrait_path(self.hero_id)
        if path.exists():
            pix = QPixmap(str(path)).scaled(
                PORTRAIT_SIZE, PORTRAIT_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._pixmap = pix
            self._grey_pixmap = self._grayscale_pixmap(pix)
        else:
            self._pixmap = QPixmap(PORTRAIT_SIZE, PORTRAIT_SIZE)
            self._pixmap.fill(QColor(60, 60, 60))
            self._grey_pixmap = self._grayscale_pixmap(self._pixmap)

    @staticmethod
    def _grayscale_pixmap(pixmap):
        img = pixmap.toImage()
        for y in range(img.height()):
            for x in range(img.width()):
                c = img.pixelColor(x, y)
                g = int(0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue())
                img.setPixelColor(x, y, QColor(g, g, g, c.alpha()))
        return QPixmap.fromImage(img)

    def set_available(self, available):
        self.setEnabled(available)
        if available:
            self._img_label.setPixmap(self._pixmap)
        else:
            self._img_label.setPixmap(self._grey_pixmap)
        self._name_label.setText(hero_name(self.hero_id))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isEnabled():
            self.hero_clicked.emit(self.hero_id)
        super().mousePressEvent(event)


class DraftMainWindow(QMainWindow):
    # Signals for cross-thread callbacks (emit from worker, slot runs on main thread)
    _phase1_ban_a_done = pyqtSignal(int)
    _phase1_ban_b_done = pyqtSignal(int)
    _phase2_ban_a_done = pyqtSignal(int)
    _phase2_ban_b_done = pyqtSignal(int)
    _computer_pick_done = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._phase1_ban_a_done.connect(self._on_phase1_ban_a_done)
        self._phase1_ban_b_done.connect(self._on_phase1_ban_b_done)
        self._phase2_ban_a_done.connect(self._on_phase2_ban_a_done)
        self._phase2_ban_b_done.connect(self._on_phase2_ban_b_done)
        self._computer_pick_done.connect(self._on_computer_pick_done)
        self.setWindowTitle("Draft Tool")
        self.setMinimumSize(720, 620)
        self.resize(820, 680)

        self.human_team_a = None  # True = human is first picker (A), False = human is second (B)
        self.team_a_picks = []
        self.team_b_picks = []
        self.available_heroes = set(full_hero_pool)
        self.phase = "phase1_ban_a"
        self.turn_index = 0
        self.waiting_for_ai = False

        self._hero_widgets = {}  # hero_id -> HeroPortraitLabel
        self._build_ui()
        # Start on team selection; draft content is hidden until choice is made
        self._stack.setCurrentWidget(self._team_select_page)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        self._stack = QStackedWidget()
        # ---- Team selection page ----
        self._team_select_page = QWidget()
        select_layout = QVBoxLayout(self._team_select_page)
        select_layout.addWidget(QLabel("Choose your team:"))
        select_layout.addWidget(QLabel("Team A picks first in each round. Team B picks second."))
        btn_a = QPushButton("Play as Team A (pick first)")
        btn_a.clicked.connect(lambda: self._on_team_chosen(True))
        btn_b = QPushButton("Play as Team B (pick second)")
        btn_b.clicked.connect(lambda: self._on_team_chosen(False))
        select_layout.addWidget(btn_a)
        select_layout.addWidget(btn_b)
        select_layout.addStretch()
        self._stack.addWidget(self._team_select_page)

        # ---- Draft page ----
        self._draft_page = QWidget()
        layout = QVBoxLayout(self._draft_page)
        layout.setSpacing(10)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(self.status_label)

        teams = QHBoxLayout()
        team_a_frame = QFrame()
        team_a_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        team_a_layout = QVBoxLayout(team_a_frame)
        self.team_a_title = QLabel("Team A")  # updated in _update_team_labels
        team_a_layout.addWidget(self.team_a_title)
        self.team_a_roster = QLabel("")
        self.team_a_roster.setWordWrap(True)
        self.team_a_roster.setStyleSheet("color: #8af;")
        team_a_layout.addWidget(self.team_a_roster)
        teams.addWidget(team_a_frame, 1)

        team_b_frame = QFrame()
        team_b_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        team_b_layout = QVBoxLayout(team_b_frame)
        self.team_b_title = QLabel("Team B")
        team_b_layout.addWidget(self.team_b_title)
        self.team_b_roster = QLabel("")
        self.team_b_roster.setWordWrap(True)
        self.team_b_roster.setStyleSheet("color: #8f8;")
        team_b_layout.addWidget(self.team_b_roster)
        teams.addWidget(team_b_frame, 1)
        layout.addLayout(teams)

        layout.addWidget(QLabel("Click a hero portrait to pick or ban:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_content = QWidget()
        grid = QGridLayout(scroll_content)
        grid.setSpacing(6)

        hero_ids = sorted(full_hero_pool, key=lambda x: hero_name(x).lower())
        cols = 8
        for i, hid in enumerate(hero_ids):
            row, col = i // cols, i % cols
            w = HeroPortraitLabel(hid)
            w.hero_clicked.connect(self._on_hero_clicked)
            self._hero_widgets[hid] = w
            grid.addWidget(w, row, col)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        log_label = QLabel("Log")
        layout.addWidget(log_label)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet("font-family: Consolas; font-size: 9px;")
        layout.addWidget(self.log_text)

        self._stack.addWidget(self._draft_page)
        main_layout.addWidget(self._stack)

    def _update_team_labels(self):
        if self.human_team_a is None:
            return
        if self.human_team_a:
            self.team_a_title.setText("Team A (You)")
            self.team_b_title.setText("Team B (Computer)")
        else:
            self.team_a_title.setText("Team A (Computer)")
            self.team_b_title.setText("Team B (You)")

    def _on_team_chosen(self, human_team_a):
        self.human_team_a = human_team_a
        self._update_team_labels()
        self._refresh_rosters()
        self._refresh_portraits()
        self._stack.setCurrentWidget(self._draft_page)
        self._log("Draft started. Team A bans first (Phase 1).")
        self._run_current_phase()

    def _is_computer_turn(self):
        """True if the current phase is the computer's turn to act."""
        if self.phase == "phase1_ban_a":
            return not self.human_team_a
        if self.phase == "phase1_ban_b":
            return self.human_team_a
        if self.phase == "phase2_ban_b":
            return self.human_team_a  # B bans first in phase 2; B is computer when human is A
        if self.phase == "phase2_ban_a":
            return not self.human_team_a
        if self.phase.startswith("pick_"):
            turn = int(self.phase.split("_")[1])
            return TURN_ORDER[turn] == TEAM_A and not self.human_team_a or TURN_ORDER[turn] == TEAM_B and self.human_team_a
        return False

    def _run_current_phase(self):
        """Start computer action if it's computer's turn; otherwise status is already set for human."""
        if self.phase == "phase1_ban_a":
            if self._is_computer_turn():
                self._schedule_computer_phase1_ban_a()
            else:
                self._set_status("Your turn to ban (Phase 1). Click a hero to ban.")
                self._log("Your turn to ban. Click a hero.")
        elif self.phase == "phase1_ban_b":
            if self._is_computer_turn():
                self._schedule_computer_phase1_ban_b()
            else:
                self._set_status("Your turn to ban (Phase 1). Click a hero to ban.")
                self._log("Your turn to ban. Click a hero.")
        elif self.phase == "phase2_ban_b":
            if self._is_computer_turn():
                self._schedule_computer_phase2_ban_b()
            else:
                self._set_status("Phase 2 bans: Your turn to ban first. Click a hero to ban.")
                self._log("Phase 2 bans. Your turn to ban. Click a hero.")
        elif self.phase == "phase2_ban_a":
            if self._is_computer_turn():
                self._schedule_computer_phase2_ban_a()
            else:
                self._set_status("Phase 2 bans: Your turn to ban. Click a hero to ban.")
                self._log("Phase 2 bans. Your turn to ban. Click a hero.")
        elif self.phase.startswith("pick_"):
            self._advance_pick_phase()

    def _on_hero_clicked(self, hero_id):
        if self.waiting_for_ai or hero_id not in self.available_heroes:
            return
        if self.phase == "phase1_ban_a":
            self._do_phase1_ban_a(hero_id)
        elif self.phase == "phase1_ban_b":
            self._do_phase1_ban_b(hero_id)
        elif self.phase == "phase2_ban_b":
            self._do_phase2_ban_b(hero_id)
        elif self.phase == "phase2_ban_a":
            self._do_phase2_ban_a(hero_id)
        elif self.phase.startswith("pick_"):
            turn = int(self.phase.split("_")[1])
            is_human_turn = (TURN_ORDER[turn] == TEAM_A and self.human_team_a) or (TURN_ORDER[turn] == TEAM_B and not self.human_team_a)
            if is_human_turn:
                self._do_human_pick(hero_id)

    def _log(self, msg):
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def _refresh_rosters(self):
        a_names = [hero_name(h) for h in self.team_a_picks]
        b_names = [hero_name(h) for h in self.team_b_picks]
        self.team_a_roster.setText(", ".join(a_names) if a_names else "(none)")
        self.team_b_roster.setText(", ".join(b_names) if b_names else "(none)")

    def _refresh_portraits(self):
        for hid, w in self._hero_widgets.items():
            w.set_available(hid in self.available_heroes)

    def _set_status(self, text):
        self.status_label.setText(text)

    def _schedule_computer_phase1_ban_a(self):
        self.waiting_for_ai = True
        self._set_status("Team A is banning...")
        self._log("Team A is choosing a ban...")
        def run():
            ban = computer_ban(self.team_a_picks, self.team_b_picks, self.available_heroes, phase=1, ban_for_team_a=True)
            self._phase1_ban_a_done.emit(ban)
        threading.Thread(target=run, daemon=True).start()

    def _schedule_computer_phase1_ban_b(self):
        self.waiting_for_ai = True
        self._set_status("Team B is banning...")
        self._log("Team B is choosing a ban...")
        def run():
            ban = computer_ban(self.team_a_picks, self.team_b_picks, self.available_heroes, phase=1, ban_for_team_a=False)
            self._phase1_ban_b_done.emit(ban)
        threading.Thread(target=run, daemon=True).start()

    def _on_phase1_ban_a_done(self, hero_id):
        self.waiting_for_ai = False
        self.available_heroes.discard(hero_id)
        self._log(f"Team A bans {hero_name(hero_id)}.")
        self._refresh_portraits()
        self._refresh_rosters()
        self.phase = "phase1_ban_b"
        self._run_current_phase()

    def _do_phase1_ban_a(self, hero_id):
        """Human bans for Team A (Phase 1)."""
        self.available_heroes.discard(hero_id)
        self._log(f"Team A bans {hero_name(hero_id)}.")
        self._refresh_portraits()
        self._refresh_rosters()
        self.phase = "phase1_ban_b"
        self._run_current_phase()

    def _on_phase1_ban_b_done(self, hero_id):
        self.waiting_for_ai = False
        self.available_heroes.discard(hero_id)
        self._log(f"Team B bans {hero_name(hero_id)}.")
        self._refresh_portraits()
        self._refresh_rosters()
        self.phase = "pick_0"
        self.turn_index = 0
        self._advance_pick_phase()

    def _do_phase1_ban_b(self, hero_id):
        """Human bans for Team B (Phase 1)."""
        self.available_heroes.discard(hero_id)
        self._log(f"Team B bans {hero_name(hero_id)}.")
        self._refresh_portraits()
        self._refresh_rosters()
        self.phase = "pick_0"
        self.turn_index = 0
        self._advance_pick_phase()

    def _schedule_computer_phase2_ban_b(self):
        self.waiting_for_ai = True
        self._set_status("Team B is banning (Phase 2)...")
        self._log("Team B is choosing a ban...")
        def run():
            ban = computer_ban(self.team_a_picks, self.team_b_picks, self.available_heroes, phase=2, ban_for_team_a=False)
            self._phase2_ban_b_done.emit(ban)
        threading.Thread(target=run, daemon=True).start()

    def _schedule_computer_phase2_ban_a(self):
        self.waiting_for_ai = True
        self._set_status("Team A is banning (Phase 2)...")
        self._log("Team A is choosing a ban...")
        def run():
            ban = computer_ban(self.team_a_picks, self.team_b_picks, self.available_heroes, phase=2, ban_for_team_a=True)
            self._phase2_ban_a_done.emit(ban)
        threading.Thread(target=run, daemon=True).start()

    def _on_phase2_ban_a_done(self, hero_id):
        self.waiting_for_ai = False
        self.available_heroes.discard(hero_id)
        self._log(f"Team A bans {hero_name(hero_id)}.")
        self._refresh_portraits()
        self._refresh_rosters()
        self.phase = "pick_6"
        self.turn_index = 6
        self._advance_pick_phase()

    def _on_phase2_ban_b_done(self, hero_id):
        self.waiting_for_ai = False
        self.available_heroes.discard(hero_id)
        self._log(f"Team B bans {hero_name(hero_id)}.")
        self._refresh_portraits()
        self._refresh_rosters()
        self.phase = "phase2_ban_a"
        self._run_current_phase()

    def _do_phase2_ban_b(self, hero_id):
        """Human bans for Team B (Phase 2, B bans first)."""
        self.available_heroes.discard(hero_id)
        self._log(f"Team B bans {hero_name(hero_id)}.")
        self._refresh_portraits()
        self._refresh_rosters()
        self.phase = "phase2_ban_a"
        self._run_current_phase()

    def _do_phase2_ban_a(self, hero_id):
        """Human bans for Team A (Phase 2)."""
        self.available_heroes.discard(hero_id)
        self._log(f"Team A bans {hero_name(hero_id)}.")
        self._refresh_portraits()
        self._refresh_rosters()
        self.phase = "pick_6"
        self.turn_index = 6
        self._advance_pick_phase()

    def _advance_pick_phase(self):
        if self.turn_index >= NUM_PICKS:
            self._finish_draft()
            return
        current_team = TURN_ORDER[self.turn_index]
        if (current_team == TEAM_A and not self.human_team_a) or (current_team == TEAM_B and self.human_team_a):
            self._schedule_computer_pick()
        else:
            self._set_status(f"Your turn to pick ({self.turn_index + 1}/{NUM_PICKS}). Click a hero portrait.")
            self._log("Your turn to pick. Click a hero.")

    def _schedule_computer_pick(self):
        turn_index = self.turn_index
        pick_for_team_a = TURN_ORDER[turn_index] == TEAM_A
        side = "A" if pick_for_team_a else "B"
        self.waiting_for_ai = True
        self._set_status(f"Team {side} is picking ({self.turn_index + 1}/{NUM_PICKS})...")
        self._log(f"Team {side} is thinking...")
        team_a = list(self.team_a_picks)
        team_b = list(self.team_b_picks)
        avail = set(self.available_heroes)

        def run():
            hero = computer_pick(team_a, team_b, avail, turn_index, pick_for_team_a=pick_for_team_a)
            self._computer_pick_done.emit(hero)
        threading.Thread(target=run, daemon=True).start()

    def _on_computer_pick_done(self, hero_id):
        self.waiting_for_ai = False
        current_team = TURN_ORDER[self.turn_index]
        if current_team == TEAM_A:
            self.team_a_picks.append(hero_id)
            self._log(f"Team A picks {hero_name(hero_id)}.")
        else:
            self.team_b_picks.append(hero_id)
            self._log(f"Team B picks {hero_name(hero_id)}.")
        self.available_heroes.discard(hero_id)
        self._refresh_portraits()
        self._refresh_rosters()
        self.turn_index += 1
        if self.turn_index == 6:
            self.phase = "phase2_ban_b"
            self._run_current_phase()
        else:
            self.phase = f"pick_{self.turn_index}"
            self._advance_pick_phase()

    def _do_human_pick(self, hero_id):
        if self.human_team_a:
            self.team_a_picks.append(hero_id)
            self._log(f"Team A picks {hero_name(hero_id)}.")
        else:
            self.team_b_picks.append(hero_id)
            self._log(f"Team B picks {hero_name(hero_id)}.")
        self.available_heroes.discard(hero_id)
        self._refresh_portraits()
        self._refresh_rosters()
        self.turn_index += 1
        if self.turn_index == 6:
            # Just finished 6th pick (both teams have 3); do Phase 2 bans before picks 7–12
            self.phase = "phase2_ban_b"
            self._set_status("Phase 2 bans: Your turn to ban first. Click a hero to ban.")
            self._log("Phase 2 bans. Your turn to ban. Click a hero.")
        else:
            self.phase = f"pick_{self.turn_index}"
            self._advance_pick_phase()

    def _finish_draft(self):
        self.phase = "done"
        score = evaluate(self.team_a_picks, self.team_b_picks)
        self._set_status("Draft complete.")
        # Score is from first picker (Team A)'s perspective; phrase it for the player
        if self.human_team_a:
            score_meaning = "positive = favorable to you"
        else:
            score_meaning = "positive = favorable to computer (first picker)"
        self._log("")
        self._log("========== Final draft ==========")
        self._log(f"Team A: {', '.join(hero_name(h) for h in self.team_a_picks)}")
        self._log(f"Team B: {', '.join(hero_name(h) for h in self.team_b_picks)}")
        self._log(f"Evaluation ({score_meaning}): {score:.2f}")
        QMessageBox.information(
            self, "Draft complete",
            f"Draft complete.\n\nScore: {score:.2f}\n({score_meaning})",
        )


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = DraftMainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
