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
import json
import logging
import os
import os.path
import platform
import shutil
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from datetime import datetime
from shutil import copytree
from packaging.utils import Version

import platform
import requests

# Import PySide6 modules before qdarkstyle to guide qtpy's binding detection
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget
import mainwindow
import qdarkstyle
import re

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

app = QtWidgets.QApplication(sys.argv)

appversion = "1.13.0"

# Constants for config
CONFIG_SECTION_MAIN = "main"
CONFIG_KEY_PATH = "path"
CONFIG_KEY_LAST_CHECK = "lastcheck"
CONFIG_KEY_LAST_DL_DESC = "lastdl_desc"  # Description of last download
CONFIG_KEY_LAST_DL_FILENAME = "lastdl_filename" # Filename of last downloaded/attempted
CONFIG_KEY_INSTALLED_FILENAME = "installed_filename" # Filename of successfully installed
CONFIG_KEY_OS_FILTER = "os_filter"
CONFIG_FILE_NAME = "config.ini"

# Default human-readable descriptions for OS/build types
OS_DESCRIPTIONS = {
    "darwin": "macOS", # For 'darwin' in filename
    "windows": "Windows", # For 'windows' in filename
    "linux": "Linux" # For 'linux' in filename
}

LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"

logging.basicConfig(
    filename="BlenderUpdater.log", format=LOG_FORMAT, level=logging.DEBUG, filemode="w"
)

logger = logging.getLogger()


class WorkerThread(QtCore.QThread):
    """Does all the actual work in the background, informs GUI about status"""

    update = QtCore.Signal(int)
    finishedDL = QtCore.Signal()
    finishedEX = QtCore.Signal()
    finishedCP = QtCore.Signal()
    finishedCL = QtCore.Signal()

    def __init__(self, url, file_path_to_download, config_updater_func, install_path):
        super(WorkerThread, self).__init__(parent=app)
        self.file_path_to_download = file_path_to_download
        self.url = url
        self._update_config = config_updater_func
        self.install_path = install_path
        self.filename_only = Path(file_path_to_download).name

        # Determine and save a description for the download
        # This is a simplified description based on major OS.
        # The original code had more granular descriptions based on glibc etc.
        # We can enhance this map if needed.
        last_dl_desc_map = {
            "macOS": "macOS", # Matches "darwin" internally
            "darwin": "macOS",
            "win32": "Windows 32bit",
            "win64": "Windows 64bit",
            "linux": "Linux", # Generic Linux
            # Add more specific glibc versions if necessary, e.g.:
            # "glibc219-x86_64": "Linux glibc219 x86_64",
        }
        for key_substring, desc_value in last_dl_desc_map.items():
            if key_substring.lower() in self.filename_only.lower():
                self._update_config(CONFIG_KEY_LAST_DL_DESC, desc_value)
                break

    def progress(self, count, blockSize, totalSize):
        """Updates progress bar"""
        percent = int(count * blockSize * 100 / totalSize)
        self.update.emit(percent)

    def run(self):
        """
        It downloads the file, emits a signal when it's done, and then unpacks the file
        """
        urllib.request.urlretrieve(self.url, self.file_path_to_download, reporthook=self.progress)
        self.finishedDL.emit()
        shutil.unpack_archive(self.file_path_to_download, "./blendertemp/")
        self.finishedEX.emit()
        source = next(os.walk("./blendertemp/"))[1]
        copytree(Path("./blendertemp/") / source[0], self.install_path, dirs_exist_ok=True)
        self.finishedCP.emit()
        shutil.rmtree("./blendertemp")
        self.finishedCL.emit()


