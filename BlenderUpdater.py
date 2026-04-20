"""
Copyright 2016-2019 Tobias Kummer/Overmind Studios.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import configparser
import hashlib
import json
import logging
import os
import os.path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from shutil import copytree

import qdarkstyle
import requests
from packaging.utils import Version

# Import PySide6 modules before qdarkstyle to guide qtpy's binding detection
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QRunnable, QThreadPool, Slot
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

import mainwindow

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

appversion = "1.13.0"

# Config keys
CONFIG_SECTION_MAIN = "main"
CONFIG_KEY_PATH = "path"
CONFIG_KEY_LAST_CHECK = "lastcheck"
CONFIG_KEY_LAST_DL_DESC = "lastdl_desc"
CONFIG_KEY_LAST_DL_FILENAME = "lastdl_filename"
CONFIG_KEY_INSTALLED_FILENAME = "installed_filename"
CONFIG_KEY_OS_FILTER = "os_filter"
CONFIG_FILE_NAME = "config.ini"

# URLs
BLENDER_DOWNLOAD_URL = "https://builder.blender.org/download/daily/"
GITHUB_CHECK_URL = "https://www.github.com"
GITHUB_RELEASES_API_URL = (
    "https://api.github.com/repos/overmindstudios/BlenderUpdater/releases/latest"
)
GITHUB_RELEASES_URL = (
    "https://github.com/overmindstudios/BlenderUpdater/releases/latest"
)

# Timeouts and sizes
DOWNLOAD_CHUNK_SIZE = 8192
CONNECTIVITY_TIMEOUT = 5
BUILD_CHECK_TIMEOUT = 15
DOWNLOAD_TIMEOUT = 10

# Sentinel value used to distinguish user cancellation from errors
CANCEL_MESSAGE = "__cancelled__"

OS_DESCRIPTIONS = {
    "darwin": "macOS",
    "windows": "Windows",
    "linux": "Linux",
}

LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"

logging.basicConfig(
    filename="BlenderUpdater.log", format=LOG_FORMAT, level=logging.DEBUG, filemode="a"
)

logger = logging.getLogger()


def _hbytes(num: float) -> str:
    if not isinstance(num, (int, float)):
        return "0 bytes"
    for unit in [" bytes", " KB", " MB", " GB"]:
        if num < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:3.1f} TB"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(DOWNLOAD_CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


class CheckWorker(QRunnable):
    """Worker for checking for new builds."""

    class WorkerSignals(QtCore.QObject):
        finished = QtCore.Signal(list, object)  # list of builds, error message or None

    def __init__(self, url, filename_regex, session):
        super().__init__()
        self.url = url
        self.filename_regex = filename_regex
        self.session = session
        self.signals = self.WorkerSignals()

    @Slot()
    def run(self):
        try:
            req = self.session.get(self.url, timeout=BUILD_CHECK_TIMEOUT)
            req.raise_for_status()

            filenames = self.filename_regex.findall(req.text)
            finallist = sorted(list(set(filenames)), reverse=True)
            self.signals.finished.emit(finallist, None)

        except requests.exceptions.RequestException as e:
            error_message = f"Error reaching server: {e}"
            logger.error(f"No connection to Blender nightly builds server: {e}")
            self.signals.finished.emit([], error_message)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            logger.error(error_message, exc_info=True)
            self.signals.finished.emit([], error_message)


class DownloadManager(QtCore.QObject):
    """Manages download and extraction process in the background."""

    progress = QtCore.Signal(int)
    finished = QtCore.Signal(bool, str)
    status_update = QtCore.Signal(str)

    def __init__(self, url, install_path, session, parent=None):
        super().__init__(parent)
        self.url = url
        self.install_path = install_path
        self.session = session
        self.threadpool = QThreadPool.globalInstance()
        self.temp_dir = None
        self._worker = None

    def start(self):
        try:
            self.temp_dir = tempfile.mkdtemp(prefix="blenderupdater-")
            logger.info(f"Created temporary directory: {self.temp_dir}")
            filename = os.path.basename(urllib.parse.urlparse(self.url).path)
            download_path = os.path.join(self.temp_dir, filename)

            self._worker = DownloadWorker(
                self.url, download_path, self.install_path, self.temp_dir, self.session
            )
            self._worker.signals.progress.connect(self.progress.emit)
            self._worker.signals.finished.connect(self.on_worker_finished)
            self._worker.signals.status_update.connect(self.status_update.emit)
            self._worker.signals.extraction_started.connect(self.parent().extraction)
            self._worker.signals.verification_started.connect(
                self.parent().verification
            )
            self._worker.signals.copying_started.connect(self.parent().finalcopy)
            self._worker.signals.cleanup_started.connect(self.parent().cleanup)
            self.threadpool.start(self._worker)
        except OSError as e:
            logger.error(f"Failed to start download: {e}", exc_info=True)
            self.finished.emit(False, str(e))

    def cancel(self):
        if self._worker is not None:
            self._worker.cancel()

    def on_worker_finished(self, success, message):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(
                    f"Successfully cleaned up temporary directory: {self.temp_dir}"
                )
            except OSError as e:
                logger.error(
                    f"Failed to clean up temporary directory {self.temp_dir}: {e}",
                    exc_info=True,
                )
        self.finished.emit(success, message)


class DownloadWorker(QRunnable):
    """Worker for handling the download and extraction."""

    class WorkerSignals(QtCore.QObject):
        progress = QtCore.Signal(int)
        finished = QtCore.Signal(bool, str)
        status_update = QtCore.Signal(str)
        extraction_started = QtCore.Signal()
        verification_started = QtCore.Signal()
        copying_started = QtCore.Signal()
        cleanup_started = QtCore.Signal()

    def __init__(self, url, download_path, install_path, temp_dir, session):
        super().__init__()
        self.url = url
        self.download_path = download_path
        self.install_path = install_path
        self.temp_dir = temp_dir
        self.session = session
        self._cancelled = False
        self.signals = self.WorkerSignals()

    def cancel(self):
        self._cancelled = True

    @Slot()
    def run(self):
        try:
            # Check available disk space before starting the download
            try:
                head_response = self.session.head(self.url, timeout=DOWNLOAD_TIMEOUT)
                content_length = int(head_response.headers.get("content-length", 0))
            except requests.exceptions.RequestException:
                content_length = 0

            if content_length > 0:
                free_space = shutil.disk_usage(
                    os.path.dirname(self.download_path)
                ).free
                if content_length > free_space:
                    raise OSError(
                        f"Insufficient disk space: {_hbytes(content_length)} needed, "
                        f"{_hbytes(free_space)} available"
                    )

            # Download
            response = self.session.get(self.url, stream=True, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            self.signals.status_update.emit(f"Downloading {_hbytes(total_size)}")

            with open(self.download_path, "wb") as f:
                downloaded_size = 0
                for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if self._cancelled:
                        self.signals.finished.emit(False, CANCEL_MESSAGE)
                        return
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if total_size > 0:
                        self.signals.progress.emit(
                            int(downloaded_size * 100 / total_size)
                        )

            # SHA256 verification
            self.signals.verification_started.emit()
            self.signals.status_update.emit("Verifying download integrity...")
            sha256_url = self.url + ".sha256"
            try:
                sha256_response = self.session.get(sha256_url, timeout=DOWNLOAD_TIMEOUT)
                sha256_response.raise_for_status()
                expected_hash = sha256_response.text.strip().split()[0]
                actual_hash = _sha256_file(self.download_path)
                if actual_hash != expected_hash:
                    raise ValueError(
                        f"SHA256 mismatch: expected {expected_hash}, got {actual_hash}"
                    )
                logger.info("SHA256 verification passed")
            except requests.exceptions.RequestException as e:
                logger.warning(f"SHA256 file unavailable, skipping verification: {e}")
            except IndexError:
                logger.warning("SHA256 file had unexpected format, skipping verification")

            # Extraction
            self.signals.extraction_started.emit()
            self.signals.status_update.emit("Extracting to temporary folder...")
            extract_dir = os.path.join(self.temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            shutil.unpack_archive(self.download_path, extract_dir)
            source_dir_name = next(os.walk(extract_dir))[1][0]
            source_path = os.path.join(extract_dir, source_dir_name)

            # Copying
            self.signals.copying_started.emit()
            copytree(source_path, self.install_path, dirs_exist_ok=True)

            # Cleanup (signal only; DownloadManager does the actual removal)
            self.signals.cleanup_started.emit()

            self.signals.finished.emit(True, "Download and extraction successful.")

        except (OSError, ValueError) as e:
            logger.error(f"Error in download worker: {e}", exc_info=True)
            self.signals.finished.emit(False, str(e))
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error in download worker: {e}", exc_info=True)
            self.signals.finished.emit(False, str(e))
        except Exception as e:
            logger.error(f"Unexpected error in download worker: {e}", exc_info=True)
            self.signals.finished.emit(False, str(e))


class BlenderUpdater(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        logger.info(f"Running version {appversion}")
        logger.debug("Constructing UI")
        super(BlenderUpdater, self).__init__(parent)
        self.config = configparser.ConfigParser()
        self.build_buttons = {}
        self.setupUi(self)
        self.session = requests.Session()
        self.filename_regex = re.compile(
            r'blender-\d+\.\d+[^"\s/]*\.(?:zip|tar\.xz|dmg|tar\.gz)'
        )
        self.threadpool = QThreadPool()
        logger.info(
            f"Multithreading with maximum {self.threadpool.maxThreadCount()} threads"
        )

        self.setStyleSheet("""
            QPushButton[highlight="true"][os="windows"] {
                background-color: #0078D4;
                color: white;
            }
            QPushButton[highlight="true"][os="macos"] {
                background-color: #A2A2A2;
                color: black;
            }
            QPushButton[highlight="true"][os="linux"] {
                background-color: #E95420;
                color: white;
            }
        """)

        self.scrollArea = QScrollArea(self.centralwidget)
        self.scrollArea.setGeometry(QtCore.QRect(6, 50, 686, 625))
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.scrollContent = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollContent)
        self.scrollLayout.setSpacing(2)
        self.scrollLayout.setContentsMargins(0, 0, 0, 0)

        self.scrollArea.setWidget(self.scrollContent)
        self.scrollArea.hide()

        self.btn_oneclick.hide()
        self.lbl_quick.hide()
        self.lbl_caution.hide()
        self.btn_newVersion.hide()
        self.btn_execute.hide()
        self.lbl_caution.setStyleSheet("background: rgb(255, 155, 8);\ncolor: white")

        self._load_config()
        self.install_path = self._get_config(CONFIG_KEY_PATH)
        self.line_path.setText(self.install_path)

        last_dl_filename = self._get_config(CONFIG_KEY_LAST_DL_FILENAME)
        last_dl_desc = self._get_config(CONFIG_KEY_LAST_DL_DESC)
        if last_dl_filename and last_dl_desc:
            self.btn_oneclick.setText(f"{last_dl_filename} | {last_dl_desc}")
            self.btn_oneclick.show()

        self.btn_cancel.hide()
        self.frm_progress.hide()
        self.btngrp_filter.hide()
        self.btn_Check.setFocus()
        self.lbl_available.hide()
        self.progressBar.setValue(0)
        self.progressBar.hide()
        self.lbl_task.hide()
        self.statusbar.showMessage(
            f"Ready - Last check: {self._get_config(CONFIG_KEY_LAST_CHECK)}"
        )
        self.btn_Quit.clicked.connect(QtCore.QCoreApplication.instance().quit)
        self.btn_Check.clicked.connect(self.check_dir)
        self.btn_about.clicked.connect(self.about)
        self.btn_path.clicked.connect(self.select_path)
        self.btn_cancel.clicked.connect(self.cancel_download)

        self.btn_osx.clicked.connect(lambda: self._set_os_filter("darwin"))
        self.btn_linux.clicked.connect(lambda: self._set_os_filter("linux"))
        self.btn_windows.clicked.connect(lambda: self._set_os_filter("windows"))
        self.btn_allos.clicked.connect(lambda: self._set_os_filter("all"))

        try:
            self.session.get(GITHUB_CHECK_URL, timeout=CONNECTIVITY_TIMEOUT)
        except requests.exceptions.RequestException:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Please check your internet connection"
            )
            logger.critical("No internet connection")

        try:
            response = self.session.get(GITHUB_RELEASES_API_URL)
            response.raise_for_status()
            update_data = response.json()
            logger.info("Reading existing configuration file")
            app_latest_version = update_data["tag_name"]
            logger.info(f"Version found online: {app_latest_version}")
            if Version(app_latest_version) > Version(appversion):
                logger.info("Newer version found on Github")
                self.btn_newVersion.clicked.connect(self.getAppUpdate)
                self.btn_newVersion.setStyleSheet("background: rgb(73, 50, 20)")
                self.btn_newVersion.show()
        except requests.exceptions.RequestException as e:
            logger.error(f"Unable to get update information from GitHub: {e}")
        except (KeyError, TypeError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing update information from GitHub: {e}")

    def _get_os_arch_details(self):
        """Returns highlighting details for builds matching the user's OS and architecture."""
        system = platform.system()
        machine = platform.machine()
        details = {"exact": None, "generic_os": None, "conflicting_arch_for_os": []}

        os_map = {
            "Windows": {
                "generic_os": "windows",
                "arch_map": {
                    "AMD64": ("windows.amd64", ["x86", "win32", "arm64"]),
                    "x86": ("windows.x86", ["amd64", "x64", "arm64"]),
                    "ARM64": ("windows.arm64", ["amd64", "x64", "x86", "win32"]),
                },
            },
            "Darwin": {
                "generic_os": "macos",
                "arch_map": {
                    "x86_64": ("macos.x86_64", ["arm64"]),
                    "arm64": ("macos.arm64", ["x86_64"]),
                },
            },
            "Linux": {
                "generic_os": "linux",
                "arch_map": {
                    "x86_64": ("linux.x86_64", ["aarch64"]),
                    "aarch64": ("linux.aarch64", ["x86_64"]),
                },
            },
        }

        if system in os_map:
            os_info = os_map[system]
            details["generic_os"] = os_info["generic_os"]
            if machine in os_info["arch_map"]:
                exact, conflicts = os_info["arch_map"][machine]
                details["exact"] = exact.lower()
                details["conflicting_arch_for_os"] = [c.lower() for c in conflicts]

        logger.debug(f"OS/Arch details for highlighting: {details}")
        return details

    def _load_config(self):
        if os.path.isfile(CONFIG_FILE_NAME):
            logger.info("Reading existing configuration file")
            self.config.read(CONFIG_FILE_NAME)
            if not self.config.has_section(CONFIG_SECTION_MAIN):
                self.config.add_section(CONFIG_SECTION_MAIN)
        else:
            logger.debug("No previous config found, creating default.")
            self.config.add_section(CONFIG_SECTION_MAIN)

        defaults = {
            CONFIG_KEY_PATH: "",
            CONFIG_KEY_LAST_CHECK: "Never",
            CONFIG_KEY_LAST_DL_DESC: "",
            CONFIG_KEY_LAST_DL_FILENAME: "",
            CONFIG_KEY_INSTALLED_FILENAME: "",
            CONFIG_KEY_OS_FILTER: "all",
        }
        for key, value in defaults.items():
            if not self.config.has_option(CONFIG_SECTION_MAIN, key):
                self.config.set(CONFIG_SECTION_MAIN, key, value)
        self._save_config()

    def _get_config(self, key, default=""):
        return self.config.get(CONFIG_SECTION_MAIN, key, fallback=default)

    def _update_config(self, key, value):
        self.config.set(CONFIG_SECTION_MAIN, key, str(value))
        self._save_config()

    def _save_config(self):
        with open(CONFIG_FILE_NAME, "w") as f:
            self.config.write(f)

    def select_path(self):
        selected_dir = QtWidgets.QFileDialog.getExistingDirectory(
            None,
            "Select a folder:",
            self.install_path or "C:\\",
            QtWidgets.QFileDialog.ShowDirsOnly,
        )
        if selected_dir:
            self.install_path = selected_dir
            self.line_path.setText(self.install_path)
            self._update_config(CONFIG_KEY_PATH, self.install_path)

    def getAppUpdate(self):
        webbrowser.open(GITHUB_RELEASES_URL)

    def about(self):
        aboutText = (
            '<html><head/><body><p>Utility to update Blender to the latest buildbot version available at<br> \
        <a href="https://builder.blender.org/download/"><span style=" text-decoration: underline; color:#2980b9;">\
        https://builder.blender.org/download/</span></a></p><p><br/>Developed by Tobias Kummer for \
        <a href="http://www.overmind-studios.de"><span style="text-decoration:underline; color:#2980b9;"> \
        Overmind Studios</span></a></p><p>\
        Licensed under the <a href="https://www.gnu.org/licenses/gpl-3.0-standalone.html"><span style=" text-decoration:\
        underline; color:#2980b9;">GPL v3 license</span></a></p><p>Project home: \
        <a href="https://overmindstudios.github.io/BlenderUpdater/"><span style=" text-decoration:\
        underline; color:#2980b9;">https://overmindstudios.github.io/BlenderUpdater/</a></p> \
        <p style="text-align: center;"><a href="https://ko-fi.com/tobkum" target="_blank"> \
        <img src="qrc://newPrefix/images/orange_img.png"></a></p> \
        <p>Application version: '
            + appversion
            + "</p></body></html> "
        )
        QtWidgets.QMessageBox.about(self, "About", aboutText)

    def check_dir(self):
        self.install_path = self.line_path.text()
        if not os.path.isdir(self.install_path):
            QtWidgets.QMessageBox.about(
                self,
                "Directory not set",
                "Please choose a valid destination directory first",
            )
            logger.error("No valid directory")
        elif not os.access(self.install_path, os.W_OK):
            QtWidgets.QMessageBox.critical(
                self,
                "Permission Error",
                "The selected directory is not writable. Please choose a different directory.",
            )
            logger.error(f"Directory not writable: {self.install_path}")
        else:
            self._update_config(CONFIG_KEY_PATH, self.install_path)
            logger.info("Checking for Blender versions")
            self.start_check()

    def start_check(self):
        self.install_path = self.line_path.text()
        self._update_config(CONFIG_KEY_PATH, self.install_path)
        self.frm_start.hide()
        self.frm_progress.hide()
        self.btn_oneclick.hide()
        self.lbl_quick.hide()
        self.btn_newVersion.hide()
        self.progressBar.hide()
        self.lbl_task.hide()
        self.btn_execute.hide()
        self.scrollArea.hide()
        self.btngrp_filter.hide()
        self.lbl_available.hide()
        self.lbl_caution.hide()

        self.statusbar.showMessage("Checking for new builds...")
        self.btn_Check.setDisabled(True)

        worker = CheckWorker(BLENDER_DOWNLOAD_URL, self.filename_regex, self.session)
        worker.signals.finished.connect(self.on_check_finished)
        self.threadpool.start(worker)

    def on_check_finished(self, build_list, error):
        self.btn_Check.setDisabled(False)
        if error:
            self.statusbar.showMessage(str(error))
            self.frm_start.show()
            return

        self.finallist = build_list

        self.appleicon = QtGui.QIcon(":/newPrefix/images/Apple-icon.png")
        self.windowsicon = QtGui.QIcon(":/newPrefix/images/Windows-icon.png")
        self.linuxicon = QtGui.QIcon(":/newPrefix/images/Linux-icon.png")

        self.scrollArea.show()
        self.lbl_available.show()
        self.lbl_caution.show()
        self.btngrp_filter.show()

        lastcheck = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
        self.statusbar.showMessage(f"Ready - Last check: {str(lastcheck)}")
        self._update_config(CONFIG_KEY_LAST_CHECK, str(lastcheck))

        saved_filter = self._get_config(CONFIG_KEY_OS_FILTER, "all")
        if saved_filter == "windows":
            self.btn_windows.setChecked(True)
        elif saved_filter == "darwin":
            self.btn_osx.setChecked(True)
        elif saved_filter == "linux":
            self.btn_linux.setChecked(True)
        else:
            self.btn_allos.setChecked(True)
        self._set_os_filter(saved_filter)

    def download(self, entry):
        url = BLENDER_DOWNLOAD_URL + entry
        installed_filename = self._get_config(CONFIG_KEY_INSTALLED_FILENAME)

        if entry == installed_filename:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Warning",
                "This version is already installed. Do you still want to continue?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            logger.info("Duplicated version detected")
            if reply == QtWidgets.QMessageBox.No:
                logger.debug("Skipping download of existing version")
                self.scrollArea.show()
                return

        self._update_config(CONFIG_KEY_PATH, self.install_path)
        self._update_config(CONFIG_KEY_LAST_DL_FILENAME, entry)

        self.scrollArea.hide()
        self.lbl_available.hide()
        self.lbl_caution.hide()
        self.progressBar.show()
        self.btngrp_filter.hide()
        self.lbl_task.setText("Downloading")
        self.lbl_task.show()
        self.frm_progress.show()
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        self.lbl_download_pic.setPixmap(nowpixmap)
        self.lbl_downloading.setText(f"<b>Downloading {entry}</b>")
        self.progressBar.setValue(0)
        self.btn_Check.setDisabled(True)
        self.btn_Quit.setDisabled(True)
        self.btn_cancel.show()

        self.download_manager = DownloadManager(
            url, self.install_path, self.session, parent=self
        )
        self.download_manager.progress.connect(self.updatepb)
        self.download_manager.status_update.connect(self.statusbar.showMessage)
        self.download_manager.finished.connect(
            lambda success, msg: self.on_download_finished(success, msg, entry)
        )
        self.download_manager.start()

    def cancel_download(self):
        if hasattr(self, "download_manager"):
            self.download_manager.cancel()
        self.btn_cancel.hide()

    def on_download_finished(self, success, message, entry):
        self.btn_Check.setEnabled(True)
        self.btn_Quit.setEnabled(True)
        self.btn_cancel.hide()
        if success:
            logger.info("Download and extraction successful.")
            self.done(installed_entry_filename=entry)
        elif message == CANCEL_MESSAGE:
            logger.info("Download cancelled by user.")
            self.statusbar.showMessage("Download cancelled.")
            self.frm_progress.hide()
            self.scrollArea.show()
            self.btngrp_filter.show()
            self.lbl_available.show()
            self.lbl_caution.show()
        else:
            logger.error(f"Download or extraction failed: {message}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"An error occurred: {message}"
            )
            self.statusbar.showMessage("Error during download/extraction.")
            self.frm_progress.hide()
            self.scrollArea.show()
            self.btngrp_filter.show()
            self.lbl_available.show()
            self.lbl_caution.show()

    def updatepb(self, percent):
        self.progressBar.setValue(percent)

    def verification(self):
        logger.info("Verifying download")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        self.lbl_download_pic.setPixmap(donepixmap)
        self.lbl_verify_pic.setPixmap(nowpixmap)
        self.lbl_verification.setText("<b>Verifying</b>")
        self.lbl_task.setText("Verifying...")
        self.statusbar.showMessage("Verifying download integrity...")
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)

    def extraction(self):
        logger.info("Extracting to temp directory")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        self.lbl_verify_pic.setPixmap(donepixmap)
        self.lbl_extract_pic.setPixmap(nowpixmap)
        self.lbl_extraction.setText("<b>Extraction</b>")
        self.lbl_task.setText("Extracting...")
        self.statusbar.showMessage("Extracting to temporary folder, please wait...")

    def finalcopy(self):
        logger.info(f"Copying to {self.install_path}")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        self.lbl_extract_pic.setPixmap(donepixmap)
        self.lbl_copy_pic.setPixmap(nowpixmap)
        self.lbl_copying.setText("<b>Copying</b>")
        self.lbl_task.setText("Copying files...")
        self.statusbar.showMessage(
            f"Copying files to {self.install_path}, please wait..."
        )

    def cleanup(self):
        logger.info("Cleaning up temp files")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        self.lbl_copy_pic.setPixmap(donepixmap)
        self.lbl_clean_pic.setPixmap(nowpixmap)
        self.lbl_cleanup.setText("<b>Cleaning up</b>")
        self.lbl_task.setText("Cleaning up...")
        self.statusbar.showMessage("Cleaning temporary files")

    def done(self, installed_entry_filename):
        logger.info("Finished")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        self.lbl_clean_pic.setPixmap(donepixmap)
        self.statusbar.showMessage("Ready")
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(100)
        self.lbl_task.setText("Finished")
        self.btn_Quit.setEnabled(True)
        self.btn_Check.setEnabled(True)

        if installed_entry_filename:
            self._update_config(CONFIG_KEY_INSTALLED_FILENAME, installed_entry_filename)

        # Disconnect any previous handlers before connecting to avoid stacking
        try:
            self.btn_execute.clicked.disconnect()
        except RuntimeError:
            pass
        self.btn_execute.show()
        opsys = platform.system()
        if opsys == "Windows":
            self.btn_execute.clicked.connect(self.exec_windows)
        elif opsys == "Darwin":
            self.btn_execute.clicked.connect(self.exec_osx)
        elif opsys == "Linux":
            self.btn_execute.clicked.connect(self.exec_linux)

        last_dl_desc = self._get_config(CONFIG_KEY_LAST_DL_DESC)
        if last_dl_desc and installed_entry_filename:
            self.btn_oneclick.setText(f"{installed_entry_filename} | {last_dl_desc}")
            self.btn_oneclick.show()
            self.lbl_quick.show()
        else:
            self.btn_oneclick.hide()
            self.lbl_quick.hide()

    def exec_windows(self):
        blender_exe = Path(self.install_path) / "blender.exe"
        if blender_exe.exists():
            subprocess.Popen([str(blender_exe)])
            logger.info(f"Executing {blender_exe}")
        else:
            logger.error(f"Blender executable not found at {blender_exe}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Blender not found at {blender_exe}"
            )

    def exec_osx(self):
        blender_executable = (
            Path(self.install_path) / "blender.app" / "Contents" / "MacOS" / "blender"
        )
        if blender_executable.exists():
            try:
                current_mode = os.stat(str(blender_executable)).st_mode
                os.chmod(str(blender_executable), current_mode | 0o111)
                subprocess.Popen([str(blender_executable)])
                logger.info(f"Executing {blender_executable}")
            except OSError as e:
                logger.error(f"Failed to execute Blender on macOS: {e}")
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Failed to run Blender: {e}"
                )
        else:
            logger.error(f"Blender executable not found at {blender_executable}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Blender not found at {blender_executable}"
            )

    def exec_linux(self):
        blender_executable = Path(self.install_path) / "blender"
        if blender_executable.exists():
            try:
                current_mode = os.stat(str(blender_executable)).st_mode
                os.chmod(str(blender_executable), current_mode | 0o111)
                subprocess.Popen([str(blender_executable)])
                logger.info(f"Executing {blender_executable}")
            except OSError as e:
                logger.error(f"Failed to execute Blender on Linux: {e}")
                QtWidgets.QMessageBox.critical(
                    self, "Error", f"Failed to run Blender: {e}"
                )
        else:
            logger.error(f"Blender executable not found at {blender_executable}")
            QtWidgets.QMessageBox.critical(
                self, "Error", f"Blender not found at {blender_executable}"
            )

    def _set_os_filter(self, os_name_key):
        self._update_config(CONFIG_KEY_OS_FILTER, os_name_key)

        filter_map = {
            "all": [],
            "darwin": ["darwin", "macos"],
            "linux": ["linux"],
            "windows": ["windows", "win64", "win32"],
        }
        self.render_buttons(os_filter_keywords=filter_map.get(os_name_key.lower(), []))

    def render_buttons(self, os_filter_keywords=None):
        if os_filter_keywords is None:
            os_filter_keywords = []

        opsys = platform.system()
        logger.info(f"Operating system: {opsys}")

        while self.scrollLayout.count():
            child = self.scrollLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.build_buttons.clear()

        os_arch_details = self._get_os_arch_details()

        for index, entry_filename in enumerate(self.finallist):
            if os_filter_keywords and not any(
                keyword.lower() in entry_filename.lower()
                for keyword in os_filter_keywords
            ):
                continue

            self.build_buttons[index] = QtWidgets.QPushButton()

            entry_lower = entry_filename.lower()
            is_highlighted = False

            if os_arch_details["exact"] and os_arch_details["exact"] in entry_lower:
                is_highlighted = True
            elif (
                os_arch_details["generic_os"]
                and os_arch_details["generic_os"] in entry_lower
            ):
                if not any(
                    c in entry_lower
                    for c in os_arch_details["conflicting_arch_for_os"]
                ):
                    is_highlighted = True

            self.build_buttons[index].setProperty("highlight", is_highlighted)
            if is_highlighted:
                self.build_buttons[index].setProperty(
                    "os", os_arch_details["generic_os"]
                )

            if "macos" in entry_lower or "darwin" in entry_lower:
                self.build_buttons[index].setIcon(self.appleicon)
            elif "linux" in entry_lower:
                self.build_buttons[index].setIcon(self.linuxicon)
            elif (
                "windows" in entry_lower
                or "win64" in entry_lower
                or "win32" in entry_lower
            ):
                self.build_buttons[index].setIcon(self.windowsicon)

            self.build_buttons[index].setIconSize(QtCore.QSize(24, 24))
            self.build_buttons[index].setText(entry_filename)
            self.build_buttons[index].setFixedWidth(670)
            self.build_buttons[index].clicked.connect(
                lambda checked=False, filename=entry_filename: self.download(filename)
            )

            self.scrollLayout.addWidget(self.build_buttons[index])

        self.scrollLayout.addStretch()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = BlenderUpdater()
    window.setWindowTitle(f"Overmind Studios Blender Updater {appversion}")
    window.statusbar.setSizeGripEnabled(False)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
