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
from datetime import datetime
from shutil import copytree
from packaging.utils import Version

import requests

# Import PySide6 modules before qdarkstyle to guide qtpy's binding detection
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget
import mainwindow
import qdarkstyle
import re

# Add QScrollArea import
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling) # Deprecated
app = QtWidgets.QApplication(sys.argv)


appversion = "1.12.1 (Unofficial Fork by Thane5)"
appversion = "1.11.0"
dir_ = ""
config = configparser.ConfigParser()
btn = {}
lastversion = ""
installedversion = ""
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

    def __init__(self, url, file):
        super(WorkerThread, self).__init__(parent=app)
        self.filename = file
        self.url = url
        if "macOS" in file:
            config.set("main", "lastdl", "OSX")
            with open("config.ini", "w") as f:
                config.write(f)
                f.close()
        elif "win32" in file:
            config.set("main", "lastdl", "Windows 32bit")
            with open("config.ini", "w") as f:
                config.write(f)
                f.close()
        elif "win64" in file:
            config.set("main", "lastdl", "Windows 64bit")
            with open("config.ini", "w") as f:
                config.write(f)
                f.close()
        elif "glibc211-i686" in file:
            config.set("main", "lastdl", "Linux glibc211 i686")
            with open("config.ini", "w") as f:
                config.write(f)
                f.close()
        elif "glibc211-x86_64" in file:
            config.set("main", "lastdl", "Linux glibc211 x86_64")
            with open("config.ini", "w") as f:
                config.write(f)
                f.close()
        elif "glibc219-i686" in file:
            config.set("main", "lastdl", "Linux glibc219 i686")
            with open("config.ini", "w") as f:
                config.write(f)
                f.close()
        elif "glibc219-x86_64" in file:
            config.set("main", "lastdl", "Linux glibc219 x86_64")
            with open("config.ini", "w") as f:
                config.write(f)
                f.close()

    def progress(self, count, blockSize, totalSize):
        """Updates progress bar"""
        percent = int(count * blockSize * 100 / totalSize)
        self.update.emit(percent)

    def run(self):
        """
        It downloads the file, emits a signal when it's done, and then unpacks the file
        """
        urllib.request.urlretrieve(self.url, self.filename, reporthook=self.progress)
        self.finishedDL.emit()
        shutil.unpack_archive(self.filename, "./blendertemp/")
        self.finishedEX.emit()
        source = next(os.walk("./blendertemp/"))[1]
        copytree(os.path.join("./blendertemp/", source[0]), dir_, dirs_exist_ok=True)
        self.finishedCP.emit()
        shutil.rmtree("./blendertemp")
        self.finishedCL.emit()


