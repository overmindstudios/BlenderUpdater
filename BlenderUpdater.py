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
from distutils.dir_util import copy_tree
from distutils.version import StrictVersion

import requests
from bs4 import BeautifulSoup

import mainwindow
import qdarkstyle

from PySide2 import QtWidgets, QtCore, QtGui

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

app = QtWidgets.QApplication(sys.argv)

app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)

appversion = "1.9.6"
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
        """
        Initialize config file.

        Args:
            self: (todo): write your description
            url: (str): write your description
            file: (str): write your description
        """
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
        Run the archive

        Args:
            self: (todo): write your description
        """
        urllib.request.urlretrieve(self.url, self.filename, reporthook=self.progress)
        self.finishedDL.emit()
        shutil.unpack_archive(self.filename, "./blendertemp/")
        self.finishedEX.emit()
        source = next(os.walk("./blendertemp/"))[1]
        copy_tree(os.path.join("./blendertemp/", source[0]), dir_)
        self.finishedCP.emit()
        shutil.rmtree("./blendertemp")
        self.finishedCL.emit()


class BlenderUpdater(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        """
        Init the global config.

        Args:
            self: (todo): write your description
            parent: (todo): write your description
        """
        logger.info(f"Running version {appversion}")
        logger.debug("Constructing UI")
        super(BlenderUpdater, self).__init__(parent)
        self.setupUi(self)
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
            if StrictVersion(applatestversion) > StrictVersion(appversion):
                logger.info("Newer version found on Github")
                self.btn_newVersion.clicked.connect(self.getAppUpdate)
                self.btn_newVersion.setStyleSheet("background: rgb(73, 50, 20)")
                self.btn_newVersion.show()
        except Exception:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Unable to get Github update information"
            )

    def select_path(self):
        """
        Select the path dialog.

        Args:
            self: (todo): write your description
        """
        global dir_
        dir_ = QtWidgets.QFileDialog.getExistingDirectory(
            None, "Select a folder:", "C:\\", QtWidgets.QFileDialog.ShowDirsOnly
        )
        if dir_:
            self.line_path.setText(dir_)
        else:
            pass

    def getAppUpdate(self):
        """
        Called when a browser

        Args:
            self: (todo): write your description
        """
        webbrowser.open(
            "https://github.com/overmindstudios/BlenderUpdater/releases/latest"
        )

    def about(self):
        """
        Prints a text message

        Args:
            self: (todo): write your description
        """
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
        """Check if a vaild directory has been set by the user."""
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
        """Translate to human readable file size."""
        for x in [" bytes", " KB", " MB", " GB"]:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, " TB")

    def check(self):
        """
        Check the installed version checkversion.

        Args:
            self: (todo): write your description
        """
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

        appleicon = QtGui.QIcon(":/newPrefix/images/Apple-icon.png")
        windowsicon = QtGui.QIcon(":/newPrefix/images/Windows-icon.png")
        linuxicon = QtGui.QIcon(":/newPrefix/images/Linux-icon.png")
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
        soup = BeautifulSoup(req.text, "html.parser")

        # iterate through the found versions
        results = []
        for ul in soup.find("div", {"class": "page-footer-main-text"}).find_all("ul"):
            for li in ul.find_all("li", class_="os"):
                info = list()
                info.append(li.find("a", href=True)["href"])  # Download URL to build
                info.append(li.find("span", class_="size").text)  # Build file size
                info.append(li.find("small").text)  # Build date
                results.append(info)
            results = [
                [
                    item.strip().strip("\xa0") if item is not None else None
                    for item in sublist
                ]
                for sublist in results
            ]  # Removes spaces
        finallist = []
        for sub in results:
            sub = list(filter(None, sub))
            sub[0] = sub[0][10:]  # Remove redundant parts of the URL (download...)
            finallist.append(sub)
        finallist = list(filter(None, finallist))

        def filterall():
            """
            Filter out all available buttons

            Args:
            """
            # Generate buttons for downloadable versions.
            global btn
            opsys = platform.system()
            logger.info(f"Operating system: {opsys}")
            for i in btn:
                btn[i].hide()
            i = 0
            btn = {}
            for index, text in enumerate(finallist):
                btn[index] = QtWidgets.QPushButton(self)
                logger.debug(text[0] + " | " + text[1] + " | " + text[2])
                if "macOS" in text[0]:  # set icon according to OS
                    if opsys.lower == "darwin":
                        btn[index].setStyleSheet("background: rgb(22, 52, 73)")
                    btn[index].setIcon(appleicon)
                elif "linux" in text[0]:
                    if opsys == "Linux":
                        btn[index].setStyleSheet("background: rgb(22, 52, 73)")
                    btn[index].setIcon(linuxicon)
                elif "win" in text[0]:
                    if opsys == "Windows":
                        btn[index].setStyleSheet("background: rgb(22, 52, 73)")
                    btn[index].setIcon(windowsicon)

                version = str(text[0])
                variation = str(text[0])
                buttontext = str(text[0]) + " | " + str(text[1]) + " | " + str(text[2])
                btn[index].setIconSize(QtCore.QSize(24, 24))
                btn[index].setText(buttontext)
                btn[index].setFixedWidth(686)
                btn[index].move(6, 50 + i)
                i += 32
                btn[index].clicked.connect(
                    lambda throwaway=0, version=version: self.download(
                        version, variation
                    )
                )
                btn[index].show()

        def filterosx():
            """
            Filters outos

            Args:
            """
            global btn
            for i in btn:
                btn[i].hide()
            btn = {}
            i = 0
            for index, text in enumerate(finallist):
                btn[index] = QtWidgets.QPushButton(self)
                if "macOS" in text[0]:
                    btn[index].setIcon(appleicon)
                    version = str(text[0])
                    variation = str(text[0])
                    buttontext = (
                        str(text[0]) + " | " + str(text[1]) + " | " + str(text[2])
                    )
                    btn[index].setIconSize(QtCore.QSize(24, 24))
                    btn[index].setText(buttontext)
                    btn[index].setFixedWidth(686)
                    btn[index].move(6, 50 + i)
                    i += 32
                    btn[index].clicked.connect(
                        lambda throwaway=0, version=version: self.download(
                            version, variation
                        )
                    )
                    btn[index].show()

        def filterlinux():
            """
            Filter out all the text.

            Args:
            """
            global btn
            for i in btn:
                btn[i].hide()
            btn = {}
            i = 0
            for index, text in enumerate(finallist):
                btn[index] = QtWidgets.QPushButton(self)
                if "linux" in text[0]:
                    btn[index].setIcon(linuxicon)
                    version = str(text[0])
                    variation = str(text[0])
                    buttontext = (
                        str(text[0]) + " | " + str(text[1]) + " | " + str(text[2])
                    )
                    btn[index].setIconSize(QtCore.QSize(24, 24))
                    btn[index].setText(buttontext)
                    btn[index].setFixedWidth(686)
                    btn[index].move(6, 50 + i)
                    i += 32
                    btn[index].clicked.connect(
                        lambda throwaway=0, version=version: self.download(
                            version, variation
                        )
                    )
                    btn[index].show()

        def filterwindows():
            """
            Removes all the filter from the filter.

            Args:
            """
            global btn
            for i in btn:
                btn[i].hide()
            btn = {}
            i = 0
            for index, text in enumerate(finallist):
                btn[index] = QtWidgets.QPushButton(self)
                if "win" in text[0]:
                    btn[index].setIcon(windowsicon)
                    version = str(text[0])
                    variation = str(text[0])
                    buttontext = (
                        str(text[0]) + " | " + str(text[1]) + " | " + str(text[2])
                    )
                    btn[index].setIconSize(QtCore.QSize(24, 24))
                    btn[index].setText(" " + buttontext)
                    btn[index].setFixedWidth(686)
                    btn[index].move(6, 50 + i)
                    i += 32
                    btn[index].clicked.connect(
                        lambda throwaway=0, version=version: self.download(
                            version, variation
                        )
                    )
                    btn[index].show()

        self.lbl_available.show()
        self.lbl_caution.show()
        self.btngrp_filter.show()
        self.btn_osx.clicked.connect(filterosx)
        self.btn_linux.clicked.connect(filterlinux)
        self.btn_windows.clicked.connect(filterwindows)
        self.btn_allos.clicked.connect(filterall)
        lastcheck = datetime.now().strftime("%a %b %d %H:%M:%S %Y")
        self.statusbar.showMessage(f"Ready - Last check: {str(lastcheck)}")
        config.read("config.ini")
        config.set("main", "lastcheck", str(lastcheck))
        with open("config.ini", "w") as f:
            config.write(f)
        f.close()
        filterall()

    def download(self, version, variation):
        """Download routines."""
        global dir_
        url = "https://builder.blender.org/download/" + version
        if version == installedversion:
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
        config.set("main", "flavor", variation)
        config.set("main", "installed", version)
        with open("config.ini", "w") as f:
            config.write(f)
        f.close()
        """Do the actual download"""
        dir_ = os.path.join(dir_, "")
        filename = "./blendertemp/" + version
        for i in btn:
            btn[i].hide()
        logger.info(f"Starting download thread for {url}{version}")
        self.lbl_available.hide()
        self.lbl_caution.hide()
        self.progressBar.show()
        self.btngrp_filter.hide()
        self.lbl_task.setText("Downloading")
        self.lbl_task.show()
        self.frm_progress.show()
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        self.lbl_download_pic.setPixmap(nowpixmap)
        self.lbl_downloading.setText(f"<b>Downloading {version}</b>")
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
        """
        Updates the progress bar.

        Args:
            self: (todo): write your description
            percent: (float): write your description
        """
        self.progressBar.setValue(percent)

    def extraction(self):
        """
        Updates the progress bar.

        Args:
            self: (todo): write your description
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
        """
        Finalizes the thumbnail.

        Args:
            self: (todo): write your description
        """
        logger.info("Copying to " + dir_)
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        self.lbl_extract_pic.setPixmap(donepixmap)
        self.lbl_copy_pic.setPixmap(nowpixmap)
        self.lbl_copying.setText("<b>Copying</b>")
        self.lbl_task.setText("Copying files...")
        self.statusbar.showMessage(f"Copying files to {dir_}, please wait... ")

    def cleanup(self):
        """
        Cleanup the clipboard.

        Args:
            self: (todo): write your description
        """
        logger.info("Cleaning up temp files")
        nowpixmap = QtGui.QPixmap(":/newPrefix/images/Actions-arrow-right-icon.png")
        donepixmap = QtGui.QPixmap(":/newPrefix/images/Check-icon.png")
        self.lbl_copy_pic.setPixmap(donepixmap)
        self.lbl_clean_pic.setPixmap(nowpixmap)
        self.lbl_cleanup.setText("<b>Cleaning up</b>")
        self.lbl_task.setText("Cleaning up...")
        self.statusbar.showMessage("Cleaning temporary files")

    def done(self):
        """
        Connects the interface.

        Args:
            self: (todo): write your description
        """
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
        """
        Execute windows in windows.

        Args:
            self: (todo): write your description
        """
        _ = subprocess.Popen(os.path.join('"' + dir_ + "\\blender.exe" + '"'))
        logger.info(f"Executing {dir_}blender.exe")

    def exec_osx(self):
        """
        Execute osx osx and osx

        Args:
            self: (todo): write your description
        """
        BlenderOSXPath = os.path.join(
            '"' + dir_ + "\\blender.app/Contents/MacOS/blender" + '"'
        )
        os.system("chmod +x " + BlenderOSXPath)
        _ = subprocess.Popen(BlenderOSXPath)
        logger.info(f"Executing {BlenderOSXPath}")

    def exec_linux(self):
        """
        Execute linux executable

        Args:
            self: (todo): write your description
        """
        _ = subprocess.Popen(os.path.join(f"{dir_}/blender"))
        logger.info(f"Executing {dir_}blender")


def main():
    """
    Main function.

    Args:
    """
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyside2())
    window = BlenderUpdater()
    window.setWindowTitle(f"Overmind Studios Blender Updater {appversion}")
    window.statusbar.setSizeGripEnabled(False)
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
