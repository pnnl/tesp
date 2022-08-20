import datetime
import json;
import shutil
import os
import prepare_case_dsot_v3 as prep_case

def generate_case(casename, port):

    with open(casename + '.json', 'r', encoding='utf-8') as json_file:
        ppc = json.load(json_file)
    splitCase = ppc['splitCase']
    caseName = ppc['caseName']
    caseStartYear = ppc['caseStartYear']
    caseEndYear = ppc['caseEndYear']

    if splitCase:
        # We need to create the experiment folder. If it already exists we delete it and then create it
        if caseName != "" and caseName != ".." and caseName != ".":
            if os.path.isdir(caseName):
                print("experiment folder already exists, deleting and moving on...")
                shutil.rmtree(caseName)
            os.makedirs(caseName)
        else:
            print('Case name is blank or Case name is "." or ".." and could cause file deletion')
            exit(1)

        while True:
            for i in range(12):
                directoryName = str(caseStartYear) + "_" + '{0:0>2}'.format(i+1)
                ppc['caseName'] = directoryName
                ppc['port'] = int(port + i)

                year = caseStartYear
                month = '{0:0>2}'.format(i)
                daytime = "-29 00:00:00"
                if i == 0:
                    month = '12'
                    year = caseStartYear - 1
                ppc['StartTime'] = str(year) + "-" + month + daytime

                year = caseStartYear
                month = '{0:0>2}'.format(i+2)
                daytime = "-02 00:00:00"
                if i == 11:
                    month = '01'
                    year = caseStartYear + 1
                ppc['EndTime'] = str(year) + "-" + month + daytime

                ep = datetime.datetime(1970, 1, 1)
                s = datetime.datetime.strptime(ppc['StartTime'], '%Y-%m-%d %H:%M:%S')
                e = datetime.datetime.strptime(ppc['EndTime'], '%Y-%m-%d %H:%M:%S')
                sIdx = (s - ep).total_seconds()
                eIdx = (e - ep).total_seconds()
                ppc['Tmax'] = int(eIdx - sIdx)

#                with open(os.path.join(directoryName, casename + ".json"), 'w') as outfile:
                with open(directoryName + ".json", 'w') as outfile:
                        json.dump(ppc, outfile)

                prep_case.prepare_case(directoryName)

            if caseStartYear == caseEndYear:
                break
            caseStartYear += 1

generate_case("system_case_config", 5570)

