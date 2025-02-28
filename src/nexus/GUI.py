import argparse
from threading import Thread
from pathlib import Path

from PySide6.QtCore import Qt, QTranslator, QLocale
from PySide6.QtWidgets import QApplication, QPushButton, QStatusBar, QTableWidget, QTableWidgetItem, QMainWindow, \
    QDialog, QFileDialog

from nexus.Freqlog import Freqlog
from nexus.ui.BanlistDialog import Ui_BanlistDialog
from nexus.ui.BanwordDialog import Ui_BanwordDialog
from nexus.ui.ConfirmDialog import Ui_ConfirmDialog
from nexus.ui.MainWindow import Ui_MainWindow

from nexus.Freqlog.Definitions import CaseSensitivity


class MainWindow(QMainWindow, Ui_MainWindow):
    """Set up the main window. Required because Qt is a PITA."""

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)


class BanlistDialog(QDialog, Ui_BanlistDialog):
    """Set up the banlist dialog. Required because Qt is a PITA."""

    def __init__(self, *args, **kwargs):
        super(BanlistDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)


class BanwordDialog(QDialog, Ui_BanwordDialog):
    """Set up the banword dialog. Required because Qt is a PITA."""

    def __init__(self, *args, **kwargs):
        super(BanwordDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)


class ConfirmDialog(QDialog, Ui_ConfirmDialog):
    """Set up the confirm dialog. Required because Qt is a PITA."""

    def __init__(self, *args, **kwargs):
        super(ConfirmDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)


class Translator(QTranslator):
    """Custom translator"""

    def translate(self, context: str, source: str, disambiguation=None, n=-1):
        final = super().translate(context, source, disambiguation, n)
        if final:
            return final
        return source


