# BlenderUpdater
A small crossplatform (Linux, Windows, OSX) Python3 GUI application to check https://builder.blender.org/download for
the latest buildbot version. Download and install nightly builds with one click.

## Dependencies
* Built with PyQt4 for GUI
* Beautiful Soup for HTML parsing.

### Mac
cx_freeze installation procedure:
TODO:

## Compiled releases
Freezing is done via cx_freeze.
On Windows, you can grab the .zip, extract it and execute BlenderUpdater.exe. Frozen binary files for OSX and Linux coming soon. As of now, just run "python BlenderUpdater.py" (make sure that the dependencies are met).

## Known limitations
Due to UAC starting in Windows Vista, you cannot use the "C:\Program Files\" directory. Please choose some other destination on your hard drive.
