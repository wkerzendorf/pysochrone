from scipy import interpolate
import cPickle as pickle
import numpy as np
import sqlite3
import pdb
import os

def convertZipPickle(blob):
    return pickle.loads(bz2.decompress(blob))

def getDBConnection(dbFName = '~/.pysochrone/pysochrone.db3'):
    dbFName = os.path.expanduser(dbFName)
    return sqlite3.connect(dbFName, detect_types=sqlite3.PARSE_DECLTYPES)
    
    
def readFromDB(conn):

    data = conn.execute('select age, mh, data from basti_iso').fetchall()
    conn.close()
    age, mh, iso = zip(*data)
    return np.array(zip(age, mh)), np.array(iso)


def getIsoChrone(age, mh, conn =None):
    if conn == None:
        conn = getDBConnection()
    
    points, values = readFromDB(conn)
    crudeData = interpolate.griddata(points=points, values=values, xi = [[age,mh]])[0].reshape(2000,13)
    return getCompleteData(crudeData)
    
def getMHDataDB(points, values, ageRange, mh):
    newPoints = np.array([(item, mh) for item in ageRange])
    newData = interpolate.griddata(points=points,
                        values=values,
                        xi=newPoints)
    return newPoints, newData
    
    
def getCompleteData(data):
    fields = [('m_in',float),
                ('m',float),
                ('log_l',float),
                ('log_te',float),
                ('m_v',float),
                ('ub',float),
                ('bv',float),
                ('vi',float),
                ('vr',float),
                ('vj',float),
                ('vk',float),
                ('vl',float),
                ('hk',float),
                ('te', float),
                ('mbol', float),
                ('logg', float),
                ]
    te = 10**data[:,3]
    mBol = 4.75 -2.5*data[:,2]
    logg = np.log10(data[:,1]) + 4*data[:,3] + 0.4*mBol - 12.516
    curLen = len(te)
    newData = [tuple(item) for item in np.hstack((data, te.reshape(curLen,1), mBol.reshape(curLen,1), logg.reshape(curLen,1)))]
    return np.array(newData, dtype = fields)
    
def getMinDataAge(teff, logg, dataDB):
    minValues = []
    for item in dataDB:
        expData = getCompleteData(item)
        dist = ((expData['te'] - teff) / teff)**2+((expData['logg'] - logg)/logg)**2
        minIDx = np.argmin(dist)
        if np.isnan(dist[minIDx]): pdb.set_trace()
        minValues.append((dist[minIDx], minIDx))
    return np.array(minValues)

def getGoodIsoAge(teff, logg, mh, isoPoints, isoValues, ageRange, ageSelectSample = 3, ageSampleNo = 20, convThresh = 1e-3, i=0):
    interpPoints, interpValues = getMHDataDB(isoPoints, isoValues, ageRange, mh)
    minData = getMinDataAge(teff, logg, interpValues)
    
    if min(minData[:,0]) < convThresh or i>5:
        
        idx = np.argmin(minData[:,0])
        return interpPoints[idx], getCompleteData(interpValues[idx]), minData[idx,1]
    else:
        sortIDx = np.argsort(minData)[:ageSelectSample]
        ageSample = ageRange[sortIDx]
        newAgeRange = np.linspace(np.min(ageSample), np.max(ageSample), ageSampleNo)
        return getGoodIsoAge(teff, logg, mh, isoPoints, isoValues, newAgeRange, i= i+1)
    
    
        
sqlite3.register_converter("npmap", np.fromstring)