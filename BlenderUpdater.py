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
import sys
import os.path
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
from datetime import datetime
import mainwindow
import configparser
import shutil
from distutils.dir_util import copy_tree


dir_ = ''
config = configparser.ConfigParser()


class WorkerThread(QtCore.QThread):

    def __init__(self, url, file):
        super(WorkerThread, self).__init__()
        self.filename = file
        self.url = url

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
        global dir_
        global config
        if os.path.isfile('./config.ini'):
            config_exist = True
            config.read('config.ini')
            dir_ = config.get('main', 'path')
            lastcheck = config.get('main', 'lastcheck')
        else:
            config_exist = False
            config.read('config.ini')
            config.add_section('main')
            config.set('main', 'path', '')
            lastcheck = 'Never'
            config.set('main', 'lastcheck', 'Never')
            with open('config.ini', 'w') as f:
                config.write(f)
        if config_exist:
            self.line_path.setText(dir_)
        else:
            pass
        dir_ = self.line_path.text()
        self.btn_cancel.hide()
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
         underline; color:#2980b9;">Apache 2.0 license</span></a></p></body></html>'
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
        dir_ = self.line_path.text()
        self.frm_start.hide()
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

        """generate buttons"""
        i = 0
        for index, text in enumerate(finallist):
            btn1 = QtGui.QPushButton(self)
            if "OSX" in text[1]:                         # set icon according to OS
                btn1.setIcon(appleicon)
            elif "linux" in text[1]:
                btn1.setIcon(linuxicon)
            elif "win" in text[1]:
                btn1.setIcon(windowsicon)

            version = str(text[1])
            buttontext = str(text[0]) + " | " + str(text[1]) + " | " + str(text[3])
            btn1.setIconSize(QtCore.QSize(24, 24))
            btn1.setText(buttontext)
            btn1.setFixedWidth(686)
            btn1.move(6, 45 + i)
            i += 30
            btn1.clicked.connect(lambda throwaway=0, version=version: self.download(version))
            btn1.show()

        self.lbl_available.show()
        lastcheck = datetime.now().strftime('%a %b %d %H:%M:%S %Y')
        self.statusbar.showMessage ("Ready - Last check: " + str(lastcheck))
        config.read('config.ini')
        config.set('main', 'lastcheck', str(lastcheck))
        with open('config.ini', 'w') as f:
            config.write(f)
        f.close()

    def download(self, version):
        global dir_
        global filename
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
        with open('config.ini', 'w') as f:
            config.write(f)
        f.close()
        '''Do the actual download'''
        dir_ = os.path.join(dir_, '')
        filename = './blendertemp/' + version

        self.progressBar.show()
        self.lbl_task.setText('Downloading')
        self.lbl_task.show()
        # self.btn_cancel.show()
        self.progressBar.setValue(0)
        self.btn_Check.setDisabled(True)
        self.statusbar.showMessage('Downloading ' + size_readable)
        thread = WorkerThread(url, filename)
        self.connect(thread, QtCore.SIGNAL('aborted'), self.aborted)
        self.connect(thread, QtCore.SIGNAL('update'), self.updatepb)
        self.connect(thread, QtCore.SIGNAL('finishedDL'), self.extraction)
        self.connect(thread, QtCore.SIGNAL('finishedEX'), self.finalcopy)
        self.connect(thread, QtCore.SIGNAL('finishedCP'), self.cleanup)
        self.connect(thread, QtCore.SIGNAL('finishedCL'), self.done)
        # self.btn_cancel.clicked.connect(thread.de)
        thread.start()

    def aborted(self):
        self.statusbar.showMessage('Aborted')
        self.lbl_task.hide()
        self.progressBar.hide()
        self.btn_cancel.hide()
        self.btn_Check.setEnabled(True)

    def updatepb(self, percent):
        self.progressBar.setValue(percent)

    def extraction(self):
        self.lbl_task.setText('Extracting...')
        self.btn_Quit.setEnabled(False)
        self.statusbar.showMessage('Extracting to temporary folder, please wait...')
        self.progressBar.setMaximum(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setValue(-1)

    def finalcopy(self):
        self.lbl_task.setText('Copying files...')
        self.statusbar.showMessage('Copying files to "' + dir_ + '", please wait... ')

    def cleanup(self):
        self.lbl_task.setText('Cleaning up...')
        self.statusbar.showMessage('Cleaning temporary files')

    def done(self):
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