class GUI(object):
    """Nexus GUI"""

    def __init__(self, args: argparse.Namespace):
        """Initialize GUI"""
        self.app = QApplication([])
        self.window = MainWindow()

        # Translation
        self.translator = Translator(self.app)
        if self.translator.load(QLocale.system(), 'i18n', '_', str(Path(__file__).resolve().parent) + '/translations'):
            self.app.installTranslator(self.translator)
        self.tr = self.translator.translate

        # Components
        self.start_stop_button: QPushButton = self.window.startStopButton
        self.refresh_button: QPushButton = self.window.refreshButton
        self.banlist_button: QPushButton = self.window.banlistButton
        self.export_button: QPushButton = self.window.exportButton
        self.chentry_table: QTableWidget = self.window.chentryTable
        self.chord_table: QTableWidget = self.window.chordTable
        self.statusbar: QStatusBar = self.window.statusbar

        # Signals
        self.start_stop_button.clicked.connect(self.start_stop)
        self.refresh_button.clicked.connect(self.refresh)
        self.banlist_button.clicked.connect(self.show_banlist)
        self.export_button.clicked.connect(self.export)

        self.freqlog: Freqlog | None = None  # for logging
        self.temp_freqlog: Freqlog = Freqlog(args.freq_log_path, loggable=False)  # for other operations
        self.logging_thread: Thread | None = None
        self.start_stop_button_started = False
        self.args = args

    def start_logging(self):
        if not self.freqlog:
            self.freqlog = Freqlog(self.args.freq_log_path, loggable=True)
        self.freqlog.start_logging()

    def stop_logging(self):
        self.freqlog.stop_logging()
        self.freqlog = None

    def start_stop(self):
        """Controller for start/stop logging button"""
        if not self.start_stop_button_started:
            # Update button to starting
            # TODO: fix signal blocking (to prevent spam-clicking the button restarting logging, not currently working)
            self.start_stop_button.blockSignals(True)
            self.start_stop_button.setEnabled(False)
            self.start_stop_button.setText(self.tr("GUI", "Starting..."))
            self.start_stop_button.setStyleSheet("background-color: yellow")
            self.window.repaint()

            # Start freqlogging
            self.logging_thread = Thread(target=self.start_logging)
            self.logging_thread.start()

            # Update button to stop
            while not (self.freqlog and self.freqlog.is_logging):
                pass
            self.start_stop_button.setText(self.tr("GUI", "Stop logging"))
            self.start_stop_button.setStyleSheet("background-color: red")
            self.start_stop_button.setEnabled(True)
            self.start_stop_button.blockSignals(False)
            self.start_stop_button_started = True
            self.statusbar.showMessage(self.tr("GUI", "Logging started"))
            self.window.repaint()
        else:
            # Update button to stopping
            self.start_stop_button.setText("Stopping...")
            self.start_stop_button.setStyleSheet("background-color: yellow")
            self.start_stop_button.blockSignals(True)
            self.start_stop_button.setEnabled(False)
            self.window.repaint()

            # Stop freqlogging
            Thread(target=self.stop_logging).start()

            # Update button to start
            self.logging_thread.join()
            self.start_stop_button.setText(self.tr("GUI", "Start logging"))
            self.start_stop_button.setStyleSheet("background-color: green")
            self.start_stop_button.setEnabled(True)
            self.start_stop_button.blockSignals(False)
            self.start_stop_button_started = False
            self.statusbar.showMessage(self.tr("GUI", "Logging stopped"))
            self.window.repaint()

    def refresh(self):
        """Controller for refresh button"""
        words = self.temp_freqlog.list_words()
        self.chentry_table.setSortingEnabled(False)
        i = 0
        words_set = set(map(lambda w: w.word, words.copy()))
        while i < self.chentry_table.rowCount():
            if self.chentry_table.item(i, 0).text() not in words_set:
                self.chentry_table.removeRow(i)
                i -= 1
            i += 1
        table_set = set(map(lambda w: self.chentry_table.item(w, 0).text(), range(self.chentry_table.rowCount())))
        for word in words:
            if word.word not in table_set:
                self.chentry_table.insertRow(i)
                self.chentry_table.setItem(i, 0, QTableWidgetItem(word.word))
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, word.frequency)
                self.chentry_table.setItem(i, 1, item)
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, word.last_used.isoformat(sep=" ", timespec="seconds"))
                self.chentry_table.setItem(
                    i, 2, item)
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, str(word.average_speed)[2:-3])
                self.chentry_table.setItem(i, 3, item)

        self.chentry_table.setRowCount(len(words))
        self.chentry_table.resizeColumnsToContents()
        self.chentry_table.setSortingEnabled(True)
        self.statusbar.showMessage(self.tr("GUI", "Loaded {} freqlogged words").format(len(words)))

    def show_banlist(self):
        """Controller for banlist button"""
        bl_dialog = BanlistDialog()

        def refresh_banlist():
            """Refresh banlist table"""
            banlist_case, banlist_caseless = self.temp_freqlog.list_banned_words()
            bl_dialog.banlistTable.setRowCount(len(banlist_case) + len(banlist_caseless))
            for i, word in enumerate(banlist_case):
                bl_dialog.banlistTable.setItem(i, 0, QTableWidgetItem(word.word))
                bl_dialog.banlistTable.setItem(i, 1,
                                               QTableWidgetItem(
                                                   str(word.date_added.isoformat(sep=" ", timespec="seconds"))))
                bl_dialog.banlistTable.setItem(i, 2, QTableWidgetItem("Sensitive"))
            for i, word in enumerate(banlist_caseless):
                bl_dialog.banlistTable.setItem(i + len(banlist_case), 0, QTableWidgetItem(word.word))
                bl_dialog.banlistTable.setItem(i + len(banlist_case), 1,
                                               QTableWidgetItem(
                                                   str(word.date_added.isoformat(sep=" ", timespec="seconds"))))
                bl_dialog.banlistTable.setItem(i + len(banlist_case), 2, QTableWidgetItem("Insensitive"))
            bl_dialog.banlistTable.resizeColumnsToContents()

        refresh_banlist()

        def banword():
            """Controller for banword button"""
            bw_dialog = BanwordDialog()

            def add_banword():
                """Controller for add button in banword dialog"""
                word = bw_dialog.wordInput.text()
                if bw_dialog.sensitive.isChecked():
                    self.temp_freqlog.ban_word(word, CaseSensitivity.SENSITIVE)
                elif bw_dialog.firstChar.isChecked():
                    self.temp_freqlog.ban_word(word, CaseSensitivity.FIRST_CHAR)
                else:
                    self.temp_freqlog.ban_word(word, CaseSensitivity.INSENSITIVE)

            # Connect Ok button to add_banword
            bw_dialog.buttonBox.accepted.connect(add_banword)
            bw_dialog.exec()
            refresh_banlist()

        # TODO: support banning from right click menu
        def remove_banword():
            """Controller for remove button in banlist dialog"""
            # Get currently selected row(s)
            selected_rows = bl_dialog.banlistTable.selectionModel().selectedRows()
            if len(selected_rows) == 0:
                return

            # Get word(s) from selected row(s)
            selected_words = {}
            for row in selected_rows:
                selected_words[
                    bl_dialog.banlistTable.item(row.row(), 0).text()
                ] = (CaseSensitivity.SENSITIVE if bl_dialog.banlistTable.item(row.row(), 2).text() == "Sensitive"
                     else CaseSensitivity.INSENSITIVE)
            conf_dialog = ConfirmDialog()
            if len(selected_words) > 1:
                confirm_text = self.tr("GUI", "Unban {} words")
            else:
                confirm_text = self.tr("GUI", "Unban one word")
            conf_dialog.confirmText.setText(confirm_text.format(len(selected_words)))
            conf_dialog.buttonBox.accepted.connect(lambda: self.temp_freqlog.unban_words(selected_words))
            conf_dialog.exec()
            refresh_banlist()

        bl_dialog.addButton.clicked.connect(banword)
        bl_dialog.removeButton.clicked.connect(remove_banword)
        bl_dialog.exec()

    def export(self):
        """Controller for export button"""
        filename = QFileDialog.getSaveFileName(self.window, "Export to CSV", "", "CSV (*.csv)")[0]
        if filename:
            if not filename.endswith(".csv"):
                filename += ".csv"
            num_exported = self.temp_freqlog.export_words_to_csv(filename)
            self.statusbar.showMessage(
                self.tr("GUI", "Exported {} words to {}".format(num_exported, filename)))

    def exec(self):
        """Start the GUI"""
        self.window.show()
        self.refresh()
        self.app.exec()
