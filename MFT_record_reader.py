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

        drive = fetchlogicalpath()
        def get_MFT_record0():
            sector_size = 512
            with open(drive,"rb") as disk:
                sector = disk.read(sector_size)
                sector_per_cluster = struct.unpack("<B",sector[13:14])[0]
                mft_cluster = struct.unpack("<Q",sector[48:56])[0]
                bytes_per_cluster = sector_size * sector_per_cluster
                mft_byte_offset = mft_cluster * bytes_per_cluster
                disk.seek(mft_byte_offset)
                record0 =disk.read(1024)
            return record0,bytes_per_cluster

        _,cluster_size = get_MFT_record0()
        MFTzero,_ = get_MFT_record0()

        def MFT_INFO(record):
            if record[0:4] != b"FILE":
                print("Error: Not a valid FILE record header.")
                return None, None
            header = struct.unpack("<H",record[20:22])[0]
            while header < len(record):
                identifier = struct.unpack("<I",record[header:header + 4])[0]
                if identifier == 0xFFFFFFFF:
                    break
                length = struct.unpack("<I",record[header + 4:header + 8])[0]
                if length == 0:
                    break
                if identifier == 0x80:
                    non_resident = record[header + 8]
                    if non_resident == 1:
                        flags = struct.unpack("<H",record[header + 12:header + 14])[0]
                        compressed = bool(flags & 0x0001 or flags & 0x8000)
                        size_offset = 16 if compressed else 0
                        file_size = struct.unpack("<Q",record[header +48 + size_offset :header + 56 +size_offset ])[0]
                        allocated_size = struct.unpack("<Q",record[header + 40 + size_offset:header + 48 + size_offset])[0]
                        #Fetch data runs
                        data_runs_offset = struct.unpack("<H",record[header + 32:header + 34])[0]
                        run_start = header + data_runs_offset
                        run_end = header + length
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
                        resident_size = struct.unpack("<I",record[header + 16:header + 20])[0]
                        return resident_size,resident_size,[]
                header += length
            return None,None,None
        file_size,allocated_size,data_runs = MFT_INFO(MFTzero)
        if file_size is not None:
            print("\n--- Parsing Successful! ---")
            print(f"Raw Size:       {file_size} bytes")
            print(f"Size in MB:     {file_size / (1024**2):.2f} MB")
            print(f"Size in GB:     {file_size / (1024**3):.2f} GB")
            print(f"{data_runs}")

        _,_,data_runs = MFT_INFO(MFTzero)

        def get_MFT_record(record_no):
            record_size = 1024
            records_per_cluster = cluster_size // record_size
            target_cluster = record_no // records_per_cluster
            record_index = record_no % records_per_cluster
            cluster_checked = 0
            for length,absolute_lcn in data_runs:
                if target_cluster < (cluster_checked + length):
                    cluster_offset_in_fragment = target_cluster - cluster_checked
                    final_lcn = absolute_lcn + cluster_offset_in_fragment
                    absolute_byte_offset = (final_lcn * cluster_size) + (record_index * record_size)

                    return {
                        "record": record_no,
                        "cluster":length,
                        "LCN": final_lcn,
                        "byte_offset":absolute_byte_offset
                    }
                cluster_checked += length
            raise IndexError("Record number exceeds the total number of the MFT's allocated size")

        def read_record(drive,record_no):
            try:
                location = get_MFT_record(record_no)
                byte_offset = location["byte_offset"]
                with open(drive,"rb") as disk:
                    disk.seek(byte_offset)
                    raw_record = disk.read(1024)
                if raw_record[0:4] != b"FILE":
                    print(f"WARNING: Record {record_no} does not contain a valid 'FILE' signature")
                    return None
                parsed_data = MFT_INFO(raw_record)
                return parsed_data,raw_record
            except IndexError:
                print(f"ERROR: Record {record_no} is out of bounds for the current MFT size")
                return None
     
        print(read_record(drive,130000))
        print("Running with administrative privileges.")
        input("\nPress Enter to exit..")   
    else:
        print("Requesting admin privileges...")
        launch_as_admin()