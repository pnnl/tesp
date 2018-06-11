import sys
import numpy as np

def removeZero(x):
    if x[0]=='0':
       x=x[1:]
    return x

abbreviations = [
    ['AL','Alabama','USA'],
    ['AK','Alaska','USA'],
    ['AS','American Samoa','ASM'],
    ['AZ','Arizona','USA'],
    ['AR','Arkansas','USA'],
    ['CA','California','USA'],
    ['CO','Colorado','USA'],
    ['CT','Connecticut','USA'],
    ['DE','Delaware','USA'],
    ['DC','District of Columbia','USA'],
    ['FM','Fed. States of Micronesia','FSM'],
    ['FL','Florida','USA'],
    ['GA','Georgia','USA'],
    ['GU','Guam','GUM'],
    ['HI','Hawaii','USA'],
    ['ID','Idaho','USA'],
    ['IL','Illinois','USA'],
    ['IN','Indiana','USA'],
    ['IA','Iowa','USA'],
    ['KS','Kansas','USA'],
    ['KY','Kentucky','USA'],
    ['LA','Louisiana','USA'],
    ['ME','Maine','USA'],
    ['MH','Marshall Islands','MHL'],
    ['MD','Maryland','USA'],
    ['MA','Massachusetts','USA'],
    ['MI','Michigan','USA'],
    ['MN','Minnesota','USA'],
    ['MS','Mississippi','USA'],
    ['MO','Missouri','USA'],
    ['MT','Montana','USA'],
    ['NE','Nebraska','USA'],
    ['NV','Nevada','USA'],
    ['NH','New Hampshire','USA'],
    ['NJ','New Jersey','USA'],
    ['NM','New Mexico','USA'],
    ['NY','New York','USA'],
    ['NC','North Carolina','USA'],
    ['ND','North Dakota','USA'],
    ['MP','Northern Mariana Is.','MNP'],
    ['OH','Ohio','USA'],
    ['OK','Oklahoma','USA'],
    ['OR','Oregon','USA'],
    ['PW','Palau','PLW'],
    ['PA','Pennsylvania','USA'],
    ['PR','Puerto Rico','PRI'],
    ['RI','Rhode Island','USA'],
    ['SC','South Carolina','USA'],
    ['SD','South Dakota','USA'],
    ['TN','Tennessee','USA'],
    ['TX','Texas','USA'],
    ['UT','Utah','USA'],
    ['VT','Vermont','USA'],
    ['VA','Virginia','USA'],
    ['VI','Virgin Islands','VIR'],
    ['WA','Washington','USA'],
    ['WV','West Virginia','USA'],
    ['WI','Wisconsin','USA'],
    ['WY','Wyoming','USA'],
    ['AB','Alberta','CAN'],
    ['BC','British Columbia','CAN'],
    ['MB','Manitoba','CAN'],
    ['NB','New Brunswick','CAN'],
    ['NF','Newfoundland','CAN'],
    ['NT','Northwest Territories','CAN'],
    ['NS','Nova Scotia','CAN'],
    ['NU','Nunavut','CAN'],
    ['ON','Ontario','CAN'],
    ['PE','Prince Edward Island','CAN'],
    ['QC','Quebec','CAN'],
    ['PQ','Quebec','CAN'],
    ['SK','Saskatchewan','CAN'],
    ['YT','Yukon','CAN'],
    ['YT','Yukon Territory','CAN']]

