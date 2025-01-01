import sqlite3
from time import gmtime, strftime
from urllib.request import pathname2url
import csv
import datetime as dt
import zmq
import json
import threading
from queue import Queue

def create_table_string(dictInstructions, strTech):
    strTable = dictInstructions[strTech]['Defaults']['Database_Table_Name']
    lstFields = ['ID', 'Time_Stamp']
    lstAtt = ['INTEGER PRIMARY KEY AUTOINCREMENT', 'DEFAULT CURRENT_TIMESTAMP']
    for key in dictInstructions[strTech]['GUI_Information']:
        lstFields.append(dictInstructions[strTech]['GUI_Information'][key]['SQL_Title'])
        lstAtt.append('TEXT')

    listLength = len(lstFields) #Determine the number of fields to be created
    for i in range(0,listLength): #For the variable i from 0 to the number of fields
        if i == 0:
            strCreateTable = 'CREATE TABLE ' + strTable + '(' + lstFields[i] + ' ' + lstAtt[i] #SQL create table with the first field item and its attribute
        if i > 0 and i <listLength - 1:
            strCreateTable = strCreateTable + ', ' + lstFields[i] + ' ' + lstAtt[i] #Adding the next field with attribute
        if i == listLength - 1:
            strCreateTable = strCreateTable + ', ' + lstFields[i] + ' ' + lstAtt[i] + ');' #Final field and attribute with closing punctuation

    lstReturn = [strCreateTable, lstFields]
    return lstReturn

