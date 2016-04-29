from distutils.core import setup
from esky.bdist_esky import Executable


setup(
    name = 'BlenderUpdater',
    version = '0.6',
    options = {"bdist_esky":
               {"includes" : ['PyQt4'],
               "freezer_module":"cxfreeze"
	      }},
    scripts = [Executable('BlenderUpdater.py', gui_only=True)],)
