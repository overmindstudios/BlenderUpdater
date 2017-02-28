from distutils.core import setup
from esky.bdist_esky import Executable

setup(
    name='BlenderUpdater',
    version='1.1',
    author='Tobias Kummer for Overmind Studios',
    options={"bdist_esky":
               {"freezer_module":"cxfreeze"
	      }},
    scripts = [Executable('BlenderUpdater.py', gui_only=True, icon="icon.ico")],)
