# This model was developed by Prof. Dr. Lilik Budi Prasetyo, Dr. Yudi Setiyawan, Desi Suyamto, Sahid Hudjimartsu
# Faculty of Forestry, Bogor Agricultural University
# References: Hudjimartsu, S., Prasetyo, L., Setiawan, Y. and Suyamto, D., 2017, November.
# Illumination Modelling for Topographic Correction of Landsat 8 and Sentinel-2A Imageries.
# In European Modelling Symposium (EMS), 2017 (pp. 95-99). IEEE.

from datetime import datetime, date
import numpy as np
import glob, math, os
from osgeo import gdal
from scipy.stats import linregress
from dict import dict
import numexpr

#Load Metadata
path = 'folder_data'
glob_f= glob.glob(path+ '/*.txt') # list txt file
f=open(glob_f[1])
def build_data(f):
    output = {}
    for line in f.readlines():
        if "=" in line:
            l = line.split("=")
            output[l[0].strip()] = l[1].strip()
    return output
data = build_data(f)

#Load data raster
print "Loading Data Raster..."
#Load data raster
raster_list=glob.glob(path+ '*.TIF')
dataRaster=[]
for i in raster_list:
    band=gdal.Open(i)
    dataRaster.append(band.GetRasterBand(1).ReadAsArray().astype(float))
filename=[]
for a in [os.path.basename(x) for x in glob.glob(path + '*.TIF')]:
    p=os.path.splitext(a)[0]
    filename.append(p)
my_dict= dict(zip(filename, dataRaster))

#Load data raster aspect & slope
pathname='Folder name' # folder consist of aspect and slope data
raster_list_dem=glob.glob(pathname +'/*.TIF')
dataTopo=[]
for d in raster_list_dem:
    band2=gdal.Open(d)
    dataTopo.append(band2.GetRasterBand(1).ReadAsArray())

def year_date():
    year_file=data['DATE_ACQUIRED']
    date_file=data['SCENE_CENTER_TIME']
    date_file2= date_file [1:16]
    all= year_file+" "+date_file2
    parsing = datetime.strptime(all, '%Y-%m-%d %H:%M:%S.%f')
    return parsing
dt=year_date()

# UTC based on zoning area
# This sample uses + 7, because in the western region of Indonesia
def hour():
    h=dt.hour+7
    return h
def second():
    s= float(dt.microsecond)/1000000+dt.second
    return s
def leap():
    if (dt.year % 4) == 0:
        if (dt.year % 100) == 0:
            if (dt.year % 400) == 0:
               a = int(366)
            else:
                a = int(365)
        else:
            a= int(366)
    else:
        a= int(365)
    return a
def cos(x):
    cos= np.cos(np.deg2rad(x))
    return  cos
def sin(x):
    sin=np.sin(np.deg2rad(x))
    return sin
def day():
    day_date= date(dt.year, dt.month, dt.day)
    sum_of_day=int(day_date.strftime('%j'))
    return sum_of_day

print "Calculating Solar Position..."
gamma=((2 * math.pi) / leap()) * ((day() - 1) + (((hour()+dt.minute/60+second()/3600) - 12) / 24) )# degree


#sun declination angle
decl=0.006918 - 0.399912 * cos(gamma) + 0.070257 * sin(gamma) - 0.006758 * cos (2 * gamma)\
     + 0.000907 * sin (2 * gamma) - 0.002697 * cos (3 * gamma) + 0.00148 * sin (3 * gamma) #radians
decl_deg= (360 / (2 * math.pi)) * decl

#lat long value
# get columns and rows of your image from gdalinfo
xoff, a, b, yoff, d, e = band.GetGeoTransform()
def pixel2coord(x, y):
    xp = a * x + b * y + xoff
    yp = d * x + e * y + yoff
    return(xp, yp)
rows=dataRaster[0].shape[0]
colms=dataRaster[0].shape[1]
coordinate=[]
for row in  range(0,rows):
  for col in  range(0,colms):
      coordinate.append(pixel2coord(col,row))
coor_2=np.array(coordinate, dtype=float)
long=coor_2[:,0]
lat=coor_2[:,1]
long_n=long.reshape(rows,colms)
lat_n=lat.reshape(rows,colms)

#eqtime
eqtime = 229.18 * (0.000075 + 0.001868 * cos(gamma) - 0.032077 * sin(gamma) - 0.014615 * cos(2 * gamma) - 0.040849 * sin(2 * gamma))  # minutes
timeoff= eqtime - 4 * long_n + 60 * 7 #minutes
tst=hour() * 60 + dt.minute + second() / 60 + timeoff #minutes
ha=(tst /4)-180 #degree

