import os
import sys
import ctypes
import subprocess
import winreg

def admin_privilege():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
def launch_as_admin():
    script_path = os.path.abspath(sys.argv[0])
    parameter = f'"{script_path}"'
    try:
        ctypes.windll.shell32.ShellExecuteW(
            None,"runas",sys.executable,parameter,None,1
        )
    except Exception as e:
        print(f"Failed to get admin privileges:{e}")
    sys.exit(0)
if __name__ == "__main__":
    if admin_privilege():
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("Error: You must run this as an admin")
            sys.exit(1)
        #For windows operating system
        def manage_access_time():
            registry_path = r"SYSTEM\CurrentControlSet\Control\FileSystem"
            key_name = "NtfsDisableLastAccessUpdate"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path,0 ,winreg.KEY_READ) as key:
                    value,_ = winreg.QueryValueEx(key,key_name)
                if value in (0,2):
                    print("Staus: Last access time is enabled ")
                else:
                    print(f"Cureent Status: Disabled (Registry value {value}). Enabling now...")
                    enable_cmd = "fsutil behavior set disablelastaccess 0"
                    subprocess.run(enable_cmd,shell=True,check=True)
                print("Successfully enabled last access time.")
                print("You may need to restart your computer for changes to take effect.")
            except subprocess.CalledProcessError as e:
                print(f"Error: Failed to change settings.\nDetails: {e.stderr}")
        if __name__ == "__main__":
            manage_access_time()
        print("Running with administrative privileges.")
        input("\nPress Enter to exit..")   
    else:
        print("Requesting admin privileges...")
        launch_as_admin()