class manage_database:
    def __init__(self, dictInstructions, parent_port):
        self.parent_port = parent_port
        self.status_operate = True
        self.task_queue = Queue()
        self.stop_event = threading.Event()
        self.db_run(dictInstructions)

    def create(self, dictInstructions):
        #Test if DB exists
        strDBLoc = dictInstructions['User_Inputs']['DB_Location']
        strDBRootName = dictInstructions['General_Inputs']['DB_Name']
        strYear = str(strftime("%Y", gmtime()))
        self.strDBName = strDBRootName + strYear
        if strDBLoc[-1:] != "/":
            self.strPath = strDBLoc + "/" + self.strDBName
        else:
            self.strPath = strDBLoc + self.strDBName

        print(f"Database path: {self.strPath}")
        db_exists = False
        try:
            db_exists_uri = f'file:{pathname2url(self.strPath)}?mode=rw'
            sqlite3.connect(db_exists_uri, uri=True)
            #dbExists = 'file:{}?mode=rw'.format(pathname2url(self.strPath)) #Open the DB in read mode
            #test = sqlite3.connect(dbExists, uri=True) #Make the connection
            print("Database found")
            db_exists = True
        except sqlite3.OperationalError: #if the conneciton fails then it means it doesn't exist
            print("New database")
            db_exists = False

        self.DBConn = sqlite3.connect(self.strPath) #SQLite3 will create a new database if a connection cannot be made
        self.c = self.DBConn.cursor()

        #Solar Info
        lstSolar = create_table_string(dictInstructions, 'Solar_Inputs')
        strSolarTable = lstSolar[0]
        self.lstSolarFields = lstSolar[1]

        #HP Info
        lstHP = create_table_string(dictInstructions, 'HP_Inputs')
        strHPTable = lstHP[0]
        self.lstHPFields = lstHP[1]

        #PV Info
        lstPV = create_table_string(dictInstructions, 'PV_Inputs')
        strPVTable = lstPV[0]
        self.lstPVFields = lstPV[1]

        #Battery Info
        lstBat = create_table_string(dictInstructions, 'BAT_Inputs')
        strBatTable = lstBat[0]
        self.lstBatFields = lstBat[1]

        #Zone Info
        lstZone = create_table_string(dictInstructions, 'ZONE_Inputs')
        strZoneTable = lstZone[0]
        self.lstZoneFields = lstZone[1]

        if db_exists == False:
            if dictInstructions['User_Inputs']['Solar_Thermal'] == True:
                self.c.execute(strSolarTable)

            if dictInstructions['User_Inputs']['Heat_Pump'] == True:
                self.c.execute(strHPTable)

            if dictInstructions['User_Inputs']['PV'] == True:
                self.c.execute(strPVTable)

            if dictInstructions['User_Inputs']['Battery'] == True:
                self.c.execute(strBatTable)

            if dictInstructions['User_Inputs']['Zone'] == True:
                self.c.execute(strZoneTable)

    def upload_data(self, args):
        strTable = args[0]
        arrFields = args[1]
        arrVals = args[2]

        if len(arrFields) > 0:
            listLength = len(arrFields) #determine the number of values being provided (allowing for multiple readings to be entered)
            for i in range(0,listLength): #for each item in the fields provided
                self.check_field_exists(strTable, str(arrFields[i]))
                if i == 0: #for the first item
                    if listLength > 1:
                        strInsert = "INSERT INTO " + strTable + " (" + str(arrFields[i]) + "," #provide the field name but with the necessary SQL insert string
                    else:
                        strInsert = "INSERT INTO " + strTable + " (" + str(arrFields[i])

                if i > 0 and i < listLength - 1: #for intermediate fields
                    if listLength > 1:
                        strInsert = strInsert + arrFields[i] + "," #enter the field name followed by a comma
                    else:
                        strInsert = strInsert + arrFields[i]

                if i == listLength - 1: #for the final field name
                    if listLength > 1:
                        strInsert = strInsert + arrFields[i] + ") " #finish with a bracket
                    else:
                        strInsert = strInsert + ") " #If there is only one list item then no need to include arrFields[i] as this will have already been included

            for i in range(0,listLength): #for each item in the fields provided
                if i == 0: #for the first item
                    if listLength > 1:
                        strInsert = strInsert + "VALUES (?," #enter the SQL VALUES string with a question mark for the first value item to be provided
                    else:
                        strInsert = strInsert + "VALUES (?"

                if i > 0 and i < listLength - 1: #for intermediate fields enter
                    if listLength > 1:
                        strInsert = strInsert + "?," #a question mark followed by comma
                    else:
                        strInsert = strInsert + "?"

                if i == listLength - 1: #for the final field
                    if listLength > 1:
                        strInsert = strInsert + "?)" #enter a question mark follwed by a close bracket
                    else:
                        strInsert = strInsert + ")" #If there is only one list item then the '?' will have aready been included

            #print(strInsert + str(arrVals)) #optional if you want to see the string that is produced
            self.DBConn.execute(strInsert, arrVals) #connect to the database and execute the INSERT with the list arrVals
            self.DBConn.commit() #commit the insertion
            #self.DBConn.close() #close the connection to the database

    def check_table_exists(self, dictInstructions, strTable):
        strSQL = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='" + strTable + "'"
        self.c.execute(strSQL)
        TBL_Count = self.c.fetchone()[0]
        if TBL_Count == 0:
            lstDefaults = []
            lstDefaults.append(dictInstructions['Solar_Inputs']['Defaults']['Database_Table_Name'])
            lstDefaults.append(dictInstructions['HP_Inputs']['Defaults']['Database_Table_Name'])
            lstDefaults.append(dictInstructions['PV_Inputs']['Defaults']['Database_Table_Name'])
            lstDefaults.append(dictInstructions['BAT_Inputs']['Defaults']['Database_Table_Name'])
            lstDefaults.append(dictInstructions['ZONE_Inputs']['Defaults']['Database_Table_Name'])

            lstTitles = ['Solar_Inputs', 'HP_Inputs', 'PV_Inputs', 'BAT_Inputs', 'ZONE_Inputs']

            for i in range(0, len(lstDefaults)):
                if lstDefaults[i] == strTable:
                    strInfo = lstTitles[i]
                    break

            # Info
            lstInfo = create_table_string(dictInstructions, strInfo)
            strTableSQL = lstInfo[0]
            self.lstFields = lstInfo[1]
            self.c.execute(strTableSQL)

    def check_field_exists(self, strTable, strField):
        strSQL = "SELECT COUNT(*) AS CNTREC FROM pragma_table_info('" + strTable + "') WHERE name='" + strField + "'"
        self.c.execute(strSQL)
        if self.c.fetchone()[0] == 0:
            strFieldSQL = "ALTER TABLE " + strTable + " ADD COLUMN " + strField + " TEXT;"
            self.c.execute(strFieldSQL)

    def close_connection(self):
        self.DBConn.close()

    def export_CSV(self, strTable, lstFields):
        data = self.c.execute("SELECT * FROM " + strTable) #Extract all of the data from the database for the current year

        with open(self.strPath + strTable +'.csv', 'w') as f:
            writer = csv.writer(f)
            writer.writerow(lstFields)
            writer.writerows(data)

    def sum_data_in_current_day(self, strTable, strField, dictInstructions):
        dtCurr = dt.datetime.now()
        strCurrMonth = str(dtCurr.month)
        if len(strCurrMonth) == 1:
            strCurrMonth = '0' + strCurrMonth
        strCurrDay = str(dtCurr.day)
        if len(strCurrDay) == 1:
            strCurrDay = '0' + strCurrDay

        dtTomorrow = dtCurr + dt.timedelta(days=1)
        strTomMonth = str(dtTomorrow.month)
        if len(strTomMonth) == 1:
            strTomMonth = '0' + strTomMonth
        strTomDay = str(dtTomorrow.day)
        if len(strTomDay) == 1:
            strTomDay = '0' + strTomDay

        strDateToday = str(dtCurr.year) + "-" + strCurrMonth + "-" + strCurrDay
        strDateTomorrow = str(dtTomorrow.year) + "-" + strTomMonth + "-" + strTomDay
        strSQL = "SELECT SUM(" + strField + ") FROM " + strTable + " WHERE date(Time_Stamp) BETWEEN date('" + strDateToday + "') AND date('" + strDateTomorrow +"')"
        #print(strSQL)
        self.c.execute(strSQL)
        sum_field = self.c.fetchone()[0]
        return sum_field

    def sum_query_between_times(self,strStartDate, strEndDate, strStartTime, strEndTime, strField, strTable):
        strSQL = "SELECT SUM(" + strField + ") FROM " + strTable + " WHERE date(Time_Stamp) BETWEEN date('" + strStartDate + "') AND date('" + strEndDate +"') AND time(Time_Stamp) >= ('" + strStartTime + "') AND time(Time_Stamp) <= ('" + strEndTime +"')"
        #print(strSQL)
        self.c.execute(strSQL)
        sum_field = self.c.fetchone()[0]
        return sum_field

    def avg_query_between_times(self,strStartDate, strEndDate, strStartTime, strEndTime, strField, strTable):
        sum_0 = self.sum_query_between_times(strStartDate, strEndDate, strStartTime, strEndTime, strField, strTable)
        if sum_0 != 0:
            strSQL = "SELECT AVG(" + strField + ") FROM " + strTable + " WHERE date(Time_Stamp) BETWEEN date('" + strStartDate + "') AND date('" + strEndDate +"') AND time(Time_Stamp) >= ('" + strStartTime + "') AND time(Time_Stamp) <= ('" + strEndTime +"')"
            #print(strSQL)
            self.c.execute(strSQL)
            sum_field = self.c.fetchone()[0]
        else:
            sum_field = 0
        return sum_field

    def extract_values(self, args):
        start_time = args[0]
        end_time = args[1]
        table_name = args[2]
        field_name = args[3]

        query = f"SELECT Time_Stamp, {field_name} FROM {table_name} WHERE Time_Stamp >= '{start_time}' AND Time_Stamp <= '{end_time}'"
        print(query)
        self.c.execute(query)
        records = self.c.fetchall()
        #print("records: " + str(records))
        if records != None:
            result_list = [[row[0], row[1]] for row in records]
        else:
            result_list = []
        #print("result list: " + str(result_list))
        return result_list

    def call_method(self, method_name, *args, **kwargs):
        method = getattr(self, method_name)
        return method(*args, **kwargs)

    def db_run(self, dictInstructions):
        self.create(dictInstructions)
        self.DB_initialised = True

        context = zmq.Context.instance()
        socket = context.socket(zmq.REP)
        print("DB using port for parent communication: " + str(self.parent_port) + " to bind with parent.")
        socket.bind(f"tcp://*:{self.parent_port}")
        print("DB Connected to " + str(self.parent_port) + " to bind with parent.")

        while self.status_operate == True:
            print("DB: waiting for parent requests")
            message = socket.recv()
            print("Received message: " + str(message))
            lstRequest = json.loads(message.decode("utf-8"))
            strFunction = lstRequest[0]
            print("DB receieved function to run from parent: " + str(strFunction))
            lstArgs = lstRequest[1]
            print("DB arguments reveived for function to run from parent: " + str(lstArgs))
            lstReturn = self.call_method(strFunction, lstArgs) #globals()[strFunction](lstArgs)
            serialised_data = json.dumps(lstReturn).encode("utf-8")
            print("DB: sending response...")
            socket.send(serialised_data)
            print("DB: response sent.")

#DB_Test = manage_database(A_Initialise.dictGlobalInstructions, 5556)