#sun zenith angle
zenit1 =sin(lat_n)* sin(decl_deg) + cos (lat_n)* cos(decl_deg) * cos(ha)
zenit2=np.arccos(zenit1) #radians
zenit_angle= np.rad2deg(zenit2)

#sun azimuth angle
theta1= -1 * ((sin(lat_n)) * cos(zenit_angle)- sin(decl_deg)/(cos (lat_n) * sin (zenit_angle)))
theta2=np.arccos(theta1) #radians
theta3=np.rad2deg(theta2)#degree
azimuth_angle=180 - theta3 #degrees

# IC calculation
delta=azimuth_angle - dataTopo[0]
IC=(cos(zenit_angle)* cos (dataTopo[1])) + (sin(zenit_angle) * sin (dataTopo[1]) * cos(delta))#radians

print "Calculating Reflectances..."
#Reflectance
reflectance_band1=(float(data['REFLECTANCE_MULT_BAND_1'])*my_dict[filename[0][:-2]+'B1']+float(data['REFLECTANCE_ADD_BAND_1']))/cos(zenit_angle)
reflectance_band2=(float(data['REFLECTANCE_MULT_BAND_2'])*my_dict[filename[0][:-2]+'B2']+float(data['REFLECTANCE_ADD_BAND_2']))/cos(zenit_angle)
reflectance_band3=(float(data['REFLECTANCE_MULT_BAND_3'])*my_dict[filename[0][:-2]+'B3']+float(data['REFLECTANCE_ADD_BAND_3']))/cos(zenit_angle)
reflectance_band4=(float(data['REFLECTANCE_MULT_BAND_4'])*my_dict[filename[0][:-2]+'B4']+float(data['REFLECTANCE_ADD_BAND_4']))/cos(zenit_angle)
reflectance_band5=(float(data['REFLECTANCE_MULT_BAND_5'])*my_dict[filename[0][:-2]+'B5']+float(data['REFLECTANCE_ADD_BAND_5']))/cos(zenit_angle)
reflectance_band6=(float(data['REFLECTANCE_MULT_BAND_6'])*my_dict[filename[0][:-2]+'B6']+float(data['REFLECTANCE_ADD_BAND_6']))/cos(zenit_angle)
reflectance_band7=(float(data['REFLECTANCE_MULT_BAND_7'])*my_dict[filename[0][:-2]+'B7']+float(data['REFLECTANCE_ADD_BAND_7']))/cos(zenit_angle)
reflectance_band9=(float(data['REFLECTANCE_MULT_BAND_9'])*my_dict[filename[0][:-2]+'B9']+float(data['REFLECTANCE_ADD_BAND_9']))/cos(zenit_angle)
reflectance_f= {filename[0][:-2]+'B1':reflectance_band1, filename[0][:-2]+'B2':reflectance_band2,filename[0][:-2]+'B3':reflectance_band3, filename[0][:-2]+'B4':reflectance_band4, filename[0][:-2]+'B5':reflectance_band5, filename[0][:-2]+'B6':reflectance_band6, filename[0][:-2]+'B7':reflectance_band7, filename[0][:-2]+'B9':reflectance_band9}


# Training sample to avoid the cloud
NDVI=numexpr.evaluate("(reflectance_band5 - reflectance_band4) / (reflectance_band5 + reflectance_band4)")
sampleArea= numexpr.evaluate("(NDVI >0.5) & (dataTopo[1] >= 18)")
area_true= sampleArea.nonzero()
a_true=area_true[0]
b_true=area_true[1]

#Topographic correction using Illumination condition and rotation model
temp={}
IC_final={}
for y in reflectance_f:
        val2=reflectance_f[y]
        temp[y]=val2[a_true,b_true].ravel()
        IC_true=IC[a_true,b_true].ravel()
        slope=linregress(IC_true, temp[y])
        IC_final[y]=reflectance_f[y]-(slope[0]*(IC-cos(zenit_angle)))
print "Exporting to GeoTIFF..."
#export auto
for item in IC_final:
    geo = band.GetGeoTransform()
    proj = band.GetProjection()
    shape = my_dict[filename[0][:-2]+'B1'].shape
    driver = gdal.GetDriverByName("GTiff")
    dst_ds = driver.Create("Folder Output" + "topo.TIF", shape[1], shape[0], 1, gdal.GDT_Float32)
    dst_ds.SetGeoTransform(geo)
    dst_ds.SetProjection(proj)
    ds=dst_ds.GetRasterBand(1)
    ds.SetNoDataValue(0)
    ds.WriteArray(IC_final[item])
    dst_ds.FlushCache()
    dst_ds = None  # save, close"""

