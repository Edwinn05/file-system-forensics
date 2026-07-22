import os
import sys
import ctypes
import struct

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
        def fetchlogicalpath():
            logicpath = os.getenv("SystemDrive")
            actualpath = f"\\\\.\\{logicpath}"
            return actualpath
        def get_MFT_record():
            drive = fetchlogicalpath()
            sector_size = 512
            with open(drive,"rb") as disk:
                sector = disk.read(sector_size)
                sector_per_cluster = struct.unpack("<B",sector[13:14])[0]
                mft_cluster = struct.unpack("<Q",sector[48:56])[0]
                bytes_per_cluster = sector_size * sector_per_cluster
                mft_byte_offset = mft_cluster * bytes_per_cluster
                disk.seek(mft_byte_offset)
                record0 =disk.read(1024)
            return record0
        MFT_RECORD = get_MFT_record()
        print(MFT_RECORD)
        print("Running with administrative privileges.")
        input("\nPress Enter to exit..")   
    else:
        print("Requesting admin privileges...")
        launch_as_admin()