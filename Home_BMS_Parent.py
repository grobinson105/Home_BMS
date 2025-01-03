import zmq
import socket
import A_Initialise
import B_GUI
import D_Database
import E_Sensors
import threading
import time
from datetime import datetime, timedelta
import json

# Function to check if a port is available
class Home_BMS:
    def __init__(self): 
        self.last_read = datetime.now()
        self.quit_sys = False
        self.created_self = False
        self.sensor_server_initialised = threading.Event()
        self.GUI_initialised = threading.Event()
        self.DB_initialised = threading.Event()
        self.sensor_server_live = False
        self.dictInstructions = A_Initialise.dictGlobalInstructions
        self.dp_2 = 2
        self.dp_0 = 0
        
        self.solar_table =  self.dictInstructions['Solar_Inputs']['Defaults']['Database_Table_Name']
        self.solar_flow_pulse_value =  self.dictInstructions['Solar_Inputs']['GUI_Information']['Flow_Rate']['Pulse_Value']
        self.solar_flow_SQL =  self.dictInstructions['Solar_Inputs']['GUI_Information']['Flow_Rate']['SQL_Title']
        self.solar_electricity_pulse_value = self.dictInstructions['Solar_Inputs']['GUI_Information']['Solar_pump_electricity']['Pulse_Value']
        self.solar_electricity_SQL = self.dictInstructions['Solar_Inputs']['GUI_Information']['Solar_pump_electricity']['SQL_Title']
        self.collector_temp_SQL =  self.dictInstructions['Solar_Inputs']['GUI_Information']['Collector_temp']['SQL_Title']
        self.tank_temp_SQL =  self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_bot_temp']['SQL_Title']
        self.collector_glycol =  self.dictInstructions['User_Inputs']['Glycol_Mix']
        self.collector_heat_load_SQL =  self.dictInstructions['Solar_Inputs']['GUI_Information']['Heat_load']['SQL_Title']

        self.allocate_ports()

        if self.ports_boolSuccess == True:
            #Database
            print("Database thread launched")
            threading.Thread(target=self.database_create).start()

            # SENSORS
            print("Sensors thread launched")
            threading.Thread(target=self.sensors_server_thread).start()
            threading.Thread(target=self.sensors_client_thread).start()
                        
            #GUI
            threading.Thread(target=self.GUI_db_query_thread).start()
            print("Starting GUI build")
            self.BMS_GUI = B_GUI.build_GUI(A_Initialise.dictGlobalInstructions, self.GUI_parent_port)
            while not self.BMS_GUI.GUI_Created:
                time.sleep(0.1)
            print("GUI is initialised")
            self.GUI_initialised.set()
            self.BMS_GUI.created_self = True    
            print("GUI created: " + str(self.BMS_GUI.created_self))        
            self.BMS_GUI.RootWin.mainloop()
        
        else:
            print("Unable to initialise BMS due to lack of available ports")

    def is_port_available(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0  # Returns True if port is free

    def allocate_ports(self):
        # ZeroMQ context
        context = zmq.Context()

        # List to store successfully bound ports and associated sensors
        self.ports_used = []

        # Define sensor names and desired ports
        ports_count = 3
        sensors = [f"sensor_{i + 1}" for i in range(ports_count)]  # e.g., sensor_1, sensor_2, ...
        starting_port = 5555
        ports_found = 0
        port = starting_port

        for i in range(starting_port,65535):
            while ports_found < ports_count:
                if self.is_port_available(port):
                    try:
                        zmq_socket = context.socket(zmq.REQ)
                        zmq_socket.connect(f"tcp://localhost:{port}")
                        zmq_socket.disconnect(f"tcp://localhost:{port}")
                        ports_found = ports_found + 1
                        self.ports_used.append([ports_found, port])  # Append sensor and port
                        print(f"Successfully bound {ports_found} to port {port}")
                    except zmq.ZMQError as e:
                        print(f"Failed to bind {ports_found} to port {port}: {e}")
                port = port + 1  # Try the next port if unavailable

        zmq_socket.close()

        if len(self.ports_used) < ports_found:
            self.ports_boolSuccess = False
        else:
            self.ports_boolSuccess = True
            self.GUI_parent_port = self.ports_used[0][1]
            self.db_parent_port = self.ports_used[1][1]
            self.sensor_parent_port = self.ports_used[2][1]
            

    def database_create(self):
        
        print("Initiating DB thread")
        self.BMS_DB = D_Database.manage_database(A_Initialise.dictGlobalInstructions, self.db_parent_port)
        while not self.BMS_DB.DB_initialised:
            time.sleep(0.1)
        print("DB is initialised")
        self.DB_initialised.set()
        
    def call_sensor_data(self):
        context = zmq.Context.instance()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:" + str(self.sensor_parent_port))
        # GET SOLAR DATA
        lstPackage = self.quit_sys
        data = json.dumps(lstPackage).encode("utf-8")
        # print("sending:" + str(data))
        print("Parent: sending sensor request via port " + str(self.sensor_parent_port))
        socket.send(data)
        print("Parent: sensor request sent. Waiting for response")
        response = socket.recv()
        print("GUI: Parent response from sensor received")
        lstData = json.loads(response.decode("utf-8"))
        # print("GUI DATA = " + str(lstData))
        return lstData

        #self.Sensor1 = F_Pressure_Sensor.pressure_sensor(self.sensor_port, 0, 1, 0)
        #self.field_name_sensor1 = A_Initialise.dictGlobalInstructions['Solar_Inputs']['GUI_Information']['SYS_Pressure']['SQL_Title']

    def ethelyne_glycol_heat_capacity(self, percent_glycol):
        # https://www.engineeringtoolbox.com/ethylene-glycol-d_146.html
        # Heat capacity (KJ/KG K) at 20DegC ambient on the basis that the solar thermal system will primarily be operating in summer
        # [% Glycol mix, heat capacity of mix of glycol and water]
        lstGlycolHeatCapacity = [[0, 4.189],
                                 [10, 4.087],
                                 [20, 3.951],
                                 [30, 3.807],
                                 [40, 3.647],  # A 40% mix should allow for -20DegC which should be sufficient for UK
                                 [50, 3.473],
                                 [60, 3.284],
                                 [70, 3.08],
                                 [80, 2.862],
                                 [90, 2.628],
                                 [100, 2.38]]

        for i in range(0, len(lstGlycolHeatCapacity)):
            if percent_glycol >= lstGlycolHeatCapacity[i][0]:
                if percent_glycol < lstGlycolHeatCapacity[i + 1][0]:
                    fltLower = float(lstGlycolHeatCapacity[i][0])
                    fltLowerCapacity = float(lstGlycolHeatCapacity[i][1])
                    fltUpper = float(lstGlycolHeatCapacity[i + 1][0])
                    fltUpperCapacity = float(lstGlycolHeatCapacity[i + 1][1])
                    fltInterpolatedCapacity = fltLowerCapacity + (
                                ((percent_glycol - fltLower) / (fltUpper - fltLower)) * (
                                    fltUpperCapacity - fltLowerCapacity))
        return fltInterpolatedCapacity

    def calculate_heat_wh(self, glycol, litres, flow_temp, return_temp):
        fluid_capacity = self.ethelyne_glycol_heat_capacity(glycol)
        heat_load_wh = fluid_capacity * litres * (flow_temp - return_temp) * (10**3) / (60**2)
        return heat_load_wh

    def call_method(self, method_name, *args, **kwargs):
        method = getattr(self, method_name)
        return method(*args, **kwargs)
    
    def convert_SQL_date_with_time(selfself, dtDate):
        #need to subtract a day and run request_db_data on the previous day
        strMonth = str(dtDate.month)
        if len(strMonth) == 1:
            strMonth = '0' + strMonth
        strDay = str(dtDate.day)
        if len(strDay) == 1:
            strDay = '0' + strDay
        
        strHr = str(dtDate.hour)
        if len(strHr) == 1:
            strHr = '0' + strHr
            
        strMin = str(dtDate.minute)
        if len(strMin) == 1:
            strMin = '0' + strMin
            
        strSec = str(dtDate.second)
        if len(strSec) == 1:
            strSec = '0' + strSec
        
        strDate = str(dtDate.year) + "-" + strMonth + "-" + strDay + ' ' + strHr + ':' + strMin + ':' + strSec
        return strDate
    
    def extract_values(self, args):
        context = zmq.Context.instance()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:" + str(self.db_parent_port))
        #print(lstPackage)
        data = json.dumps(args).encode("utf-8")
        #print("sending:" + str(data))
        print("Parent: requesting GUI data from DB " + str(self.db_parent_port))
        socket.send(data)
        print("Parent: GUI DB request sent. Waiting for response")
        response = socket.recv()
        print("Parent: DB response received for GUI")
        lstData = json.loads(response.decode("utf-8"))
        #print("GUI DATA = " + str(lstData))
        return lstData

    def DB_upload_data(self, args):
        context = zmq.Context.instance()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:" + str(self.db_parent_port))
        lstPackage = ["upload_data", args]
        data = json.dumps(lstPackage).encode("utf-8")
        #print("sending:" + str(data))
        print("Parent: sending data to DB for upload " + str(self.db_parent_port))
        socket.send(data)
        print("Parent: DB data upload request sent. Waiting for response")
        response = socket.recv()
        print("Parent: DB data upload response received")
        lstData = json.loads(response.decode("utf-8"))
        #print("GUI DATA = " + str(lstData))
        return lstData

    def GUI_db_query_thread(self):
        context = zmq.Context.instance()
        socket = context.socket(zmq.REP)
        print("Parent using port for GUI communication: " + str(self.GUI_parent_port))
        socket.bind(f"tcp://*:{self.GUI_parent_port}")
        print("Parent connected to " + str(self.GUI_parent_port) + " to bind with GUI.")

        while self.quit_sys == False:
            print("Parent: waiting for GUI graph requests")
            message = socket.recv()
            print("Parent received message from GUI: " + str(message))
            lstRequest = json.loads(message.decode("utf-8"))
            strFunction = lstRequest[0]
            print("GUI function requested: " + str(strFunction))
            lstArgs = lstRequest[1]
            print("GUI graph request arguments provided: " + str(lstArgs))
            lstReturn = self.call_method(strFunction, lstRequest) #globals()[strFunction](lstArgs)
            serialised_data = json.dumps(lstReturn).encode("utf-8")
            print("Parent: sending response...")
            socket.send(serialised_data)
            print("DB: response sent.")

    def sensors_server_thread(self):
        print("Initiating sensor server thread")
        self.BMS_Sensors = E_Sensors.BMS_Sensors(self.sensor_parent_port)
        while not self.BMS_Sensors.sensor_server_live:
            time.sleep(0.1)
        print("Sensor server is initialised")
        self.sensor_server_initialised.set()
    
    def last_hour_query(self, args):
        dtNow = datetime.now()
        strNow = self.convert_SQL_date_with_time(dtNow)
        dtHRearlier = dtNow - timedelta(hours=1)
        strHRearlier = self.convert_SQL_date_with_time(dtHRearlier)
        
        table_name = args[0]
        field_name = args[1]
        lstQuery = [strHRearlier, strNow, table_name, field_name]
        lstArgs = ["extract_values", lstQuery]
        lstData = self.extract_values(lstArgs)
        return lstData

    def all_day_query(self, args):
        dtNow = datetime.now()
        strNow = self.convert_SQL_date_with_time(dtNow)
        dtYesterdayMidnight = datetime(dtNow.year, dtNow.month, dtNow.day)
        strYesterdayMidnight = self.convert_SQL_date_with_time(dtYesterdayMidnight)

        table_name = args[0]
        field_name = args[1]
        lstQuery = [strYesterdayMidnight, strNow, table_name, field_name]
        lstArgs = ["extract_values", lstQuery]
        lstData = self.extract_values(lstArgs)
        return lstData

    def sensors_client_thread(self):
        
        print("Waiting for sensor server to initialise...")
        print("Waiting for GUI to be created...")
        print("Waiting for DB to be created...")
        self.sensor_server_initialised.wait()
        self.GUI_initialised.wait()
        self.DB_initialised.wait()
        print("Sensor server, DB server and GUI initialised. Starting sensor client thread.")
        
        while self.quit_sys == False:
            
            self.quit_sys = self.BMS_GUI.quit_sys
            lstAll = self.call_sensor_data()
            print("Sensor data received: " + str(lstAll))
            Seconds_Elapsed = int(lstAll[0]) #Used for pulse meter calculations
            print("Seconds elapsed for sensor read: " + str(Seconds_Elapsed))
            
            #########################
            # NEW DB RECORDS #
            #########################

            #Solar records
            lstData = lstAll[1]
            lstSolar = lstData[0] # solar data is the first item in lstData
            print("Solar data received: " + str(lstSolar))
            
            #Calculate collector flow in period
            lstSolarWaterFlowCount = next((sublist for sublist in lstSolar if sublist[0] == self.solar_flow_SQL), None)
            #print("Solar water flow pulses: ")
            #print(lstSolarWaterFlowCount)
            fltSolarWaterFlow = float(lstSolarWaterFlowCount[1]) * self.solar_flow_pulse_value
            #print("Solar water flow in period Litres: " + str(fltSolarWaterFlow))
            
            for item in lstSolar:
                if item[0] == self.solar_flow_SQL:
                    item[1] = fltSolarWaterFlow #Update the solar data with the litres rather than pulse count
                    break
            
            #Calculate collector electricity in period
            lstSolarElectricityCount = next((sublist for sublist in lstSolar if sublist[0] == self.solar_electricity_SQL), None)
            #print("Solar electricity pulses: ")
            #print(lstSolarElectricityCount)
            fltElectricity = float(lstSolarElectricityCount[1]) * self.solar_electricity_pulse_value
            print("Solar electricity in period Wh: " + str(fltElectricity))

            for item in lstSolar:
                if item[0] == self.solar_electricity_SQL:
                    item[1] = fltElectricity  # Update the solar data with the litres rather than pulse count
                    break
            
            lstSolarFields = [item[0] for item in lstSolar]
            #print("Solar fields: " + str(lstSolarFields))
            lstSolarVals = [item[1] for item in lstSolar]
            #print("Solar Vals: " + str(lstSolarVals))

            #heat transferred in period
            solar_heat_transferred = self.calculate_heat_wh(self.collector_glycol, fltSolarWaterFlow, lstSolarVals[1], lstSolarVals[4])
            print("Heat transferred in period (wh): " + str(solar_heat_transferred))
            lstSolarFields.append(self.collector_heat_load_SQL)
            print("Solar fields: " + str(lstSolarFields))
            lstSolarVals.append(solar_heat_transferred)

            lstSolarArgs = [[self.solar_table], lstSolarFields, lstSolarVals]
            self.DB_upload_data(lstSolarArgs)
            #print("BMS DB uploaded: solar values")

            #####################
            # UPDATE GUI #
            #####################

            #Solar tab
            lblPressure = self.dictInstructions['Solar_Inputs']['GUI_Information']['SYS_Pressure']['GUI_Val']
            solar_pressure = lstSolarVals[0]
            solar_pressure_str = f"{solar_pressure:.{self.dp_2}f}"
            #print("Solar pressure: " + str(solar_pressure))
            lblPressure.config(text=solar_pressure_str)
            
            lblCollector = self.dictInstructions['Solar_Inputs']['GUI_Information']['Collector_temp']['GUI_Val']
            collector_temp = lstSolarVals[1]
            collector_temp_str = f"{collector_temp:.{self.dp_2}f}"
            #print("Collector temp: " + str(solar_pressure))
            lblCollector.config(text=collector_temp_str)
            
            lblTankTop = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_top_temp']['GUI_Val']
            tank_top_temp = lstSolarVals[2]
            tank_top_temp_str = f"{tank_top_temp:.{self.dp_2}f}"
            #print("Tank top temp: " + str(tank_top_temp))
            lblTankTop.config(text=tank_top_temp_str)
            
            lblTankMid = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_temp']['GUI_Val']
            tank_mid_temp = lstSolarVals[3]
            tank_mid_temp_str = f"{tank_mid_temp:.{self.dp_2}f}"
            #print("Tank mid temp: " + str(tank_mid_temp))
            lblTankMid.config(text=tank_mid_temp_str)
            
            lblTankBot = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_bot_temp']['GUI_Val']
            tank_bot_temp = lstSolarVals[4]
            tank_bot_temp_str = f"{tank_bot_temp:.{self.dp_2}f}"
            #print("Tank bottom temp: " + str(tank_bot_temp))
            lblTankBot.config(text=tank_bot_temp_str)

            #solar hourly flow rate for GUI
            lstSolarFlowQry = [self.solar_table, self.solar_flow_SQL]
            lstFlow_Rate_lstHr = self.last_hour_query(lstSolarFlowQry)
            print("lstFlow_Rate_lstHr: " + str(lstFlow_Rate_lstHr))
            Flow_Rate_lstHr = sum(float(item[1]) for item in lstFlow_Rate_lstHr)
            lblFlowRate = self.dictInstructions['Solar_Inputs']['GUI_Information']['Flow_Rate']['GUI_Val']
            solar_flow_str = f"{Flow_Rate_lstHr :.{self.dp_0}f}"
            #print("Solar flow rate: " + str(solar_flow))
            lblFlowRate.config(text=solar_flow_str)

            #solar thermal capacity over previous hour
            lstSolarThermCap = [self.solar_table, self.collector_heat_load_SQL]
            lstThermal_Capacity_W = self.last_hour_query(lstSolarThermCap)
            Thermal_Capacity_W = sum(float(item[1]) for item in lstThermal_Capacity_W if item[1] is not None)
            self.BMS_GUI.Solar_Gauge.add_gauge_line(Thermal_Capacity_W)
            lblThermCapacity = self.dictInstructions['Solar_Inputs']['GUI_Information']['Heat_capacity']['GUI_Val']
            Thermal_Capacity_W_str = f"{Thermal_Capacity_W :.{self.dp_0}f}"
            #print("Solar capacity: " + str(Thermal_Capacity_W))
            lblThermCapacity.config(text=Thermal_Capacity_W_str)

            #Heat transferred in day
            lstSolarHeatArgs = [self.solar_table, self.collector_heat_load_SQL]
            lstSolarDayHeat = self.all_day_query(lstSolarHeatArgs)
            Solar_Heat_Wh = sum(float(item[1]) for item in lstSolarDayHeat if item[1] is not None)
            lblSolarHeat = self.dictInstructions['Solar_Inputs']['GUI_Information']['Heat_load']['GUI_Val']
            Solar_Heat_Wh_str = f"{Solar_Heat_Wh :.{self.dp_0}f}"
            #print("Solar heat: " + str(Solar_Heat_Wh))
            lblSolarHeat.config(text=Solar_Heat_Wh_str)

            #Solar electricity
            lstSolarElecArgs = [self.solar_table, self.solar_electricity_SQL]
            lstSolarDayElec = self.all_day_query(lstSolarElecArgs)
            Solar_Elec_Wh = sum(float(item[1]) for item in lstSolarDayElec if item[1] is not None)
            lblSolarElec = self.dictInstructions['Solar_Inputs']['GUI_Information']['Solar_pump_electricity']['GUI_Val']
            Solar_Elec_Wh_str = f"{Solar_Elec_Wh :.{self.dp_0}f}"
            #print("Solar heat: " + str(Solar_Heat_Wh))
            lblSolarElec.config(text=Solar_Elec_Wh_str)

            #Update solar graph
            self.BMS_GUI.current_solar()
            
            now = datetime.now()
            seconds_until_next_minute = 60 - now.second - now.microsecond / 1_000_000
            print("Seconds until next sensor check: " + str(seconds_until_next_minute))
            time.sleep(seconds_until_next_minute )
            
Home_BMS = Home_BMS()
