#!/usr/bin/python3
# View, edit and create openbox/labwc keybindings via a Qt5 GUI.

import os
import sys
import xml.etree.ElementTree as ET

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox
from PyQt5.uic import loadUi

NS = "http://openbox.org/3.4/rc"
NSP = f"{{{NS}}}"
DEFAULT_CONFIG_PATH = "~/.config/labwc/rc.xml"


class KeybinderDialog(QDialog):
    def __init__(self):
        super().__init__()
        ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keybinder.ui")
        loadUi(ui_path, self)

        self.config_path = os.path.expanduser(DEFAULT_CONFIG_PATH)
        self.tree = None
        self.root = None

        self.model = QStandardItemModel()
        self.Keybinds_list.setModel(self.model)

        self.AddKeybind_btn.clicked.connect(self.add_keybind)
        self.RemoveKeybind_btn.clicked.connect(self.remove_keybind)
        self.Update_btn.clicked.connect(self.update_keybind)
        self.Load_btn.clicked.connect(self.load_config)
        self.FileChooser_btn.clicked.connect(self.choose_file)
        self.Keybinds_list.clicked.connect(self.on_keybind_selected)

        if os.path.exists(self.config_path):
            self.load_from_path(self.config_path)
        else:
            QMessageBox.information(
                self,
                "Config not found",
                f"Default config not found:\n{self.config_path}\n\n"
                'Use "Load Keybinds" to open a file.',
            )

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def load_from_path(self, path):
        ET.register_namespace("", NS)
        try:
            self.tree = ET.parse(path)
            self.root = self.tree.getroot()
            self.config_path = path
            self.populate_list()
        except ET.ParseError as e:
            QMessageBox.critical(self, "Parse Error", f"Failed to parse config:\n{e}")
            self.tree = None
            self.root = None

    def save_config(self):
        ET.register_namespace("", NS)
        try:
            self.tree.write(self.config_path, xml_declaration=True, encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save config:\n{e}")

    # ------------------------------------------------------------------
    # List population
    # ------------------------------------------------------------------

    def populate_list(self):
        self.model.clear()
        keyboard = self.root.find(f"{NSP}keyboard")
        if keyboard is None:
            return
        for kb in keyboard.findall(f"{NSP}keybind"):
            key = kb.get("key", "")
            command = ""
            action = kb.find(f"{NSP}action")
            if action is not None:
                cmd_el = action.find(f"{NSP}command")
                if cmd_el is not None and cmd_el.text:
                    command = cmd_el.text
            item = QStandardItem(f"{key}  →  {command}")
            item.setData((key, command), Qt.UserRole)
            item.setEditable(False)
            self.model.appendRow(item)

    # ------------------------------------------------------------------
    # UI slots
    # ------------------------------------------------------------------

    def on_keybind_selected(self, index):
        item = self.model.itemFromIndex(index)
        if item:
            key, command = item.data(Qt.UserRole)
            self.Keybind_edit.setPlainText(key)
            self.ExecuteFile_edit.setPlainText(command)

    def add_keybind(self):
        if self.tree is None:
            QMessageBox.warning(self, "No Config", "No configuration file loaded.")
            return
        key = self.Keybind_edit.toPlainText().strip()
        command = self.ExecuteFile_edit.toPlainText().strip()
        if not key or not command:
            QMessageBox.warning(
                self, "Input Error", "Both Keybind and Execute file must be filled in."
            )
            return
        keyboard = self._get_keyboard()
        for kb in keyboard.findall(f"{NSP}keybind"):
            if kb.get("key") == key:
                QMessageBox.warning(
                    self,
                    "Duplicate",
                    f"Keybind '{key}' already exists.\nUse Update to modify it.",
                )
                return
        kb_el = ET.SubElement(keyboard, f"{NSP}keybind", key=key)
        action_el = ET.SubElement(kb_el, f"{NSP}action", name="Execute")
        cmd_el = ET.SubElement(action_el, f"{NSP}command")
        cmd_el.text = command
        self.save_config()
        self.populate_list()
        self.Keybind_edit.clear()
        self.ExecuteFile_edit.clear()

    def remove_keybind(self):
        indexes = self.Keybinds_list.selectedIndexes()
        if not indexes:
            QMessageBox.warning(self, "No Selection", "Select a keybind to remove.")
            return
        item = self.model.itemFromIndex(indexes[0])
        key, _ = item.data(Qt.UserRole)
        keyboard = self._get_keyboard()
        for kb in keyboard.findall(f"{NSP}keybind"):
            if kb.get("key") == key:
                keyboard.remove(kb)
                break
        self.save_config()
        self.populate_list()
        self.Keybind_edit.clear()
        self.ExecuteFile_edit.clear()

    def update_keybind(self):
        indexes = self.Keybinds_list.selectedIndexes()
        if not indexes:
            QMessageBox.warning(self, "No Selection", "Select a keybind to update.")
            return
        item = self.model.itemFromIndex(indexes[0])
        old_key, _ = item.data(Qt.UserRole)
        new_key = self.Keybind_edit.toPlainText().strip()
        new_command = self.ExecuteFile_edit.toPlainText().strip()
        if not new_key or not new_command:
            QMessageBox.warning(
                self, "Input Error", "Both Keybind and Execute file must be filled in."
            )
            return
        keyboard = self._get_keyboard()
        for kb in keyboard.findall(f"{NSP}keybind"):
            if kb.get("key") == old_key:
                kb.set("key", new_key)
                action_el = kb.find(f"{NSP}action")
                if action_el is None:
                    action_el = ET.SubElement(kb, f"{NSP}action", name="Execute")
                cmd_el = action_el.find(f"{NSP}command")
                if cmd_el is None:
                    cmd_el = ET.SubElement(action_el, f"{NSP}command")
                cmd_el.text = new_command
                break
        self.save_config()
        self.populate_list()

    def load_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Config File",
            os.path.expanduser("~"),
            "XML Files (*.xml);;All Files (*)",
        )
        if path:
            self.load_from_path(path)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose Executable", os.path.expanduser("~"), "All Files (*)"
        )
        if path:
            self.ExecuteFile_edit.setPlainText(path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_keyboard(self):
        kb_el = self.root.find(f"{NSP}keyboard")
        if kb_el is None:
            kb_el = ET.SubElement(self.root, f"{NSP}keyboard")
        return kb_el


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = KeybinderDialog()
    dialog.show()
    sys.exit(app.exec_())