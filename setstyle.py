from vendor.Qt import QtWidgets, QtGui
import sys

def setPalette():


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
    return(dark_palette)
