# TKInter GUI class
# Frame sortieren, Auswahl Batteriesimulation, OK, Laufzeit, message done
import tkinter as tk
from tkinter import filedialog
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tkinter import messagebox
import threading
import os


class GUI(tk.Frame): 
    def __init__(self, master= None):
        super().__init__(master)
        self.grid(row=0,column=1)
        self.createWidgets()

    def createWidgets(self):
        
        self.Label_Pfadeingabe = tk.Label(text='Pfadeingabe:')
        self.Label_Pfadeingabe.grid(row=0,column=0)
        self.PathEntry = tk.Entry(self)
        self.PathEntry.grid(row=0,column=1)
        
        self.button_explore = tk.Button(text="Browse", command=self.browseFiles)
        self.button_explore.grid(row=0,column=2)
        
        self.check_sim = tk.IntVar()
        self.check_sim_button = tk.Checkbutton(text = 'EVO',variable=self.check_sim, onvalue=1, offvalue=0)
        self.check_sim_button.grid(row=1,column=1)

        self.button_run = tk.Button(text="Run", command=self.Run_Simulation)
        self.button_run.grid(row=1, column=2)

        self.Label_runtime = tk.Label(text= 'runtime: -')
        self.Label_runtime.grid(row=2, column=0)

        self.Label_currently_running = tk.Label(text= '')
        self.Label_currently_running.grid(row=2, column=1)


    def browseFiles(self):
        Filename = filedialog.askopenfilename(initialdir = os.getcwd(), title = "Select a File", filetypes = (("all files", "*.*"), ("Text files","*.txt*")))
        self.PathEntry.select_clear()
        self.PathEntry.insert(0, Filename)


    def Run_Simulation(self):
        # Simulationen
        if self.check_sim.get() == 1:
            self.Label_currently_running.config(text='Battery Simulation running')
            self.EVO_Read_Input_from_ExcelFile()
            
            self.SimVarEVO()
            self.Label_currently_running.config(text='Battery Simulation done')

        else:
            messagebox.showinfo("Info", "Please choose a battery simulation")

    
    def EVO_Read_Input_from_ExcelFile(self):

        # Initialisierung
        self.P_PVspez = None
        self.P_PV_Steps = None
        self.P_PV = None
        self.P_Load = None
        self.P_Batt_Steps = None
        self.E_Batt_Steps = None
        self.P_BATTMAX = None
        self.E_BATTMAX = None
        self.Eta_Batt = None
        self.Eta_WRBatt = None
        self.SCHRITT = None

        #  Einlesen Excel-Datei
        self.Path = self.PathEntry.get()
        self.df = pd.read_excel(self.Path, sheet_name='SimBatt-Input')

        #  Auslesen relevanter Serien aus df und Konvertierung zu np array
        self.P_PVspez = pd.Series(self.df.loc[0:35040, 'PV-Erzeugungsprofil in kW/kWp'])
        self.P_PVspez = self.P_PVspez.to_numpy()
        self.P_Load = pd.Series(self.df.loc[0:35040, 'Last in kW'])#
        self.P_Load = self.P_Load.to_numpy()
        self.P_PV_Steps = pd.Series(self.df.loc[0:9,'PV: Leistungsschritte in kWp'])
        self.P_PV_Steps = self.P_PV_Steps.to_numpy()
        self.E_Batt_Steps = pd.Series(self.df.loc[0:9,'Speicher: Kapazität in kWh'])
        self.E_Batt_Steps = self.E_Batt_Steps.to_numpy()
        self.P_Batt_Steps = pd.Series(self.df.loc[0:9,'Speicher: Leistung in kW'])
        self.P_Batt_Steps = self.P_Batt_Steps.to_numpy()
        self.Eta_Batt = pd.Series(self.df.at[0, 'Speicher: Wirkungsgrad in %'])
        self.Eta_Batt = self.Eta_Batt.to_numpy()
        self.Eta_WRBatt = pd.Series(self.df.at[0, 'Speicher WR: Wirkungsgrad in %'])
        self.Eta_WRBatt = self.Eta_WRBatt.to_numpy()
        self.SCHRITT = pd.Series(self.df.at[0, 'Schrittweite'])
        self.SCHRITT = self.SCHRITT.to_numpy()



    def SimPVdirekt(self):

        # Initialisierung Variable
        self.P_PVdirekt = np.zeros(len(self.P_Load))
        
        #  Startzeit-Endzeit-Schrittweite
        self.t_START = 0
        self.T_END = len(self.P_Load)

        # PV-Direktverbrauch berechnen
        for t in range(self.t_START,self.T_END):
            if self.P_PV[t] > 0:
                self.P_PVdirekt[t] = min(self.P_PV[t],self.P_Load[t])
            else:
                self.P_PVdirekt[t] = 0



    def SimBatEVO(self):

        #  Differenzleistung
        self.P_DIFF = self.P_PV - self.P_Load

        #  Startzeit-Endzeit-Schrittweite
        self.t_START = 0
        self.T_END = len(self.P_Load)

        # Vorinitialisierung benötigter Variablen
        self.P_BATTIN = np.zeros(len(self.P_Load))
        self.P_BATTOUT = np.zeros(len(self.P_Load)) 
        self.P_BATT = np.zeros(len(self.P_Load))
        self.P_BS = np.zeros(len(self.P_Load)) 
        self.E_BATT = np.zeros(len(self.P_Load))
        self.SOC = np.zeros(len(self.P_Load))
        self.P_Netz = np.zeros(len(self.P_Load))


        #  PV-Speichersimulation
        for t in range(self.t_START, self.T_END):
            
            #  Batterieladung
            if self.P_DIFF[t] > 0:
                self.P_BATTIN[t] = min((min(self.P_BATTMAX, self.P_DIFF[t])*self.Eta_WRBatt), (self.E_BATTMAX*(1-self.SOC[t-1])/self.SCHRITT/self.Eta_Batt))
            #Batterieentladung
            elif  self.P_DIFF[t] < 0:
                self.P_BATTOUT[t] = -min((min(self.P_BATTMAX, -self.P_DIFF[t])/self.Eta_WRBatt), (self.E_BATTMAX*self.SOC[t-1]/self.SCHRITT))

            # Batteriespeicherleistung
            self.P_BATT[t] = self.P_BATTIN[t]+self.P_BATTOUT[t]

            #  Batteriesystemleistung
            self.P_BS[t] = self.P_BATTIN[t]/self.Eta_WRBatt + self.P_BATTOUT[t]*self.Eta_WRBatt

            #  Gespeicherte Energie
            self.E_BATT[t] = self.E_BATT[t-1] + (self.P_BATTIN[t]*self.Eta_Batt + self.P_BATTOUT[t])*self.SCHRITT

            #  SOC bestimmen
            self.SOC[t] = self.E_BATT[t]/self.E_BATTMAX

    def SimVarEVO(self): 
        self.P_BS_Variation = np.zeros((10, 35043))  # Initialiesierung array für Variation
        self.P_PV_BS_Variation = np.zeros((120, 35044))

        for j in range(0,10):

            self.P_PV = (self.P_PV_Steps[j]*self.P_PVspez)  # aktuell Wahl der PV Skalierung  !

            self.P_PV_BS_Variation[j, 0] = self.P_PV_Steps[j]  # abspeichern PV-Leistung kWp über PV-Leistung Zeitreihe in Ergebnisarray P_PV_BS_Variation
            self.P_PV_BS_Variation[j, 4:35044] = self.P_PV  # abspeichern PV-Leistung Zeitreihe in Ergebnisarray P_PV_BS_Variation

            self.P_PV_BS_Variation[j+10, 0] = self.P_PV_Steps[j]  # abspeichern PV-Leistung kWp über SimBat in Ergebnisarray P_PV_BS_Variation

            self.SimPVdirekt()  # Berechnung und speichern PV-Direktverbrauch
            self.P_PV_BS_Variation[j+10, 4:35044] = self.P_PVdirekt  # abspeichern PV-Direktverbrauch in Ergebnisarray P_PV_BS_Variation

            
            k = 20+j*10  # index für Eintrag PV-Leistung

            for i in range(0,10):

                self.P_BATTMAX = self.P_Batt_Steps[i]  # Aktuell Wahl Speicherleistung  !
                self.E_BATTMAX = self.E_Batt_Steps[i]  # Aktuell Wahl Speicherkapazität  !

                self.SimBatEVO()  # Batteriesimulation EVO

                self.P_BS_Variation[i, 0] = self.P_BATTMAX  # P_BATTMAX abspeichern
                self.P_BS_Variation[i, 1] = self.E_BATTMAX  # E_BATTMAX abspeichern
                self.P_BS_Variation[i, 3:35043] = self.P_BS  # BS Variation abspeichern
                
                self.P_PV_BS_Variation[(k+i), 0] = self.P_PV_Steps[j]
            

            self.P_PV_BS_Variation[k:(k+10), 1:35044] = self.P_BS_Variation[0:10,0:35043]
        self.SaveSimBat()

    def SaveSimBat(self):
        self.P_PV_BS_Variation_trans = np.transpose(self.P_PV_BS_Variation)
        self.df2Excel = pd.DataFrame(self.P_PV_BS_Variation_trans)
        with pd.ExcelWriter(self.Path, mode='a', if_sheet_exists='replace', engine='openpyxl') as writer:
            self.df2Excel.to_excel(writer, sheet_name='SimBatt-Output')


# Hauptprogramm
window = tk.Tk()
app = GUI(window)
app.mainloop()

