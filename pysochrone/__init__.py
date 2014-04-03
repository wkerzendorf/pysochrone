import os
from iso_interpolate import *
from iso_get import *

pyIsoPath = os.path.expanduser('~/.pysochrone')
dbPath = os.path.join(pyIsoPath,'pysochrone.db3')
#Check for the pyIsoDB3 file
if not os.path.exists(dbPath):
    raise IOError('Database not found at %s' % dbPath)