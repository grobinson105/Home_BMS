import zmq
import socket
import A_Initialise
import B_GUI
import D_Database
import E_Sensors
import threading
import time
from datetime import datetime

# Function to check if a port is available
class Home_BMS:
    def __init__(self):
        self.last_read = datetime.now()
        self.quit_sys = False
        self.created_self = False
        self.dictInstructions = A_Initialise.dictGlobalInstructions
        self.dp_2 = 2
        self.dp_0 = 0

        self.solar_table =  self.dictInstructions['Solar_Inputs']['Defaults']['Database_Table_Name']

        self.solar_flow_pulse_value =  self.dictInstructions['Solar_Inputs']['GUI_Information']['Flow_Rate']['Pulse_Value']
        self.solar_flow_SQL =  self.dictInstructions['Solar_Inputs']['GUI_Information']['Flow_Rate']['SQL_Title']
        self.collector_temp_SQL =  self.dictInstructions['Solar_Inputs']['GUI_Information']['Collector_temp']['SQL_Title']
        self.tank_temp_SQL =  self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_bot_temp']['SQL_Title']
        self.collector_glycol =  self.dictInstructions['User_Inputs']['Glycol_Mix']

        self.allocate_ports()

        if self.ports_boolSuccess == True:
            #Database
            threading.Thread(target=self.database_create, daemon=True).start()

            #GUI
            self.BMS_GUI = B_GUI.build_GUI(A_Initialise.dictGlobalInstructions, self.db_GUI_port)
            self.BMS_GUI.created_self = True

            # SENSORS
            threading.Thread(target=self.sensors_thread(), daemon=True).start()

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
        ports_count = 4
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
            self.db_GUI_port = self.ports_used[0][1]
            self.db_parent_port = self.ports_used[1][1]
            self.GUI_port = self.ports_used[2][1]
            self.sensor_port = self.ports_used[3][1]

    def database_create(self):
        self.BMS_DB = D_Database.manage_database(A_Initialise.dictGlobalInstructions, self.db_GUI_port)

    def call_sensor_data(self):
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:" + str(self.sensor_port))
        # GET SOLAR DATA
        lstPackage = ['SOLAR']
        data = json.dumps(lstPackage).encode("utf-8")
        # print("sending:" + str(data))
        print("Parent: sending sensor request via port " + str(self.sensor_port))
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

    def calculate_heat_wh(self, glycol_mix, litres, flow_temp, return_temp, seconds_duration):

        fluid_capacity = ethelyne_glycol_heat_capacity(glycol_mix)
        heat_load_wh = fluid_capacity * litres * (flow_temp - return_temp) * seconds_duration * (10**3) / (60**2)
        return heat_load_wh

    def sensors_thread(self):
        self.BMS_Sensors = E_Sensors.BMS_Sensors(self.sensor_port)

        while self.quit_sys == False:
            lstData = self.call_sensor_data()

            #########################
            # NEW DB RECORDS thread #
            #########################

            Seconds_Elapsed = int(lstData[0]) #Used for pulse meter calculations

            #Solar records
            lstSolar = lstData[1] # solar data is the item[1] in the list (item[0] is the seconds elapsed)

            #Calculate solar thermal collected in period
            #lstSolarWaterFlowCount = next((sublist for sublist in lstSolar if sublist[0] == self.solar_flow_SQL), None)
            fltSolarWaterFlow = float(lstSolarWaterFlowCount[1]) * self.solar_flow_pulse_value
            #for item in lstSolar:
            #    if item[0] == self.solar_flow_SQL:
            #        item[1] = fltSolarWaterFlow #Update the solar data with the litres rather than pulse count
            #        break

            #lstCollectorTemp = next((sublist for sublist in lstSolar if sublist[0] == self.collector_temp_SQL), None)
            #fltCollector = float(lstCollectorTemp[1])

            lstSolarFields = [item[0] for item in lstSolar]
            print("Solar fields: " + str(lstSolarFields))
            lstSolarVals = [float(item[1]) for item in lstSolar]
            print("Solar Vals: " + str(lstSolarVals))

            self.BMS_DB.upload_data(self.solar_table, lstSolarFields, lstSolarVals)
            print("BMS DB uploaded: solar values")

            #####################
            # UPDATE GUI thread #
            #####################

            #Solar tab
            lblPressure = self.dictInstructions['Solar_Inputs']['GUI_Information']['Heat_capacity']['GUI_Val']
            solar_pressure = f"{value:.{self.dp_0}f}"
            print("Solar pressure: " + str(solar_pressure))
            lblPressure.config(text=solar_pressure)

            now = datetime.now()
            seconds_until_next_minute = 60 - now.second - now.microsecond / 1_000_000
            time.sleep(seconds_until_next_minute )

# launch database
#to complete

Home_BMS = Home_BMS()
Home_BMS.BMS_GUI.RootWin.mainloop()

'''
# launch Sensor 2
### MAIN RUN ###
BMS_GUI = build_GUI(dictGlobalInstructions)
dictGlobalInstructions['General_Inputs']['GUI_BMS'] = BMS_GUI
BMS_GUI.created_self = True
BMS_GUI.initiate_all_threads()
BMS_GUI.RootWin.mainloop()
'''
