
# Hourly waeather data is avaliable from NOAA only for the year of 2010 (temperture windspeed pressure)
# If multiple years of weather data is required, this may not be a appropriate source
# Scipy need to be install          desired data type: temperature,humidity,solar_direct,solar_diffuse,pressure,wind_speed

import pandas as pd
import csv, requests
from datetime import datetime

def downloadweather_NOAA(stationid, startdate, enddate, outputFilename):
# token is required and can be obtained from https://www.ncdc.noaa.gov/cdo-web/token
    myToken='GlQbxfsaOUPCWrtJylfRwRuXwAZJnyVK'
    myUrl='https://www.ncdc.noaa.gov/cdo-web/api/v2/stations?datasetid=NORMAL_HLY&limit=1000'
    head={'token':myToken}
    r=requests.get(url=myUrl, headers=head)
    data=r.json()
    
    list_station=[]
    list_id=[]
    for dicts in data['results']:        
        list_station.append(dicts['name'])        
        list_id.append(dicts['id'])
        station_dict=dict(zip(list_id, list_station))  
        
    myUrl_1='https://www.ncdc.noaa.gov/cdo-web/api/v2/data?datasetid=NORMAL_HLY&datatypeid=HLY-TEMP-NORMAL&unit=standard&stationid='+stationid+'&startdate='+startdate+'&enddate='+enddate+'&limit=1000'
    myUrl_2='https://www.ncdc.noaa.gov/cdo-web/api/v2/data?datasetid=NORMAL_HLY&datatypeid=HLY-WIND-AVGSPD&unit=standard&stationid='+stationid+'&startdate='+startdate+'&enddate='+enddate+'&limit=1000'
    myUrl_3='https://www.ncdc.noaa.gov/cdo-web/api/v2/data?datasetid=NORMAL_HLY&datatypeid=HLY-PRES-NORMAL&unit=standard&stationid='+stationid+'&startdate='+startdate+'&enddate='+enddate+'&limit=1000'
    head={'token':myToken}
    r1=requests.get(url=myUrl_1, headers=head)
    r2=requests.get(url=myUrl_2, headers=head)
    r3=requests.get(url=myUrl_3, headers=head)
    data1=r1.json()
    data2=r2.json()
    data3=r3.json()
    
    if data1=={} or data2=={} or data3=={}:
        print('no data avaliable for one of the url')
    else:
               
        f_1 = open("temperature.csv","w",newline='')
        w_1 = csv.writer(f_1)
        keys=['time','value'] 
        w_1.writerow(keys)
        for dicts in data1['results']:
            row_arrayt=[]
            #remove the 'T' between date and time
            timestamp=dicts['date']
            timestampfixed=timestamp.replace("T", " ")
            row_arrayt.append(timestampfixed)
            row_arrayt.append(float(dicts['value'])/10) #the temperature (F) value need to be divided by ten
            w_1.writerow(row_arrayt)       
        f_1.close()
             
        f_2 = open("windspeed.csv","w",newline='')
        w_2 = csv.writer(f_2)
        keys=['time','value'] 
        w_2.writerow(keys)
        for dicts in data2['results']:
            row_arrayw=[]
            #remove the 'T' between date and time
            timestamp=dicts['date']
            timestampfixed=timestamp.replace("T", " ")
            row_arrayw.append(timestampfixed)
            row_arrayw.append(float(dicts['value'])/10)
            w_2.writerow(row_arrayw)   
        f_2.close()
        
        f_3 = open("pressure.csv","w",newline='')
        w_3 = csv.writer(f_3)
        keys=['time','value'] 
        w_3.writerow(keys)
        for dicts in data3['results']:
            row_arrayp=[]
            #remove the 'T' between date and time
            timestamp=dicts['date']
            timestampfixed=timestamp.replace("T", " ")
            row_arrayp.append(timestampfixed)
            row_arrayp.append(float(dicts['value'])*10)
            w_3.writerow(row_arrayp)   
        f_3.close()
    # linear interpolation
  
    with open("temperature.csv") as f1:
         reader_1 = csv.reader(f1)
         timestamp=[]
         temperature=[]
         for row in reader_1:
             #skip frist row
             if reader_1.line_num == 1:
                 continue
             #read the timestamp after transfer the data type
             timestamp.append(datetime.strptime(row[0],"%Y-%m-%d %H:%M:%S"))
             temperature.append(row[1])        
    f1.close()
    
    with open("windspeed.csv") as f2:
         reader_2 = csv.reader(f2)
         #timestamp=[]
         windspeed=[]
         for row in reader_2:
             #skip frist row
             if reader_2.line_num == 1:
                 continue             
             windspeed.append(row[1])     
    f2.close()
    
    with open("pressure.csv") as f3:
         reader_3 = csv.reader(f3)
         #timestamp=[]
         pressure=[]
         for row in reader_3:
             #skip frist row
             if reader_3.line_num == 1:
                 continue             
             pressure.append(row[1])     
    f3.close()
   
    #Creat a timeseries data      
    dti=pd.to_datetime(timestamp)
    ts1 = pd.Series(temperature, index=dti)
    ts2 = pd.Series(windspeed, index=dti)
    ts3 = pd.Series(pressure, index=dti)
    #upsample to every 5 minutes
    s1=ts1.resample('300s').interpolate()
    s2=ts2.resample('300s').interpolate()
    s3=ts3.resample('300s').interpolate()
    #transfering to float
    s1=s1.astype(float)
    s2=s2.astype(float)
    s3=s3.astype(float)
    s1=s1.interpolate(method='quadratic')
    s2=s2.interpolate(method='quadratic')
    s3=s3.interpolate(method='quadratic')
    
    dt=pd.DataFrame(data={'temperature':list(s1.values), 'windspeed':list(s2.values), 'pressure':list(s3.values)}, index=s1.index)
    #write the DataFrame into a csv file
    dt.to_csv(outputFilename)
    print('weather data from '+station_dict[stationid]+' saved in '+outputFilename)

def _tests():
    # avaliable station id is in stationid_with_hourly_data.csv 
	downloadweather_NOAA('GHCND:USW00024233','2010-05-01','2010-06-01','5min_temp_wind_pressure.csv')

if __name__ == '__main__':
	_tests()
