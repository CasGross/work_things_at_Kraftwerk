# alle Funktionen für die Analyse der Wetterdaten

  
def timeshift_WOZ_to_UTC_func(messdaten, start):
    '''
    description:
    funktioniert für Zeitreihen mit beliebiger länge
    verschiebt die Zeitreihe im pd-df-Format von UTC auf WOZ Zeit
    checkout https://www.pveducation.org/pvcdrom/properties-of-sunlight/solar-time for equation explenation (I used Equation of Time (EoT) for timeshift_UTC_to_WOZ )

    input:
    pd df mit Spalte 'MESS_DATUM'
    output:
    gibt Spalte mit korrigierten Zeitstempeln zurück
    '''

    import numpy as np
    import pandas as pd

    # initialisieren der np arrays --> kann später auch gekürzt werden, wenn eh Schleife genutzt wird, müssen einzelne Werte nicht gespeichert werden
    # B = np.zeros(len(messdaten))
    # timeshift_UTC_to_WOZ = np.zeros(len(messdaten))
    UTC = messdaten['MESS_DATUM']

    for i in range(len(messdaten)):  
        # hier wird Formel für shift von UTC zu WOZ umgesetzt --> der WOZ-df hat als Messzeitpunkt Einträge immer die Zeitlichen Einträge, verschoben um die Korrektur, die sich aus der oben visualisierten Kurve ergibt
        
        today = messdaten['MESS_DATUM'][i]
        d = today - start 
        d = d.days
        B = 360/365*(d - 81)
        timeshift_WOZ_to_UTC = round(9.87* np.sin(  np.deg2rad(2*B)  ) -   7.53 * np.cos(  np.deg2rad(B)  )  - 1.5 * np.sin( np.deg2rad(B) ))
        UTC[i] = today + pd.to_timedelta(timeshift_WOZ_to_UTC, unit='m')
    return(UTC)


# eine Funktion für alles