class BlenderUpdater(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        logger.info(f"Running version {appversion}")
        logger.debug("Constructing UI")
        super(BlenderUpdater, self).__init__(parent)
        self.config = configparser.ConfigParser()
        self.build_buttons = {}
        self.setupUi(self)
        
        # Apply stylesheet for highlighting
        self.setStyleSheet(u"""
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

        # Create scroll area for the build buttons
        self.scrollArea = QScrollArea(self.centralwidget)
        self.scrollArea.setGeometry(QtCore.QRect(6, 50, 686, 625))  # Adjust height to leave space for buttons
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        
        # Create a container widget for the buttons
        self.scrollContent = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollContent)
        self.scrollLayout.setSpacing(2)
        self.scrollLayout.setContentsMargins(0, 0, 0, 0)
        
        # Set the scroll content widget
        self.scrollArea.setWidget(self.scrollContent)
        self.scrollArea.hide()  # Hide initially until needed
        
        # Rest of the initialization remains the same
        self.btn_oneclick.hide()
        self.lbl_quick.hide()
        self.lbl_caution.hide()
        self.btn_newVersion.hide()
        self.btn_execute.hide()
        self.lbl_caution.setStyleSheet("background: rgb(255, 155, 8);\n" "color: white")

        self._load_config()
        self.install_path = self._get_config(CONFIG_KEY_PATH)
        self.line_path.setText(self.install_path)

        last_dl_desc = self._get_config(CONFIG_KEY_LAST_DL_DESC)
        last_dl_filename = self._get_config(CONFIG_KEY_LAST_DL_FILENAME)

        if last_dl_filename and last_dl_desc:
            self.btn_oneclick.setText(f"{last_dl_filename} | {last_dl_desc}")
            # self.btn_oneclick.show() # Visibility handled later or in done()
        else:
            self.btn_oneclick.hide()

        self.btn_cancel.hide()
        self.frm_progress.hide()
        self.btngrp_filter.hide()
        self.btn_Check.setFocus()
        self.lbl_available.hide()
        self.progressBar.setValue(0)
        self.progressBar.hide()
        self.lbl_task.hide()
        self.statusbar.showMessage(f"Ready - Last check: {self._get_config(CONFIG_KEY_LAST_CHECK)}")
        self.btn_Quit.clicked.connect(QtCore.QCoreApplication.instance().quit)
        self.btn_Check.clicked.connect(self.check_dir)
        self.btn_about.clicked.connect(self.about)
        self.btn_path.clicked.connect(self.select_path)
        
        self.btn_osx.clicked.connect(lambda: self._set_os_filter("darwin"))
        self.btn_linux.clicked.connect(lambda: self._set_os_filter("linux"))
        self.btn_windows.clicked.connect(lambda: self._set_os_filter("windows"))
        self.btn_allos.clicked.connect(lambda: self._set_os_filter("all"))

        # Check internet connection, disable SSL
        # FIXME - should be changed! (preliminary fix to work in OSX)
        ssl._create_default_https_context = ssl._create_unverified_context
        try:
            _ = requests.get("https://www.github.com", timeout=5) # Use https and add timeout
        except requests.exceptions.RequestException:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Please check your internet connection"
            )
            logger.critical("No internet connection")
        # Check for new version on github
        try:
            response = requests.get(
                "https://api.github.com/repos/overmindstudios/BlenderUpdater/releases/latest"
            )
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            UpdateData = response.json()
            logger.info("Reading existing configuration file")
            applatestversion = UpdateData["tag_name"]
            logger.info(f"Version found online: {applatestversion}")
            if Version(applatestversion) > Version(appversion):
                logger.info("Newer version found on Github")
                self.btn_newVersion.clicked.connect(self.getAppUpdate)
                self.btn_newVersion.setStyleSheet("background: rgb(73, 50, 20)")
                self.btn_newVersion.show()
        except requests.exceptions.RequestException as e:
            logger.error(f"Unable to get update information from GitHub: {e}")
            # QtWidgets.QMessageBox.warning(self, "Update Check Failed",
            # "Could not check for application updates from GitHub.")
        except (KeyError, TypeError, json.JSONDecodeError) as e: # For issues with JSON structure or parsing
            logger.error(f"Error parsing update information from GitHub: {e}")
            # QtWidgets.QMessageBox.warning(self, "Update Check Error",
            # "Error parsing application update information.")

    def _get_os_arch_details(self):
        """
        Returns a dictionary with details for highlighting builds matching the user's OS and architecture.
        'exact': A specific string pattern for OS and architecture (e.g., "windows.amd64", "macos.arm64").
        'generic_os': A generic string for the OS (e.g., "windows", "macos", "linux").
        'conflicting_arch_for_os': A list of architecture strings that would conflict if found with 'generic_os'.
        """
        current_os_system = platform.system()
        current_arch_machine = platform.machine()
        details = {'exact': None, 'generic_os': None, 'conflicting_arch_for_os': []}

        if current_os_system == "Windows":
            details['generic_os'] = "windows"
            if current_arch_machine == "AMD64": # Common for 64-bit Windows
                details['exact'] = "windows.amd64"
                details['conflicting_arch_for_os'] = ["x86", "win32", "arm64"]
            elif current_arch_machine == "x86": # For 32-bit Windows
                details['exact'] = "windows.x86" # Assuming this pattern or "win32"
                details['conflicting_arch_for_os'] = ["amd64", "x64", "arm64"]
            elif current_arch_machine == "ARM64": # For Windows on ARM
                details['exact'] = "windows.arm64"
                details['conflicting_arch_for_os'] = ["amd64", "x64", "x86", "win32"]

        elif current_os_system == "Darwin":  # macOS
            details['generic_os'] = "macos"  # Blender filenames use "macos"
            if current_arch_machine == "x86_64": # Intel macOS
                details['exact'] = "macos.x86_64"
                details['conflicting_arch_for_os'] = ["arm64"]
            elif current_arch_machine == "arm64": # Apple Silicon macOS
                details['exact'] = "macos.arm64"
                details['conflicting_arch_for_os'] = ["x86_64"]

        elif current_os_system == "Linux":
            details['generic_os'] = "linux"
            if current_arch_machine == "x86_64":
                details['exact'] = "linux.x86_64"
                details['conflicting_arch_for_os'] = ["aarch64"]
            elif current_arch_machine == "aarch64": # For ARM Linux
                details['exact'] = "linux.aarch64"
                details['conflicting_arch_for_os'] = ["x86_64"]

        # Normalize all keywords to lowercase for case-insensitive matching
        if details['exact']:
            details['exact'] = details['exact'].lower()
        if details['generic_os']:
            details['generic_os'] = details['generic_os'].lower()
        details['conflicting_arch_for_os'] = [kw.lower() for kw in details['conflicting_arch_for_os']]

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
            None, "Select a folder:", self.install_path or "C:\\", QtWidgets.QFileDialog.ShowDirsOnly
        )
        if selected_dir:
            self.install_path = selected_dir
            self.line_path.setText(self.install_path)
            self._update_config(CONFIG_KEY_PATH, self.install_path)

    def getAppUpdate(self):
        webbrowser.open(
            "https://github.com/overmindstudios/BlenderUpdater/releases/latest"
        )

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
        """
        Check if a valid directory has been set by the user
        """
        self.install_path = self.line_path.text()
        if not os.path.exists(self.install_path):
            QtWidgets.QMessageBox.about(
                self,
                "Directory not set",
                "Please choose a valid destination directory first",
            )
            logger.error("No valid directory")
        else:
            self._update_config(CONFIG_KEY_PATH, self.install_path)
            logger.info("Checking for Blender versions")
            self.check()

    def hbytes(self, num):
        """
        Return a human readable file size
        
        :param num: The number of bytes to convert
        :return: a string of the number of bytes in a more human readable way.
        """
        for x in [" bytes", " KB", " MB", " GB"]:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, " TB")

    def check(self):
        self.install_path = self.line_path.text()
        self._update_config(CONFIG_KEY_PATH, self.install_path)
        self.frm_start.hide()
        self.frm_progress.hide()
        self.btn_oneclick.hide()
        self.lbl_quick.hide()
        self.btn_newVersion.hide()
        self.progressBar.hide()
        self.lbl_task.hide()
        self.btn_newVersion.hide()
        self.btn_execute.hide()

        # Reset filter button to "all OS" and ensure it's checked
        self.btn_allos.setChecked(True)

        # Show the scroll area for build buttons
        self.scrollArea.show()

        # Store these as instance variables so they can be accessed by render_buttons
        self.appleicon = QtGui.QIcon(":/newPrefix/images/Apple-icon.png")
        self.windowsicon = QtGui.QIcon(":/newPrefix/images/Windows-icon.png")
        self.linuxicon = QtGui.QIcon(":/newPrefix/images/Linux-icon.png")

        url = "https://builder.blender.org/download/"

        try:
            req = requests.get(url)
        except Exception:
            self.statusBar().showMessage(
                "Error reaching server - check your internet connection"
            )
            logger.error("No connection to Blender nightly builds server")
            self.frm_start.show()
            return

        # Rest of the existing code...

        # Parse and prepare the list of builds
        templist = []

        filenames = re.findall(
            r'blender-[^\s][^"]+',
            req.text,
        )

        for el in filenames:
            if "sha256" not in el and "/" not in el and "msi" not in el:
                templist.append(el)

        self.finallist = list(set(templist))  # Store as instance variable
        self.finallist.sort(reverse=True)

        # Connect the buttons to the class methods
        self.lbl_available.show()
        self.lbl_caution.show()
        self.btngrp_filter.show()

        lastcheck = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
        self.statusbar.showMessage(f"Ready - Last check: {str(lastcheck)}")
        self._update_config(CONFIG_KEY_LAST_CHECK, str(lastcheck))
        
        # Apply saved filter preference instead of just showing all
        saved_filter = self._get_config(CONFIG_KEY_OS_FILTER)
        if saved_filter == "windows":
            self.btn_windows.setChecked(True)
        elif saved_filter == "darwin":
            self.btn_osx.setChecked(True)
        elif saved_filter == "linux":
            self.btn_linux.setChecked(True)
        else:  # Default or "all"
            self.btn_allos.setChecked(True)
        self._set_os_filter(saved_filter)

    def download(self, entry):
        # Hide the scroll area during download
        self.scrollArea.hide()
        
        # The rest of the download method remains unchanged
        # ... (existing code)
        """
        Download the file
        
        :param entry: The version of Blender you want to download
        :return: Nothing.
        """
        url = "https://builder.blender.org/download/daily/" + entry
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
                return
            else:
                pass
        else:
            pass

        if os.path.isdir("./blendertemp"):
            shutil.rmtree("./blendertemp")

        os.makedirs("./blendertemp")
        file = urllib.request.urlopen(url)
        totalsize_str = file.info().get("Content-Length")
        size_readable = "Unknown size"
        if totalsize_str:
            size_readable = self.hbytes(float(totalsize_str))

        self._update_config(CONFIG_KEY_PATH, self.install_path)
        self._update_config(CONFIG_KEY_LAST_DL_FILENAME, entry)
        # CONFIG_KEY_INSTALLED_FILENAME will be updated in done() upon success

        ##########################
        # Do the actual download #
        ##########################
        download_target_path = Path("./blendertemp/") / entry

        # self.scrollArea.hide() # Already done at the start of the method
        logger.info(f"Starting download thread for {url}{entry}")

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
        self.statusbar.showMessage(f"Downloading {size_readable}")

        thread = WorkerThread(url, str(download_target_path), self._update_config, self.install_path)
        thread.update.connect(self.updatepb)
        thread.finishedDL.connect(self.extraction)
        thread.finishedEX.connect(self.finalcopy)
        thread.finishedCP.connect(self.cleanup)
        thread.finishedCL.connect(self.done)
        thread.start()

    def updatepb(self, percent):
        self.progressBar.setValue(percent)

    def extraction(self):
        """
        Extract the downloaded file to a temporary directory
        """
        logger.info("Extracting to temp directory")
        self.lbl_task.setText("Extracting...")
        self.btn_Quit.setEnabled(False)
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        self.lbl_download_pic.setPixmap(donepixmap)
        self.lbl_extract_pic.setPixmap(nowpixmap)
        self.lbl_extraction.setText("<b>Extraction</b>")
        self.statusbar.showMessage("Extracting to temporary folder, please wait...")
        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setValue(-1)

    def finalcopy(self):
        logger.info(f"Copying to {self.install_path}")
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        self.lbl_extract_pic.setPixmap(donepixmap)
        self.lbl_copy_pic.setPixmap(nowpixmap)
        self.lbl_copying.setText("<b>Copying</b>")
        self.lbl_task.setText("Copying files...")
        self.statusbar.showMessage(f"Copying files to {self.install_path}, please wait... ")

    def cleanup(self):
        logger.info("Cleaning up temp files")
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        self.lbl_copy_pic.setPixmap(donepixmap)
        self.lbl_clean_pic.setPixmap(nowpixmap)
        self.lbl_cleanup.setText("<b>Cleaning up</b>")
        self.lbl_task.setText("Cleaning up...")
        self.statusbar.showMessage("Cleaning temporary files")

    def done(self):
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

        # Update installed version in config
        # Assuming 'entry' from the download context is what was installed.
        # This needs to be available here, or passed through signals, or retrieved from last_dl_filename.
        # For simplicity, let's assume the last downloaded filename is the one installed.
        installed_entry_filename = self._get_config(CONFIG_KEY_LAST_DL_FILENAME)
        if installed_entry_filename:
            self._update_config(CONFIG_KEY_INSTALLED_FILENAME, installed_entry_filename)

        self.btn_execute.show()
        opsys = platform.system()
        if opsys == "Windows":
            self.btn_execute.clicked.connect(self.exec_windows)
        elif opsys == "Darwin": # platform.system() returns "Darwin" for macOS
            self.btn_execute.clicked.connect(self.exec_osx)
        elif opsys == "Linux":
            self.btn_execute.clicked.connect(self.exec_linux)
        
        # Update and show one-click button
        last_dl_desc = self._get_config(CONFIG_KEY_LAST_DL_DESC)
        # last_dl_filename is already 'installed_entry_filename'
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
            QtWidgets.QMessageBox.critical(self, "Error", f"Blender not found at {blender_exe}")

    def exec_osx(self):
        blender_executable = Path(self.install_path) / "blender.app" / "Contents" / "MacOS" / "blender"
        if blender_executable.exists():
            try:
                current_mode = os.stat(str(blender_executable)).st_mode
                os.chmod(str(blender_executable), current_mode | 0o111) # Add execute for user/group/other
                subprocess.Popen([str(blender_executable)])
                logger.info(f"Executing {blender_executable}")
            except Exception as e:
                logger.error(f"Failed to execute Blender on macOS: {e}")
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to run Blender: {e}")
        else:
            logger.error(f"Blender executable not found at {blender_executable}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Blender not found at {blender_executable}")

    def exec_linux(self):
        blender_executable = Path(self.install_path) / "blender"
        if blender_executable.exists():
            try:
                current_mode = os.stat(str(blender_executable)).st_mode
                os.chmod(str(blender_executable), current_mode | 0o111)
                subprocess.Popen([str(blender_executable)])
                logger.info(f"Executing {blender_executable}")
            except Exception as e:
                logger.error(f"Failed to execute Blender on Linux: {e}")
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to run Blender: {e}")
        else:
            logger.error(f"Blender executable not found at {blender_executable}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Blender not found at {blender_executable}")

    def _set_os_filter(self, os_name_key):
        """Applies OS filter and saves preference."""
        self._update_config(CONFIG_KEY_OS_FILTER, os_name_key)
        
        filter_map = {
            "all": [], # Empty list means no OS filtering, show all
            "darwin": ["darwin", "macos"],
            "linux": ["linux"],
            "windows": ["windows", "win64", "win32"]
        }
        self.render_buttons(os_filter_keywords=filter_map.get(os_name_key.lower(), []))

    # Also move render_buttons to be a class method
    def render_buttons(self, os_filter_keywords=None):
        """Renders the download buttons on screen.

        os_filter: Will modify the buttons to be rendered.
                    If an empty list is being provided, all operating systems
                    will be shown.
        """
        # Generate buttons for downloadable versions.
        if os_filter_keywords is None:
            os_filter_keywords = []
            
        opsys = platform.system()
        logger.info(f"Operating system: {opsys}")

        # Clear previous buttons
        while self.scrollLayout.count():
            child = self.scrollLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.build_buttons.clear()

        # Get keywords for the current OS and architecture for highlighting
        os_arch_details = self._get_os_arch_details()
        # logger.debug already called in _get_os_arch_details

        # Map OS keywords to icons
        os_icon_map = {
            "windows": self.windowsicon,
            "win64": self.windowsicon,
            "win32": self.windowsicon,
            "darwin": self.appleicon,
            "linux": self.linuxicon,
        }
        for index, entry_filename in enumerate(self.finallist):
            skip_entry = False

            if os_filter_keywords: # If there are keywords to filter by
                # Entry must contain at least one of the keywords for its OS group
                if not any(keyword.lower() in entry_filename.lower() for keyword in os_filter_keywords):
                    skip_entry = True

            if skip_entry:
                continue

            self.build_buttons[index] = QtWidgets.QPushButton()
            
            entry_lower = entry_filename.lower()
            is_highlighted = False

            # 1. Check for exact OS and Arch match
            if os_arch_details['exact'] and os_arch_details['exact'] in entry_lower:
                is_highlighted = True
            # 2. If no exact match, check for generic OS match WITHOUT conflicting architectures
            elif os_arch_details['generic_os'] and os_arch_details['generic_os'] in entry_lower:
                has_conflicting_arch_marker_in_filename = False
                if os_arch_details['conflicting_arch_for_os']:
                    for conf_arch_kw in os_arch_details['conflicting_arch_for_os']:
                        if conf_arch_kw in entry_lower:
                            has_conflicting_arch_marker_in_filename = True
                            break
                
                if not has_conflicting_arch_marker_in_filename:
                    is_highlighted = True

            self.build_buttons[index].setProperty("highlight", is_highlighted)
            if is_highlighted:
                self.build_buttons[index].setProperty("os", os_arch_details['generic_os'])

            # Icon assignment based on filename content (more robust might use os_arch_details['generic_os'])
            if "macos" in entry_lower or "darwin" in entry_lower: # "darwin" for older compatibility if any
                self.build_buttons[index].setIcon(self.appleicon)
            elif "linux" in entry_lower:
                self.build_buttons[index].setIcon(self.linuxicon)
            elif "windows" in entry_lower or "win64" in entry_lower or "win32" in entry_lower:
                self.build_buttons[index].setIcon(self.windowsicon)

            self.build_buttons[index].setIconSize(QtCore.QSize(24, 24))
            self.build_buttons[index].setText(entry_filename)
            self.build_buttons[index].setFixedWidth(670)
            self.build_buttons[index].clicked.connect(
                lambda checked=False, filename=entry_filename: self.download(filename)
            )

            # Add to the scroll layout instead of placing manually
            self.scrollLayout.addWidget(self.build_buttons[index])

        # Add stretch at the end to push buttons to the top
        self.scrollLayout.addStretch()


def main():
    """
    This function creates an instance of the BlenderUpdater class and passes it to the Qt application
    """
    window = BlenderUpdater()
    window.setWindowTitle(f"Overmind Studios Blender Updater {appversion}")
    window.statusbar.setSizeGripEnabled(False)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()