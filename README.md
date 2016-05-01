# BlenderUpdater
A small crossplatform (Linux, Windows, OSX) Python3 GUI application to check https://builder.blender.org/download for 
the latest buildbot version. Download and install nightly builds with one click.

## Dependencies
Built with PyQt4 for the UI and Beautiful Soup for HTML parsing.

## Compiled releases
### Windows
You can grab the release .zip, extract it and execute BlenderUpdater.exe. Freezing is done via esky/cx_freeze. ("python setup.py bdist_esky")



### Linux & OSX
Frozen binary files for Linux and OSX coming soon. As of now, just run "python BlenderUpdater.py" (make sure that the dependencies are met).

## Known limitations
Due to UAC starting in Windows Vista, you cannot use the "C:\Program Files\" directory. Please choose some other destination on your hard drive.
