import tkinter as tk
from tkinter import ttk
import time
import datetime as dt
import subprocess
# from rpi_backlight import Backlight
import threading
from PIL import Image, ImageTk
from A_Initialise import *
import C_chart_plots as cht_plt
import D_Database as db
import G_Check_Time as chk_time
#import TEST_Pulse as test_pulse
import zmq
import json

class build_GUI:
    def __init__(self, dictInstructions, parent_port):
        self.RootWin = tk.Tk()  # Create the main GUI window
        self.quit_sys = False
        self.created_self = False
        self.parent_port = parent_port
        self.create_master_window(dictInstructions)
        self.solar_table_name = dictInstructions['Solar_Inputs']['Defaults']['Database_Table_Name']
        self.HP_table_name = dictInstructions['HP_Inputs']['Defaults']['Database_Table_Name']
        self.PV_table_name = dictInstructions['PV_Inputs']['Defaults']['Database_Table_Name']
        self.BAT_table_name = dictInstructions['BAT_Inputs']['Defaults']['Database_Table_Name']
        self.Zone_table_name = dictInstructions['ZONE_Inputs']['Defaults']['Database_Table_Name']
        self.dictInstructions = dictInstructions

    def quit_GUI(self):
        ####QUIT DEFAULTS
        self.quit_sys = True
        print("quit")

    def request_db_data(self, function, lstArgs):
        context = zmq.Context.instance()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://localhost:" + str(self.parent_port))
        lstPackage = [function, lstArgs]
        print("GUI sending to parent following information: " + str(lstPackage))
        data = json.dumps(lstPackage).encode("utf-8")
        #print("sending:" + str(data))
        print("GUI: sending DB request via port " + str(self.parent_port))
        socket.send(data)
        print("GUI: DB request sent. Waiting for response")
        response = socket.recv()
        print("GUI: DB response received")
        lstData = json.loads(response.decode("utf-8"))
        #print("GUI DATA = " + str(lstData))
        return lstData

    def convert_SQL_date(selfself, dtDate):
        #need to subtract a day and run request_db_data on the previous day
        strMonth = str(dtDate.month)
        if len(strMonth) == 1:
            strMonth = '0' + strMonth
        strDay = str(dtDate.day)
        if len(strDay) == 1:
            strDay = '0' + strDay

        strDate = str(dtDate.year) + "-" + strMonth + "-" + strDay
        return strDate + ' 00:00:00'

    def convert_time_to_minutes(self, lstVals):
        for item in lstVals:
            tm_val_str = item[0]
            tm_val = dt.datetime.strptime(tm_val_str, "%Y-%m-%d %H:%M:%S")
            #print(tm_val)
            min_val = tm_val.minute
            hr_val = tm_val.hour
            item[0] = (min_val / 60) + hr_val
            if item[1] != None:
                item[1] = float(item[1])
            else:
                item[1] = 0
        #print("Time stamp updated to minutes:" + str(lstVals))
        return lstVals

    def convert_time_to_minutes_zones(self, lstVals, zone_ID):
        for item in lstVals:
            tm_val_str = item[0]
            tm_val = dt.datetime.strptime(tm_val_str, "%Y-%m-%d %H:%M:%S")
            #print(tm_val)
            min_val = tm_val.minute
            hr_val = tm_val.hour
            item[0] = (min_val / 60) + hr_val
            if item[1] != None:
                fltMultiple = zone_ID + 1
                if item[1] != 0:
                    item[1] = fltMultiple - ((1-float(item[1])) * 0.5)
                else:
                    item[1] = fltMultiple - 0.5
            else:
                item[1] = 0
        #print("Time stamp updated to minutes:" + str(lstVals))
        return lstVals

    def convert_time_to_minutes_and_sum_all(self, lstVals):
        fltTotal = 0
        for item in lstVals:
            tm_val_str = item[0]
            tm_val = dt.datetime.strptime(tm_val_str, "%Y-%m-%d %H:%M:%S")
            #print(tm_val)
            min_val = tm_val.minute
            hr_val = tm_val.hour
            item[0] = (min_val / 60) + hr_val
            if item[1] != None:
                fltTotal = fltTotal + float(item[1])
                item[1] = fltTotal
            else:
                item[1] = fltTotal
        #print("Time stamp updated to minutes:" + str(lstVals))
        return lstVals

    def previous_PV(self):
        strDate = self.PV_Graph.return_title()
        #print(strDate)
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDatePrev = dtDate - dt.timedelta(days=1)
        if dtDate == dt.datetime.now():
            self.Date_HP_Next_Cmd.pack()

        strDatePrevSQL = self.convert_SQL_date(dtDatePrev)
        strDateCurrSQL = self.convert_SQL_date(dtDate)
        self.PV_Graph.update_graph_title(dt.datetime.strftime(dtDatePrev, "%d/%m/%Y", ))
        self.run_PV(strDatePrevSQL, strDateCurrSQL)

    def next_PV(self):
        strDate = self.PV_Graph.return_title()
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDateNext = dtDate + dt.timedelta(days=1)
        dtDateNext1 = dtDateNext + dt.timedelta(days=1)
        if dtDateNext == dt.datetime.now():
            self.Date_HP_Next_Cmd.pack_forget()

        strDateNextSQL = self.convert_SQL_date(dtDateNext1)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.PV_Graph.update_graph_title(dt.datetime.strftime(dtDateNext, "%d/%m/%Y", ))
        self.run_PV(strDateCurrSQL, strDateNextSQL)

    def previous_BAT(self):
        strDate = self.BAT_Graph.return_title()
        #print(strDate)
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDatePrev = dtDate - dt.timedelta(days=1)
        if dtDate == dt.datetime.now():
            self.Date_HP_Next_Cmd.pack()

        strDatePrevSQL = self.convert_SQL_date(dtDatePrev)
        strDateCurrSQL = self.convert_SQL_date(dtDate)
        self.BAT_Graph.update_graph_title(dt.datetime.strftime(dtDatePrev, "%d/%m/%Y", ))
        self.run_BAT(strDatePrevSQL, strDateCurrSQL)

    def next_BAT(self):
        strDate = self.BAT_Graph.return_title()
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDateNext = dtDate + dt.timedelta(days=1)
        dtDateNext1 = dtDateNext + dt.timedelta(days=1)
        if dtDateNext == dt.datetime.now():
            self.Date_HP_Next_Cmd.pack_forget()

        strDateNextSQL = self.convert_SQL_date(dtDateNext1)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.BAT_Graph.update_graph_title(dt.datetime.strftime(dtDateNext, "%d/%m/%Y", ))
        self.run_BAT(strDateCurrSQL, strDateNextSQL)

    def previous_Zone(self):
        strDate = self.Zone_Graph.return_title()
        #print(strDate)
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDatePrev = dtDate - dt.timedelta(days=1)
        if dtDate == dt.datetime.now():
            self.Date_HP_Next_Cmd.pack()

        strDatePrevSQL = self.convert_SQL_date(dtDatePrev)
        strDateCurrSQL = self.convert_SQL_date(dtDate)
        self.Zone_Graph.update_graph_title(dt.datetime.strftime(dtDatePrev, "%d/%m/%Y", ))
        self.run_Zone(strDatePrevSQL, strDateCurrSQL)

    def next_Zone(self):
        strDate = self.Zone_Graph.return_title()
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDateNext = dtDate + dt.timedelta(days=1)
        dtDateNext1 = dtDateNext + dt.timedelta(days=1)
        if dtDateNext == dt.datetime.now():
            self.Date_HP_Next_Cmd.pack_forget()

        strDateNextSQL = self.convert_SQL_date(dtDateNext1)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.Zone_Graph.update_graph_title(dt.datetime.strftime(dtDateNext, "%d/%m/%Y", ))
        self.run_Zone(strDateCurrSQL, strDateNextSQL)

    def previous_HP(self):
        strDate = self.HP_Graph.return_title()
        #print(strDate)
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDatePrev = dtDate - dt.timedelta(days=1)
        if dtDate == dt.datetime.now():
            self.Date_HP_Next_Cmd.pack()

        strDatePrevSQL = self.convert_SQL_date(dtDatePrev)
        strDateCurrSQL = self.convert_SQL_date(dtDate)
        self.HP_Graph.update_graph_title(dt.datetime.strftime(dtDatePrev, "%d/%m/%Y", ))
        self.run_HP(strDatePrevSQL, strDateCurrSQL, False)

    def next_HP(self):
        strDate = self.HP_Graph.return_title()
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDateNext = dtDate + dt.timedelta(days=1)
        dtDateNext1 = dtDateNext + dt.timedelta(days=1)
        if dtDateNext == dt.datetime.now():
            self.Date_HP_Next_Cmd.pack_forget()

        strDateNextSQL = self.convert_SQL_date(dtDateNext1)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.HP_Graph.update_graph_title(dt.datetime.strftime(dtDateNext, "%d/%m/%Y", ))
        self.run_HP(strDateCurrSQL, strDateNextSQL, False)

    def reset_HP(self):
        #print(strDate)
        dtDate = dt.datetime.now()
        dtDateNext = dtDate + dt.timedelta(days=1)
        self.Date_HP_Next_Cmd.pack_forget()

        strDatePrevSQL = self.convert_SQL_date(dtDate)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.HP_Graph.update_graph_title(dt.datetime.strftime(dtDate, "%d/%m/%Y", ))
        self.run_HP(strDatePrevSQL, strDateCurrSQL, False)

    def reset_Zone(self):
        #print(strDate)
        dtDate = dt.datetime.now()
        dtDateNext = dtDate + dt.timedelta(days=1)
        self.Date_Zone_Next_Cmd.pack_forget()

        strDatePrevSQL = self.convert_SQL_date(dtDate)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.Zone_Graph.update_graph_title(dt.datetime.strftime(dtDate, "%d/%m/%Y", ))
        self.run_Zone(strDatePrevSQL, strDateCurrSQL, False)

    def reset_PV(self):
        #print(strDate)
        dtDate = dt.datetime.now()
        dtDateNext = dtDate + dt.timedelta(days=1)
        self.Date_PV_Next_Cmd.pack_forget()

        strDatePrevSQL = self.convert_SQL_date(dtDate)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.PV_Graph.update_graph_title(dt.datetime.strftime(dtDate, "%d/%m/%Y", ))
        self.run_PV(strDatePrevSQL, strDateCurrSQL)

    def reset_BAT(self):
        #print(strDate)
        dtDate = dt.datetime.now()
        dtDateNext = dtDate + dt.timedelta(days=1)
        self.Date_BAT_Next_Cmd.pack_forget()

        strDatePrevSQL = self.convert_SQL_date(dtDate)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.BAT_Graph.update_graph_title(dt.datetime.strftime(dtDate, "%d/%m/%Y", ))
        self.run_BAT(strDatePrevSQL, strDateCurrSQL)

    def previous_solar(self):
        strDate = self.Solar_Graph.return_title()
        #print(strDate)
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDatePrev = dtDate - dt.timedelta(days=1)
        if dtDate == dt.datetime.now():
            self.Date_Solar_Next_Cmd.pack()

        strDatePrevSQL = self.convert_SQL_date(dtDatePrev)
        strDateCurrSQL = self.convert_SQL_date(dtDate)
        self.Solar_Graph.update_graph_title(dt.datetime.strftime(dtDatePrev, "%d/%m/%Y", ))
        self.run_solar(strDatePrevSQL, strDateCurrSQL)

    def next_solar(self):
        strDate = self.Solar_Graph.return_title()
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDateNext = dtDate + dt.timedelta(days=1)
        dtDateNext1 = dtDateNext + dt.timedelta(days=1)
        if dtDateNext == dt.datetime.now():
            self.Date_Solar_Next_Cmd.pack_forget()

        strDateNextSQL = self.convert_SQL_date(dtDateNext1)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.Solar_Graph.update_graph_title(dt.datetime.strftime(dtDateNext, "%d/%m/%Y", ))
        self.run_solar(strDateCurrSQL, strDateNextSQL)

    def reset_solar(self):
        #print(strDate)
        dtDate = dt.datetime.now()
        dtDateNext = dtDate + dt.timedelta(days=1)
        self.Date_Solar_Next_Cmd.pack_forget()

        strDatePrevSQL = self.convert_SQL_date(dtDate)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.Solar_Graph.update_graph_title(dt.datetime.strftime(dtDate, "%d/%m/%Y", ))
        self.run_solar(strDatePrevSQL, strDateCurrSQL)

    def current_solar(self):
        #print(strDate)
        strDate = self.Solar_Graph.return_title()
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDateNext = dtDate + dt.timedelta(days=1)

        strDatePrevSQL = self.convert_SQL_date(dtDate)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.run_solar(strDatePrevSQL, strDateCurrSQL)

    def current_HP(self):
        #print(strDate)
        strDate = self.HP_Graph.return_title()
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDateNext = dtDate + dt.timedelta(days=1)

        strDatePrevSQL = self.convert_SQL_date(dtDate)
        strDateCurrSQL = self.convert_SQL_date(dtDateNext)
        self.run_HP(strDatePrevSQL, strDateCurrSQL, False)

    def run_solar(self, strDatePrevSQL, strDateCurrSQL):
        #Collector Temperature
        Collect_Field = self.dictInstructions['Solar_Inputs']['GUI_Information']['Collector_temp']['SQL_Title']
        plot_colour = self.dictInstructions['Solar_Inputs']['GUI_Information']['Collector_temp']['Plot_colour']
        plot_series = self.dictInstructions['Solar_Inputs']['GUI_Information']['Collector_temp']['Plot_index']
        plot_name = self.dictInstructions['Solar_Inputs']['GUI_Information']['Collector_temp']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.solar_table_name, Collect_Field]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes(lstData)
        self.Solar_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

        #tank top temperature
        tank_top_Field = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_top_temp']['SQL_Title']
        plot_tank_top_colour = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_top_temp']['Plot_colour']
        plot_tank_top_series = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_top_temp']['Plot_index']
        plot_tank_top_name = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_top_temp']['Plot_label']
        lstTankTopArgs = [strDatePrevSQL, strDateCurrSQL, self.solar_table_name, tank_top_Field]
        #print(lstArgs)
        lstTankTopData = self.request_db_data("extract_values", lstTankTopArgs)
        lstTankTopVals = self.convert_time_to_minutes(lstTankTopData)
        self.Solar_Graph.plot_chart(lstTankTopVals, plot_tank_top_colour, plot_tank_top_series, plot_tank_top_name)

        #tank mid temperature
        tank_mid_Field = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_temp']['SQL_Title']
        plot_tank_mid_colour = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_temp']['Plot_colour']
        plot_tank_mid_series = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_temp']['Plot_index']
        plot_tank_mid_name = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_temp']['Plot_label']
        lstTankMidArgs = [strDatePrevSQL, strDateCurrSQL, self.solar_table_name, tank_mid_Field]
        #print(lstArgs)
        lstTankMidData = self.request_db_data("extract_values", lstTankMidArgs)
        lstTankMidVals = self.convert_time_to_minutes(lstTankMidData)
        self.Solar_Graph.plot_chart(lstTankMidVals, plot_tank_mid_colour, plot_tank_mid_series, plot_tank_mid_name)

        #tank bottom temperature
        tank_bot_Field = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_bot_temp']['SQL_Title']
        plot_tank_bot_colour = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_bot_temp']['Plot_colour']
        plot_tank_bot_series = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_bot_temp']['Plot_index']
        plot_tank_bot_name = self.dictInstructions['Solar_Inputs']['GUI_Information']['Tank_bot_temp']['Plot_label']
        lstTankBotArgs = [strDatePrevSQL, strDateCurrSQL, self.solar_table_name, tank_bot_Field]
        #print(lstArgs)
        lstTankBotData = self.request_db_data("extract_values", lstTankBotArgs)
        lstTankBotVals = self.convert_time_to_minutes(lstTankBotData)
        self.Solar_Graph.plot_chart(lstTankBotVals, plot_tank_bot_colour, plot_tank_bot_series, plot_tank_bot_name)

    def run_HP(self, strDatePrevSQL, strDateCurrSQL, bool_chg):
        strLabel = self.HP_chg_graph_cmd.cget("text")
        lstArgs = [strDatePrevSQL, strDateCurrSQL]

        print("CHANGING GRAPH: " + str(bool_chg))

        if bool_chg == True:
            strDate = self.HP_Graph.return_title()
            self.frmHPGraph.destroy()
            self.frmHPGraph = tk.Frame(self.HP_Tab, pady=5, padx=5, highlightbackground="black",
                                       highlightcolor="black",
                                       highlightthickness=1)
            # frmSolarGraph.bind('<Button>',cmd_lightUp)
            self.frmHPGraph.pack()
            self.frmHPGraph.place(y=self.dictInstructions['HP_Inputs']['GUI_params']['Graph_Section']['Graph_y'],
                                  x=self.dictInstructions['HP_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                                  height=self.dictInstructions['HP_Inputs']['GUI_params']['Graph_Section'][
                                      'GraphFm_height'],
                                  width=self.dictInstructions['HP_Inputs']['GUI_params']['Graph_Section'][
                                      'GraphFm_width'])

            if strLabel == "GRAPH 1":
                self.HP_Graph = cht_plt.GUI_graph(self.dictInstructions['HP_Inputs']['Graph2_params'],
                                                    self.frmHPGraph)
                self.HP_Graph.update_graph_title(strDate)
                self.HP_chg_graph_cmd.config(text="GRAPH 2")

            if strLabel == "GRAPH 2":
                self.HP_Graph = cht_plt.GUI_graph(self.dictInstructions['HP_Inputs']['Graph1_params'], self.frmHPGraph)
                self.HP_Graph.update_graph_title(strDate)
                self.HP_chg_graph_cmd.config(text="GRAPH 1")

        strLabel = self.HP_chg_graph_cmd.cget("text")
        if strLabel == "GRAPH 1":
            self.run_HP_1(lstArgs)

        if strLabel == "GRAPH 2":
            self.run_HP_2(lstArgs)

    def run_HP_1(self, lstArgs):
        #Heat Load
        strDatePrevSQL = lstArgs[0]
        strDateCurrSQL = lstArgs[1]

        HeatLoad_Field = self.dictInstructions['HP_Inputs']['GUI_Information']['Heat_load']['SQL_Title']
        plot_colour = self.dictInstructions['HP_Inputs']['GUI_Information']['Heat_load']['Plot_colour']
        plot_series = self.dictInstructions['HP_Inputs']['GUI_Information']['Heat_load']['Plot_index']
        plot_name = self.dictInstructions['HP_Inputs']['GUI_Information']['Heat_load']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.HP_table_name, HeatLoad_Field]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes_and_sum_all(lstData)
        self.HP_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

        #Heat Load
        Electricity_Field = self.dictInstructions['HP_Inputs']['GUI_Information']['External_Unit_Elec_Wh']['SQL_Title']
        plot_colour = self.dictInstructions['HP_Inputs']['GUI_Information']['External_Unit_Elec_Wh']['Plot_colour']
        plot_series = self.dictInstructions['HP_Inputs']['GUI_Information']['External_Unit_Elec_Wh']['Plot_index']
        plot_name = self.dictInstructions['HP_Inputs']['GUI_Information']['External_Unit_Elec_Wh']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.HP_table_name, Electricity_Field]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes_and_sum_all(lstData)
        self.HP_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

    def run_HP_2(self, lstArgs):
        #HP Outlet
        strDatePrevSQL = lstArgs[0]
        strDateCurrSQL = lstArgs[1]

        Outlet_Temp = self.dictInstructions['HP_Inputs']['GUI_Information']['Outlet_Temperature']['SQL_Title']
        print("Outliet_Temp: " + Outlet_Temp)
        plot_colour = self.dictInstructions['HP_Inputs']['GUI_Information']['Outlet_Temperature']['Plot_colour']
        print("plot_colour: " + plot_colour)
        plot_series = self.dictInstructions['HP_Inputs']['GUI_Information']['Outlet_Temperature']['Plot_index']
        print("plot_series: " + str(plot_series))
        plot_name = self.dictInstructions['HP_Inputs']['GUI_Information']['Outlet_Temperature']['Plot_label']
        print("plot_name: " + plot_name)
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.HP_table_name, Outlet_Temp]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        #print("lstDATA: " + str(lstData))
        lstVals = self.convert_time_to_minutes(lstData)
        self.HP_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

        #HP inlet
        Inlet_Temp = self.dictInstructions['HP_Inputs']['GUI_Information']['Inlet_Temperature']['SQL_Title']
        plot_colour = self.dictInstructions['HP_Inputs']['GUI_Information']['Inlet_Temperature']['Plot_colour']
        plot_series = self.dictInstructions['HP_Inputs']['GUI_Information']['Inlet_Temperature']['Plot_index']
        plot_name = self.dictInstructions['HP_Inputs']['GUI_Information']['Inlet_Temperature']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.HP_table_name, Inlet_Temp]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes(lstData)
        self.HP_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

    def run_PV(self, strDatePrevSQL, strDateCurrSQL):
        #Collector Temperature
        PV_Field = self.dictInstructions['PV_Inputs']['GUI_Information']['Generation']['SQL_Title']
        plot_colour = self.dictInstructions['PV_Inputs']['GUI_Information']['Generation']['Plot_colour']
        plot_series = self.dictInstructions['PV_Inputs']['GUI_Information']['Generation']['Plot_index']
        plot_name = self.dictInstructions['PV_Inputs']['GUI_Information']['Generation']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.PV_table_name, PV_Field]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes_and_sum_all(lstData)
        self.PV_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

    def run_BAT(self, strDatePrevSQL, strDateCurrSQL):
        #Collector Temperature
        Discharge_Field = self.dictInstructions['BAT_Inputs']['GUI_Information']['Discharge_Supply']['SQL_Title']
        plot_colour = self.dictInstructions['BAT_Inputs']['GUI_Information']['Discharge_Supply']['Plot_colour']
        plot_series = self.dictInstructions['BAT_Inputs']['GUI_Information']['Discharge_Supply']['Plot_index']
        plot_name = self.dictInstructions['BAT_Inputs']['GUI_Information']['Discharge_Supply']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.BAT_table_name, Discharge_Field]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes_and_sum_all(lstData)
        self.BAT_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

        Charge_Field = self.dictInstructions['BAT_Inputs']['GUI_Information']['Charge_Supply']['SQL_Title']
        plot_colour = self.dictInstructions['BAT_Inputs']['GUI_Information']['Charge_Supply']['Plot_colour']
        plot_series = self.dictInstructions['BAT_Inputs']['GUI_Information']['Charge_Supply']['Plot_index']
        plot_name = self.dictInstructions['BAT_Inputs']['GUI_Information']['Charge_Supply']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.BAT_table_name, Charge_Field]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes_and_sum_all(lstData)
        self.BAT_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

    def run_Zone(self, strDatePrevSQL, strDateCurrSQL):
        #Zone 1
        Zone_Field = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_1']['SQL_Title']
        plot_colour = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_1']['Plot_colour']
        plot_series = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_1']['Plot_index']
        plot_name = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_1']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.Zone_table_name, Zone_Field]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes_zones(lstData, 1)
        self.Zone_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

        #Zone 2
        Zone_Field = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_2']['SQL_Title']
        plot_colour = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_2']['Plot_colour']
        plot_series = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_2']['Plot_index']
        plot_name = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_2']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.Zone_table_name, Zone_Field]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes_zones(lstData, 2)
        self.Zone_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

        #Zone 3
        Zone_Field = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_3']['SQL_Title']
        plot_colour = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_3']['Plot_colour']
        plot_series = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_3']['Plot_index']
        plot_name = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_3']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.Zone_table_name, Zone_Field]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes_zones(lstData, 3)
        self.Zone_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

        #Zone 4
        Zone_Field = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_4']['SQL_Title']
        plot_colour = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_4']['Plot_colour']
        plot_series = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_4']['Plot_index']
        plot_name = self.dictInstructions['ZONE_Inputs']['GUI_Information']['Zone_4']['Plot_label']
        lstArgs = [strDatePrevSQL, strDateCurrSQL, self.Zone_table_name, Zone_Field]
        #print(lstArgs)
        lstData = self.request_db_data("extract_values", lstArgs)
        lstVals = self.convert_time_to_minutes_zones(lstData, 4)
        self.Zone_Graph.plot_chart(lstVals, plot_colour, plot_series, plot_name)

    def restart_GUI(self):
        ### RESET DEFAULTS
        self.quit_sys = True
        time.sleep(60)
        self.quit_sys = False
        self.initiate_all_threads()
        print("restart")

    def change_HP_chart(self):
        strDate = self.HP_Graph.return_title()
        dtDate = dt.datetime.strptime(strDate, "%d/%m/%Y")
        dtDateNext = dtDate + dt.timedelta(days=1)
        if dtDateNext == dt.datetime.now():
            self.Date_HP_Next_Cmd.pack_forget()

        strDateNextSQL = self.convert_SQL_date(dtDateNext)
        strDateCurrSQL = self.convert_SQL_date(dtDate)
        self.run_HP(strDateCurrSQL, strDateNextSQL, True)

    def create_master_window(self, dictInstructions):
        self.RootWin.wm_title("HEATSET: Home Energy Management System")
        lngScreenWidth = dictInstructions['General_Inputs']['Screen_Width']
        lngScreenHeight = dictInstructions['General_Inputs']['Screen_Height']
        self.RootWin.geometry('%dx%d+%d+%d' % (lngScreenWidth, lngScreenHeight, 0, 0))

        # Create TABS
        self.TAB_CONTROL = ttk.Notebook(self.RootWin)
        if dictInstructions['User_Inputs']['Solar_Thermal'] == True:
            self.Solar_Tab = ttk.Frame(self.TAB_CONTROL)
            self.TAB_CONTROL.add(self.Solar_Tab, text='SolarThermal')
            self.populate_solar_tab(dictInstructions)

        if dictInstructions['User_Inputs']['Heat_Pump'] == True:
            self.HP_Tab = ttk.Frame(self.TAB_CONTROL)
            self.TAB_CONTROL.add(self.HP_Tab, text='HeatPump')
            self.populate_HP_tab(dictInstructions)

        if dictInstructions['User_Inputs']['PV'] == True:
            self.PV_Tab = ttk.Frame(self.TAB_CONTROL)
            self.TAB_CONTROL.add(self.PV_Tab, text='PV')
            self.populate_PV_tab(dictInstructions)

        if dictInstructions['User_Inputs']['Battery'] == True:
            self.BAT_Tab = ttk.Frame(self.TAB_CONTROL)
            self.TAB_CONTROL.add(self.BAT_Tab, text='Battery')
            self.populate_BAT_tab(dictInstructions)

        if dictInstructions['User_Inputs']['Zone'] == True:
            self.ZONE_Tab = ttk.Frame(self.TAB_CONTROL)
            self.TAB_CONTROL.add(self.ZONE_Tab, text='Zones')
            self.populate_ZONE_tab(dictInstructions)

        self.TAB_CONTROL.pack(expand=1, fill="both")
        self.GUI_Created = True
        self.time_created = dt.datetime.now()

    def populate_solar_tab(self, dictInstructions):
        #CREATE KEY FORMS WITHIN TAB
        self.frmSolarLogo = tk.Frame(self.Solar_Tab, pady=5, padx=5, highlightbackground="black",
                                     highlightcolor="black", highlightthickness=1)
        #self.frmSolarLogo.bind('<Button>', cmd_lightUp)
        self.frmSolarLogo.pack()
        self.frmSolarLogo.place(y=dictInstructions['General_Inputs']['Logo_y'],
                                x=dictInstructions['General_Inputs']['Logo_x'],
                                height=dictInstructions['General_Inputs']['Logo_height'],
                                width=dictInstructions['General_Inputs']['Logo_width'])

        self.frmSolarSensors = tk.Frame(self.Solar_Tab, pady=5, padx=5, highlightbackground="black",
                                        highlightcolor="black", highlightthickness=1)
        #frmSensors.bind('<Button>', cmd_lightUp)
        self.frmSolarSensors.pack()
        self.frmSolarSensors.place(y=dictInstructions['Solar_Inputs']['GUI_params']['Sensor_Section']['Sensor_y'],
                                   x=dictInstructions['Solar_Inputs']['GUI_params']['Sensor_Section']['Sensor_x'],
                                   height=dictInstructions['Solar_Inputs']['GUI_params']['Sensor_Section'][
                                       'SensorFm_height'],
                                   width=dictInstructions['Solar_Inputs']['GUI_params']['Sensor_Section'][
                                       'SensorFm_width'])

        self.frmSolarSYS = tk.Frame(self.Solar_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                    highlightthickness=1)
        #frmSYS.bind('<Button>',cmd_lightUp)
        self.frmSolarSYS.pack()
        self.frmSolarSYS.place(y=dictInstructions['Solar_Inputs']['GUI_params']['System_Section']['SYS_y'],
                               x=dictInstructions['Solar_Inputs']['GUI_params']['System_Section']['SYS_x'],
                               height=dictInstructions['Solar_Inputs']['GUI_params']['System_Section']['SYSFm_height'],
                               width=dictInstructions['Solar_Inputs']['GUI_params']['System_Section']['SYSFm_width'])

        self.frmSolarGraph = tk.Frame(self.Solar_Tab, pady=5, padx=5, highlightbackground="black",
                                      highlightcolor="black", highlightthickness=1)
        #frmSolarGraph.bind('<Button>',cmd_lightUp)
        self.frmSolarGraph.pack()

        self.frmSolarGraph.place(y=dictInstructions['Solar_Inputs']['GUI_params']['Graph_Section']['Graph_y'],
                                 x=dictInstructions['Solar_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                                 height=dictInstructions['Solar_Inputs']['GUI_params']['Graph_Section'][
                                     'GraphFm_height'],
                                 width=dictInstructions['Solar_Inputs']['GUI_params']['Graph_Section']['GraphFm_width'])

        #Date backward button
        self.frmSolarGraphButton = tk.Frame(self.Solar_Tab, pady=5, padx=5, highlightbackground="black",
                                            highlightcolor="black", highlightthickness=1)
        self.frmSolarGraphButton.pack()

        self.frmSolarGraphButton.place(y=dictInstructions['Solar_Inputs']['GUI_params']['Graph_Section']['Graph_y'] -
                                         dictInstructions['General_Inputs']['Graph_button_height'],
                                       x=dictInstructions['Solar_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                                       height= dictInstructions['General_Inputs']['Graph_button_height'],
                                       width=dictInstructions['Solar_Inputs']['GUI_params']['Graph_Section'][
                                           'GraphFm_width'])

        self.Date_Solar_Back_Cmd = tk.Button(self.frmSolarGraphButton,
                                       text="<",
                                       font=(dictInstructions['General_Inputs']['Font'],
                                             dictInstructions['General_Inputs']['Font_size']),
                                       command=self.previous_solar)
        self.Date_Solar_Back_Cmd.place(y=1,
                                 x=10,
                                 height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                 width=20 * dictInstructions['General_Inputs']['Width_ADJ'])

        self.Date_Solar_Next_Cmd = tk.Button(self.frmSolarGraphButton,
                                       text=">",
                                       font=(dictInstructions['General_Inputs']['Font'],
                                             dictInstructions['General_Inputs']['Font_size']),
                                       command=self.next_solar)
        self.Date_Solar_Next_Cmd.place(y=1,
                                 x=dictInstructions['Solar_Inputs']['GUI_params']['Graph_Section'][
                                           'GraphFm_width'] - 40,
                                 height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                 width=20 * dictInstructions['General_Inputs']['Width_ADJ'])
        self.Date_Solar_Next_Cmd.pack_forget()

        self.Date_Solar_Reset_Cmd = tk.Button(self.frmSolarGraphButton,
                                       text="TODAY",
                                       font=(dictInstructions['General_Inputs']['Font'],
                                             dictInstructions['General_Inputs']['Font_size']),
                                       command=self.reset_solar)
        self.Date_Solar_Reset_Cmd.place(y=1,
                                 x=dictInstructions['Solar_Inputs']['GUI_params']['Graph_Section'][
                                           'GraphFm_width']/2 - 40,
                                 height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                 width=50 * dictInstructions['General_Inputs']['Width_ADJ'])

        # Place HeatSet Logo
        strImageLoc = str(dictInstructions['Solar_Inputs']['Defaults']['Logo'])
        self.tkSolarImage = ImageTk.PhotoImage(Image.open(strImageLoc))
        self.lblSolarImgLogo = tk.Label(self.frmSolarLogo, image=self.tkSolarImage)
        #lblLogo.bind('<Button>',cmd_lightUp)
        self.lblSolarImgLogo.pack(side="bottom", fill="both", expand="yes")
        self.lblSolarImgLogo.place(x=0, y=0)

        #Set up restart button
        lngFreeSapce = dictInstructions['General_Inputs']['Logo_width'] - 160  #Logo width
        lngRestartWidth = lngFreeSapce / 3

        self.btnSolarRestart = tk.Button(self.frmSolarLogo,
                                         text="RESTART",
                                         font=(dictInstructions['General_Inputs']['Font'],
                                               dictInstructions['General_Inputs']['Font_size']),
                                         command=self.restart_GUI)
        #btnRestart.bind('<Button>',cmd_lightUp)
        self.btnSolarRestart.place(y=dictInstructions['General_Inputs']['Logo_y'],
                                   x=dictInstructions['General_Inputs']['Logo_width'] - lngRestartWidth - 10,
                                   height=40 * dictInstructions['General_Inputs']['Height_ADJ'],
                                   width=lngRestartWidth)

        self.btnSolarQuit = tk.Button(self.frmSolarLogo,
                                      text="QUIT",
                                      font=(dictInstructions['General_Inputs']['Font'],
                                            dictInstructions['General_Inputs']['Font_size']),
                                      command=self.quit_GUI)
        #self.btnSolarQuit.bind('<Button>',cmd_lightUp)
        self.btnSolarQuit.place(y=dictInstructions['General_Inputs']['Logo_y'],
                                x=dictInstructions['General_Inputs']['Logo_width'] - lngRestartWidth * 2 - 10,
                                height=40 * dictInstructions['General_Inputs']['Height_ADJ'],
                                width=lngRestartWidth)

        # Sensor & SYS section relative measurements
        self.lstSolarSensOrderByID = dictInstructions['Solar_Inputs']['GUI_Sections'][0]
        self.lstSolarSysOrderByID = dictInstructions['Solar_Inputs']['GUI_Sections'][1]
        self.frmSolarSensorHeight = dictInstructions['Solar_Inputs']['GUI_params']['Sensor_Section']['SensorFm_height']
        self.frmSolarSensorsWidth = dictInstructions['Solar_Inputs']['GUI_params']['Sensor_Section']['SensorFm_width']
        self.frmSolarSYSWidth = dictInstructions['Solar_Inputs']['GUI_params']['System_Section']['SYSFm_width']
        self.frmSolarSYSHeight = dictInstructions['Solar_Inputs']['GUI_params']['System_Section']['SYSFm_height']

        SensCounter = 0
        SysCounter = 0
        for key in dictInstructions['Solar_Inputs']['GUI_Information']:
            for i in range(0, len(self.lstSolarSensOrderByID)):
                if dictInstructions['Solar_Inputs']['GUI_Information'][key]['ID'] == self.lstSolarSensOrderByID[i]:
                    if dictInstructions['Solar_Inputs']['GUI_Information'][key]['Include?'] == True:
                        SensCounter += 1
            for i in range(0, len(self.lstSolarSysOrderByID)):
                if dictInstructions['Solar_Inputs']['GUI_Information'][key]['ID'] == self.lstSolarSysOrderByID[i]:
                    if dictInstructions['Solar_Inputs']['GUI_Information'][key]['Include?'] == True:
                        SysCounter += 1

        self.dblSolarSensHeight = int((self.frmSolarSensorHeight - 10) / SensCounter)
        self.dblSolarSensWidthLBL = int((self.frmSolarSensorsWidth - 10) * 2 / 3)
        self.dblSolarSensWidthVal = int((self.frmSolarSensorsWidth - 10) * 1 / 3)
        self.dblSolarSYSWidthLBL = int((self.frmSolarSYSWidth - 10) * 1.5 / 3)
        self.dblSolarSYSWidthVal = int((self.frmSolarSYSWidth - 10) * 0.8 / 3)
        self.dblSolarSYSWidthCmd = int((self.frmSolarSYSWidth - 10) * 0.7 / 3)
        self.dblSolarSYSHeight = int((self.frmSolarSYSHeight - 10) / (
                    SysCounter + 3))  #Plus 3 as need last section to be free for final command buttons

        SensCounter = 0
        # Create sensor section labels and outputs and update global dictionary
        for i in range(0,
                       len(self.lstSolarSensOrderByID)):  #Loop through all of the global library lists as calibrated within System_Initialize
            boolContinue = False
            for key in dictInstructions['Solar_Inputs']['GUI_Information']:
                if boolContinue == True:
                    continue
                if dictInstructions['Solar_Inputs']['GUI_Information'][key]['ID'] == self.lstSolarSensOrderByID[
                    i]:  #if the ID of the library item
                    if dictInstructions['Solar_Inputs']['GUI_Information'][key]['Include?'] == True:
                        lblTitle = tk.Label(self.frmSolarSensors,
                                            text=dictInstructions['Solar_Inputs']['GUI_Information'][key]['GUI_Label'],
                                            font=(dictInstructions['General_Inputs']['Font'],
                                                  dictInstructions['General_Inputs']['Font_size']),
                                            anchor="w")  #This is the label that provides the description to the value
                        #lblTitle.bind('<Button>', cmd_lightUp)
                        lblTitle.place(y=(self.dblSolarSensHeight * SensCounter),
                                       x=5,
                                       height=self.dblSolarSensHeight,
                                       width=self.dblSolarSensWidthLBL)
                        lblVal = tk.Label(self.frmSolarSensors,
                                          text=dictInstructions['Solar_Inputs']['GUI_Information'][key]['GUI_Default'],
                                          font=(dictInstructions['General_Inputs']['Font'],
                                                dictInstructions['General_Inputs']['Font_size']),
                                          relief="sunken")
                        #lblVal.bind('<Button>', cmd_lightUp)
                        lblVal.place(y=(self.dblSolarSensHeight * SensCounter),
                                     x=self.dblSolarSensWidthLBL,
                                     height=self.dblSolarSensHeight,
                                     width=self.dblSolarSensWidthVal)
                        dictInstructions['Solar_Inputs']['GUI_Information'][key][
                            'GUI_Val'] = lblVal  # Local level insturctions
                        dictGlobalInstructions['Solar_Inputs']['GUI_Information'][key][
                            'GUI_Val'] = lblVal  # Module level instructions
                        boolContinue = True
                        SensCounter += 1
                        continue

        #Insert Gauge
        self.Solar_Gauge = cht_plt.GUI_gauge(dictInstructions['Solar_Inputs']['Gauge_params'], self.frmSolarSYS)

        #Insert Solar Graph
        self.Solar_Graph = cht_plt.GUI_graph(dictInstructions['Solar_Inputs']['Graph_params'], self.frmSolarGraph)

        if dictInstructions['User_Inputs']['Solar_Control'] == True:
            #Loop through all system buttons per list lstSolarSysOrderByID defined in System_Initialize
            for i in range(0,
                           len(self.lstSolarSysOrderByID)):  #The system_initialize allows the GUI to be calibrated as required
                for key in dictGlobalInstructions['Solar_Inputs'][
                    'GUI_Information']:  #Loop through each solar GUI dictionary
                    if dictInstructions['Solar_Inputs']['GUI_Information'][key][
                        'Include?'] == True:  #If the user has selected a non-pressurised system or no immersion heater in the tank then this adjusts for that
                        if dictGlobalInstructions['Solar_Inputs']['GUI_Information'][key]['ID'] == \
                                self.lstSolarSysOrderByID[i]:  #if the ID of the library item
                            cmdCnt = dictGlobalInstructions['Solar_Inputs']['GUI_Information'][key]['cmd_count']
                            for j in range(0, cmdCnt):
                                lbl = dictGlobalInstructions['Solar_Inputs']['GUI_Information'][key][
                                    'cmd_Val' + str(1 + j)]
                                lbl.config(command=dictGlobalInstructions['Solar_Inputs']['GUI_Information'][key][
                                    'cmd_def' + str(1 + j)])

    def populate_HP_tab(self, dictInstructions):
        #CREATE KEY FORMS WITHIN TAB
        self.frmHPLogo = tk.Frame(self.HP_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                  highlightthickness=1)
        #self.frmHPLogo.bind('<Button>', cmd_lightUp)
        self.frmHPLogo.pack()
        self.frmHPLogo.place(y=dictInstructions['General_Inputs']['Logo_y'],
                             x=dictInstructions['General_Inputs']['Logo_x'],
                             height=dictInstructions['General_Inputs']['Logo_height'],
                             width=dictInstructions['General_Inputs']['Logo_width'])

        self.frmHPSensors = tk.Frame(self.HP_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                     highlightthickness=1)
        #frmHPSensors.bind('<Button>', cmd_lightUp)
        self.frmHPSensors.pack()
        self.frmHPSensors.place(y=dictInstructions['HP_Inputs']['GUI_params']['Sensor_Section']['Sensor_y'],
                                x=dictInstructions['HP_Inputs']['GUI_params']['Sensor_Section']['Sensor_x'],
                                height=dictInstructions['HP_Inputs']['GUI_params']['Sensor_Section']['SensorFm_height'],
                                width=dictInstructions['HP_Inputs']['GUI_params']['Sensor_Section']['SensorFm_width'])

        if dictInstructions['User_Inputs']['Heat_Pump_Control'] == True:
            self.frmHPSYS = tk.Frame(self.HP_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                     highlightthickness=1)
            #frmSYS.bind('<Button>',cmd_lightUp)
            self.frmHPSYS.pack()
            self.frmHPSYS.place(y=dictInstructions['HP_Inputs']['GUI_params']['System_Section']['SYS_y'],
                                x=dictInstructions['HP_Inputs']['GUI_params']['System_Section']['SYS_x'],
                                height=dictInstructions['HP_Inputs']['GUI_params']['System_Section']['SYSFm_height'],
                                width=dictInstructions['HP_Inputs']['GUI_params']['System_Section']['SYSFm_width'])

        self.frmHPGraph = tk.Frame(self.HP_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                   highlightthickness=1)
        #frmSolarGraph.bind('<Button>',cmd_lightUp)
        self.frmHPGraph.pack()
        self.frmHPGraph.place(y=dictInstructions['HP_Inputs']['GUI_params']['Graph_Section']['Graph_y'],
                              x=dictInstructions['HP_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                              height=dictInstructions['HP_Inputs']['GUI_params']['Graph_Section']['GraphFm_height'],
                              width=dictInstructions['HP_Inputs']['GUI_params']['Graph_Section']['GraphFm_width'])

        #Date backward button
        self.frmHPGraphButton = tk.Frame(self.HP_Tab, pady=5, padx=5, highlightbackground="black",
                                            highlightcolor="black", highlightthickness=1)
        self.frmHPGraphButton.pack()

        self.frmHPGraphButton.place(y=dictInstructions['HP_Inputs']['GUI_params']['Graph_Section']['Graph_y'] -
                                         dictInstructions['General_Inputs']['Graph_button_height'],
                                       x=dictInstructions['HP_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                                       height= dictInstructions['General_Inputs']['Graph_button_height'],
                                       width=dictInstructions['HP_Inputs']['GUI_params']['Graph_Section'][
                                           'GraphFm_width'])

        self.Date_HP_Back_Cmd = tk.Button(self.frmHPGraphButton,
                                       text="<",
                                       font=(dictInstructions['General_Inputs']['Font'],
                                             dictInstructions['General_Inputs']['Font_size']),
                                       command=self.previous_HP)
        self.Date_HP_Back_Cmd.place(y=1,
                                 x=10,
                                 height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                 width=20 * dictInstructions['General_Inputs']['Width_ADJ'])

        self.Date_HP_Next_Cmd = tk.Button(self.frmHPGraphButton,
                                       text=">",
                                       font=(dictInstructions['General_Inputs']['Font'],
                                             dictInstructions['General_Inputs']['Font_size']),
                                       command=self.next_HP)
        self.Date_HP_Next_Cmd.place(y=1,
                                 x=dictInstructions['HP_Inputs']['GUI_params']['Graph_Section'][
                                           'GraphFm_width'] - 40,
                                 height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                 width=20 * dictInstructions['General_Inputs']['Width_ADJ'])
        self.Date_HP_Next_Cmd.pack_forget()

        self.Date_HP_Reset_Cmd = tk.Button(self.frmHPGraphButton,
                                       text="TODAY",
                                       font=(dictInstructions['General_Inputs']['Font'],
                                             dictInstructions['General_Inputs']['Font_size']),
                                       command=self.reset_HP)
        self.Date_HP_Reset_Cmd.place(y=1,
                                 x=dictInstructions['HP_Inputs']['GUI_params']['Graph_Section'][
                                           'GraphFm_width']/2 - 70,
                                 height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                 width=70 * dictInstructions['General_Inputs']['Width_ADJ'])

        self.HP_chg_graph_cmd = tk.Button(self.frmHPGraphButton,
                                       text="GRAPH 1",
                                       font=(dictInstructions['General_Inputs']['Font'],
                                             dictInstructions['General_Inputs']['Font_size']),
                                       command=self.change_HP_chart)
        self.HP_chg_graph_cmd.place(y=1,
                                 x=dictInstructions['HP_Inputs']['GUI_params']['Graph_Section'][
                                           'GraphFm_width']/2 + 20,
                                 height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                 width=70 * dictInstructions['General_Inputs']['Width_ADJ'])

        self.frmHPGauge = tk.Frame(self.HP_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                   highlightthickness=1)
        #frmSolarGraph.bind('<Button>',cmd_lightUp)
        self.frmHPGauge.pack()
        self.frmHPGauge.place(y=dictInstructions['HP_Inputs']['GUI_params']['Gauge_Section']['Gauge_y'],
                              x=dictInstructions['HP_Inputs']['GUI_params']['Gauge_Section']['Gauge_x'],
                              height=dictInstructions['HP_Inputs']['GUI_params']['Gauge_Section']['Fm_height'],
                              width=dictInstructions['HP_Inputs']['GUI_params']['Gauge_Section']['Fm_width'])

        # Place HeatSet Logo
        strImageLoc = str(dictInstructions['HP_Inputs']['Defaults']['Logo'])
        self.tkHPImage = ImageTk.PhotoImage(Image.open(strImageLoc))
        self.lblHPImgLogo = tk.Label(self.frmHPLogo, image=self.tkHPImage)
        #lblLogo.bind('<Button>',cmd_lightUp)
        self.lblHPImgLogo.pack(side="bottom", fill="both", expand="yes")
        self.lblHPImgLogo.place(x=0, y=0)

        #Set up restart button
        self.btnHPRestart = tk.Button(self.frmHPLogo,
                                      text="RESTART",
                                      font=(dictInstructions['General_Inputs']['Font'],
                                            dictInstructions['General_Inputs']['Font_size']),
                                      command=self.restart_GUI)
        #btnRestart.bind('<Button>',cmd_lightUp)
        lngHPFreeSapce = dictInstructions['General_Inputs']['Logo_width'] - 160  #Logo width
        lngHPRestartWidth = lngHPFreeSapce / 3
        self.btnHPRestart.place(y=dictInstructions['General_Inputs']['Logo_y'],
                                x=dictInstructions['General_Inputs']['Logo_width'] - lngHPRestartWidth - 10,
                                height=40 * dictInstructions['General_Inputs']['Height_ADJ'],
                                width=lngHPRestartWidth)

        self.btnHPQuit = tk.Button(self.frmHPLogo,
                                   text="QUIT",
                                   font=(dictInstructions['General_Inputs']['Font'],
                                         dictInstructions['General_Inputs']['Font_size']),
                                   command=self.quit_GUI)
        #self.btnSolarQuit.bind('<Button>',cmd_lightUp)
        self.btnHPQuit.place(y=dictInstructions['General_Inputs']['Logo_y'],
                             x=dictInstructions['General_Inputs']['Logo_width'] - lngHPRestartWidth * 2 - 10,
                             height=40 * dictInstructions['General_Inputs']['Height_ADJ'],
                             width=lngHPRestartWidth)

        # Sensor & SYS section relative measurements
        self.lstHPSensOrderByID = dictInstructions['HP_Inputs']['GUI_Sections'][0]
        self.lstHPSysOrderByID = dictInstructions['HP_Inputs']['GUI_Sections'][1]
        self.frmHPSensorHeight = dictInstructions['HP_Inputs']['GUI_params']['Sensor_Section']['SensorFm_height']
        self.frmHPSensorsWidth = dictInstructions['HP_Inputs']['GUI_params']['Sensor_Section']['SensorFm_width']
        self.frmHPSYSWidth = dictInstructions['HP_Inputs']['GUI_params']['System_Section']['SYSFm_width']
        self.frmHPSYSHeight = dictInstructions['HP_Inputs']['GUI_params']['System_Section']['SYSFm_height']

        SensCounter = 0
        SysCounter = 0
        for key in dictInstructions['HP_Inputs']['GUI_Information']:
            for i in range(0, len(self.lstHPSensOrderByID)):
                if dictInstructions['HP_Inputs']['GUI_Information'][key]['ID'] == self.lstHPSensOrderByID[i]:
                    if dictInstructions['HP_Inputs']['GUI_Information'][key]['Include?'] == True:
                        SensCounter += 1
            for i in range(0, len(self.lstHPSysOrderByID)):
                if dictInstructions['HP_Inputs']['GUI_Information'][key]['ID'] == self.lstHPSysOrderByID[i]:
                    if dictInstructions['HP_Inputs']['GUI_Information'][key]['Include?'] == True:
                        SysCounter += 1

        self.dblHPSensHeight = int((self.frmHPSensorHeight - 10) / SensCounter)
        self.dblHPSensWidthLBL = int((self.frmHPSensorsWidth - 10) * 2 / 3)
        self.dblHPSensWidthVal = int((self.frmHPSensorsWidth - 10) * 1 / 3)
        self.dblHPSYSWidthLBL = int((self.frmHPSYSWidth - 10) * 1.5 / 3)
        self.dblHPSYSWidthVal = int((self.frmHPSYSWidth - 10) * 0.8 / 3)
        self.dblHPSYSWidthCmd = int((self.frmHPSYSWidth - 10) * 0.7 / 3)
        self.dblHPSYSHeight = int((self.frmHPSYSHeight - 10) / SysCounter)

        SensCounter = 0
        # Create sensor section labels and outputs and update global dictionary
        for i in range(0,
                       len(self.lstHPSensOrderByID)):  #Loop through all of the global library lists as calibrated within System_Initialize
            boolContinue = False
            for key in dictInstructions['HP_Inputs']['GUI_Information']:
                if boolContinue == True:
                    continue
                if dictInstructions['HP_Inputs']['GUI_Information'][key]['ID'] == self.lstHPSensOrderByID[
                    i]:  #if the ID of the library item
                    if dictInstructions['HP_Inputs']['GUI_Information'][key]['Include?'] == True:
                        lblTitle = tk.Label(self.frmHPSensors,
                                            text=dictInstructions['HP_Inputs']['GUI_Information'][key]['GUI_Label'],
                                            font=(dictInstructions['General_Inputs']['Font'],
                                                  dictInstructions['General_Inputs']['Font_size']),
                                            anchor="w")  #This is the label that provides the description to the value
                        #lblTitle.bind('<Button>', cmd_lightUp)
                        lblTitle.place(y=(self.dblHPSensHeight * SensCounter),
                                       x=5,
                                       height=self.dblHPSensHeight,
                                       width=self.dblHPSensWidthLBL)
                        lblVal = tk.Label(self.frmHPSensors,
                                          text=dictInstructions['HP_Inputs']['GUI_Information'][key]['GUI_Default'],
                                          font=(dictInstructions['General_Inputs']['Font'],
                                                dictInstructions['General_Inputs']['Font_size']),
                                          relief="sunken")
                        #lblVal.bind('<Button>', cmd_lightUp)
                        lblVal.place(y=(self.dblHPSensHeight * SensCounter),
                                     x=self.dblHPSensWidthLBL,
                                     height=self.dblHPSensHeight,
                                     width=self.dblHPSensWidthVal)
                        dictInstructions['HP_Inputs']['GUI_Information'][key][
                            'GUI_Val'] = lblVal  # Local level insturctions
                        dictGlobalInstructions['HP_Inputs']['GUI_Information'][key][
                            'GUI_Val'] = lblVal  # Module level instructions
                        boolContinue = True
                        SensCounter += 1
                        continue

        if dictInstructions['User_Inputs']['Heat_Pump_Control'] == True:
            SysCounter = 0
            # Create SYS section labels and outputs and update global dictionary
            for i in range(0, len(self.lstHPSysOrderByID)):  #Loop through each library within the respective list
                boolContinue = False
                for key in dictInstructions['HP_Inputs'][
                    'GUI_Information']:  #The system_initialize allows the GUI to be calibrated as required
                    if dictInstructions['HP_Inputs']['GUI_Information'][key]['ID'] == self.lstHPSysOrderByID[
                        i]:  #if the ID of the library item
                        if dictInstructions['HP_Inputs']['GUI_Information'][key]['Include?'] == True:
                            lblTitle = tk.Label(self.frmHPSYS,
                                                text=dictInstructions['HP_Inputs']['GUI_Information'][key]['GUI_Label'],
                                                font=(dictInstructions['General_Inputs']['Font'],
                                                      dictInstructions['General_Inputs']['Font_size']),
                                                anchor="w")  #This is the label that provides the description to the value
                            lblTitle.place(y=(self.dblHPSYSHeight * SysCounter),
                                           x=5,
                                           height=self.dblHPSYSHeight,
                                           width=self.dblHPSYSWidthLBL)
                            #lblTitle.bind('<Button>', cmd_lightUp)
                            lblVal = tk.Label(self.frmHPSYS,
                                              text=dictInstructions['HP_Inputs']['GUI_Information'][key]['GUI_Default'],
                                              font=(dictInstructions['General_Inputs']['Font'],
                                                    dictInstructions['General_Inputs']['Font_size']),
                                              relief="sunken")
                            #lblVal.bind('<Button>', cmd_lightUp)
                            lblVal.place(y=(self.dblHPSYSHeight * SysCounter),
                                         x=self.dblHPSYSWidthLBL,
                                         height=self.dblHPSYSHeight,
                                         width=self.dblHPSYSWidthVal)
                            dictInstructions['HP_Inputs']['GUI_Information'][key][
                                'GUI_Val'] = lblVal  # Local level insturctions
                            dictGlobalInstructions['HP_Inputs']['GUI_Information'][key][
                                'GUI_Val'] = lblVal  # Module level instructions
                            cmdCnt = dictInstructions['HP_Inputs']['GUI_Information'][key]['cmd_count']
                            widthTemp = int(self.dblHPSYSWidthCmd / cmdCnt)
                            if cmdCnt == 1:
                                txtCmd0 = "CHANGE"
                                lstTxt = [txtCmd0]
                            else:
                                txtCmd0 = "\N{black medium up-pointing triangle}"  #Up symbol
                                txtCmd1 = "\N{black medium down-pointing triangle}"  #down subol
                                lstTxt = [txtCmd0, txtCmd1]
                            for j in range(0, cmdCnt):
                                lblCmd = tk.Button(self.frmHPSYS,
                                                   text=lstTxt[j],
                                                   font=(dictInstructions['General_Inputs']['Font'],
                                                         dictInstructions['General_Inputs']['Font_size']),
                                                   command=dictInstructions['HP_Inputs']['GUI_Information'][key][
                                                       'cmd_def' + str(j + 1)])
                                lblCmd.place(y=(self.dblHPSYSHeight * SysCounter),
                                             x=self.dblHPSYSWidthLBL + self.dblHPSYSWidthVal + widthTemp * j,
                                             height=self.dblHPSYSHeight, width=widthTemp)
                                dictInstructions['HP_Inputs']['GUI_Information'][key]['cmd_Val' + str(j + 1)] = lblCmd
                            boolContinue = True
                            SysCounter += 1
                            continue

            #Update_Commands in global instructions
            dictGlobalInstructions['HP_Inputs']['GUI_Information']['HP_On_Off'][
                'cmd_def1'] = HP_on_off  #global dictionary update

        #Insert HP Graph and gauge
        self.HP_Graph = cht_plt.GUI_graph(dictInstructions['HP_Inputs']['Graph1_params'], self.frmHPGraph)
        self.HP_Gauge = cht_plt.GUI_gauge(dictInstructions['HP_Inputs']['Gauge_params'], self.frmHPGauge)

        if dictInstructions['User_Inputs']['Heat_Pump_Control'] == True:
            #Loop through all system buttons per list lstHPSysOrderByID defined in System_Initialize
            for i in range(0,
                           len(self.lstHPSysOrderByID)):  #The system_initialize allows the GUI to be calibrated as required
                for key in dictGlobalInstructions['HP_Inputs'][
                    'GUI_Information']:  #Loop through each solar GUI dictionary
                    if dictInstructions['HP_Inputs']['GUI_Information'][key][
                        'Include?'] == True:  #If the user has selected a non-pressurised system or no immersion heater in the tank then this adjusts for that
                        if dictGlobalInstructions['HP_Inputs']['GUI_Information'][key]['ID'] == self.lstHPSysOrderByID[
                            i]:  #if the ID of the library item
                            cmdCnt = dictGlobalInstructions['HP_Inputs']['GUI_Information'][key]['cmd_count']
                            for j in range(0, cmdCnt):
                                lbl = dictGlobalInstructions['HP_Inputs']['GUI_Information'][key][
                                    'cmd_Val' + str(1 + j)]
                                lbl.config(command=dictGlobalInstructions['HP_Inputs']['GUI_Information'][key][
                                    'cmd_def' + str(1 + j)])

    def populate_PV_tab(self, dictInstructions):
        #CREATE KEY FORMS WITHIN TAB
        self.frmPVLogo = tk.Frame(self.PV_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                  highlightthickness=1)
        #self.frmPVLogo.bind('<Button>', cmd_lightUp)
        self.frmPVLogo.pack()
        self.frmPVLogo.place(y=dictInstructions['General_Inputs']['Logo_y'],
                             x=dictInstructions['General_Inputs']['Logo_x'],
                             height=dictInstructions['General_Inputs']['Logo_height'],
                             width=dictInstructions['General_Inputs']['Logo_width'])

        self.frmPVSensors = tk.Frame(self.PV_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                     highlightthickness=1)
        #frmPVSensors.bind('<Button>', cmd_lightUp)
        self.frmPVSensors.pack()
        self.frmPVSensors.place(y=dictInstructions['PV_Inputs']['GUI_params']['Sensor_Section']['Sensor_y'],
                                x=dictInstructions['PV_Inputs']['GUI_params']['Sensor_Section']['Sensor_x'],
                                height=dictInstructions['PV_Inputs']['GUI_params']['Sensor_Section']['SensorFm_height'],
                                width=dictInstructions['PV_Inputs']['GUI_params']['Sensor_Section']['SensorFm_width'])

        self.frmPVGraph = tk.Frame(self.PV_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                   highlightthickness=1)
        #frmSolarGraph.bind('<Button>',cmd_lightUp)
        self.frmPVGraph.pack()
        self.frmPVGraph.place(y=dictInstructions['PV_Inputs']['GUI_params']['Graph_Section']['Graph_y'],
                              x=dictInstructions['PV_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                              height=dictInstructions['PV_Inputs']['GUI_params']['Graph_Section']['GraphFm_height'],
                              width=dictInstructions['PV_Inputs']['GUI_params']['Graph_Section']['GraphFm_width'])

        self.frmPVGauge = tk.Frame(self.PV_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                   highlightthickness=1)
        #frmSolarGraph.bind('<Button>',cmd_lightUp)
        self.frmPVGauge.pack()
        self.frmPVGauge.place(y=dictInstructions['PV_Inputs']['GUI_params']['Gauge_Section']['Gauge_y'],
                              x=dictInstructions['PV_Inputs']['GUI_params']['Gauge_Section']['Gauge_x'],
                              height=dictInstructions['PV_Inputs']['GUI_params']['Gauge_Section']['Fm_height'],
                              width=dictInstructions['PV_Inputs']['GUI_params']['Gauge_Section']['Fm_width'])

        # Place HeatSet Logo
        strImageLoc = str(dictInstructions['PV_Inputs']['Defaults']['Logo'])
        self.tkPVImage = ImageTk.PhotoImage(Image.open(strImageLoc))
        self.lblPVImgLogo = tk.Label(self.frmPVLogo, image=self.tkPVImage)
        #lblLogo.bind('<Button>',cmd_lightUp)
        self.lblPVImgLogo.pack(side="bottom", fill="both", expand="yes")
        self.lblPVImgLogo.place(x=0, y=0)

        #Set up restart button
        self.btnPVRestart = tk.Button(self.frmPVLogo,
                                      text="RESTART",
                                      font=(dictInstructions['General_Inputs']['Font'],
                                            dictInstructions['General_Inputs']['Font_size']),
                                      command=self.restart_GUI)
        #btnRestart.bind('<Button>',cmd_lightUp)
        lngPVFreeSapce = dictInstructions['General_Inputs']['Logo_width'] - 160  #Logo width
        lngPVRestartWidth = lngPVFreeSapce / 3
        self.btnPVRestart.place(y=dictInstructions['General_Inputs']['Logo_y'],
                                x=dictInstructions['General_Inputs']['Logo_width'] - lngPVRestartWidth - 10,
                                height=40 * dictInstructions['General_Inputs']['Height_ADJ'],
                                width=lngPVRestartWidth)

        self.btnPVQuit = tk.Button(self.frmPVLogo,
                                   text="QUIT",
                                   font=(dictInstructions['General_Inputs']['Font'],
                                         dictInstructions['General_Inputs']['Font_size']),
                                   command=self.quit_GUI)
        #self.btnSolarQuit.bind('<Button>',cmd_lightUp)
        self.btnPVQuit.place(y=dictInstructions['General_Inputs']['Logo_y'],
                             x=dictInstructions['General_Inputs']['Logo_width'] - lngPVRestartWidth * 2 - 10,
                             height=40 * dictInstructions['General_Inputs']['Height_ADJ'],
                             width=lngPVRestartWidth)

        # Sensor  section relative measurements
        self.lstPVSensOrderByID = dictInstructions['PV_Inputs']['GUI_Sections'][0]
        self.frmPVSensorHeight = dictInstructions['PV_Inputs']['GUI_params']['Sensor_Section']['SensorFm_height']
        self.frmPVSensorsWidth = dictInstructions['PV_Inputs']['GUI_params']['Sensor_Section']['SensorFm_width']

        # Date backward button
        self.frmPVGraphButton = tk.Frame(self.PV_Tab, pady=5, padx=5, highlightbackground="black",
                                            highlightcolor="black", highlightthickness=1)
        self.frmPVGraphButton.pack()

        self.frmPVGraphButton.place(y=dictInstructions['PV_Inputs']['GUI_params']['Graph_Section']['Graph_y'] -
                                         dictInstructions['General_Inputs']['Graph_button_height'],
                                       x=dictInstructions['PV_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                                       height=dictInstructions['General_Inputs']['Graph_button_height'],
                                       width=dictInstructions['PV_Inputs']['GUI_params']['Graph_Section'][
                                           'GraphFm_width'])

        self.Date_PV_Back_Cmd = tk.Button(self.frmPVGraphButton,
                                             text="<",
                                             font=(dictInstructions['General_Inputs']['Font'],
                                                   dictInstructions['General_Inputs']['Font_size']),
                                             command=self.previous_PV)
        self.Date_PV_Back_Cmd.place(y=1,
                                       x=10,
                                       height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                       width=20 * dictInstructions['General_Inputs']['Width_ADJ'])

        self.Date_PV_Next_Cmd = tk.Button(self.frmPVGraphButton,
                                             text=">",
                                             font=(dictInstructions['General_Inputs']['Font'],
                                                   dictInstructions['General_Inputs']['Font_size']),
                                             command=self.next_PV)
        self.Date_PV_Next_Cmd.place(y=1,
                                       x=dictInstructions['PV_Inputs']['GUI_params']['Graph_Section'][
                                             'GraphFm_width'] - 40,
                                       height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                       width=20 * dictInstructions['General_Inputs']['Width_ADJ'])
        self.Date_PV_Next_Cmd.pack_forget()

        self.Date_PV_Reset_Cmd = tk.Button(self.frmPVGraphButton,
                                              text="TODAY",
                                              font=(dictInstructions['General_Inputs']['Font'],
                                                    dictInstructions['General_Inputs']['Font_size']),
                                              command=self.reset_PV)
        self.Date_PV_Reset_Cmd.place(y=1,
                                        x=dictInstructions['PV_Inputs']['GUI_params']['Graph_Section'][
                                              'GraphFm_width'] / 2 - 40,
                                        height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                        width=50 * dictInstructions['General_Inputs']['Width_ADJ'])

        SensCounter = 0
        for key in dictInstructions['PV_Inputs']['GUI_Information']:
            for i in range(0, len(self.lstPVSensOrderByID)):
                if dictInstructions['PV_Inputs']['GUI_Information'][key]['ID'] == self.lstPVSensOrderByID[i]:
                    if dictInstructions['PV_Inputs']['GUI_Information'][key]['Include?'] == True:
                        SensCounter += 1

        self.dblPVSensHeight = int((self.frmPVSensorHeight - 10) / SensCounter)
        self.dblPVSensWidthLBL = int((self.frmPVSensorsWidth - 10) * 2 / 3)
        self.dblPVSensWidthVal = int((self.frmPVSensorsWidth - 10) * 1 / 3)

        SensCounter = 0
        # Create sensor section labels and outputs and update global dictionary
        for i in range(0,
                       len(self.lstPVSensOrderByID)):  #Loop through all of the global library lists as calibrated within System_Initialize
            boolContinue = False
            for key in dictInstructions['PV_Inputs']['GUI_Information']:
                if boolContinue == True:
                    continue
                if dictInstructions['PV_Inputs']['GUI_Information'][key]['ID'] == self.lstPVSensOrderByID[
                    i]:  #if the ID of the library item
                    if dictInstructions['PV_Inputs']['GUI_Information'][key]['Include?'] == True:
                        lblTitle = tk.Label(self.frmPVSensors,
                                            text=dictInstructions['PV_Inputs']['GUI_Information'][key]['GUI_Label'],
                                            font=(dictInstructions['General_Inputs']['Font'],
                                                  dictInstructions['General_Inputs']['Font_size']),
                                            anchor="w")  #This is the label that provides the description to the value
                        #lblTitle.bind('<Button>', cmd_lightUp)
                        lblTitle.place(y=(self.dblPVSensHeight * SensCounter),
                                       x=5,
                                       height=self.dblPVSensHeight,
                                       width=self.dblPVSensWidthLBL)
                        lblVal = tk.Label(self.frmPVSensors,
                                          text=dictInstructions['PV_Inputs']['GUI_Information'][key]['GUI_Default'],
                                          font=(dictInstructions['General_Inputs']['Font'],
                                                dictInstructions['General_Inputs']['Font_size']),
                                          relief="sunken")
                        #lblVal.bind('<Button>', cmd_lightUp)
                        lblVal.place(y=(self.dblPVSensHeight * SensCounter),
                                     x=self.dblPVSensWidthLBL,
                                     height=self.dblPVSensHeight,
                                     width=self.dblPVSensWidthVal)
                        dictInstructions['PV_Inputs']['GUI_Information'][key][
                            'GUI_Val'] = lblVal  # Local level insturctions
                        dictGlobalInstructions['PV_Inputs']['GUI_Information'][key][
                            'GUI_Val'] = lblVal  # Module level instructions
                        boolContinue = True
                        SensCounter += 1
                        continue

        #Insert PV Graph and gauge
        self.PV_Graph = cht_plt.GUI_graph(dictInstructions['PV_Inputs']['Graph_params'], self.frmPVGraph)
        self.PV_Gauge = cht_plt.GUI_gauge(dictInstructions['PV_Inputs']['Gauge_params'], self.frmPVGauge)

    def populate_BAT_tab(self, dictInstructions):
        #CREATE KEY FORMS WITHIN TAB
        self.frmBATLogo = tk.Frame(self.BAT_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                   highlightthickness=1)
        #self.frmBATLogo.bind('<Button>', cmd_lightUp)
        self.frmBATLogo.pack()
        self.frmBATLogo.place(y=dictInstructions['General_Inputs']['Logo_y'],
                              x=dictInstructions['General_Inputs']['Logo_x'],
                              height=dictInstructions['General_Inputs']['Logo_height'],
                              width=dictInstructions['General_Inputs']['Logo_width'])

        self.frmBATSensors = tk.Frame(self.BAT_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                      highlightthickness=1)
        #frmBATSensors.bind('<Button>', cmd_lightUp)
        self.frmBATSensors.pack()
        self.frmBATSensors.place(y=dictInstructions['BAT_Inputs']['GUI_params']['Sensor_Section']['Sensor_y'],
                                 x=dictInstructions['BAT_Inputs']['GUI_params']['Sensor_Section']['Sensor_x'],
                                 height=dictInstructions['BAT_Inputs']['GUI_params']['Sensor_Section'][
                                     'SensorFm_height'],
                                 width=dictInstructions['BAT_Inputs']['GUI_params']['Sensor_Section']['SensorFm_width'])

        self.frmBATGraph = tk.Frame(self.BAT_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                    highlightthickness=1)
        #frmSolarGraph.bind('<Button>',cmd_lightUp)
        self.frmBATGraph.pack()
        self.frmBATGraph.place(y=dictInstructions['BAT_Inputs']['GUI_params']['Graph_Section']['Graph_y'],
                               x=dictInstructions['BAT_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                               height=dictInstructions['BAT_Inputs']['GUI_params']['Graph_Section']['GraphFm_height'],
                               width=dictInstructions['BAT_Inputs']['GUI_params']['Graph_Section']['GraphFm_width'])

        self.frmBATGauge = tk.Frame(self.BAT_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                    highlightthickness=1)
        #frmSolarGraph.bind('<Button>',cmd_lightUp)
        self.frmBATGauge.pack()
        self.frmBATGauge.place(y=dictInstructions['BAT_Inputs']['GUI_params']['Gauge_Section']['Gauge_y'],
                               x=dictInstructions['BAT_Inputs']['GUI_params']['Gauge_Section']['Gauge_x'],
                               height=dictInstructions['BAT_Inputs']['GUI_params']['Gauge_Section']['Fm_height'],
                               width=dictInstructions['BAT_Inputs']['GUI_params']['Gauge_Section']['Fm_width'])

        # Place HeatSet Logo
        strImageLoc = str(dictInstructions['BAT_Inputs']['Defaults']['Logo'])
        self.tkBATImage = ImageTk.PhotoImage(Image.open(strImageLoc))
        self.lblBATImgLogo = tk.Label(self.frmBATLogo, image=self.tkBATImage)
        #lblLogo.bind('<Button>',cmd_lightUp)
        self.lblBATImgLogo.pack(side="bottom", fill="both", expand="yes")
        self.lblBATImgLogo.place(x=0, y=0)

        #Set up restart button
        self.btnBATRestart = tk.Button(self.frmBATLogo,
                                       text="RESTART",
                                       font=(dictInstructions['General_Inputs']['Font'],
                                             dictInstructions['General_Inputs']['Font_size']),
                                       command=self.restart_GUI)
        #btnRestart.bind('<Button>',cmd_lightUp)
        lngBATFreeSapce = dictInstructions['General_Inputs']['Logo_width'] - 160  #Logo width
        lngBATRestartWidth = lngBATFreeSapce / 3
        self.btnBATRestart.place(y=dictInstructions['General_Inputs']['Logo_y'],
                                 x=dictInstructions['General_Inputs']['Logo_width'] - lngBATRestartWidth - 10,
                                 height=40 * dictInstructions['General_Inputs']['Height_ADJ'],
                                 width=lngBATRestartWidth)

        self.btnBATQuit = tk.Button(self.frmBATLogo,
                                    text="QUIT",
                                    font=(dictInstructions['General_Inputs']['Font'],
                                          dictInstructions['General_Inputs']['Font_size']),
                                    command=self.quit_GUI)
        #self.btnSolarQuit.bind('<Button>',cmd_lightUp)
        self.btnBATQuit.place(y=dictInstructions['General_Inputs']['Logo_y'],
                              x=dictInstructions['General_Inputs']['Logo_width'] - lngBATRestartWidth * 2 - 10,
                              height=40 * dictInstructions['General_Inputs']['Height_ADJ'],
                              width=lngBATRestartWidth)

        # Sensor  section relative measurements
        self.lstBATSensOrderByID = dictInstructions['BAT_Inputs']['GUI_Sections'][0]
        self.frmBATSensorHeight = dictInstructions['BAT_Inputs']['GUI_params']['Sensor_Section']['SensorFm_height']
        self.frmBATSensorsWidth = dictInstructions['BAT_Inputs']['GUI_params']['Sensor_Section']['SensorFm_width']

        SensCounter = 0
        for key in dictInstructions['BAT_Inputs']['GUI_Information']:
            for i in range(0, len(self.lstBATSensOrderByID)):
                if dictInstructions['BAT_Inputs']['GUI_Information'][key]['ID'] == self.lstBATSensOrderByID[i]:
                    if dictInstructions['BAT_Inputs']['GUI_Information'][key]['Include?'] == True:
                        SensCounter += 1

        self.dblBATSensHeight = int((self.frmBATSensorHeight - 10) / SensCounter)
        self.dblBATSensWidthLBL = int((self.frmBATSensorsWidth - 10) * 2 / 3)
        self.dblBATSensWidthVal = int((self.frmBATSensorsWidth - 10) * 1 / 3)

        # Date backward button
        self.frmBATGraphButton = tk.Frame(self.BAT_Tab, pady=5, padx=5, highlightbackground="black",
                                         highlightcolor="black", highlightthickness=1)
        self.frmBATGraphButton.pack()

        self.frmBATGraphButton.place(y=dictInstructions['BAT_Inputs']['GUI_params']['Graph_Section']['Graph_y'] -
                                      dictInstructions['General_Inputs']['Graph_button_height'],
                                    x=dictInstructions['BAT_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                                    height=dictInstructions['General_Inputs']['Graph_button_height'],
                                    width=dictInstructions['BAT_Inputs']['GUI_params']['Graph_Section'][
                                        'GraphFm_width'])

        self.Date_BAT_Back_Cmd = tk.Button(self.frmBATGraphButton,
                                          text="<",
                                          font=(dictInstructions['General_Inputs']['Font'],
                                                dictInstructions['General_Inputs']['Font_size']),
                                          command=self.previous_BAT)
        self.Date_BAT_Back_Cmd.place(y=1,
                                    x=10,
                                    height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                    width=20 * dictInstructions['General_Inputs']['Width_ADJ'])

        self.Date_BAT_Next_Cmd = tk.Button(self.frmBATGraphButton,
                                          text=">",
                                          font=(dictInstructions['General_Inputs']['Font'],
                                                dictInstructions['General_Inputs']['Font_size']),
                                          command=self.next_BAT)
        self.Date_BAT_Next_Cmd.place(y=1,
                                    x=dictInstructions['BAT_Inputs']['GUI_params']['Graph_Section'][
                                          'GraphFm_width'] - 40,
                                    height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                    width=20 * dictInstructions['General_Inputs']['Width_ADJ'])
        self.Date_BAT_Next_Cmd.pack_forget()

        self.Date_BAT_Reset_Cmd = tk.Button(self.frmBATGraphButton,
                                           text="TODAY",
                                           font=(dictInstructions['General_Inputs']['Font'],
                                                 dictInstructions['General_Inputs']['Font_size']),
                                           command=self.reset_BAT)
        self.Date_BAT_Reset_Cmd.place(y=1,
                                     x=dictInstructions['BAT_Inputs']['GUI_params']['Graph_Section'][
                                           'GraphFm_width'] / 2 - 40,
                                     height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                     width=50 * dictInstructions['General_Inputs']['Width_ADJ'])

        SensCounter = 0
        # Create sensor section labels and outputs and update global dictionary
        for i in range(0,
                       len(self.lstBATSensOrderByID)):  #Loop through all of the global library lists as calibrated within System_Initialize
            boolContinue = False
            for key in dictInstructions['BAT_Inputs']['GUI_Information']:
                if boolContinue == True:
                    continue
                if dictInstructions['BAT_Inputs']['GUI_Information'][key]['ID'] == self.lstBATSensOrderByID[
                    i]:  #if the ID of the library item
                    if dictInstructions['BAT_Inputs']['GUI_Information'][key]['Include?'] == True:
                        lblTitle = tk.Label(self.frmBATSensors,
                                            text=dictInstructions['BAT_Inputs']['GUI_Information'][key]['GUI_Label'],
                                            font=(dictInstructions['General_Inputs']['Font'],
                                                  dictInstructions['General_Inputs']['Font_size']),
                                            anchor="w")  #This is the label that provides the description to the value
                        #lblTitle.bind('<Button>', cmd_lightUp)
                        lblTitle.place(y=(self.dblBATSensHeight * SensCounter),
                                       x=5,
                                       height=self.dblBATSensHeight,
                                       width=self.dblBATSensWidthLBL)
                        lblVal = tk.Label(self.frmBATSensors,
                                          text=dictInstructions['BAT_Inputs']['GUI_Information'][key]['GUI_Default'],
                                          font=(dictInstructions['General_Inputs']['Font'],
                                                dictInstructions['General_Inputs']['Font_size']),
                                          relief="sunken")
                        #lblVal.bind('<Button>', cmd_lightUp)
                        lblVal.place(y=(self.dblBATSensHeight * SensCounter),
                                     x=self.dblBATSensWidthLBL,
                                     height=self.dblBATSensHeight,
                                     width=self.dblBATSensWidthVal)
                        dictInstructions['BAT_Inputs']['GUI_Information'][key][
                            'GUI_Val'] = lblVal  # Local level insturctions
                        dictGlobalInstructions['BAT_Inputs']['GUI_Information'][key][
                            'GUI_Val'] = lblVal  # Module level instructions
                        boolContinue = True
                        SensCounter += 1
                        continue

        #Insert BAT Graph and gauge
        self.BAT_Graph = cht_plt.GUI_graph(dictInstructions['BAT_Inputs']['Graph_params'], self.frmBATGraph)
        self.BAT_Gauge = cht_plt.GUI_gauge(dictInstructions['BAT_Inputs']['Gauge_params'], self.frmBATGauge)

    def populate_ZONE_tab(self, dictInstructions):
        #CREATE KEY FORMS WITHIN TAB
        self.frmZoneLogo = tk.Frame(self.ZONE_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                    highlightthickness=1)
        #self.frmPVLogo.bind('<Button>', cmd_lightUp)
        self.frmZoneLogo.pack()
        self.frmZoneLogo.place(y=dictInstructions['General_Inputs']['Logo_y'],
                               x=dictInstructions['General_Inputs']['Logo_x'],
                               height=dictInstructions['General_Inputs']['Logo_height'],
                               width=dictInstructions['General_Inputs']['Logo_width'])

        self.frmZoneSensors = tk.Frame(self.ZONE_Tab, pady=5, padx=5, highlightbackground="black",
                                       highlightcolor="black", highlightthickness=1)
        #frmPVSensors.bind('<Button>', cmd_lightUp)
        self.frmZoneSensors.pack()
        self.frmZoneSensors.place(y=dictInstructions['ZONE_Inputs']['GUI_params']['Sensor_Section']['Sensor_y'],
                                  x=dictInstructions['ZONE_Inputs']['GUI_params']['Sensor_Section']['Sensor_x'],
                                  height=dictInstructions['ZONE_Inputs']['GUI_params']['Sensor_Section'][
                                      'SensorFm_height'],
                                  width=dictInstructions['ZONE_Inputs']['GUI_params']['Sensor_Section'][
                                      'SensorFm_width'])

        self.frmZoneGraph = tk.Frame(self.ZONE_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                     highlightthickness=1)
        #frmSolarGraph.bind('<Button>',cmd_lightUp)
        self.frmZoneGraph.pack()
        self.frmZoneGraph.place(y=dictInstructions['ZONE_Inputs']['GUI_params']['Graph_Section']['Graph_y'],
                                x=dictInstructions['ZONE_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                                height=dictInstructions['ZONE_Inputs']['GUI_params']['Graph_Section']['GraphFm_height'],
                                width=dictInstructions['ZONE_Inputs']['GUI_params']['Graph_Section']['GraphFm_width'])

        self.frmZoneGauge = tk.Frame(self.ZONE_Tab, pady=5, padx=5, highlightbackground="black", highlightcolor="black",
                                     highlightthickness=1)
        #frmSolarGraph.bind('<Button>',cmd_lightUp)
        self.frmZoneGauge.pack()
        self.frmZoneGauge.place(y=dictInstructions['ZONE_Inputs']['GUI_params']['Gauge_Section']['Gauge_y'],
                                x=dictInstructions['ZONE_Inputs']['GUI_params']['Gauge_Section']['Gauge_x'],
                                height=dictInstructions['ZONE_Inputs']['GUI_params']['Gauge_Section']['Fm_height'],
                                width=dictInstructions['ZONE_Inputs']['GUI_params']['Gauge_Section']['Fm_width'])

        # Place HeatSet Logo
        strImageLoc = str(dictInstructions['ZONE_Inputs']['Defaults']['Logo'])
        self.tkZoneImage = ImageTk.PhotoImage(Image.open(strImageLoc))
        self.lblZoneImgLogo = tk.Label(self.frmZoneLogo, image=self.tkZoneImage)
        #lblLogo.bind('<Button>',cmd_lightUp)
        self.lblZoneImgLogo.pack(side="bottom", fill="both", expand="yes")
        self.lblZoneImgLogo.place(x=0, y=0)

        #Set up restart button
        self.btnZoneRestart = tk.Button(self.frmZoneLogo,
                                        text="RESTART",
                                        font=(dictInstructions['General_Inputs']['Font'],
                                              dictInstructions['General_Inputs']['Font_size']),
                                        command=self.restart_GUI)
        #btnRestart.bind('<Button>',cmd_lightUp)
        lngZoneFreeSapce = dictInstructions['General_Inputs']['Logo_width'] - 160  #Logo width
        lngZoneRestartWidth = lngZoneFreeSapce / 3
        self.btnZoneRestart.place(y=dictInstructions['General_Inputs']['Logo_y'],
                                  x=dictInstructions['General_Inputs']['Logo_width'] - lngZoneRestartWidth - 10,
                                  height=40 * dictInstructions['General_Inputs']['Height_ADJ'],
                                  width=lngZoneRestartWidth)

        self.btnZoneQuit = tk.Button(self.frmZoneLogo,
                                     text="QUIT",
                                     font=(dictInstructions['General_Inputs']['Font'],
                                           dictInstructions['General_Inputs']['Font_size']),
                                     command=self.quit_GUI)
        #self.btnSolarQuit.bind('<Button>',cmd_lightUp)
        self.btnZoneQuit.place(y=dictInstructions['General_Inputs']['Logo_y'],
                               x=dictInstructions['General_Inputs']['Logo_width'] - lngZoneRestartWidth * 2 - 10,
                               height=40 * dictInstructions['General_Inputs']['Height_ADJ'],
                               width=lngZoneRestartWidth)

        # Sensor  section relative measurements
        self.lstZoneSensOrderByID = dictInstructions['ZONE_Inputs']['GUI_Sections'][0]
        self.frmZoneSensorHeight = dictInstructions['ZONE_Inputs']['GUI_params']['Sensor_Section']['SensorFm_height']
        self.frmZoneSensorsWidth = dictInstructions['ZONE_Inputs']['GUI_params']['Sensor_Section']['SensorFm_width']

        SensCounter = 0
        for key in dictInstructions['ZONE_Inputs']['GUI_Information']:
            for i in range(0, len(self.lstZoneSensOrderByID)):
                if dictInstructions['ZONE_Inputs']['GUI_Information'][key]['ID'] == self.lstZoneSensOrderByID[i]:
                    if dictInstructions['ZONE_Inputs']['GUI_Information'][key]['Include?'] == True:
                        SensCounter += 1

        self.dblZoneSensHeight = int((self.frmZoneSensorHeight - 10) / SensCounter)
        self.dblZoneSensWidthLBL = int((self.frmZoneSensorsWidth - 10) * 2 / 3)
        self.dblZoneSensWidthVal = int((self.frmZoneSensorsWidth - 10) * 1 / 3)

        # Date backward button
        self.frmZoneGraphButton = tk.Frame(self.ZONE_Tab, pady=5, padx=5, highlightbackground="black",
                                         highlightcolor="black", highlightthickness=1)
        self.frmZoneGraphButton.pack()

        self.frmZoneGraphButton.place(y=dictInstructions['ZONE_Inputs']['GUI_params']['Graph_Section']['Graph_y'] -
                                      dictInstructions['General_Inputs']['Graph_button_height'],
                                    x=dictInstructions['ZONE_Inputs']['GUI_params']['Graph_Section']['Graph_x'],
                                    height=dictInstructions['General_Inputs']['Graph_button_height'],
                                    width=dictInstructions['ZONE_Inputs']['GUI_params']['Graph_Section'][
                                        'GraphFm_width'])

        self.Date_Zone_Back_Cmd = tk.Button(self.frmZoneGraphButton,
                                          text="<",
                                          font=(dictInstructions['General_Inputs']['Font'],
                                                dictInstructions['General_Inputs']['Font_size']),
                                          command=self.previous_Zone)
        self.Date_Zone_Back_Cmd.place(y=1,
                                    x=10,
                                    height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                    width=20 * dictInstructions['General_Inputs']['Width_ADJ'])

        self.Date_Zone_Next_Cmd = tk.Button(self.frmZoneGraphButton,
                                          text=">",
                                          font=(dictInstructions['General_Inputs']['Font'],
                                                dictInstructions['General_Inputs']['Font_size']),
                                          command=self.next_Zone)
        self.Date_Zone_Next_Cmd.place(y=1,
                                    x=dictInstructions['ZONE_Inputs']['GUI_params']['Graph_Section'][
                                          'GraphFm_width'] - 40,
                                    height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                    width=20 * dictInstructions['General_Inputs']['Width_ADJ'])
        self.Date_Zone_Next_Cmd.pack_forget()

        self.Date_Zone_Reset_Cmd = tk.Button(self.frmZoneGraphButton,
                                           text="TODAY",
                                           font=(dictInstructions['General_Inputs']['Font'],
                                                 dictInstructions['General_Inputs']['Font_size']),
                                           command=self.reset_Zone)
        self.Date_Zone_Reset_Cmd.place(y=1,
                                     x=dictInstructions['ZONE_Inputs']['GUI_params']['Graph_Section'][
                                           'GraphFm_width'] / 2 - 40,
                                     height=20 * dictInstructions['General_Inputs']['Height_ADJ'],
                                     width=50 * dictInstructions['General_Inputs']['Width_ADJ'])

        SensCounter = 0
        # Create sensor section labels and outputs and update global dictionary
        for i in range(0,
                       len(self.lstZoneSensOrderByID)):  #Loop through all of the global library lists as calibrated within System_Initialize
            boolContinue = False
            for key in dictInstructions['ZONE_Inputs']['GUI_Information']:
                if boolContinue == True:
                    continue
                if dictInstructions['ZONE_Inputs']['GUI_Information'][key]['ID'] == self.lstZoneSensOrderByID[
                    i]:  #if the ID of the library item
                    if dictInstructions['ZONE_Inputs']['GUI_Information'][key]['Include?'] == True:
                        lblTitle = tk.Label(self.frmZoneSensors,
                                            text=dictInstructions['ZONE_Inputs']['GUI_Information'][key]['GUI_Label'],
                                            font=(dictInstructions['General_Inputs']['Font'],
                                                  dictInstructions['General_Inputs']['Font_size']),
                                            anchor="w")  #This is the label that provides the description to the value
                        #lblTitle.bind('<Button>', cmd_lightUp)
                        lblTitle.place(y=(self.dblZoneSensHeight * SensCounter),
                                       x=5,
                                       height=self.dblZoneSensHeight,
                                       width=self.dblZoneSensWidthLBL)
                        lblVal = tk.Label(self.frmZoneSensors,
                                          text=dictInstructions['ZONE_Inputs']['GUI_Information'][key]['GUI_Default'],
                                          font=(dictInstructions['General_Inputs']['Font'],
                                                dictInstructions['General_Inputs']['Font_size']),
                                          relief="sunken")
                        #lblVal.bind('<Button>', cmd_lightUp)
                        lblVal.place(y=(self.dblZoneSensHeight * SensCounter),
                                     x=self.dblZoneSensWidthLBL,
                                     height=self.dblZoneSensHeight,
                                     width=self.dblZoneSensWidthVal)
                        dictInstructions['ZONE_Inputs']['GUI_Information'][key][
                            'GUI_Val'] = lblVal  # Local level insturctions
                        dictGlobalInstructions['ZONE_Inputs']['GUI_Information'][key][
                            'GUI_Val'] = lblVal  # Module level instructions
                        boolContinue = True
                        SensCounter += 1
                        continue

        #Insert PV Graph and gauge
        self.Zone_Graph = cht_plt.GUI_graph(dictInstructions['ZONE_Inputs']['Graph_params'], self.frmZoneGraph)
        self.Zone_Gauge = cht_plt.GUI_gauge(dictInstructions['ZONE_Inputs']['Gauge_params'], self.frmZoneGauge)

    def update_GUI_vals_thread(self, dictUpdates):
        for key in dictInstructions['Solar_Inputs']['GUI_Information']:
            if dictInstructions['Solar_Inputs']['GUI_Information'][key]['Include?'] == True:
                self.lblSolarVal = dictInstructions['Solar_Inputs']['GUI_Information'][key]['GUI_Val']
                strSQLTitle = dictInstructions['Solar_Inputs']['GUI_Information'][key]['SQL_Title']
                self.lblSolarVal.config(text=dictUpdates[strSQLTitle])

    def day_plot_reset_thread(self):
        if self.created_self == True:
            BMS_thread_lock = dictGlobalInstructions['Threads']['BMS_thread_lock']
            lstInclude = ['Solar_Thermal', 'Heat_Pump', 'PV', 'Battery', 'Zone']
            lstTech = ['Solar_Inputs', 'HP_Inputs', 'PV_Inputs', 'BAT_Inputs', 'ZONE_Inputs']

            while self.quit_sys == False:
                current_minute = chk_time.return_abs_minute_in_day()
                if current_minute == 90:  #At 1.30am
                    #Reset Graph plots
                    for i in range(0, len(lstTech)):
                        if dictGlobalInstructions['User_Inputs'][lstInclude[i]] == True:
                            for key in dictGlobalInstructions[lstTech[i]]['GUI_Information']:
                                if dictGlobalInstructions[lstTech[i]]['GUI_Information'][key]['Include?'] == True:
                                    if dictGlobalInstructions[lstTech[i]]['GUI_Information'][key][
                                        'Plot_Values?'] == True:
                                        BMS_thread_lock.acquire(True)
                                        dictGlobalInstructions[lstTech[i]]['GUI_Information'][key][
                                            'Plot_Value_List'] = []
                                        BMS_thread_lock.release()

                    #Update Graph Titles
                    if dictGlobalInstructions['User_Inputs']['Solar_Thermal'] == True:
                        self.Solar_Graph.update_graph_title(dt.datetime.now().strftime("%d/%m/%Y"))
                    if dictGlobalInstructions['User_Inputs']['Heat_Pump'] == True:
                        self.HP_Graph.update_graph_title(dt.datetime.now().strftime("%d/%m/%Y"))
                    if dictGlobalInstructions['User_Inputs']['PV'] == True:
                        self.PV_Graph.update_graph_title(dt.datetime.now().strftime("%d/%m/%Y"))
                    if dictGlobalInstructions['User_Inputs']['Battery'] == True:
                        self.BAT_Graph.update_graph_title(dt.datetime.now().strftime("%d/%m/%Y"))
                    if dictGlobalInstructions['User_Inputs']['Zone'] == True:
                        self.Zone_Graph.update_graph_title(dt.datetime.now().strftime("%d/%m/%Y"))

                time.sleep(20)

    def initiate_DB_Graph_update_thread(self):
        DB_graph_thread = threading.Thread(target=db.DB_extract_graph_update_thread,
                                           args=(dictGlobalInstructions,)).start()
        dictGlobalInstructions['Threads']['DB_Graph_Thread'] = DB_graph_thread

    def initiate_gauge_thread(self):
        gauge_thread = threading.Thread(target=self.gauge_update_thread).start()
        dictGlobalInstructions['Threads']['Gauge_Thread'] = gauge_thread

    def initiate_plot_day_reset_thread(self):
        plot_reset_thread = threading.Thread(target=self.day_plot_reset_thread).start()
        dictGlobalInstructions['Threads']['Plot_reset_thread'] = plot_reset_thread

    def initiate_all_threads(self):
        if self.created_self == True:
            BMS_thread_lock = threading.Lock()
            dictGlobalInstructions['Threads']['BMS_thread_lock'] = BMS_thread_lock
            self.initiate_DB_Graph_update_thread()
            self.initiate_gauge_thread()
            self.initiate_plot_day_reset_thread()
            #self.initiate_list_review_thread()


'''
    def gauge_update_thread(self):
        if self.created_self == True:
            while self.quit_sys == False:
                #if dictGlobalInstructions['User_Inputs']['Solar_Thermal'] == True:
                    #Managed through D_Database routine Solar_Gauage

                #if dictGlobalInstructions['User_Inputs']['Heat_Pump'] == True:
                    #GUI Gauge Line manged through D_Database routine 'heat_xchange_thread'

                #if dictGlobalInstructions['User_Inputs']['PV'] == True:
                    #GUI Gauge Line manged through D_Database routine 'heat_xchange_thread

                if dictGlobalInstructions['User_Inputs']['Battery'] == True:
                    GUI_BATTChargeVal = dictGlobalInstructions['BAT_Inputs']['GUI_Information']['Charge_Supply']['GUI_Val']
                    if GUI_BATTChargeVal.cget("text") != "None":
                        fltCharge = float(GUI_BATTChargeVal.cget("text"))
                        GUI_DisChargeVal = dictGlobalInstructions['BAT_Inputs']['GUI_Information']['Discharge_Supply']['GUI_Val']
                        if GUI_DisChargeVal.cget("text") != "None":
                            fltDisCharge = float(GUI_DisChargeVal.cget("text"))
                            if fltCharge > fltDisCharge:
                                fltGauge = (fltCharge - fltDisCharge) / fltCharge * 100
                                self.BAT_Gauge.add_gauge_line(fltGauge)
                            elif fltDisCharge > fltCharge:
                                fltGauge = (fltDisCharge - fltCharge) / fltDisCharge * (-100)
                                self.BAT_Gauge.add_gauge_line(fltGauge)
                time.sleep(60)

'''