def wetter_daten_laden_und_auf_fehler_checken(base_path_tamb,base_path_GHI, name_GHI, name_tamb,stationsID,timestep,start, ende,  save_as_file ):
    """
    
    """
    import pandas as pd
    import numpy as np
    import os
    import matplotlib.pyplot as plt

    
    # CSV-Datei laden

    file_path_GHI = os.path.join(base_path_GHI, name_GHI)
    file_path_tamb = os.path.join(base_path_tamb, name_tamb)

    # CSV-Datei laden
    df = pd.read_csv(file_path_GHI,sep=';')
    df_Tamb = pd.read_csv(file_path_tamb,sep=';')
    print("daten geladen")
    df

    # Zeitstempel konvertieren:

    # hier muss aufgepasst werden: manche Dateien haben %Y%m%d%H%M als Format, andere haben %Y%m%d%H:%M
    df_neu = df

    df_neu['MESS_DATUM'] = pd.to_datetime(df['MESS_DATUM'], format  ='%Y%m%d%H:%M') # hier muss aufgepasst werden: manche Dateien haben %Y%m%d%H%M als Format, andere haben %Y%m%d%H:%M
    df_neu

    df_neu_tamb = df_Tamb
    df_neu_tamb['MESS_DATUM'] = pd.to_datetime(df_Tamb['MESS_DATUM'], format='%Y%m%d%H')
    print("Zeitstempel konvertiert")
    df_neu

    # Filtere den DataFrame im gewünschten Zeitraum
    df_neu = df_neu[(df_neu['MESS_DATUM'] >= start) & (df_neu['MESS_DATUM'] <= ende)].reset_index(drop=True) 
    df_neu_tamb = df_neu_tamb[(df_neu_tamb['MESS_DATUM'] >= start) & (df_neu_tamb['MESS_DATUM'] <= ende)].reset_index(drop=True)
    print("gewünschter Zeitraum gefiltert")
    df_neu
    
    UTC = timeshift_WOZ_to_UTC_func(df_neu, start)
    print("WOZ zu UTC konvertiert")
    UTC

    #Transition von J/cm^2 [DWD] zu W/m^2 [PVSyst]
    # 
    # 1W = 1J/s 
    # 1m^2 = 100^2 cm^2
    # alle Werte sind in 15 Minuten Schritten
    # --> 1 J/cm^2 = 100^2[Fläche]/(60[s->min]*15[timestep]*) W/m^2

    # energy_to_power_15min = (100^2)/(60*15) # J/cm^2 to W/m^2 [15min]
    energy_to_power_1h    = (100**2)/(60**2) # J/cm^2 to W/m^2 [1h] # später addiere ich ja werte und teile sie durch 4 --> braucht nur einen Transition Faktor



    df_neu_relevant = df_neu[['MESS_DATUM']]

    # hier von WOZ auf UTC-Timestamps wechseln und in Format von PV-Sys speichern (für alles eigene Spalten)

    df_neu_relevant['Year'] = UTC.dt.year
    df_neu_relevant['Month'] = UTC.dt.month
    df_neu_relevant['Day'] = UTC.dt.day
    df_neu_relevant['Hour'] = UTC.dt.hour
    df_neu_relevant['Minute'] = UTC.dt.minute

    df_neu_relevant['GHI'] = df_neu['FG_LBERG'] * energy_to_power_1h
    df_neu_relevant['DHI'] = df_neu['FD_LBERG'] * energy_to_power_1h
    # Temperatur hinzufügen
    df_neu_relevant['Tamb'] = df_neu_tamb['TT_TU']

    # da ich aus 1h Werten 1h Werte mache, brauche ich hier keine weiteren Berechnungen (nur Timeshift von oben)


    df_neu_relevant.drop(columns=['MESS_DATUM'], inplace=True)

    df_neu_relevant

    print("Zeitstempel in Zielformat übertragen")
    #   -->  Ziel Format: ;;;;;W/m2;W/m2;deg.C

    # max_ghi = df_neu_relevant['GHI'].max()
    # max_ghi
    print("___________________Fehleranalyse___________________")
    maximale_globalstrahlung = df_neu_relevant['GHI'].max()
    print("maximale_globalstrahlung: ", maximale_globalstrahlung)
    clearnes_index_kt = maximale_globalstrahlung / (1361 * (1-0.033) ) #ist indikator von PV*Syst https://www.pvsyst.com/help/physical-models-used/irradiation-models/clearness-index.html
    print("clearnes_index_kt: ",clearnes_index_kt)

    # errors =(df_neu_relevant['GHI'] < 0)

    # negative_values = df_neu_relevant[df_neu_relevant['GHI'] < 0]['GHI']
    def negative_werte_bereinigen(df_neu_relevant, spaltenname):
        
        negative_indices = df_neu_relevant.index[df_neu_relevant[spaltenname] < 0]
        print(f"Fehlerwerte {spaltenname}: {len(negative_indices)}")
        return negative_indices



    # errors = df_neu_relevant.loc[negative_indices]
    # errors


    # print(errors)

    # maximale_globalstrahlung = df_neu_relevant['GHI'].value_counts().get(, 0)
    # print(maximale_globalstrahlung)



    # Df einfach um negative Werte bereinigen. (keine Interpolation oder so, aber bei wenigen Werten sollte das kein Problem sein)


    negative_indices_ghi = negative_werte_bereinigen(df_neu_relevant, 'GHI')
    df_neu_relevant['GHI'].loc[negative_indices_ghi] = 0

    negative_indices_dhi = negative_werte_bereinigen(df_neu_relevant, 'DHI')
    df_neu_relevant['DHI'].loc[negative_indices_dhi] = 0

    negative_indices_tamb = negative_werte_bereinigen(df_neu_relevant, 'Tamb')
    df_neu_relevant['Tamb'].loc[negative_indices_tamb] = 7

    df_neu_relevant.loc[negative_indices_ghi]

    UTC.loc[negative_indices_ghi]

        
    print(f"Fehlerwerte GHI: {len(negative_indices_ghi)}")
    plt.figure(figsize=(8,4))
    plt.plot(UTC.loc[negative_indices_ghi], df_neu_relevant.loc[negative_indices_ghi]['Hour'], linestyle="none", marker="x")
    plt.xlim(start, ende)
    plt.ylim(0, 24)
    plt.xticks(rotation=45)
    plt.xlabel("Zeitpunkt im Jahr")
    plt.ylabel("Uhrzeit des Fehlerwerts")
    plt.title(stationsID)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    new_row = ['', '', '', '', '','W/m2','W/m2','deg.C']   
    # einheiten einfügen bei CSV -> entkommentieren der beiden Zeilen unten
    # #df_15 = pd.concat([pd.DataFrame([new_row], columns=df_15.columns), df_15], ignore_index=True) # nur einmal einfügen
    # Einheiten-Spalte nur einmal einfügen:
    df_neu_relevant = pd.concat([pd.DataFrame([new_row], columns=df_neu_relevant.columns), df_neu_relevant], ignore_index=True) 
    df_neu_relevant

    #achtung! name muss noch im cache sein!

    # name_new_1 = name.replace('.csv', '_2024_1h_1_for_pv_syst.csv')
    if save_as_file :
        from ntpath import join


        start_string = start.strftime("%Y-%m-%d")
        ende_string = ende.strftime("%Y-%m-%d") 

        csv_eding = 'for_pv_syst.csv'
        name_new_1 = ''.join([stationsID,"_",start_string,"_",ende_string,"_",timestep,'_1_',csv_eding])

        # nur ausführen wenn Datei ready ist, sonst wird bestehende Datei überschrieben 
        df_neu_relevant.to_csv(name_new_1, sep=';', index=False, header=['Year','Month','Day','Hour','Minute','GHI','DHI','Tamb'])

        print("abgespeichert - metadaten händisch ergänzen!")
    else:
        print("nicht gespeichert")





