from scipy import interpolate, spatial
import cPickle as pickle
import numpy as np
import sqlite3
import pdb
import os

from matplotlib.widgets import Slider, Button, RadioButtons, CheckButtons
import pandas as pd

def convertZipPickle(blob):
    return pickle.loads(bz2.decompress(blob))

def getDBConnection(dbFName = '~/.pysochrone/pysochrone.db3'):
    dbFName = os.path.expanduser(dbFName)
    return sqlite3.connect(dbFName, detect_types=sqlite3.PARSE_DECLTYPES)
    
    
def readFromDB(conn=None):
    if conn==None:
        conn = getDBConnection()
        
    data = conn.execute('select age, mh, data from basti_iso').fetchall()
    conn.close()
    age, mh, iso = zip(*data)
    iso = np.array([item.reshape(2000,13) for item in iso])
    return np.array(zip(age, mh)), iso

def get_panel_from_data(index, data):
    column_names = ['mass_in', 'mass', 'log_luminosity', 'log_teff', 'm_v',
                    'ub', 'bv', 'vi', 'vr', 'vj', 'vk', 'vl', 'hk']

    frame_collection = []
    for frame in data:
        frame = pd.DataFrame(frame, columns=column_names)
        frame['teff'] = 10**frame['log_teff']
        frame['m_bolometric'] = 4.75 - 2.5 * frame['log_luminosity']
        frame['logg'] = (np.log10(frame['mass']) + 4 * frame['log_teff'] +
                         0.4 * frame['m_bolometric'] - 12.516)
        del frame['log_teff']
        frame_collection.append(frame)

    isochrone_panel = pd.Panel.from_dict(dict(zip(
        [tuple(item) for item in index],
        frame_collection)))


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
                ('teff', float),
                ('mbol', float),
                ('logg', float),
                ]
    te = 10**data[:,3]
    mBol = 4.75 -2.5*data[:,2]
    logg = np.log10(data[:,1]) + 4*data[:,3] + 0.4*mBol - 12.516
    curLen = len(te)
    newData = [tuple(item) for item in np.hstack((data, te.reshape(curLen,1), mBol.reshape(curLen,1), logg.reshape(curLen,1)))]
    return np.array(newData, dtype = fields)

def getIsoInterpolator(conn=None):
    points, values = readFromDB(conn)
    return interpolate.LinearNDInterpolator(points, values)
    
def getTeffLoggInterpolator(conn=None):
    points, values = readFromDB(conn)
    newValues = []
    for value in values:
        teff = 10**value[:,3]
        mBol = 4.75 -2.5*value[:,2]
        logg = np.log10(value[:,1]) + 4*value[:,3] + 0.4*mBol - 12.516
        newValues.append(np.vstack((teff, logg)))

    return interpolate.LinearNDInterpolator(points, newValues)

def getPhot(teff, logg, feh, isoInterpolator, stepSize=0.1):
    ages = np.arange(isoInterpolator.points[:,0].min(), isoInterpolator.points[:,0].max(), stepSize)
    dists = []
    distIDx = []
    for age in ages:
        isoData = getCompleteData(isoInterpolator(age, feh))
        teffLoggData = isoData[['teff','logg']].view(np.float).reshape((isoData.size, 2))
        #teffLoggKDTree = spatial.kdtree.KDTree(teffLoggData/np.array((teff, logg)))
        tmpDist = (teffLoggData-np.array((teff, logg)))/(teffLoggData+np.array((teff, logg)))
#        dist, idx = teffLoggKDTree.query((1, 1))
        calcDist = np.sum(tmpDist**2,axis=1)
        dists.append(np.min(calcDist))
        distIDx.append(np.argmin(calcDist))
    minIDx = np.argmin(dists)
    return getCompleteData(isoInterpolator(ages[minIDx], feh))[distIDx[minIDx]]    

def getMinuitGrid(interpolator, params):
    if len(params) == 0:
        raise ValueError('Please give a kwargs')
    def errfunc(age, feh):
        iso = getCompleteData(interpolator((age, feh)))
        dists = [((iso[key]-value)/(value))**2 for key, value in params.items()]
        dist = np.sum(dists, axis=0)
        #pdb.set_trace()
        return np.min(dist)
    minf = minuit.Minuit(errfunc)
    return minf
    
    
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
    
def showTeffLogg(teffLoggInterpolator, fig=None):
    import pylab
    if fig==None:
        fig = pylab.figure(1)
    def sliderUpdate(val):
        teff, logg = teffLoggInterpolator(tuple([slider.val for slider in sliders]))
        isoPlot.set_data([teff, logg])
        plotAxis.relim()
        plotAxis.autoscale_view()
        pylab.draw()
        
    
    #adding sliders
    sliders=[]
    paramNames = ['age','[Fe/H]']
    paramInit = [5, 0]
    ages, fehs = np.unique(teffLoggInterpolator.points[:,0]), np.unique(teffLoggInterpolator.points[:,1])
    for i,axis in enumerate([ages, fehs]):
        ax = fig.add_axes([0.1,i*0.05+0.05,0.7,0.03])
        sliders.append(Slider(ax, paramNames[i], min(axis), max(axis), valinit=paramInit[i]))
        
        
    for slider in sliders:
        slider.on_changed(sliderUpdate)
        
        
    
    plotAxis = fig.add_axes([0.1, 0.1+0.15, 0.8, (1-0.1+0.1)*0.7])
#    if sampleStar != None:
#        plotAxis.plot(sampleStar.x, sampleStar.y, lw=3, color='black')
    teff, logg = teffLoggInterpolator(tuple([slider.val for slider in sliders]))
    isoPlot, = plotAxis.plot(teff, logg)
    plotAxis.invert_xaxis()
    plotAxis.invert_yaxis()
    plotAxis.set_xlabel('Teff [K]')
    plotAxis.set_ylabel('log(g)')
    pylab.show()    
    


        
sqlite3.register_converter("npmap", np.fromstring)