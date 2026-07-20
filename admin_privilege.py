import os
import sys
import ctypes

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
        #INSERT ADMIN-ONLY CODE
        print("Running with administrative privileges.")
        input("\nPress Enter to exit..")   
    else:
        print("Requesting admin privileges...")
        launch_as_admin()