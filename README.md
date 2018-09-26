[![GPL3 License](https://img.shields.io/badge/license-GPL3-blue.svg)](https://github.com/MrKepzie/Natron/blob/master/LICENSE)[![Build Status](https://travis-ci.org/overmindstudios/BlenderUpdater.svg?branch=master)](https://travis-ci.org/overmindstudios/BlenderUpdater)

![Screenshot](https://raw.githubusercontent.com/overmindstudios/BlenderUpdater/master/screenshot.png)

# BlenderUpdater
 ![logo](https://raw.githubusercontent.com/overmindstudios/BlenderUpdater/master//images/appicon.png)

A small crossplatform (Linux, Windows, OSX) Python3 GUI application to check [https://builder.blender.org/download](https://builder.blender.org/download) for
the latest buildbot version. Download and install nightly builds with one click. Brought to you by [Overmind Studios](http://www.overmind-studios.de).

## Download
Here's the latest release: [https://github.com/overmindstudios/BlenderUpdater/releases/latest](https://github.com/overmindstudios/BlenderUpdater/releases/latest)

### Windows
You can grab the release .exe, copy it into a folder on your hard drive and execute BlenderUpdater.exe.

### Linux & OSX
Frozen binary files for Linux and OSX coming soon. As of now, just run "python BlenderUpdater.py" on your system (make sure that the dependencies are met).

## Usage
Specify a folder on your system (e.g. `C:\Blender`) where the Blender build will be copied to. The tool will not create a new directory by itself, so make sure you create one first.
Then click on the "Version Check" button to see a list of currently available builds. The ones matching your operating system will be highlighted. Click on the desired version to download and copy to your specified folder.
When everything has finished, you'll see a "Run Blender" button to start the new version right away.

![Screenshot](https://raw.githubusercontent.com/overmindstudios/BlenderUpdater/master/run_blender.png)

In case there is an update for BlenderUpdater, you'll see a button in the top right corner to go to the download page.

![Screenshot](https://raw.githubusercontent.com/overmindstudios/BlenderUpdater/master/app_update.png)

## Known limitations
Due to UAC starting in Windows Vista, you cannot use the `C:\Program Files\` directory as a
normal user. Please choose some other destination on your hard drive OR right-click
the application and choose "Run as Administrator" to be able to access those special folders.

## Freezing
Freezing is done via pyinstaller (`pyinstaller --icon=icon.ico --onefile --windowed BlenderUpdater.py`)

## Dependencies
Developed with Python 3.7. It *should* work with Python 3.6 as well, but no guarantees here.
It uses Qt.py as an abstraction layer for Qt, so you should be able to use either PySide2 or
PyQt5 in the background. BeautifulSoup is used for website parsing.

## Disclaimer
This application was originally developed for in-house usage at [Overmind Studios](http://www.overmind-studios.de). Released as-is.
