import os

pyIsoPath = os.path.expanduser('~/.pyisochrone')
dbPath = os.path.join(pyIsoPath,'pyiso.db3')
#Check for the pyIsoDB3 file
if not os.path.exists(dbPath):
    raise IOError('Database not found at %s' % dbPath)