# BlenderUpdater
A small crossplatform (Linux, Windows, OSX) Python3 GUI application to check https://builder.blender.org/download for 
the latest buildbot version. Download and install nightly builds with one click.

## Dependencies
Built with PyQt4 for the and Beautiful Soup for HTML parsing.

## Compiled releases
### Windows
You can grab the release .zip, extract it and execute BlenderUpdater.exe. Freezing is done via cx_freeze. ("cxfreeze --base-name Win32Gui Blenderupdater.py")


### Linux and OSX
Frozen binary files for OSX and Linux coming soon. As of now, just run "python BlenderUpdater.py" (make sure that the dependencies are met).

## Known limitations
Due to UAC starting in Windows Vista, you cannot use the "C:\Program Files\" directory. Please choose some other destination on your hard drive.
