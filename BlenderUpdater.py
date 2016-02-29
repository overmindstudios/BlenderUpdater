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

        self.btn_Check.setFocus()                   # set focus to Check Now button
        self.lbl_available.hide()                   # hide the message at the top
        self.progressBar.setValue(0)                # reset progress bar
        self.progressBar.hide()                     # Hide the progress bar on startup
        self.lbl_task.hide()                        # Hide progress description on startup
        self.statusBar().showMessage('Ready - Last check: ' + lastcheck)       # Update last checked label in status bar
        self.btn_Quit.clicked.connect(QtCore.QCoreApplication.instance().quit)  # Implement quit button
        self.btn_Check.clicked.connect(self.check)  # connect Check Now button
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

    def check(self):
        global dir_
        dir_ = self.line_path.text()
        self.frm_start.hide()
        appleicon = QtGui.QIcon('./images/Apple-icon.png')
        windowsicon = QtGui.QIcon('./images/Windows-icon.png')
        linuxicon = QtGui.QIcon('./images/Linux-icon.png')
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
        soup = BeautifulSoup(req.read())
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
            btn1.setIconSize(QtCore.QSize(24,24))
            btn1.setText(buttontext)
            btn1.setFixedWidth(686)
            btn1.move(6, 45 + i)
            i += 30
            btn1.clicked.connect(lambda throwaway=0, version=version: self.download(version))
            btn1.show()

        self.lbl_available.show()
        lastcheck = datetime.now().strftime('%a %b %d %H:%M:%S %Y')
        self.statusBar().showMessage ("Ready - Last check: " + str(lastcheck))
        config.read('config.ini')
        config.set('main', 'lastcheck', str(lastcheck))
        with open('config.ini', 'w') as f:
            config.write(f)
        f.close()

    def download(self, version):
        global dir_
        if os.path.isdir('./blendertemp'):
            shutil.rmtree('./blendertemp')
        os.makedirs('./blendertemp')

        url = 'https://builder.blender.org/download/' + version
        file = urllib.request.urlopen(url)
        totalsize = file.info()['Content-Length']
        size_readable = self.hbytes(float(totalsize))
        global dir_
        self.check_dir(dir_)
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
        self.progressBar.setValue(0)
        self.btn_Check.setDisabled(True)
        self.statusBar().showMessage('Downloading ' + size_readable)

        def progress (count, blockSize, totalSize):
            percent = int(count*blockSize*100/totalSize)
            self.progressBar.setValue(percent)
            QtGui.QApplication.processEvents()      # Avoid locking the GUI
            if self.progressBar.value() >= 100:
                self.statusBar().showMessage('Ready')
                self.lbl_task.hide()
                self.progressBar.hide()

            else:
                pass

        def dlthread():
            urllib.request.urlretrieve(url, filename, reporthook=progress)
            self.emit(QtCore.SIGNAL('DONE'))

        dl = QtCore.QThread(dlthread())
        dl.start()
        dl.connect(dl, QtCore.SIGNAL('DONE'), self.extraction(filename))

    def check_dir(self, path):
        global dir_
        if not os.path.exists(path):
            QtGui.QMessageBox.about(self, 'Directory not set', 'Please choose a valid destination directory first')
            dir_ = QtGui.QFileDialog.getExistingDirectory(None, 'Select a folder:', 'C:\\', QtGui.QFileDialog.ShowDirsOnly)
            self.check_dir(dir_)
        else:
            pass

    def hbytes(self, num):      # translate to human readable file size
        for x in ['bytes','KB','MB','GB']:
            if num < 1024.0:
                return "%3.1f%s" % (num, x)
            num /= 1024.0
        return "%3.1f%s" % (num, 'TB')

    def extraction(self, filename):
        self.lbl_task.hide()
        self.progressBar.hide()
        self.btn_Quit.setEnabled(False)
        self.statusBar().showMessage('Extracting, please wait... (Application may become unresponsive)')
        shutil.unpack_archive(filename, './blendertemp/')
        self.finalcopy()

    def finalcopy(self):
        global dir_
        self.statusBar().showMessage('Copying files... (Application may become unresponsive)')
        source = next(os.walk('./blendertemp/'))[1]
        copy_tree(os.path.join('./blendertemp/', source[0]), dir_)
        shutil.rmtree('./blendertemp')
        self.statusBar().showMessage('Ready')
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
