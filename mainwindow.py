# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(700, 435)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(700, 435))
        MainWindow.setMaximumSize(QtCore.QSize(700, 435))
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.btn_Quit = QtGui.QPushButton(self.centralwidget)
        self.btn_Quit.setGeometry(QtCore.QRect(560, 366, 131, 35))
        self.btn_Quit.setFocusPolicy(QtCore.Qt.StrongFocus)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/Application-exit-icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.btn_Quit.setIcon(icon)
        self.btn_Quit.setObjectName(_fromUtf8("btn_Quit"))
        self.btn_Check = QtGui.QPushButton(self.centralwidget)
        self.btn_Check.setGeometry(QtCore.QRect(6, 366, 131, 35))
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/Refresh-icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.btn_Check.setIcon(icon1)
        self.btn_Check.setAutoDefault(False)
        self.btn_Check.setDefault(False)
        self.btn_Check.setObjectName(_fromUtf8("btn_Check"))
        self.progressBar = QtGui.QProgressBar(self.centralwidget)
        self.progressBar.setEnabled(True)
        self.progressBar.setGeometry(QtCore.QRect(140, 316, 551, 30))
        self.progressBar.setProperty("value", 24)
        self.progressBar.setTextVisible(True)
        self.progressBar.setInvertedAppearance(False)
        self.progressBar.setObjectName(_fromUtf8("progressBar"))
        self.lbl_task = QtGui.QLabel(self.centralwidget)
        self.lbl_task.setGeometry(QtCore.QRect(10, 320, 121, 20))
        self.lbl_task.setObjectName(_fromUtf8("lbl_task"))
        self.lbl_available = QtGui.QLabel(self.centralwidget)
        self.lbl_available.setGeometry(QtCore.QRect(250, 19, 210, 19))
        self.lbl_available.setObjectName(_fromUtf8("lbl_available"))
        self.btn_about = QtGui.QPushButton(self.centralwidget)
        self.btn_about.setGeometry(QtCore.QRect(657, 10, 35, 35))
        self.btn_about.setText(_fromUtf8(""))
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/Information-icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.btn_about.setIcon(icon2)
        self.btn_about.setIconSize(QtCore.QSize(24, 24))
        self.btn_about.setCheckable(False)
        self.btn_about.setChecked(False)
        self.btn_about.setObjectName(_fromUtf8("btn_about"))
        self.frm_start = QtGui.QFrame(self.centralwidget)
        self.frm_start.setGeometry(QtCore.QRect(6, 50, 686, 271))
        self.frm_start.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frm_start.setFrameShadow(QtGui.QFrame.Raised)
        self.frm_start.setObjectName(_fromUtf8("frm_start"))
        self.lbl_start = QtGui.QLabel(self.frm_start)
        self.lbl_start.setGeometry(QtCore.QRect(90, 70, 491, 41))
        self.lbl_start.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop)
        self.lbl_start.setWordWrap(True)
        self.lbl_start.setObjectName(_fromUtf8("lbl_start"))
        self.line_path = QtGui.QLineEdit(self.frm_start)
        self.line_path.setGeometry(QtCore.QRect(80, 160, 491, 35))
        self.line_path.setObjectName(_fromUtf8("line_path"))
        self.btn_path = QtGui.QPushButton(self.frm_start)
        self.btn_path.setGeometry(QtCore.QRect(576, 160, 35, 35))
        self.btn_path.setText(_fromUtf8(""))
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/Open-folder-icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.btn_path.setIcon(icon3)
        self.btn_path.setObjectName(_fromUtf8("btn_path"))
        self.label = QtGui.QLabel(self.frm_start)
        self.label.setGeometry(QtCore.QRect(190, 130, 311, 20))
        self.label.setScaledContents(False)
        self.label.setAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignTop)
        self.label.setWordWrap(True)
        self.label.setObjectName(_fromUtf8("label"))
        self.btn_cancel = QtGui.QPushButton(self.centralwidget)
        self.btn_cancel.setGeometry(QtCore.QRect(110, 320, 24, 24))
        self.btn_cancel.setText(_fromUtf8(""))
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(_fromUtf8(":/newPrefix/images/Cancel-icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.btn_cancel.setIcon(icon4)
        self.btn_cancel.setObjectName(_fromUtf8("btn_cancel"))
        self.frm_start.raise_()
        self.btn_Quit.raise_()
        self.btn_Check.raise_()
        self.progressBar.raise_()
        self.lbl_task.raise_()
        self.lbl_available.raise_()
        self.btn_about.raise_()
        self.btn_cancel.raise_()
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "Overmind Studios BlenderUpdater", None))
        self.btn_Quit.setText(_translate("MainWindow", "Quit", None))
        self.btn_Check.setText(_translate("MainWindow", "Version Check", None))
        self.lbl_task.setText(_translate("MainWindow", "TextLabel", None))
        self.lbl_available.setText(_translate("MainWindow", "Available versions from buildbot:", None))
        self.btn_about.setToolTip(_translate("MainWindow", "Settings", None))
        self.lbl_start.setText(_translate("MainWindow", "<html><head/><body><p>Press &quot;Version Check&quot; to get a list of the most current buildbot versions.</p></body></html>", None))
        self.line_path.setText(_translate("MainWindow", "not set", None))
        self.label.setText(_translate("MainWindow", "Choose path (must be an existing folder):", None))

import res_rc
