[![GPL3 License](https://img.shields.io/badge/license-GPL3-blue.svg)](https://github.com/ogierm/BlenderUpdater/blob/master/LICENSE)
![Screenshot](https://raw.githubusercontent.com/ogierm/BlenderUpdater/master/screenshot.png)

# BlenderUpdater
A small crossplatform (Linux, Windows, OSX) Python3 GUI application to check [https://builder.blender.org/download](https://builder.blender.org/download) for
the latest buildbot version. Download and install nightly builds with one click.

![](/images/appicon.svg)

## Download
Here's the latest release: [https://github.com/ogierm/BlenderUpdater/releases/latest](https://github.com/ogierm/BlenderUpdater/releases/latest)
You can also download it on [Itch.io](https://fettiemettie.itch.io/blenderupdater)

### Windows x86-64
You can grab the release .exe, copy it into a folder on your hard drive and execute BlenderUpdater.exe. If it fails to run, try running it as admin.

### Windows x86, Linux & OSX
As I am not using these, I can't freeze (build) any executable files for them. Please check out the [original repository](https://github.com/ogierm/BlenderUpdater/releases/latest), as the main dev planned on adding those down the line.
As of now, just run "python BlenderUpdater.py" on your system (make sure that the dependencies are met).

## Usage
Specify a folder on your system (e.g. `C:\Blender`) where the Blender build will be copied to. The tool will not create a new directory by itself, so make sure you create one first.
Then click on the "Version Check" button to see a list of currently available builds. The ones matching your operating system will be highlighted. Click on the desired version to download and copy to your specified folder.
When everything has finished, you'll see a "Run Blender" button to start the new version right away.

![Screenshot](https://raw.githubusercontent.com/ogierm/BlenderUpdater/master/run_blender.png)

In case there is an update for BlenderUpdater, you'll see a button in the top right corner to go to the download page.

![Screenshot](https://raw.githubusercontent.com/ogierm/BlenderUpdater/master/app_update.png)

## Known limitations
Due to UAC starting in Windows Vista, you cannot use the `C:\Program Files\` directory as a
normal user. Please choose some other destination on your hard drive OR right-click
the application and choose "Run as Administrator" to be able to access those special folders.

## Freezing
Freezing is done via pyinstaller (`pyinstaller --icon=icon.ico --onefile --windowed BlenderUpdater.py`)

## Dependencies
Built with PySide2 for the UI and Beautiful Soup and requests for HTML parsing.

## Disclaimer
This application was originally developed for in-house usage at [Overmind Studios](http://www.overmind-studios.de). Released as-is.