def convert_tmy2_to_epw (fileroot):
  f=open(fileroot + '.tmy2','r')
  lines=f.readlines()
  f.close()

  newline=[]

  WBAN=lines[0][1:6]

  city=lines[0][7:29]

  state=lines[0][30:32]
  #print (state)
  for row in abbreviations:
    if row[0].lower().find(state.lower())!=-1:
      country=row[2]
  #print (country)
  tz=lines[0][34:37]
  #print (tz)
  dir=lines[0][37]
  if dir.lower().find('n')!=-1:
     sim=''
  else:
     sim='-'
  deg=float(lines[0][39:41])
  min=round(float(lines[0][39:41])/60,1)
  lat=sim+str(deg+min)
  #print (lat)
  dir=lines[0][45]
  if dir.lower().find('e')!=-1:
     sim=''
  else:
     sim='-'
  deg=float(lines[0][47:50])
  min=round(float(lines[0][51:53])/60,1)
  lot=sim+str(deg+min)
  #print (lot)
  ele=lines[0][55:59].replace(' ','')
  #print (ele)
  temp='LOCATION,'+str(city)+','+str(state)+','+str(country)+','+str(WBAN)+',,'+str(lat)+','+str(lot)+','+str(tz)+','+str(ele)
  newline.append(temp)

  newline.append('DESIGN CONDITIONS,0')
  newline.append('TYPICAL/EXTREME PERIODS,0')
  newline.append('GROUND TEMPERATURES,0')
  newline.append('HOLIDAYS/DAYLIGHT SAVINGS,No,0,0,0')
  newline.append('COMMENTS 1,TMY3-'+str(WBAN)+' -- WMO#')
  newline.append('COMMENTS 2,')
  temp=('DATA PERIODS,1,1,Data,Sunday,')
  month=removeZero(lines[1][3:5])
  day=removeZero(lines[1][5:7])
  temp=temp+str(month)+'/'+str(day)
  month=removeZero(lines[-1][3:5])
  day=removeZero(lines[-1][5:7])
  temp=temp+','+ str(month)+'/'+str(day)
  newline.append(temp)

  datasource=[71,77,82,88,9,21,27,33,39,45,51,57,93,98,61,65,104,111,126,131,136,140]

  for i in range(1,len(lines)-1):
      temp=''
      year=lines[i][1:3]
      if year[0]=='0':
            year='20'+year
      else:
            year='20'+year
      temp=temp+year		  
      month=removeZero(lines[i][3:5])
      temp=temp+','+month
      day=removeZero(lines[i][5:7])
      temp=temp+','+day
      hour=removeZero(lines[i][7:9])
      temp=temp+','+hour	
      minute='0'
      temp=temp+','+minute	
      data=''
      for j in range(len(datasource)):
             if datasource[j]!=9:
                  data=data+lines[i][datasource[j]:datasource[j]+2]
             else:
                  data=data+'?0'		   
  #    if i==1:
  #          print (data)
      temp=temp+','+data
  #    print (i)	
      drybulb=float(lines[i][67:71])/10
      temp=temp+','+str(drybulb)		
      dewpoi=float(lines[i][73:77])/10	
  #    print (drybulb)
      temp=temp+','+str(dewpoi)	
      RelHum =float(lines[i][79:82])
      temp=temp+','+str(RelHum)		
      AtmPre =float(lines[i][84:88])*100
      temp=temp+','+str(AtmPre)		
      ExtHorRad=lines[i][9:13]
      temp=temp+','+str(ExtHorRad)	
      ExtDirNorRad=lines[i][13:17]
      temp=temp+','+str(ExtDirNorRad)	
      OpaSkyCov=float(lines[i][63:65])
  #    temp=temp+','+str(OpaSkyCov)	
      skyemi=(0.787+0.764*np.log((dewpoi+273.0)/273.0))*(1+0.0224*OpaSkyCov+0.0035*OpaSkyCov*OpaSkyCov+0.00028*OpaSkyCov*OpaSkyCov*OpaSkyCov)
      HorzIRSky=skyemi* 5.6697/100000000*((drybulb+273)*(drybulb+273)*(drybulb+273)*(drybulb+273))
  #    if i==1:
  #          print (HorzIRSky)
      temp=temp+','+str(HorzIRSky)		  
      GloHorzRad=float(lines[i][17:21])
      temp=temp+','+str(GloHorzRad)		
      DirNormRad=float(lines[i][23:27])
      temp=temp+','+str(DirNormRad)		
      DifHorzRad=float(lines[i][29:33])
      temp=temp+','+str(DifHorzRad)		
      GloHorzIllum=float(lines[i][35:39])
      temp=temp+','+str(GloHorzIllum)			
      DirNormIllum=float(lines[i][41:45])
      temp=temp+','+str(DirNormIllum)			
      DifHorzIllum=float(lines[i][47:51])
      temp=temp+','+str(DifHorzIllum)		
      ZenLum=float(lines[i][53:57])
      temp=temp+','+str(ZenLum)		
      WindDir=float(lines[i][90:93])
      temp=temp+','+str(WindDir)			
      WindSpd=float(lines[i][95:98])/10
      temp=temp+','+str(WindSpd)	
      TotSkyCvr=float(lines[i][59:61])
      temp=temp+','+str(TotSkyCvr)	
      OpaqSkyCvr=float(lines[i][63:65])
      temp=temp+','+str(OpaqSkyCvr)	
      Visibility=float(lines[i][100:104])/10
      temp=temp+','+str(Visibility)		
      Ceiling_Hgt=float(lines[i][106:111])
      temp=temp+','+str(Ceiling_Hgt)		
      PresWeath=lines[i][113:123]
      temp=temp+','+str(PresWeath)			
      if PresWeath.find('999999999')!=-1:
          PresWeathObs='9'
      else:
          PresWeathObs='0'
  #    if i==1:
  #          print (PresWeathObs)
      temp=temp+','+str(PresWeath)
      Precip_Wtr=float(lines[i][123:126])
      temp=temp+','+str(Precip_Wtr)	
      AerOptDep=float(lines[i][128:131])
      temp=temp+','+str(AerOptDep)		
      SnoDep=float(lines[i][133:136])
      temp=temp+','+str(SnoDep)		
      DayLasSno=float(lines[i][138:140])
      temp=temp+','+str(DayLasSno)	
      Albedo='0'
      temp=temp+','+str(Albedo)	
      Rain='0'
      temp=temp+','+str(Rain)		
      RaiQua='0'
      temp=temp+','+str(RaiQua)	
      newline.append(temp)

  f=open(fileroot + '.epw','w')
  	
  for i in range(len(newline)):
      f.writelines(newline[i]+'\n')
  f.close()	