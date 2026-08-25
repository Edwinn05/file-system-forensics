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

        def get_MFT_record0():
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
        MFTzero = get_MFT_record0()

        def MFT_INFO(record):
            if record[0:4] != b"FILE":
                print("Error: Not a valid FILE record header.")
                return None, None
            first_attribute_offset = struct.unpack("<H",record[20:22])[0]
            while first_attribute_offset < len(record):
                identifier = struct.unpack("<I",record[first_attribute_offset:first_attribute_offset + 4])[0]
                if identifier == 0xFFFFFFFF:
                    break
                length = struct.unpack("<I",record[first_attribute_offset + 4:first_attribute_offset + 8])[0]
                if length == 0:
                    break
                if identifier == 0x80:
                    non_resident = record[first_attribute_offset + 8]
                    if non_resident == 1:
                        flags = struct.unpack("<H",record[first_attribute_offset + 12:first_attribute_offset + 14])[0]
                        compressed = bool(flags & 0x0001 or flags & 0x0002)
                        size_offset = 16 if compressed else 0
                        file_size = struct.unpack("<Q",record[first_attribute_offset + 48 + size_offset :first_attribute_offset + 56 +size_offset ])[0]
                        allocated_size = struct.unpack("<Q",record[first_attribute_offset + 40 + size_offset:first_attribute_offset + 48 + size_offset])[0]
                        #Fetch data runs
                        data_runs_offset = struct.unpack("<H",record[first_attribute_offset + 32:first_attribute_offset + 34])[0]
                        run_start = first_attribute_offset + data_runs_offset
                        run_end = first_attribute_offset + length
                        raw_data_runs = record[run_start:run_end]
                        data_runs = []
                        offset = 0
                        prev_lcn = 0
                        while offset < len(raw_data_runs):
                            header_byte = raw_data_runs[offset]
                            if header_byte == 0x00:
                                break
                            length_bytes = header_byte & 0x0F #low_nibble
                            offset_bytes = header_byte >> 4 #high_nibble
                            offset += 1
                            run_length = int.from_bytes(raw_data_runs[offset:offset + length_bytes],byteorder='little')
                            offset += length_bytes
                            run_off_bytes = raw_data_runs[offset:offset + offset_bytes]
                            run_off = int.from_bytes(run_off_bytes,byteorder='little',signed=True)
                            offset += offset_bytes
                            current_lcn = prev_lcn + run_off
                            prev_lcn = current_lcn
                            data_runs.append((run_length,current_lcn))
                            
                        return file_size,allocated_size,data_runs
                    else:
                        resident_size = struct.unpack("<I",record[first_attribute_offset + 16:first_attribute_offset + 20])[0]
                        return resident_size,resident_size
                first_attribute_offset += length
            return None,None,None
        file_size,allocated_size,data_runs = MFT_INFO(MFTzero)
        if file_size is not None:
            print("\n--- Parsing Successful! ---")
            print(f"Raw Size:       {file_size} bytes")
            print(f"Size in MB:     {file_size / (1024**2):.2f} MB")
            print(f"Size in GB:     {file_size / (1024**3):.2f} GB")
            print(f"{data_runs}")
        print("Running with administrative privileges.")
        input("\nPress  Enter to exit..")   
    else:
        print("Requesting admin privileges...")
        launch_as_admin()
