"""Copyright 2016-2018 Tobias Kummer/Overmind Studios.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


from PyQt5 import QtWidgets, QtCore, QtGui
import os.path
from os import system
from bs4 import BeautifulSoup
import requests
import urllib.request
import urllib.parse
from datetime import datetime
import mainwindow
import configparser
import shutil
from distutils.dir_util import copy_tree
import sys
import platform
from distutils.version import StrictVersion
import json
import webbrowser
import logging
import ssl


app = QtWidgets.QApplication(sys.argv)
appversion = '1.6'
dir_ = ''
config = configparser.ConfigParser()
btn = {}
quicky = False
lastversion = ''
installedversion = ''
flavor = ''

LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"
logging.basicConfig(filename='BlenderUpdater.log',
                    format=LOG_FORMAT,
                    level=logging.DEBUG,
                    filemode='w')

logger = logging.getLogger()


class WorkerThread(QtCore.QThread):
    update = QtCore.pyqtSignal(int)
    finishedDL = QtCore.pyqtSignal()
    finishedEX = QtCore.pyqtSignal()
    finishedCP = QtCore.pyqtSignal()
    finishedCL = QtCore.pyqtSignal()

    def __init__(self, url, file):
        super(WorkerThread, self).__init__(parent=app)
        self.filename = file
        self.url = url
        if "OSX" in file:
            config.set('main', 'lastdl', 'OSX')
            with open('config.ini', 'w') as f:
                config.write(f)
                f.close()
        elif "win32" in file:
            config.set('main', 'lastdl', 'Windows 32bit')
            with open('config.ini', 'w') as f:
                config.write(f)
                f.close()
        elif "win64" in file:
            config.set('main', 'lastdl', 'Windows 64bit')
            with open('config.ini', 'w') as f:
                config.write(f)
                f.close()
        elif "glibc211-i686" in file:
            config.set('main', 'lastdl', 'Linux glibc211 i686')
            with open('config.ini', 'w') as f:
                config.write(f)
                f.close()
        elif "glibc211-x86_64" in file:
            config.set('main', 'lastdl', 'Linux glibc211 x86_64')
            with open('config.ini', 'w') as f:
                config.write(f)
                f.close()
        elif "glibc219-i686" in file:
            config.set('main', 'lastdl', 'Linux glibc219 i686')
            with open('config.ini', 'w') as f:
                config.write(f)
                f.close()
        elif "glibc219-x86_64" in file:
            config.set('main', 'lastdl', 'Linux glibc219 x86_64')
            with open('config.ini', 'w') as f:
                config.write(f)
                f.close()

    def progress(self, count, blockSize, totalSize):
        percent = int(count * blockSize * 100 / totalSize)
        self.update.emit(percent)

    def run(self):
        global quicky
        urllib.request.urlretrieve(self.url, self.filename,
                                   reporthook=self.progress)
        self.finishedDL.emit()
        shutil.unpack_archive(self.filename, './blendertemp/')
        self.finishedEX.emit()
        source = next(os.walk('./blendertemp/'))[1]
        copy_tree(os.path.join('./blendertemp/', source[0]), dir_)
        self.finishedCP.emit()
        shutil.rmtree('./blendertemp')
        quicky = False
        self.finishedCL.emit()


class BlenderUpdater(QtWidgets.QMainWindow, mainwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        logger.debug('Constructing UI')
        super(BlenderUpdater, self).__init__(parent)
        self.setupUi(self)
        self.btn_oneclick.hide()
        self.lbl_quick.hide()
        self.lbl_caution.hide()
        self.btn_newVersion.hide()
        self.btn_execute.hide()
        self.lbl_caution.setStyleSheet('background: rgb(255, 155, 8);\n'
                                       'color: white')
        global lastversion
        global dir_
        global config
        global installedversion
        global flavor
        global appversion
        if os.path.isfile('./config.ini'):
            config_exist = True
            logger.info('Reading existing configuration file')
            config.read('config.ini')
            dir_ = config.get('main', 'path')
            lastcheck = config.get('main', 'lastcheck')
            lastversion = config.get('main', 'lastdl')
            installedversion = config.get('main', 'installed')
            flavor = config.get('main', 'flavor')
            if lastversion is not '':
                self.btn_oneclick.setText(flavor + ' | ' + lastversion)
                self.btn_oneclick.clicked.connect(self.quickupdate)
                # self.btn_oneclick.show()
                # self.lbl_quick.show() Disable QuickUpdate for now
                # TODO re-implement Quickupdate, therefore refactor flavor
            else:
                pass

        else:
            logger.debug('No previous config found')
            self.btn_oneclick.hide()
            config_exist = False
            config.read('config.ini')
            config.add_section('main')
            config.set('main', 'path', '')
            lastcheck = 'Never'
            config.set('main', 'lastcheck', lastcheck)
            config.set('main', 'lastdl', '')
            config.set('main', 'installed', '')
            config.set('main', 'flavor', '')
            with open('config.ini', 'w') as f:
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
        self.statusbar.showMessage('Ready - Last check: ' + lastcheck)
        self.btn_Quit.clicked.connect(QtCore.QCoreApplication.instance().quit)
        self.btn_Check.clicked.connect(self.check_dir)
        self.btn_about.clicked.connect(self.about)
        self.btn_path.clicked.connect(self.select_path)
        """Checking internet connection"""
        ssl._create_default_https_context = ssl._create_unverified_context
        try:
            testConnection = urllib.request.urlopen("http://www.google.com")
        except Exception:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Please check your internet connection")
            logger.critical('No internet connection')
            sys.exit()
        # Check for new version on github
        try:
            Appupdate = urllib.request.urlopen('https://api.github.com/repos/overmindstudios/BlenderUpdater/releases/latest').read().decode('utf-8')
        except Exception:
            QtWidgets.QMessageBox.critical(
                self, "Error", "Unable to get update information")
            logger.error('Unable to get update information from GitHub')
        UpdateData = json.loads(Appupdate)
        applatestversion = UpdateData['tag_name']
        # print(UpdateData['tag_name'])
        if StrictVersion(applatestversion) > StrictVersion(appversion):
            logger.info('Updated version found on Github')
            self.btn_newVersion.clicked.connect(self.getAppUpdate)
            self.btn_newVersion.show()

    def select_path(self):
        global dir_
        dir_ = QtWidgets.QFileDialog.getExistingDirectory(
            None, 'Select a folder:',
            'C:\\', QtWidgets.QFileDialog.ShowDirsOnly)
        if dir_:
            self.line_path.setText(dir_)
        else:
            pass

    def getAppUpdate(self):
        webbrowser.open("https://github.com/overmindstudios/BlenderUpdater/releases/latest")

    def about(self):
        aboutText = '<html><head/><body><p>Utility to update Blender to the latest buildbot version available at \
        <a href="https://builder.blender.org/download/"><span style=" text-decoration: underline; color:#2980b9;">\
        https://builder.blender.org/download/</span></a></p><p><br/>Developed by Tobias Kummer for \
        <a href="http://www.overmind-studios.de"><span style="text-decoration:underline; color:#2980b9;"> \
        Overmind Studios</span></a></p><p>\
        Licensed under the <a href="http://www.apache.org/licenses/LICENSE-2.0"><span style=" text-decoration:\
         underline; color:#2980b9;">Apache 2.0 license</span></a></p><p>Project home: \
         <a href="https://github.com/tobkum/BlenderUpdater"><span style=" text-decoration:\
         underline; color:#2980b9;">https://github.com/overmindstudios/BlenderUpdater</a></p> \
         Application version: ' + appversion + '</body></html> '
        QtWidgets.QMessageBox.about(self, 'About', aboutText)

    def check_dir(self):
        """Check if a vaild directory has been set by the user."""
        global dir_
        dir_ = self.line_path.text()
        if not os.path.exists(dir_):
            QtWidgets.QMessageBox.about(
                self, 'Directory not set',
                'Please choose a valid destination directory first')
            logger.error('No valid directory')
        else:
            logger.info('Checking for Blender versions')
            self.check()

    def hbytes(self, num):
        """Translate to human readable file size."""
        for x in [' bytes', ' KB', ' MB', ' GB']:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, ' TB')

    def check(self):
        global dir_
        global quicky
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

        appleicon = QtGui.QIcon(':/newPrefix/images/Apple-icon.png')
        windowsicon = QtGui.QIcon(':/newPrefix/images/Windows-icon.png')
        linuxicon = QtGui.QIcon(':/newPrefix/images/Linux-icon.png')
        url = 'https://builder.blender.org/download/'
        """Do path settings save here, in case user has manually edited it"""
        global config
        config.read('config.ini')
        config.set('main', 'path', dir_)
        with open('config.ini', 'w') as f:
            config.write(f)
        f.close()
        try:
            req = requests.get(url)
        except Exception:
            self.statusBar().showMessage(
                'Error - check your internet connection')
            logger.error('No connection to server')
            self.frm_start.show()
        soup = BeautifulSoup(req.text, "html.parser")
        """iterate through the found versions"""

        results = []
        for tr in soup.find_all('tr'):
            tds = tr.find_all('td')
            results.append([data.string for data in tds])
            results = [[item.strip().strip("\xa0") if item is not None else None for item in sublist] for sublist in results]
        finallist = []
        for sub in results:
            sub = list(filter(None, sub))
            finallist.append(sub)
        finallist = list(filter(None, finallist))
        if quicky:
            self.btn_Check.setDisabled(True)
            if lastversion == 'Windows 32bit':
                quickversion = 'win32'
                variation = flavor
            if lastversion == 'Windows 64bit':
                quickversion = 'win64'
                variation = flavor
            if lastversion == 'OSX':
                quickversion = 'OSX'
                variation = flavor
            if lastversion == 'Linux glibc211 i686':
                quickversion = 'linux-glibc211-i686'
                variation = flavor
            if lastversion == 'Linux glibc219 i686':
                quickversion = 'linux-glibc219-i686'
                variation = flavor
            if lastversion == 'Linux glibc211 x86_64':
                quickversion = 'linux-glibc211-x86_64'
                variation = flavor
            if lastversion == 'Linux glibc219 x86_64':
                quickversion = 'linux-glibc219_x86_64'
                variation = flavor
            for index, text in enumerate(finallist):
                if quickversion in text[1] and variation in text[0]:
                    version = str(text[0])
                    if version == installedversion and variation in text[0]:
                        reply = QtWidgets.QMessageBox.question(
                            self, 'Warning',
                            "This version is already installed. Do you still want to continue?",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                            QtWidgets.QMessageBox.No)
                        if reply == QtWidgets.QMessageBox.Yes:
                            self.download(version, variation)
                            logger.info('Re-downloading installed version')
                        else:
                            logger.info('Skipping download of existing version')
                    else:
                        self.download(version, variation)
                        return

        def filterall():
            """Generate buttons for downloadable versions."""
            global btn
            global flavor
            opsys = platform.system()
            logger.info('Operating system: ' + opsys)
            for i in btn:
                btn[i].hide()
            i = 0
            btn = {}
            for index, text in enumerate(finallist):
                btn[index] = QtWidgets.QPushButton(self)
                logger.debug(text[0] + " | " + text[1] + " | " + text[2])
                if "OSX" in text[0]:             # set icon according to OS
                    if opsys == "Darwin":
                        btn[index].setStyleSheet('background: rgb(22, 52, 73)')
                    btn[index].setIcon(appleicon)
                elif "linux" in text[0]:
                    if opsys == "Linux":
                        btn[index].setStyleSheet('background: rgb(22, 52, 73)')
                    btn[index].setIcon(linuxicon)
                elif "win" in text[0]:
                    if opsys == "Windows":
                        btn[index].setStyleSheet('background: rgb(22, 52, 73)')
                    btn[index].setIcon(windowsicon)

                version = str(text[0])
                variation = str(text[0])
                buttontext = str(
                    text[0]) + " | " + str(text[1]) + " | " + str(text[2])
                btn[index].setIconSize(QtCore.QSize(24, 24))
                btn[index].setText(buttontext)
                btn[index].setFixedWidth(686)
                btn[index].move(6, 50 + i)
                i += 32
                btn[index].clicked.connect(
                    lambda throwaway=0,
                    version=version: self.download(version, variation))
                btn[index].show()

        def filterosx():
            global btn
            for i in btn:
                btn[i].hide()
            btn = {}
            i = 0
            for index, text in enumerate(finallist):
                btn[index] = QtWidgets.QPushButton(self)
                if "OSX" in text[0]:
                    btn[index].setIcon(appleicon)
                    version = str(text[0])
                    variation = str(text[0])
                    buttontext = str(
                        text[0]) + " | " + str(text[1]) + " | " + str(text[2])
                    btn[index].setIconSize(QtCore.QSize(24, 24))
                    btn[index].setText(buttontext)
                    btn[index].setFixedWidth(686)
                    btn[index].move(6, 50 + i)
                    i += 32
                    btn[index].clicked.connect(
                        lambda throwaway=0,
                        version=version: self.download(version, variation))
                    btn[index].show()

        def filterlinux():
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
                    buttontext = str(
                        text[0]) + " | " + str(text[1]) + " | " + str(text[2])
                    btn[index].setIconSize(QtCore.QSize(24, 24))
                    btn[index].setText(buttontext)
                    btn[index].setFixedWidth(686)
                    btn[index].move(6, 50 + i)
                    i += 32
                    btn[index].clicked.connect(
                        lambda throwaway=0,
                        version=version: self.download(version, variation))
                    btn[index].show()

        def filterwindows():
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
                    buttontext = str(
                        text[0]) + " | " + str(text[1]) + " | " + str(text[2])
                    btn[index].setIconSize(QtCore.QSize(24, 24))
                    btn[index].setText(buttontext)
                    btn[index].setFixedWidth(686)
                    btn[index].move(6, 50 + i)
                    i += 32
                    btn[index].clicked.connect(
                        lambda throwaway=0,
                        version=version: self.download(version, variation))
                    btn[index].show()

        self.lbl_available.show()
        self.lbl_caution.show()
        self.btngrp_filter.show()
        self.btn_osx.clicked.connect(filterosx)
        self.btn_linux.clicked.connect(filterlinux)
        self.btn_windows.clicked.connect(filterwindows)
        self.btn_allos.clicked.connect(filterall)
        lastcheck = datetime.now().strftime('%a %b %d %H:%M:%S %Y')
        self.statusbar.showMessage("Ready - Last check: " + str(lastcheck))
        config.read('config.ini')
        config.set('main', 'lastcheck', str(lastcheck))
        with open('config.ini', 'w') as f:
            config.write(f)
        f.close()
        filterall()

    def download(self, version, variation):
        """Download routines."""
        global dir_
        global filename
        url = 'https://builder.blender.org/download/' + version
        if version == installedversion:
            reply = QtWidgets.QMessageBox.question(
                self, 'Warning',
                "This version is already installed. Do you still want to continue?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No)
            logger.info('Duplicated version detected')
            if reply == QtWidgets.QMessageBox.No:
                logger.debug('Skipping download of existing version')
                return
            else:
                pass
        else:
            pass

        if os.path.isdir('./blendertemp'):
            shutil.rmtree('./blendertemp')
        os.makedirs('./blendertemp')
        file = urllib.request.urlopen(url)
        totalsize = file.info()['Content-Length']
        size_readable = self.hbytes(float(totalsize))
        global config
        config.read('config.ini')
        config.set('main', 'path', dir_)
        config.set('main', 'flavor', variation)
        config.set('main', 'installed', version)
        with open('config.ini', 'w') as f:
            config.write(f)
        f.close()
        '''Do the actual download'''
        dir_ = os.path.join(dir_, '')
        filename = './blendertemp/' + version
        for i in btn:
            btn[i].hide()
        logger.info('Starting download thread for ' + url + version)
        self.lbl_available.hide()
        self.lbl_caution.hide()
        self.progressBar.show()
        self.btngrp_filter.hide()
        self.lbl_task.setText('Downloading')
        self.lbl_task.show()
        self.frm_progress.show()
        nowpixmap = QtGui.QPixmap(
            ':/newPrefix/images/Actions-arrow-right-icon.png')
        self.lbl_download_pic.setPixmap(nowpixmap)
        self.lbl_downloading.setText('<b>Downloading</b>')
        self.progressBar.setValue(0)
        self.btn_Check.setDisabled(True)
        self.statusbar.showMessage('Downloading ' + size_readable)
        thread = WorkerThread(url, filename)
        thread.update.connect(self.updatepb)
        thread.finishedDL.connect(self.extraction)
        thread.finishedEX.connect(self.finalcopy)
        thread.finishedCP.connect(self.cleanup)
        thread.finishedCL.connect(self.done)
        thread.start()

    def quickupdate(self):
        global quicky
        quicky = True
        self.check()

    def updatepb(self, percent):
        self.progressBar.setValue(percent)

    def extraction(self):
        logger.info('Extracting to temp directory')
        self.lbl_task.setText('Extracting...')
        self.btn_Quit.setEnabled(False)
        nowpixmap = QtGui.QPixmap(
            ':/newPrefix/images/Actions-arrow-right-icon.png')
        donepixmap = QtGui.QPixmap(':/newPrefix/images/Check-icon.png')
        self.lbl_downloading.setText('Downloading')
        self.lbl_download_pic.setPixmap(donepixmap)
        self.lbl_extract_pic.setPixmap(nowpixmap)
        self.lbl_extraction.setText('<b>Extraction</b>')
        self.statusbar.showMessage(
            'Extracting to temporary folder, please wait...')
        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setValue(-1)

    def finalcopy(self):
        logger.info('Copying to ' + dir_)
        nowpixmap = QtGui.QPixmap(
            ':/newPrefix/images/Actions-arrow-right-icon.png')
        donepixmap = QtGui.QPixmap(':/newPrefix/images/Check-icon.png')
        self.lbl_extract_pic.setPixmap(donepixmap)
        self.lbl_copy_pic.setPixmap(nowpixmap)
        self.lbl_extraction.setText('Extraction')
        self.lbl_copying.setText('<b>Copying</b>')
        self.lbl_task.setText('Copying files...')
        self.statusbar.showMessage(
            'Copying files to "' + dir_ + '", please wait... ')

    def cleanup(self):
        logger.info('Cleaning up temp files')
        nowpixmap = QtGui.QPixmap(
            ':/newPrefix/images/Actions-arrow-right-icon.png')
        donepixmap = QtGui.QPixmap(':/newPrefix/images/Check-icon.png')
        self.lbl_copy_pic.setPixmap(donepixmap)
        self.lbl_clean_pic.setPixmap(nowpixmap)
        self.lbl_copying.setText('Copying')
        self.lbl_cleanup.setText('<b>Cleaning up</b>')
        self.lbl_task.setText('Cleaning up...')
        self.statusbar.showMessage('Cleaning temporary files')

    def done(self):
        logger.info('Finished')
        donepixmap = QtGui.QPixmap(':/newPrefix/images/Check-icon.png')
        self.lbl_clean_pic.setPixmap(donepixmap)
        self.lbl_cleanup.setText('Cleaning up')
        self.statusbar.showMessage('Ready')
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(100)
        self.lbl_task.setText('Finished')
        self.btn_Quit.setEnabled(True)
        self.btn_Check.setEnabled(True)
        self.btn_execute.show()
        opsys = platform.system()
        if opsys == 'Windows':
            self.btn_execute.clicked.connect(self.exec_windows)
        if opsys == 'Darwin':
            self.btn_execute.clicked.connect(self.exec_osx)
        if opsys == 'Linux':
            self.btn_execute.clicked.connect(self.exec_linux)


    def exec_windows(self):
        system(dir_ + 'blender.exe')
        logger.info('Executing ' + dir_ + 'blender.exe' )

    def exec_osx(self):
        system(dir_ + 'blender.app')
        logger.info('Executing ' + dir_ + 'blender.app')

    def exec_linux(self):
        logger.info('Executing ' + dir_ + 'blender')


def main():
    app.setStyle("Fusion")

    dark_palette = QtGui.QPalette()

    dark_palette.setColor(dark_palette.Window, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(dark_palette.WindowText, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(dark_palette.Disabled, dark_palette.WindowText, QtGui.QColor(127, 127, 127))
    dark_palette.setColor(dark_palette.Base, QtGui.QColor(42, 42, 42))
    dark_palette.setColor(dark_palette.AlternateBase, QtGui.QColor(66, 66, 66))
    dark_palette.setColor(dark_palette.ToolTipBase, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(dark_palette.ToolTipText, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(dark_palette.Text, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(dark_palette.Disabled, dark_palette.Text, QtGui.QColor(127, 127, 127))
    dark_palette.setColor(dark_palette.Dark, QtGui.QColor(35, 35, 35))
    dark_palette.setColor(dark_palette.Shadow, QtGui.QColor(20, 20, 20))

    dark_palette.setColor(dark_palette.Button, QtGui.QColor(53, 53, 53))
    dark_palette.setColor(dark_palette.ButtonText, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(dark_palette.BrightText, QtGui.QColor(255, 0, 0))
    dark_palette.setColor(dark_palette.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(dark_palette.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(dark_palette.Disabled, dark_palette.Highlight, QtGui.QColor(80, 80, 80))
    dark_palette.setColor(dark_palette.HighlightedText, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(dark_palette.Disabled, dark_palette.HighlightedText, QtGui.QColor(255, 255, 255))
    dark_palette.setColor(dark_palette.Disabled, dark_palette.ButtonText,
                          QtGui.QColor(127, 127, 127))
    app.setPalette(dark_palette)

    # qfdarkstyle = open('darkstyle/darkstyle.qss').read()
    # app.setStyleSheet(qfdarkstyle)
    window = BlenderUpdater()

    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