class BlenderUpdater(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        logger.info(f"Running version {appversion}")
        logger.debug("Constructing UI")
        super(BlenderUpdater, self).__init__(parent)
        self.setupUi(self)
        
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
        global lastversion
        global dir_
        global config
        global installedversion
        if os.path.isfile("./config.ini"):
            config_exist = True
            logger.info("Reading existing configuration file")
            config.read("config.ini")
            dir_ = config.get("main", "path")
            lastcheck = config.get("main", "lastcheck")
            lastversion = config.get("main", "lastdl")
            installedversion = config.get("main", "installed")
            flavor = config.get("main", "flavor")
            if lastversion != "":
                self.btn_oneclick.setText(f"{flavor} | {lastversion}")
            else:
                pass

        else:
            logger.debug("No previous config found")
            self.btn_oneclick.hide()
            config_exist = False
            config.read("config.ini")
            config.add_section("main")
            config.set("main", "path", "")
            lastcheck = "Never"
            config.set("main", "lastcheck", lastcheck)
            config.set("main", "lastdl", "")
            config.set("main", "installed", "")
            config.set("main", "flavor", "")
            config.set("main", "os_filter", "all")
            with open("config.ini", "w") as f:
                config.write(f)
        if config_exist:
            self.line_path.setText(dir_)
        else:
            pass
        dir_ = self.line_path.text()
        self.btn_cancel.hide()
        self.frm_progress.hide()
        self.btngrp_filter.hide()
        self.btn_Check.setFocus()
        self.lbl_available.hide()
        self.progressBar.setValue(0)
        self.progressBar.hide()
        self.lbl_task.hide()
        self.statusbar.showMessage(f"Ready - Last check: {lastcheck}")
        self.btn_Quit.clicked.connect(QtCore.QCoreApplication.instance().quit)
        self.btn_Check.clicked.connect(self.check_dir)
        self.btn_about.clicked.connect(self.about)
        self.btn_path.clicked.connect(self.select_path)
        # Connect filter buttons signals once during initialization
        self.btn_osx.clicked.connect(self.filterosx)
        self.btn_linux.clicked.connect(self.filterlinux)
        self.btn_windows.clicked.connect(self.filterwindows)
        self.btn_allos.clicked.connect(self.filterall)

        # Check internet connection, disable SSL
        # FIXME - should be changed! (preliminary fix to work in OSX)
        ssl._create_default_https_context = ssl._create_unverified_context
        try:
            _ = requests.get("http://www.github.com")
        except Exception:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Please check your internet connection"
            )
            logger.critical("No internet connection")
        # Check for new version on github
        try:
            Appupdate = requests.get(
                "https://api.github.com/repos/overmindstudios/BlenderUpdater/releases/latest"
            ).text
            logger.info("Getting update info - success")
        except Exception:
            logger.error("Unable to get update information from GitHub")

        try:
            UpdateData = json.loads(Appupdate)
            applatestversion = UpdateData["tag_name"]
            logger.info(f"Version found online: {applatestversion}")
            if Version(applatestversion) > Version(appversion):
                logger.info("Newer version found on Github")
                self.btn_newVersion.clicked.connect(self.getAppUpdate)
                self.btn_newVersion.setStyleSheet("background: rgb(73, 50, 20)")
                self.btn_newVersion.show()
        except Exception:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Unable to get Github update information"
            )

    def select_path(self):
        global dir_
        dir_ = QtWidgets.QFileDialog.getExistingDirectory(
            None, "Select a folder:", "C:\\", QtWidgets.QFileDialog.ShowDirsOnly
        )
        if dir_:
            self.line_path.setText(dir_)
        else:
            pass

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
        global dir_
        dir_ = self.line_path.text()
        if not os.path.exists(dir_):
            QtWidgets.QMessageBox.about(
                self,
                "Directory not set",
                "Please choose a valid destination directory first",
            )
            logger.error("No valid directory")
        else:
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
        global dir_
        global lastversion
        global installedversion
        dir_ = self.line_path.text()
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
        # Do path settings save here, in case user has manually edited it
        global config
        config.read("config.ini")
        config.set("main", "path", dir_)
        with open("config.ini", "w") as f:
            config.write(f)
        f.close()
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
        config.read("config.ini")
        config.set("main", "lastcheck", str(lastcheck))
        with open("config.ini", "w") as f:
            config.write(f)
        f.close()
        
        # Apply saved filter preference instead of just showing all
        saved_filter = config.get("main", "os_filter")
        if saved_filter == "windows":
            self.btn_windows.setChecked(True)
            self.filterwindows()
        elif saved_filter == "darwin":
            self.btn_osx.setChecked(True)
            self.filterosx()
        elif saved_filter == "linux":
            self.btn_linux.setChecked(True)
            self.filterlinux()
        else:  # Default or "all"
            self.btn_allos.setChecked(True)
            self.filterall()

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
        global dir_

        url = "https://builder.blender.org/download/daily/" + entry

        if entry == installedversion:
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
        totalsize = file.info()["Content-Length"]
        size_readable = self.hbytes(float(totalsize))

        global config
        config.read("config.ini")
        config.set("main", "path", dir_)
        config.set("main", "flavor", entry)
        config.set("main", "installed", entry)

        with open("config.ini", "w") as f:
            config.write(f)
        f.close()

        ##########################
        # Do the actual download #
        ##########################

        dir_ = os.path.join(dir_, "")
        filename = "./blendertemp/" + entry

        for i in btn:
            btn[i].hide()
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

        thread = WorkerThread(url, filename)
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
        logger.info("Copying to " + dir_)
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        self.lbl_extract_pic.setPixmap(donepixmap)
        self.lbl_copy_pic.setPixmap(nowpixmap)
        self.lbl_copying.setText("<b>Copying</b>")
        self.lbl_task.setText("Copying files...")
        self.statusbar.showMessage(f"Copying files to {dir_}, please wait... ")

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
        self.btn_execute.show()
        opsys = platform.system()
        if opsys == "Windows":
            self.btn_execute.clicked.connect(self.exec_windows)
        if opsys.lower == "darwin":
            self.btn_execute.clicked.connect(self.exec_osx)
        if opsys == "Linux":
            self.btn_execute.clicked.connect(self.exec_linux)

    def exec_windows(self):
        _ = subprocess.Popen(os.path.join('"' + dir_ + "\\blender.exe" + '"'))
        logger.info(f"Executing {dir_}blender.exe")

    def exec_osx(self):
        BlenderOSXPath = os.path.join(
            '"' + dir_ + "\\blender.app/Contents/MacOS/blender" + '"'
        )
        os.system("chmod +x " + BlenderOSXPath)
        _ = subprocess.Popen(BlenderOSXPath)
        logger.info(f"Executing {BlenderOSXPath}")

    def exec_linux(self):
        _ = subprocess.Popen(os.path.join(f"{dir_}/blender"))
        logger.info(f"Executing {dir_}blender")

    def filterall(self):
        """Show all operating systems"""
        # Save the filter preference
        config.read("config.ini")
        config.set("main", "os_filter", "all")
        with open("config.ini", "w") as f:
            config.write(f)
        self.render_buttons(os_filter=[])

    def filterosx(self):
        """Show only macOS builds"""
        # Save the filter preference
        config.read("config.ini")
        config.set("main", "os_filter", "darwin")
        with open("config.ini", "w") as f:
            config.write(f)
        self.render_buttons(os_filter=["darwin"])

    def filterlinux(self):
        """Show only Linux builds"""
        # Save the filter preference
        config.read("config.ini")
        config.set("main", "os_filter", "linux")
        with open("config.ini", "w") as f:
            config.write(f)
        self.render_buttons(os_filter=["linux"])

    def filterwindows(self):
        """Show only Windows builds"""
        # Save the filter preference
        config.read("config.ini")
        config.set("main", "os_filter", "windows")
        with open("config.ini", "w") as f:
            config.write(f)
        self.render_buttons(os_filter=["windows"])

    # Also move render_buttons to be a class method
    def render_buttons(self, os_filter=["windows", "darwin", "linux"]):
        """Renders the download buttons on screen.

        os_filter: Will modify the buttons to be rendered.
                    If an empty list is being provided, all operating systems
                    will be shown.
        """
        # Generate buttons for downloadable versions.
        global btn
        opsys = platform.system()
        logger.info(f"Operating system: {opsys}")

        # Clear previous buttons
        for i in btn:
            btn[i].setParent(None)
            btn[i].deleteLater()

        # Clear layout
        while self.scrollLayout.count():
            child = self.scrollLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        btn = {}

        for index, entry in enumerate(self.finallist):  # Update to use self.finallist
            skip_entry = False

            # Skip based on os_filter entries
            if os_filter and any(filter not in entry for filter in os_filter):
                skip_entry = True

            if skip_entry:
                continue

            btn[index] = QtWidgets.QPushButton()
            buttontext = f"{entry}"
            logger.debug(buttontext)

            if "windows" in entry:
                btn[index].setIcon(self.windowsicon)  # Update to use self.windowsicon
            elif "darwin" in entry:
                btn[index].setIcon(self.appleicon)  # Update to use self.appleicon
            elif "linux" in entry:
                btn[index].setIcon(self.linuxicon)  # Update to use self.linuxicon

            btn[index].setIconSize(QtCore.QSize(24, 24))
            btn[index].setText(buttontext)
            btn[index].setFixedWidth(670)  # Slightly narrower to fit in scroll area
            btn[index].clicked.connect(
                lambda throwaway=0, entry=entry: self.download(entry)
            )

            # Add to the scroll layout instead of placing manually
            self.scrollLayout.addWidget(btn[index])

        # Add stretch at the end to push buttons to the top
        self.scrollLayout.addStretch()


def main():
    """
    This function creates an instance of the BlenderUpdater class and passes it to the Qt application
    """
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    window = BlenderUpdater()
    window.setWindowTitle(f"Overmind Studios Blender Updater {appversion}")
    window.statusbar.setSizeGripEnabled(False)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()