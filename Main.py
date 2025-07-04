import pandas as pd
import os
import glob
import shutil
import time
from datetime import datetime, timedelta
import configparser
import tkinter as tk
from tkinter import messagebox

from fitsdll import fn_handshake, fn_query, fn_log

class AutoFITs_Dispensing():
    def __init__(self):
        config = configparser.ConfigParser()
        try:
            config.read("C:\Projects\AutoFITs_Dispensing_Scanner\Properties\Config.ini")
            self.model = config["DEFAULT"].get("model", "")
            self.operation = config["DEFAULT"].get("operation", "")
            self.extractpath = config["DEFAULT"].get("start_path", "")
            self.Archpath  = config["DEFAULT"].get("Arch_path", "")
            # self.hand_fail  = config["DEFAULT"].get("hand_fail", "")
            self.potlife = config["DEFAULT"].get("potlife", "") # min.
            self.safety_time = config["DEFAULT"].get("safety_time", "") # min.
        except Exception as e:
            print(f"{e}\nPlease check config.ini")
            quit()
            
        os.makedirs(self.Archpath, exist_ok=True)
        # os.makedirs(self.hand_fail, exist_ok=True)

    def extractDataFile(self):
        extractedfiles = []
        now = datetime.now()
        path = os.path.join(self.extractpath, str(now.year), now.strftime("%m_%d_%Y"), "*","*.csv")
        allfiles = glob.glob(path)
        for filename in allfiles:
            serial = os.path.basename(filename).split(".")[0]
            serial = serial.split("_")[0]
            handshake_status = fn_handshake(self.model, self.operation, serial)
            # handshake_status = True
            if handshake_status == True:
                extractedfiles.append(filename)
            else:
                print(f"Serial: {serial} Handcheck Fail | Please check FITs process flow")
                timestamp = now.strftime("%H-%M-%S")
                new_path = filename.replace("Logging", "Log_Handcheck")
                new_path = new_path.replace(serial, f"{serial}_{timestamp}")
                shutil.move(os.path.dirname(filename),os.path.dirname(new_path))
            time.sleep(0.25)
        # print(extractedfiles)
        return extractedfiles
    
    def TransformData(self, file):
        df = pd.read_csv(file).astype(str)
        value = df.iloc[3, :15]
        query = fn_query("*", "C011", value.iloc[9], "Start use date;Start use time")
        opendatetime = datetime.strptime(query, "%d%b%Y;%H:%M:%S")
        expired = opendatetime + timedelta(minutes=int(self.potlife))
        saftey = expired - timedelta(minutes=int(self.safety_time))
        now = datetime.now()
        if saftey <= now:
            Verify = "OVER STOP USE TIME!"
        else:
            Verify = "ACCEPT"

        extrcted_df = {
            "EN": value.iloc[5].split(".")[0],
            "Shift": value.iloc[4],
            "MC": value.iloc[6],
            "SN Scanner": value.iloc[8],
            "WO#": value.iloc[7],
            "Epoxy_PN_1": "GAP FILLER 4000, 50cc CARTRIDGE",
            "Epoxy_IQR_1": value.iloc[9],
            "Safety date 1": saftey.strftime("%d-%b-%Y"),
            "Safety time 1": saftey.strftime("%H:%M:%S"),
            "Expired date 1": expired.strftime("%d-%b-%Y"),
            "Expired time 1": expired.strftime("%H:%M:%S"),
            "Verify pot life of epoxy": Verify,
            "Value of Gap filler 1": value.iloc[11],
            "Value of Gap filler 2": value.iloc[12],
            "Value of Gap filler 3": value.iloc[13],
            "Result": value.iloc[14]
        }

        fits_df = extrcted_df
        print(pd.Series(extrcted_df))
        quit()
        return fits_df

    def LoadData(self, file, df):
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        serial = df["SN Scanner"]
        timestamp = now = datetime.now().strftime("%H-%M-%S")
        retries_path = file.replace("Logging", "Log_retries")
        retries_path = retries_path.replace(serial, f"{serial}_{timestamp}")
        if df["Result"] == "FAIL":
            messagebox.showerror("FITs Denied", "Result Failed, Please check Please check value gap filler.")
            
            shutil.move(os.path.dirname(file),os.path.dirname(retries_path))
            root.destroy()
            return
        if df["Result"] == "OVER STOP USE TIME!":
            messagebox.showerror("FITs Denied", "EXPOXY EXPIRED, Please check epoxy potlife datetime.")
            shutil.move(os.path.dirname(file),os.path.dirname(retries_path))
            return
            
        parameters = ";".join(df.keys())
        values = ";".join(df.values())
        log_status = fn_log(self.model, self.operation, parameters,values)
        if log_status == True:
            print(datetime.now().strftime("%m:%d:%Y_%H:%M:%S") + "\t|\t" + "Success uploaded serial >> {serial}")
            print(f"{serial} ")
        else:
            messagebox.showerror("FITs Message", "Failed uploaded data to FITs")
            
        root.destroy()
        timestamp = datetime.now().strftime("%H-%M-%S")
        ach_path = file.replace("Logging", "Log_Ach")
        ach_path = ach_path.replace(serial, f"{serial}_{timestamp}")
        shutil.move(os.path.dirname(file),os.path.dirname(ach_path))

if __name__ == "__main__":
    dispensing = AutoFITs_Dispensing()
    print("----Start----")
    
    while True:
        allfile = dispensing.extractDataFile()
        for file in allfile:
            df = dispensing.TransformData(file)
            dispensing.LoadData(file, df)
     
        print("sleep 5 sec.")
        time.sleep(5)
