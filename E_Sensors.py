import time
import spidev
import zmq
import A_Initialise
import threading
import RPi.GPIO as GPIO
import json
import math as math

class BMS_Sensors:
    def __init__(self, port):
        self.continue_to_operate = True
        self.sensor_server_live = False
        self.dictInstructions = A_Initialise.dictGlobalInstructions
        self.Vref = 3.3
        self.port = port

        # Initialize attributes used by threads
        self.solar_sensors_collated = False
        self.HP_sensors_collated = False
        self.PV_sensors_collated = False
        self.BAT_sensors_collated = False
        self.Zone_sensors_collated = False

        self.solar_pressure_SQL = self.dictInstructions['Solar_Inputs']['GUI_Information']['SYS_Pressure']['SQL_Title']
        self.solar_collector_SQL = self.dictInstructions['Solar_Inputs']['GUI_Information']['Collector_temp']['SQL_Title']
        self.solar_tank_top_SQL = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_top_temp']['SQL_Title']
        self.solar_tank_mid_SQL = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_temp']['SQL_Title']
        self.solar_tank_bot_SQL = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_bot_temp']['SQL_Title']
        self.solar_flow_SQL = self.dictInstructions['Solar_Inputs']['GUI_Information']['Flow_Rate']['SQL_Title']
        self.solar_electricity_SQL = self.dictInstructions['Solar_Inputs']['GUI_Information']['Solar_pump_electricity']['SQL_Title']

        self.HP_outlet_SQL = self.dictInstructions['HP_Inputs']['GUI_Information']['Outlet_Temperature']['SQL_Title']
        self.HP_inlet_SQL = self.dictInstructions['HP_Inputs']['GUI_Information']['Inlet_Temperature']['SQL_Title']
        self.HP_flow_SQL = self.dictInstructions['HP_Inputs']['GUI_Information']['Flow_Rate']['SQL_Title']
        self.HP_electricity_SQL = self.dictInstructions['HP_Inputs']['GUI_Information']['External_Unit_Elec_Wh']['SQL_Title']
        self.HP_int_electricity_SQL = self.dictInstructions['HP_Inputs']['GUI_Information']['Internal_Unit_Elec_Wh']['SQL_Title']
        self.HP_pressure_SQL = self.dictInstructions['HP_Inputs']['GUI_Information']['HP_Pressure']['SQL_Title']

        self.PV_elec_SQL = self.dictInstructions['PV_Inputs']['GUI_Information']['Generation']['SQL_Title']

        self.BAT_charge_SQL = self.dictInstructions['BAT_Inputs']['GUI_Information']['Charge_Supply']['SQL_Title']
        self.BAT_discharge_SQL = self.dictInstructions['BAT_Inputs']['GUI_Information']['Discharge_Supply']['SQL_Title']

        self.Zone1_SQL = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_1']['SQL_Title']
        self.Zone2_SQL = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_2']['SQL_Title']
        self.Zone3_SQL = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_3']['SQL_Title']
        self.Zone4_SQL = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_4']['SQL_Title']

        self.restart_threads()
        

    def restart_threads(self):
        #Solar Threads
        threading.Thread(target=self.pressure_sensor_read_thread, daemon=True).start() #start solar pressure sensor thread
        threading.Thread(target=self.collector_sensor_read_thread, daemon=True).start() #start solar collector temperature sensor thread
        threading.Thread(target=self.tank_top_sensor_read_thread, daemon=True).start() # start solar tank top temperature sensor thread
        threading.Thread(target=self.tank_mid_sensor_read_thread, daemon=True).start()  # start solar tank mid temperature sensor thread
        threading.Thread(target=self.tank_bot_sensor_read_thread, daemon=True).start()  # start solar tank bottom temperature sensor thread
        threading.Thread(target=self.solar_hot_water_meter_read_thread, daemon=True).start()  # start solar hot water pulse meter thread
        threading.Thread(target=self.solar_electricity_meter_read_thread, daemon=True).start()  # start solar electricity pulse meter thread
        
        #Heat Pump Threads
        threading.Thread(target=self.HP_outlet_read_thread, daemon=True).start()
        threading.Thread(target=self.HP_inlet_read_thread, daemon=True).start()
        threading.Thread(target=self.HP_water_meter_read_thread, daemon=True).start()
        threading.Thread(target=self.HP_elec_meter_read_thread, daemon=True).start()
        threading.Thread(target=self.HP_internal_elec_meter_read_thread, daemon=True).start()
        threading.Thread(target=self.HP_pressure_sensor_read_thread, daemon=True).start()

        #PV threads
        threading.Thread(target=self.PV_meter_read_thread, daemon=True).start()

        #BATTERY threads
        threading.Thread(target=self.BAT_Charge_read_thread, daemon=True).start()
        threading.Thread(target=self.BAT_discharge_read_thread, daemon=True).start()

        #ZONE threads
        threading.Thread(target=self.Zone1, daemon=True).start()
        threading.Thread(target=self.Zone2, daemon=True).start()
        threading.Thread(target=self.Zone3, daemon=True).start()
        threading.Thread(target=self.Zone4, daemon=True).start()

        threading.Thread(target=self.create, args=(self.port,), daemon=True).start()

    def create(self, port):
        self.last_request_time = None
        self.lstPressureReading = []
        
        self.Vref = 3.3 #MCP3008 Vref and Vdd when connected to the Pi via SPI

        context = zmq.Context.instance()
        socket = context.socket(zmq.REP)
        socket.bind(f"tcp://*:{port}")
        self.continue_to_operate = True

        while self.continue_to_operate == True:
            print("Sensor: waiting for requests")
            self.sensor_server_live = True
            message = socket.recv()
            current_time = time.time()

            if self.last_request_time is not None:
                elapsed_time = current_time - self.last_request_time
            else:
                elapsed_time = 0  # For the first request

            self.last_request_time = current_time

            print("Received message: " + str(message))

            lstReturn = [elapsed_time]
            lstReturn.append(self.collate_sensors())
            serialised_data = json.dumps(lstReturn).encode("utf-8")
            print("Sensors: sending response...")
            socket.send(serialised_data)
            print("Sensors: response sent.")

            if message == True:
                self.continue_to_operate = False

    def collate_Zone_sensors(self):
        # Zone1 sensor
        if len(self.lstZone1Reading) != 0:
            avZone1 = sum(self.lstZone1Reading) / len(self.lstZone1Reading)
        else:
            avZone1 = 0
        self.lstZone1Reading = []

        # Zone2 sensor
        if len(self.lstZone2Reading) != 0:
            avZone2 = sum(self.lstZone2Reading) / len(self.lstZone2Reading)
        else:
            avZone2 = 0
        self.lstZone2Reading = []

        # Zone3 sensor
        if len(self.lstZone3Reading) != 0:
            avZone3 = sum(self.lstZone3Reading) / len(self.lstZone3Reading)
        else:
            avZone3 = 0
        self.lstZone3Reading = []

        # Zone4 sensor
        if len(self.lstZone4Reading) != 0:
            avZone4 = sum(self.lstZone4Reading) / len(self.lstZone4Reading)
        else:
            avZone4 = 0
        self.lstZone4Reading = []

        self.dictZoneData = [[self.Zone1_SQL, avZone1],
                                [self.Zone2_SQL, avZone2],
                                [self.Zone3_SQL, avZone3],
                                [self.Zone4_SQL, avZone4]]

        self.Zone_sensors_collated = True

    def collate_BAT_sensors(self):
        # BAT charge electricity meter
        total_BAT_charge_elec_in_period = sum(self.lstBATcharge_electricity)
        self.lstBATcharge_electricity = []

        total_BAT_discharge_elec_in_period = sum(self.lstBATdischarge_electricity)
        self.lstBATdischarge_electricity = []

        self.dictBATData = [[self.BAT_charge_SQL, total_BAT_charge_elec_in_period],
                           [self.BAT_discharge_SQL, total_BAT_discharge_elec_in_period]]

        self.BAT_sensors_collated = True

    def collate_PV_sensors(self):
        # PV electricity meter
        total_PV_elec_in_period = sum(self.lstPV_electricity)
        self.lstPV_electricity = []

        self.dictPVData = [[self.PV_elec_SQL, total_PV_elec_in_period]]

        self.PV_sensors_collated = True

    def collate_HP_sensors(self):
        if len(self.lstHPOutlet) != 0:
            avHPOutletTemp = sum(self.lstHPOutlet) / len(self.lstHPOutlet)
        else:
            avHPOutletTemp = 0
        self.lstHPOutlet = []

        if len(self.lstHPInlet) != 0:
            avHPInletTemp = sum(self.lstHPInlet) / len(self.lstHPInlet)
        else:
            avHPInletTemp = 0
        self.lstHPInlet = []

        # HP hot water flow meter
        total_HP_flow_in_period = sum(self.lstHPflow)
        self.lstHPflow = []

        # HP electricity flow meter
        total_HP_elec_in_period = sum(self.lstHPelectricity)
        self.lstHPelectricity = []

        # HP electricity internalflow meter
        total_HP_elec_int_in_period = sum(self.lstHP_int_electricity)
        self.lstHP_int_electricity = []

        #HP pressure sensor
        if len(self.lstHPPressureReading) != 0:
            avHPPressure = sum(self.lstHPPressureReading) / len(self.lstHPPressureReading)
        else:
            avHPPressure = 0
        self.lstHPPressureReading = []

        self.dictHPData = [[self.HP_outlet_SQL, avHPOutletTemp],
                              [self.HP_inlet_SQL, avHPInletTemp],
                              [self.HP_flow_SQL, total_HP_flow_in_period],
                              [self.HP_electricity_SQL, total_HP_elec_in_period],
                              [self.HP_int_electricity_SQL, total_HP_elec_int_in_period],
                            [self.HP_pressure_SQL, avHPPressure]]

        self.HP_sensors_collated = True

    def collate_solar_sensors(self):
        ###############
        #Solar Sensors#
        ###############

        #PRESSURE SENSOR
        if len(self.lstPressureReading) != 0:
            avSolarPressure = sum(self.lstPressureReading) / len(self.lstPressureReading)
        else:
            avSolarPressure = 0
        #print("Pressure readings prior to reset: " + str(self.lstPressureReading))
        self.lstPressureReading = []
        #print("Pressure reading reset")
        #print(self.lstPressureReading)
        #print("Pressrure reading taken to DB: " + str(avSolarPressure))

        #Collector temperature
        if len(self.lstCollector) != 0:
            avSolarCollector = sum(self.lstCollector) / len(self.lstCollector)
        else:
            avSolarCollector = 0
        #print("Solar collector readings prior to reset: " + str(self.lstCollector))
        self.lstCollector = []
        #print("Solar collector reading reset")
        #print(self.lstCollector)
        #print("Solar collector reading taken to DB: " + str(avSolarCollector))

        #Top cylinder temperature
        if len(self.lstTankTop) != 0:
            avTankTop = sum(self.lstTankTop) / len(self.lstTankTop)
        else:
            avTankTop = 0
        self.lstTankTop = []

        #Mid cylinder temperature
        if len(self.lstTankMid) != 0:
            avTankMid = sum(self.lstTankMid) / len(self.lstTankMid)
        else:
            avTankMid = 0
        self.lstTankMid = []

        #Bottom cylinder temperature
        if len(self.lstTankBot) != 0:
            avTankBot = sum(self.lstTankBot) / len(self.lstTankBot)
        else:
            avTankBot = 0
        self.lstTankBot = []

        #Solar hot water flow meter
        total_solar_flow_in_period = sum(self.lstSolarWater)
        self.lstsolarWater = []

        #Solar hot water flow meter
        total_solar_electricity_in_period = sum(self.lstSolarElectricity)
        self.lstSolarElectricity = []

        self.dictSolarData = [[self.solar_pressure_SQL, avSolarPressure],
                            [self.solar_collector_SQL, avSolarCollector],
                            [self.solar_tank_top_SQL, avTankTop],
                            [self.solar_tank_mid_SQL, avTankMid],
                            [self.solar_tank_bot_SQL, avTankBot],
                            [self.solar_flow_SQL, total_solar_flow_in_period],
                            [self.solar_electricity_SQL, total_solar_electricity_in_period]]

        self.solar_sensors_collated = True

    def collate_sensors(self):
        self.solar_sensors_collated = False
        self.HP_sensors_collated = False
        self.PV_sensors_collated = False
        self.BAT_sensors_collated = False
        self.Zone_sensors_collated = False

        threading.Thread(target=self.collate_solar_sensors, daemon=True).start()
        threading.Thread(target=self.collate_HP_sensors, daemon=True).start()
        threading.Thread(target=self.collate_PV_sensors, daemon=True).start()
        threading.Thread(target=self.collate_BAT_sensors, daemon=True).start()
        threading.Thread(target=self.collate_Zone_sensors, daemon=True).start()

        while not all([self.solar_sensors_collated, self.HP_sensors_collated, self.PV_sensors_collated,
                      self.BAT_sensors_collated, self.Zone_sensors_collated]):
            time.sleep(0.01)

        dictData = [self.dictSolarData, self.dictHPData, self.dictPVData, self.dictBATData, self.dictZoneData]

        return dictData

    def call_method(self, method_name, *args, **kwargs):
        method = getattr(self, method_name)
        return method(*args, **kwargs)

    def read_MCP3008_SPI(self, SPIBus, SPIChannel, MCP3008_Channel):
        spi = spidev.SpiDev()
        spi.open(SPIBus,SPIChannel) #Operating SPI in 'low' state - as such data extracted corresponds to SPI communication where SCLK idles low
        spi.max_speed_hz = 1200000

        assert 0 <= MCP3008_Channel <=7 #there are 8 channels on the MCP3008
        r = spi.xfer2([1, 8 + MCP3008_Channel << 4,0])
        msg = ((r[1] & 3) << 8) + r[2] #the data out
        spi.close()
        voltage_ratio = msg / 1024 #per the data sheet for the MCP3008 to provide the LSB Size
        voltage = voltage_ratio * self.Vref
        return voltage

    def pressure_5V_via_MCP3008(self, lstArgs):
        #IMPORTANT: as the Pi's GPIOs are 3.3V a voltage divider is needed to protect the pi
        #Assumed component: 5V PRESSURE TRANSDUCER SENSOR 0 - 175 PSI 0 - 1.2 MPa OIL GAS AIR WATER 0.5-4.5V 1/4"
        #Output voltage: 0.5 - 4.5V DC, Working current: less than or equal to 10 mA
        #A voltage divider is used to step down the maximum 4.5V down to 3.3V as such

        SPIBus = lstArgs[0]
        SPIChannel = lstArgs[1]
        MCP3008_Channel = lstArgs[2]

        Vout = self.read_MCP3008_SPI(SPIBus, SPIChannel, MCP3008_Channel)
        #print(Vout)
        minVoltage = 0.5 * 10000 / 13600 #0.5V is minimum Vin * R2 (10k Ohm resistor) / (10k Ohm + 3k6 Ohm (R1) resistors)
        maxVoltage = 4.5 * 10000 / 13600 #4.5 is maximum Vin * R2 (10k Ohm resistor) / (10k Ohm + 3k6 Ohm (R1) resistors)
        #print(minVoltage)
        #print(maxVoltage)
        minPressure = 0 #PSI
        maxPressure = 175 #PSI
        fltInterpolatedPSI = minPressure + (((Vout - minVoltage) / (maxVoltage - minVoltage)) * (maxPressure - minPressure))
        fltBar = fltInterpolatedPSI * 0.0689476 #conversion of PSI to bar
        return fltBar

    def temp_from_MCP3008_10K_NTC_Thermistor(self, lstArgs):
        SPIBus = lstArgs[0]
        SPIChannel = lstArgs[1]
        MPC3008_Channel = lstArgs[2]

        R1 = 10000  # 10k ohm thermistor - worth checking the actual resistance with multi-meter and updating
        #Vref = 3.3  # The Raspberry Pi's SPI pins are 3.3V so the supply voltage should also be 3.3V not 5V

        voltage = self.read_MCP3008_SPI(SPIBus, SPIChannel, MPC3008_Channel)
        thermistor_resistance = self.R2_resistance_OHM(R1, self.Vref, voltage)
        TempDegC = self.TenK_NTC_Thermistor(thermistor_resistance)
        return TempDegC

    def TenK_NTC_Thermistor(self, R2_resistance):
        # Reistance = Ae^(Beta/T) for standard NTC resistor
        Rref = 10000  # 10k Ohm resistor
        Beta = 3977  # For specific thermistor used in this project: https://www.sterlingsensors.co.uk/ntc-thermistor-sensor-with-fixed-process-connection.html
        TRef = 25  # DegC
        Kelvin = 273  # DegC to absolute zero

        # Rearranging formula: A = Resistance/(e^(Beta/T)
        A = Rref / (math.exp(Beta / (TRef + Kelvin)))

        # The thermistor has provided the actual resistance reading being R2_resistance
        # Rearranging formula: T (DegC) = Beta / LN(Resistance/A) - Kelvin
        if R2_resistance / A != 0:
            TempDegC = (Beta / math.log(R2_resistance / A)) - Kelvin
            return TempDegC
        else:
            return 0

    def R1_resistance_OHM(self, R2, Vin, Vout):  # Used to calculate the first resistor in a voltage divide circuit - used where Vin is too high for Pi
        if Vout != 0:
            R1 = (R2 * (Vin - Vout)) / Vout
            return R1
        else:
            return 0

    def R2_resistance_OHM(self, R1, Vin, Vout):  # Used to calculate the second resistor in a voltage divide circuit
        if Vin - Vout != 0:
            R2 = (R1 * Vout) / (Vin - Vout)
            return R2
        else:
            return 0

    def light_sensor(self, lstArgs):
        SPIBus = lstArgs[0]
        SPIChannel = lstArgs[1]
        MCP3008_Channel = lstArgs[2]

        voltage = self.read_MCP3008_SPI(SPIBus, SPIChannel, MCP3008_Channel)
        # print(voltage)
        R1_ohm = self.R1_resistance_OHM(10000, self.Vref, voltage)  # Resistor 2 on HeatSet PCB = 10k ohm    #print(R1_ohm)
        # print(R1_ohm)
        Resistance_ON = 2000  # The resistance of the photoresistor will be different for different LED lights so this needs to be calbirated but need not be exact
        if R1_ohm >= Resistance_ON:  # Photo resistors have a lower resistance with greater light intensity
            return 1  # The graph will plot a straight line against each zone
        else:
            return 0

    def pressure_sensor_read_thread(self):
        self.lstPressureReading = []
        lstArgs = self.dictInstructions['Solar_Inputs']['GUI_Information']['SYS_Pressure']['Interface_args']

        while self.continue_to_operate == True:
            self.lstPressureReading.append(self.pressure_5V_via_MCP3008(lstArgs))
            #print("Pressure readings: " + str(self.lstPressureReading))
            time.sleep(1)

    def collector_sensor_read_thread(self):
        self.lstCollector = []
        lstArgs = self.dictInstructions['Solar_Inputs']['GUI_Information']['Collector_temp']['Interface_args']

        while self.continue_to_operate == True:
            self.lstCollector.append(self.temp_from_MCP3008_10K_NTC_Thermistor(lstArgs))
            time.sleep(1)

    def tank_top_sensor_read_thread(self):
        self.lstTankTop = []
        lstArgs = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_top_temp']['Interface_args']

        while self.continue_to_operate == True:
            self.lstTankTop.append(self.temp_from_MCP3008_10K_NTC_Thermistor(lstArgs))
            time.sleep(1)

    def tank_mid_sensor_read_thread(self):
        self.lstTankMid = []
        lstArgs = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_temp']['Interface_args']

        while self.continue_to_operate == True:
            self.lstTankMid.append(self.temp_from_MCP3008_10K_NTC_Thermistor(lstArgs))
            time.sleep(1)

    def tank_bot_sensor_read_thread(self):
        self.lstTankBot = []
        lstArgs = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_bot_temp']['Interface_args']

        while self.continue_to_operate == True:
            self.lstTankBot.append(self.temp_from_MCP3008_10K_NTC_Thermistor(lstArgs))
            time.sleep(1)

    def solar_hot_water_meter_read_thread(self):
        self.lstSolarWater = []
        GPIO_Pin = self.dictInstructions['Solar_Inputs']['GUI_Information']['Flow_Rate']['Pulse_GPIO']
        last_state = GPIO.input(GPIO_Pin)

        while self.continue_to_operate == True:
            current_state = GPIO.input(GPIO_Pin)
            if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                self.lstSolarWater.append(1)
                #print("Pulse from solar hot water")
            last_state = current_state
            time.sleep(0.01)

    def solar_electricity_meter_read_thread(self):
        self.lstSolarElectricity = []
        GPIO_Pin = self.dictInstructions['Solar_Inputs']['GUI_Information']['Solar_pump_electricity']['Pulse_GPIO']
        last_state = GPIO.input(GPIO_Pin)

        while self.continue_to_operate == True:
            current_state = GPIO.input(GPIO_Pin)
            if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                self.lstSolarElectricity.append(1)
                #print("Pulse from solar electricity")
            last_state = current_state
            time.sleep(0.01)

    def HP_outlet_read_thread(self):
        self.lstHPOutlet = []
        lstArgs = self.dictInstructions['HP_Inputs']['GUI_Information']['Outlet_Temperature']['Interface_args']

        while self.continue_to_operate == True:
            self.lstHPOutlet.append(self.temp_from_MCP3008_10K_NTC_Thermistor(lstArgs))
            time.sleep(1)

    def HP_inlet_read_thread(self):
        self.lstHPInlet = []
        lstArgs = self.dictInstructions['HP_Inputs']['GUI_Information']['Inlet_Temperature']['Interface_args']

        while self.continue_to_operate == True:
            self.lstHPInlet.append(self.temp_from_MCP3008_10K_NTC_Thermistor(lstArgs))
            time.sleep(1)

    def HP_water_meter_read_thread(self):
        self.lstHPflow = []
        GPIO_Pin = self.dictInstructions['HP_Inputs']['GUI_Information']['Flow_Rate']['Pulse_GPIO']
        last_state = GPIO.input(GPIO_Pin)

        while self.continue_to_operate == True:
            current_state = GPIO.input(GPIO_Pin)
            if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                self.lstHPflow.append(1)
                #print("Pulse from HP hot water meter")
            last_state = current_state
            time.sleep(0.01)

    def HP_elec_meter_read_thread(self):
        self.lstHPelectricity = []
        GPIO_Pin = self.dictInstructions['HP_Inputs']['GUI_Information']['External_Unit_Elec_Wh']['Pulse_GPIO']
        last_state = GPIO.input(GPIO_Pin)

        while self.continue_to_operate == True:
            current_state = GPIO.input(GPIO_Pin)
            if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                self.lstHPelectricity.append(1)
                #print("Pulse from HP electricity meter")
            last_state = current_state
            time.sleep(0.01)

    def HP_internal_elec_meter_read_thread(self):
        self.lstHP_int_electricity = []
        GPIO_Pin = self.dictInstructions['HP_Inputs']['GUI_Information']['Internal_Unit_Elec_Wh']['Pulse_GPIO']
        last_state = GPIO.input(GPIO_Pin)

        while self.continue_to_operate == True:
            current_state = GPIO.input(GPIO_Pin)
            if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                self.lstHP_int_electricity.append(1)
                #print("Pulse from HP internal electricity meter")
            last_state = current_state
            time.sleep(0.01)

    def HP_pressure_sensor_read_thread(self):
        self.lstHPPressureReading = []
        lstArgs = self.dictInstructions['HP_Inputs']['GUI_Information']['HP_Pressure']['Interface_args']

        while self.continue_to_operate == True:
            self.lstHPPressureReading.append(self.pressure_5V_via_MCP3008(lstArgs))
            #print("HP Pressure readings: " + str(self.lstHPPressureReading))
            time.sleep(1)

    def PV_meter_read_thread(self):
        self.lstPV_electricity = []
        GPIO_Pin = self.dictInstructions['PV_Inputs']['GUI_Information']['Generation']['Pulse_GPIO']
        last_state = GPIO.input(GPIO_Pin)

        while self.continue_to_operate == True:
            current_state = GPIO.input(GPIO_Pin)
            if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                self.lstPV_electricity.append(1)
                #print("Pulse from PV electricity meter")
            last_state = current_state
            time.sleep(0.01)

    def BAT_Charge_read_thread(self):
        self.lstBATcharge_electricity = []
        GPIO_Pin = self.dictInstructions['BAT_Inputs']['GUI_Information']['Charge_Supply']['Pulse_GPIO']
        last_state = GPIO.input(GPIO_Pin)

        while self.continue_to_operate == True:
            current_state = GPIO.input(GPIO_Pin)
            if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                self.lstBATcharge_electricity.append(1)
                #print("Pulse from BAT charge electricity meter")
            last_state = current_state
            time.sleep(0.01)

    def BAT_discharge_read_thread(self):
        self.lstBATdischarge_electricity = []
        GPIO_Pin = self.dictInstructions['BAT_Inputs']['GUI_Information']['Discharge_Supply']['Pulse_GPIO']
        last_state = GPIO.input(GPIO_Pin)

        while self.continue_to_operate == True:
            current_state = GPIO.input(GPIO_Pin)
            if last_state == GPIO.HIGH and current_state == GPIO.LOW:
                self.lstBATdischarge_electricity.append(1)
                #print("Pulse from BAT discharge electricity meter")
            last_state = current_state
            time.sleep(0.01)

    def Zone1(self):
        self.lstZone1Reading = []
        lstArgs = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_1']['Interface_args']

        while self.continue_to_operate == True:
            self.lstZone1Reading.append(self.light_sensor(lstArgs))
            #print("HP Pressure readings: " + str(self.lstHPPressureReading))
            time.sleep(1)

    def Zone2(self):
        self.lstZone2Reading = []
        lstArgs = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_2']['Interface_args']

        while self.continue_to_operate == True:
            self.lstZone2Reading.append(self.light_sensor(lstArgs))
            #print("HP Pressure readings: " + str(self.lstHPPressureReading))
            time.sleep(1)

    def Zone3(self):
        self.lstZone3Reading = []
        lstArgs = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_3']['Interface_args']

        while self.continue_to_operate == True:
            self.lstZone3Reading.append(self.light_sensor(lstArgs))
            #print("HP Pressure readings: " + str(self.lstHPPressureReading))
            time.sleep(1)

    def Zone4(self):
        self.lstZone4Reading = []
        lstArgs = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_4']['Interface_args']

        while self.continue_to_operate == True:
            self.lstZone4Reading.append(self.light_sensor(lstArgs))
            #print("HP Pressure readings: " + str(self.lstHPPressureReading))
            time.sleep(1)
