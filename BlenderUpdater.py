'''
Copyright 2016 Tobias Kummer/Overmind Studios

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''


from PyQt4 import QtGui, QtCore
import qdarkstyle
import os.path
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
from datetime import datetime
import mainwindow
import configparser
import shutil
from distutils.dir_util import copy_tree
from esky import *
import sys


appversion = '0.7'
dir_ = ''
config = configparser.ConfigParser()
btn = {}
quicky = False
lastversion = ''
installedversion = ''




class WorkerThread(QtCore.QThread):

    def __init__(self, url, file):
        super(WorkerThread, self).__init__()
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
        percent = int(count*blockSize*100/totalSize)
        self.emit(QtCore.SIGNAL('update'), percent)

    def run(self):
        urllib.request.urlretrieve(self.url, self.filename, reporthook=self.progress)
        self.emit(QtCore.SIGNAL('finishedDL'))
        shutil.unpack_archive(self.filename, './blendertemp/')
        self.emit(QtCore.SIGNAL('finishedEX'))
        source = next(os.walk('./blendertemp/'))[1]
        copy_tree(os.path.join('./blendertemp/', source[0]), dir_)
        self.emit(QtCore.SIGNAL('finishedCP'))
        shutil.rmtree('./blendertemp')
        self.emit(QtCore.SIGNAL('finishedCL'))


class BlenderUpdater(QtGui.QMainWindow, mainwindow.Ui_MainWindow):  
    def __init__(self, parent=None):
        super(BlenderUpdater, self).__init__(parent)
        self.setupUi(self)
        self.btn_oneclick.hide()
        self.lbl_quick.hide()
        global lastversion
        global dir_
        global config
        global installedversion
        if os.path.isfile('./config.ini'):
            config_exist = True
            config.read('config.ini')
            dir_ = config.get('main', 'path')
            lastcheck = config.get('main', 'lastcheck')
            lastversion = config.get('main', 'lastdl')
            installedversion = config.get('main', 'installed')
            if lastversion is not '':
                self.btn_oneclick.setText(lastversion)
                self.btn_oneclick.clicked.connect(self.quickupdate)
                self.btn_oneclick.show()
                self.lbl_quick.show()
            else:
                pass

        else:
            self.btn_oneclick.hide()
            config_exist = False
            config.read('config.ini')
            config.add_section('main')
            config.set('main', 'path', '')
            lastcheck = 'Never'
            config.set('main', 'lastcheck', 'Never')
            config.set('main', 'lastdl', '')
            config.set('main', 'installed', '')
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
        self.btn_Check.setFocus()                   # set focus to Check Now button
        self.lbl_available.hide()                   # hide the message at the top
        self.progressBar.setValue(0)                # reset progress bar
        self.progressBar.hide()                     # Hide the progress bar on startup
        self.lbl_task.hide()                        # Hide progress description on startup
        self.statusbar.showMessage('Ready - Last check: ' + lastcheck)       # Update last checked label in status bar
        self.btn_Quit.clicked.connect(QtCore.QCoreApplication.instance().quit)  # Implement quit button
        self.btn_Check.clicked.connect(self.check_dir)  # connect Check Now button
        self.btn_about.clicked.connect(self.about)  # connect About button
        self.btn_path.clicked.connect(self.select_path)  # connect the path button
        ''' Check internet connection '''
        try:
            testConnection = urllib.request.urlopen("http://www.google.com")
        except Exception:
            QtGui.QMessageBox.critical(self, "Error", "Please check your internet connection")
            sys.exit()

        ''' Auto-update function'''
        if hasattr(sys, "frozen"):      # Only check for updates in frozen application
            exe = esky.Esky(sys.executable, "http://www.overmind-studios.de/blenderupdater")
            if exe.find_update():
                reply = QtGui.QMessageBox.question(self, 'Update', "New version of BlenderUpdater available. Do you want to update?",
                                                  QtGui.QMessageBox.Yes | QtGui.QMessageBox.No, QtGui.QMessageBox.No)
                if reply == QtGui.QMessageBox.Yes:
                        exe.auto_update()
        else:
            pass

    def select_path(self):
        global dir_
        dir_ = QtGui.QFileDialog.getExistingDirectory(None, 'Select a folder:', 'C:\\', QtGui.QFileDialog.ShowDirsOnly)
        if dir_:
            self.line_path.setText(dir_)
        else:
            pass

    def about(self):
        aboutText = '<html><head/><body><p>Utility to update Blender to the latest buildbot version available at \
        <a href="https://builder.blender.org/download/"><span style=" text-decoration: underline; color:#2980b9;">\
        https://builder.blender.org/download/</span></a></p><p><br/>Developed by Tobias Kummer for Overmind Studios</p><p>\
        Licensed under the <a href="http://www.apache.org/licenses/LICENSE-2.0"><span style=" text-decoration:\
         underline; color:#2980b9;">Apache 2.0 license</span></a></p><p>Project home: \
         <a href="https://github.com/tobkum/BlenderUpdater"><span style=" text-decoration:\
         underline; color:#2980b9;">https://github.com/tobkum/BlenderUpdater</a></p> \
         Application version: ' + appversion + '</body></html>'
        QtGui.QMessageBox.about(self, 'About', aboutText)

    def check_dir(self):
        global dir_
        dir_ = self.line_path.text()
        if not os.path.exists(dir_):
            QtGui.QMessageBox.about(self, 'Directory not set', 'Please choose a valid destination directory first')
        else:
            self.check()

    def hbytes(self, num):      # translate to human readable file size
        for x in [' bytes',' KB',' MB',' GB']:
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
        appleicon = QtGui.QIcon(':/newPrefix/images/Apple-icon.png')
        windowsicon = QtGui.QIcon(':/newPrefix/images/Windows-icon.png')
        linuxicon = QtGui.QIcon(':/newPrefix/images/Linux-icon.png')
        url = 'https://builder.blender.org/download/'
        '''Do the path settings save here, in case the user has manually edited it'''
        global config
        config.read('config.ini')
        config.set('main', 'path', dir_)
        with open('config.ini', 'w') as f:
            config.write(f)
        f.close()
        try:
            req = urllib.request.urlopen(url)
        except Exception:
            self.statusBar().showMessage('Error - check your internet connection')
            self.frm_start.show()
        soup = BeautifulSoup(req.read(), "html.parser")
        """iterate through the found versions"""
        table = soup.find(class_='table')
        results = []
        for col in table.find_all('tr', text=None, recursive=True)[0:]:
            results.append([data.string for data in col])
        results = [[item.strip().strip("\xa0") if item is not None else None for item in sublist] for sublist in results]
        finallist = []
        for sub in results:
            sub = list(filter(None, sub))
            finallist.append(sub)
        finallist = list(filter(None, finallist))
        del finallist[0]            # remove first entry which is the header of the table

        if quicky:
            self.btn_Check.setDisabled(True)
            if lastversion == 'Windows 32bit':
                quickversion = 'win32'
            if lastversion == 'Windows 64bit':
                quickversion = 'win64'
            if lastversion == 'OSX':
                quickversion = 'OSX'
            if lastversion == 'Linux glibc211 i686':
                quickversion = 'linux-glibc211-i686'
            if lastversion == 'Linux glibc219 i686':
                quickversion = 'linux-glibc219-i686'
            if lastversion == 'Linux glibc211 x86_64':
                quickversion = 'linux-glibc211-x86_64'
            if lastversion == 'Linux glibc219 x86_64':
                quickversion = 'linux-glibc219_x86_64'
            for index, text in enumerate(finallist):
                if quickversion in text[1]:
                    version = str(text[1])
                    if version == installedversion:
                        reply = QtGui.QMessageBox.question(self, 'Warning',
                                                           "This version is already installed. Do you still want to continue?",
                                                           QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                                           QtGui.QMessageBox.No)
                        if reply == QtGui.QMessageBox.Yes:
                            self.download(version)
                        else:
                            pass
                    else:
                        self.download(version)
                        return



        """generate buttons"""
        def filterall():
            global btn
            for i in btn:
                btn[i].hide()
            i = 0
            btn = {}
            for index, text in enumerate(finallist):
                btn[index] = QtGui.QPushButton(self)
                if "OSX" in text[1]:                         # set icon according to OS
                    btn[index].setIcon(appleicon)
                elif "linux" in text[1]:
                    btn[index].setIcon(linuxicon)
                elif "win" in text[1]:
                    btn[index].setIcon(windowsicon)

                version = str(text[1])
                buttontext = str(text[0]) + " | " + str(text[1]) + " | " + str(text[3])
                btn[index].setIconSize(QtCore.QSize(24, 24))
                btn[index].setText(buttontext)
                btn[index].setFixedWidth(686)
                btn[index].move(6, 50 + i)
                i += 32
                btn[index].clicked.connect(lambda throwaway=0, version=version: self.download(version))
                btn[index].show()

        def filterosx():
            global btn
            for i in btn:
                btn[i].hide()
            btn = {}
            i = 0
            for index, text in enumerate(finallist):
                btn[index] = QtGui.QPushButton(self)
                if "OSX" in text[1]:
                    btn[index].setIcon(appleicon)
                    version = str(text[1])
                    buttontext = str(text[0]) + " | " + str(text[1]) + " | " + str(text[3])
                    btn[index].setIconSize(QtCore.QSize(24, 24))
                    btn[index].setText(buttontext)
                    btn[index].setFixedWidth(686)
                    btn[index].move(6, 50 + i)
                    i += 32
                    btn[index].clicked.connect(lambda throwaway=0, version=version: self.download(version))
                    btn[index].show()

        def filterlinux():
            global btn
            for i in btn:
                btn[i].hide()
            btn = {}
            i = 0
            for index, text in enumerate(finallist):
                btn[index] = QtGui.QPushButton(self)
                if "linux" in text[1]:
                    btn[index].setIcon(linuxicon)
                    version = str(text[1])
                    buttontext = str(text[0]) + " | " + str(text[1]) + " | " + str(text[3])
                    btn[index].setIconSize(QtCore.QSize(24, 24))
                    btn[index].setText(buttontext)
                    btn[index].setFixedWidth(686)
                    btn[index].move(6, 50 + i)
                    i += 32
                    btn[index].clicked.connect(lambda throwaway=0, version=version: self.download(version))
                    btn[index].show()

        def filterwindows():
            global btn
            for i in btn:
                btn[i].hide()
            btn = {}
            i = 0
            for index, text in enumerate(finallist):
                btn[index] = QtGui.QPushButton(self)
                if "win" in text[1]:
                    btn[index].setIcon(windowsicon)
                    version = str(text[1])
                    buttontext = str(text[0]) + " | " + str(text[1]) + " | " + str(text[3])
                    btn[index].setIconSize(QtCore.QSize(24, 24))
                    btn[index].setText(buttontext)
                    btn[index].setFixedWidth(686)
                    btn[index].move(6, 50 + i)
                    i += 32
                    btn[index].clicked.connect(lambda throwaway=0, version=version: self.download(version))
                    btn[index].show()

        self.lbl_available.show()
        self.btngrp_filter.show()
        self.btn_osx.clicked.connect(filterosx)
        self.btn_linux.clicked.connect(filterlinux)
        self.btn_windows.clicked.connect(filterwindows)
        self.btn_allos.clicked.connect(filterall)
        lastcheck = datetime.now().strftime('%a %b %d %H:%M:%S %Y')
        self.statusbar.showMessage ("Ready - Last check: " + str(lastcheck))
        config.read('config.ini')
        config.set('main', 'lastcheck', str(lastcheck))
        with open('config.ini', 'w') as f:
            config.write(f)
        f.close()
        filterall()

    def download(self, version):
        global dir_
        global filename
        if version == installedversion:
            reply = QtGui.QMessageBox.question(self, 'Warning',
                                               "This version is already installed. Do you still want to continue?",
                                               QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
                                               QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.No:
                return
            else:
                pass
        else:
            pass

        if os.path.isdir('./blendertemp'):
            shutil.rmtree('./blendertemp')
        os.makedirs('./blendertemp')
        url = 'https://builder.blender.org/download/' + version
        file = urllib.request.urlopen(url)
        totalsize = file.info()['Content-Length']
        size_readable = self.hbytes(float(totalsize))
        global config
        config.read('config.ini')
        config.set('main', 'path', dir_)
        config.set('main', 'installed', version)
        with open('config.ini', 'w') as f:
            config.write(f)
        f.close()
        '''Do the actual download'''
        dir_ = os.path.join(dir_, '')
        filename = './blendertemp/' + version
        for i in btn:
            btn[i].hide()
        self.lbl_available.hide()
        self.progressBar.show()
        self.btngrp_filter.hide()
        self.lbl_task.setText('Downloading')
        self.lbl_task.show()
        self.frm_progress.show()
        nowpixmap = QtGui.QPixmap(':/newPrefix/images/Actions-arrow-right-icon.png')
        self.lbl_download_pic.setPixmap(nowpixmap)
        self.lbl_downloading.setText('<b>Downloading</b>')
        # self.btn_cancel.show()
        self.progressBar.setValue(0)
        self.btn_Check.setDisabled(True)
        self.statusbar.showMessage('Downloading ' + size_readable)
        thread = WorkerThread(url, filename)
        self.connect(thread, QtCore.SIGNAL('update'), self.updatepb)
        self.connect(thread, QtCore.SIGNAL('finishedDL'), self.extraction)
        self.connect(thread, QtCore.SIGNAL('finishedEX'), self.finalcopy)
        self.connect(thread, QtCore.SIGNAL('finishedCP'), self.cleanup)
        self.connect(thread, QtCore.SIGNAL('finishedCL'), self.done)
        thread.start()

    def quickupdate(self):
        global quicky
        quicky = True
        self.check()

    def updatepb(self, percent):
        self.progressBar.setValue(percent)

    def extraction(self):
        self.lbl_task.setText('Extracting...')
        self.btn_Quit.setEnabled(False)
        nowpixmap = QtGui.QPixmap(':/newPrefix/images/Actions-arrow-right-icon.png')
        donepixmap = QtGui.QPixmap(':/newPrefix/images/Check-icon.png')
        self.lbl_downloading.setText('Downloading')
        self.lbl_download_pic.setPixmap(donepixmap)
        self.lbl_extract_pic.setPixmap(nowpixmap)
        self.lbl_extraction.setText('<b>Extraction</b>')
        self.statusbar.showMessage('Extracting to temporary folder, please wait...')
        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setValue(-1)

    def finalcopy(self):
        nowpixmap = QtGui.QPixmap(':/newPrefix/images/Actions-arrow-right-icon.png')
        donepixmap = QtGui.QPixmap(':/newPrefix/images/Check-icon.png')
        self.lbl_extract_pic.setPixmap(donepixmap)
        self.lbl_copy_pic.setPixmap(nowpixmap)
        self.lbl_extraction.setText('Extraction')
        self.lbl_copying.setText('<b>Copying</b>')
        self.lbl_task.setText('Copying files...')
        self.statusbar.showMessage('Copying files to "' + dir_ + '", please wait... ')

    def cleanup(self):
        nowpixmap = QtGui.QPixmap(':/newPrefix/images/Actions-arrow-right-icon.png')
        donepixmap = QtGui.QPixmap(':/newPrefix/images/Check-icon.png')
        self.lbl_copy_pic.setPixmap(donepixmap)
        self.lbl_clean_pic.setPixmap(nowpixmap)
        self.lbl_copying.setText('Copying')
        self.lbl_cleanup.setText('<b>Cleaning up</b>')
        self.lbl_task.setText('Cleaning up...')
        self.statusbar.showMessage('Cleaning temporary files')

    def done(self):
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


def main():
    app = QtGui.QApplication(sys.argv)
    form = BlenderUpdater()
    app.setStyleSheet(qdarkstyle.load_stylesheet(pyside=False))
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()
