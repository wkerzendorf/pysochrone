import urllib
import urllib2
import numpy as np
import re
from matplotlib import mlab
import StringIO
import urllib, pycurl
import sqlite3
import os
from glob import glob
metalVals=['z0001', 'z0003', 'z0006', 
    'z001', 'z002', 'z004', 
    'z008', 'z01', 'z02', 
    'z03', 'z04']
from copy import copy
url1 = "http://albione.oa-teramo.inaf.it/cgi-bin/IM_WORK/iso_maker_1.pl"    
url2 = "http://albione.oa-teramo.inaf.it/cgi-bin/IM_WORK/iso_maker_2.pl"
values2=[('mixture','solarmix'),
        ('transfo','ubvri'),
        ('modtype','stand'),
        ('t1','21.6'), #22.6
        ('t2','19397.2')] #19197.2


values2=dict([('mixture','solarmix'),
        ('transfo','ubvri'),
        ('modtype','stand'),
        ('t1','22.3'), #22.6
        ('t2','25939.7')]) #19197.2

values1=dict([('output','iso'),
        ('mixture','solarmix'),
        ('transfo','ubvri'),
        ('modtype','stand')])
 
class htmlcatch():
    def __init__(self):
        self.contents = ''

    def html(self, code):
        self.contents += code
        
def getIso(age, metallicity=None, metalVal=None, verbose=True):
    if metallicity!=None:
        metalPattern = re.compile('z(\d+)')
        #return [float('0.'+metalPattern.search(item).groups()[0]) for item in metalVals]
        isoMetals = [np.log10(float('0.'+metalPattern.search(item).groups()[0])/0.02) for item in metals]
        isoMetals = np.array(isoMetals)
        metalIDx = np.argmin(abs(isoMetals - metallicity))
        curMetalVal = metalVals[metalIDx]
    
    elif metalVal!=None:
        curMetalVal = metalVal
    else:
        raise NotImplementedError('Please give metallicity or metalVal')
    if verbose:
        print "Choosing closest metallicity: %s" % curMetalVal
    



    Z = curMetalVal
    theage = str(age)
    verbose = 0
    
    iso_output1 = htmlcatch()
    
    iso_maker1 = pycurl.Curl()
    
    data = [
            ('output', 'iso'),
            ('mixture', 'solarmix'),
            ('transfo', 'ubvri'),
            ('modtype', 'stand'),
            ('Z', Z)
            ]
    
    print data 
    options = {
            pycurl.URL : 'albione.oa-teramo.inaf.it/cgi-bin/IM_WORK/iso_maker_1.pl',
            pycurl.POST : 1,
            pycurl.POSTFIELDS : urllib.urlencode(data),
            pycurl.REFERER : 'http://albione.oa-teramo.inaf.it/BASTI/WEB_TOOLS/IM_HTML/index.html',
            pycurl.VERBOSE : verbose,
            pycurl.FOLLOWLOCATION: 1,
            pycurl.WRITEFUNCTION : iso_output1.html
            }
    
    [iso_maker1.setopt(option, value) for option, value in options.iteritems()]
    
    iso_maker1.perform()
    
    print iso_output1.contents
    hiddenFields = iso_output1.contents.split(' type="hidden"')[1::]
    
    data = [('theage', theage)]
    for hiddenField in hiddenFields:
        name = hiddenField.split('"')[1]
        value = hiddenField.split('"')[3]
        
        data.append((name, value))
    
    print data
    iso_output2 = htmlcatch()
    iso_maker2 = pycurl.Curl()
    
    options = {
            pycurl.URL : 'albione.oa-teramo.inaf.it/cgi-bin/IM_WORK/iso_maker_2.pl',
            pycurl.POST : 1,
            pycurl.POSTFIELDS : urllib.urlencode(data),
            pycurl.REFERER : 'albione.oa-teramo.inaf.it/cgi-bin/IM_WORK/iso_maker_1.pl',
            pycurl.VERBOSE : verbose,
            pycurl.FOLLOWLOCATION : 1,
            pycurl.WRITEFUNCTION : iso_output2.html
            }
    
    [iso_maker2.setopt(option, value) for option, value in options.iteritems()]
    
    iso_maker2.perform()
        
    file('bastia%05d%s.dat' % (age, curMetalVal), 'w').write(iso_output2.contents)
    
    #fields = ['m_in', 'm', 'log_l_bol', 'log_te', 
    #        'm_v', 'ub', 'bv', 'vi', 'vr', 'vj','vk','vl','hk']
    #buff = StringIO.StringIO(response.readlines())
    #return np.recfromtxt(buff, names = fields)
    

def getGrid(ageRange):
    for age in ageRange:
        for metalVal in metalVals:
            print "currently at age %s and metallicity %s" % (age, metalVal)
            getIso(age, metalVal=metalVal)

def readBastiIso(fName):
    fh = file(fName)
    headParse = re.compile("#\s+Np=\s+(\d+)\s+\[M/H\]=\s*([+-]?\d+\.\d+)\s+"
                           "Z=\s+([+-]?\d+\.\d+)\s+Y=([+-]?\d+\.\d+)"
                           "\s+t\(Gyr\)=\s+([+-]?\d+\.\d+)\s+normalized:\s+(\d+\s+\d+\s+\d+)")
    curHeader = None
    for line in fh:
        head = headParse.search(line)
        if head!=None:
            print curHeader
            curHeader = head.groups()
            break
    if curHeader == None:
        raise ValueError('Problem reading header with file %s' % fName)
    tabData = loadtxt(fName)
    fh.close()
    return curHeader, tabData
        
    
def createIsoDB(dbName):
    conn = sqlite3.connect(dbName)
    dbSchema = "create table BASTI_ISO (ID integer primary key,"\
                "AGE float,"\
                "MH float,"\
                "Z float,"\
                "Y float,"\
                "NP integer,"\
                "PARAM1 text,"\
                "DATA npmap);"
    conn.executescript(dbSchema)
    conn.commit()
    conn.close()
    
def storeInDB(dbName, rawFileDir='.'):
    conn = sqlite3.connect(dbName)
    for fname in glob(os.path.join(rawFileDir,'bastia*.dat')):
        print "Inserting %s" % fname
        curHead, curData = readBastiIso(fname)
        prepData = sqlite3.Binary(curData.tostring())
        insertData = tuple(list(curHead) + [prepData])
        conn.execute('insert into BASTI_ISO (NP, MH, Z, Y, AGE, PARAM1, DATA) VALUES (?, ?, ?, ?, ?, ?, ?)', insertData)
    conn.commit()
    conn.close()
        
    