import os
import sys
import ctypes
import struct
from time_stamp_convertor import time_convertor


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

        MFTzero,_ = get_MFT_record0()
        _,cluster_size = get_MFT_record0()

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
     
        _,sample_record = read_record(drive,130000)
        print(sample_record)
        def record_header(record):
            signature = record[0:4]
            (USA_offset,USA_size,LSN,sequence_number,hard_link_count,
            first_attribute_offset,flag,record_size,allocated_size,
            file_reference,next_attribute_ID,boundary,record_number) = struct.unpack("<HHQHHHHIIQHHI" ,record[4:48])
            USN = struct.unpack("<H",record[USA_offset:USA_offset + 2])[0]
            return {"signature":signature,
                    "Update Sequence Array offset":USA_offset,
                    "Update Sequence Array size":USA_size,
                    "LogFile Sequence Number":LSN,
                    "Sequence Number":sequence_number,
                    "Hard link count":hard_link_count,
                    "First attribute offset":first_attribute_offset,
                    "Flag":flag,
                    "File record size":record_size,
                    "Allocated_size":allocated_size,
                    "File reference":file_reference,
                    "Next attribute ID":next_attribute_ID,
                    "Boundary":boundary,
                    "Record Number":record_number,
                    "Update Sequence Number":USN}
        header = record_header(sample_record)
        offset = header.get("First attribute offset")
        
        def standard_info_header(record):
            signature = struct.unpack("<I",record[offset:offset + 4])[0]
            if signature != 16:
                return      
            (
                attribute_length,flag,name_length,offset_field_name,status_flag,
                attribute_ID,standard_info_length,standard_info_offset,indexed_flag
                )=struct.unpack("<IBBHHHIHH",record[offset + 4:offset + 24])
            
            return {"standard info signature":signature,
                    "standard info length":attribute_length,
                    "residency flag":flag,
                    "Name length":name_length,
                    "Offset name":offset_field_name,
                    "Status flag":status_flag,
                    "Standard info ID":attribute_ID,
                    "Content length":standard_info_length,
                    "Content offset":standard_info_offset,
                    "Padding":indexed_flag}
        length = standard_info_header(sample_record)
        size = length.get("Content length")
        
        def standard_info(record):
            (
                creation_time,alteration_time,modified_time,accessed_time,file_permissions,
                maximum_versions,version_number,class_ID,owner_ID,security_ID,Quota_charged,USN
             )= struct.unpack("<QQQQIIIIIIQQ",record[offset + 24:(offset+ size) + 24])
            return {
                "Creation timestamp":time_convertor(creation_time),
                "Alteration timestamp":time_convertor(alteration_time),
                "MFT modification timestamp":time_convertor(modified_time),
                "Accessed timestamp":time_convertor(accessed_time),
                "DOS file permission":file_permissions,
                "Maximum versions":maximum_versions,
                "Version number":version_number,
                "Class ID":class_ID,
                "Owner ID":owner_ID,
                "Security ID":security_ID,
                "Quota charged":Quota_charged,
                "Update Sequence Number":USN
            },(offset + size) + 24 
        
        def file_name_header(record,current_offset):
                signature = struct.unpack("<I",record[current_offset:current_offset + 4])[0]
                if signature != 48:
                    return
                else:
                    (
                        attribute_length,residency_flag,name_length,name_offset,attribute_flags,
                        attribute_ID,attribute_length2,payload_offset,indexed_flag,padding
                     ) = struct.unpack("<IBBHHHIHBB",record[current_offset + 4:current_offset + 24])
                return {"File name signature":signature,
                        "File name length":attribute_length,
                        "Residency flag":residency_flag,
                        "name length":name_length,
                        "Name offset":name_offset,
                        "Attribute flag":attribute_flags,
                        "Attribute ID":attribute_ID,
                        "Payload length":attribute_length2,
                        "Payload Offset":payload_offset,
                        "Index flag":indexed_flag,
                        "Padding":padding}    
        def file_name_payload(record,current_offset,payload_offset):
            start = current_offset + payload_offset
            end = start + 66
            (parent_directory_file_reference,duplicate_creation_time,duplicate_alteration_time,duplicate_modified_time,duplicate_accessed_time,allocated_file_size,real_file_size,
                     file_attributes,document_space_requirement,file_name_length,file_name_space) = struct.unpack("<QQQQQQQIIBB",record[start:end])
            file_name_ = 2 * file_name_length
            end_offset = file_name_ + end
            file_name_text = struct.unpack(f"<{file_name_}s",record[end:end_offset])[0]
            text = file_name_text.decode("utf-16-le")
            return {"Parent directory":parent_directory_file_reference,
                    "Creation time 2":time_convertor(duplicate_creation_time),
                    "Alteration time 2":time_convertor(duplicate_alteration_time),
                    "Modification time 2":time_convertor(duplicate_modified_time),
                    "Accessed time 2":time_convertor(duplicate_accessed_time),
                    "Allocated size":allocated_file_size,
                    "Real size":real_file_size,
                    "File attributes":file_attributes,
                    "Space requirement":document_space_requirement,
                    "File name length":file_name_length,
                    "Namespace":file_name_space,
                    "File name":text,
                    "End offset":end_offset}
        def data_block(record,current_offset):
            signature = struct.unpack("<I",record[current_offset:current_offset + 4])[0]
            if signature != 128:
                return
            else:
                (attribute_length,residency_flag,name_length,
                    name_offset,flags,attribute_ID
                    ) = struct.unpack("<IBBBHH",record[current_offset + 4:current_offset + 15])
                values = {"Signature":signature,
                          "Length":attribute_length,
                          "Residency flag":residency_flag,
                          "Name length":name_length,
                          "Name offset":name_offset,
                          "Flag":flags,
                          "Identifier":attribute_ID}
                if values.get("Residency flag") == 0:
                    (content_length,content_offset,indexed_flag,padding) = struct.unpack("<IHBB",record[current_offset + 15:current_offset + 23])
                    resident_content = {"Content length":content_length,
                                        "Content offset":content_offset,
                                        "Indexed flag":indexed_flag,
                                        "Padding":padding}
                    values.update(resident_content)
                    return values
                elif values.get("Residency flag") == 1:
                            (
                                first_VCN,last_VCN,data_run_offset,compression_unit_size,
                                padding,allocated_size,actual_size,initialized_file_size
                                ) = struct.unpack("<QQHHIQQQ",record[current_offset + 15:current_offset + 63])
                            non_resident_content = {"Starting VCN":first_VCN,
                                                    "Ending VCN":last_VCN,
                                                    "Runlist offset":data_run_offset,
                                                    "Compression Unit Size":compression_unit_size,
                                                    "Padding":padding,
                                                    "Allocated size":allocated_size,
                                                    "Actual size":actual_size,
                                                    "Initialized file size":initialized_file_size}
                            values.update(non_resident_content)
                            return values
        print(standard_info(sample_record))
        print(file_name_header(sample_record,152))
        print(file_name_payload(sample_record,152,24))
        print(file_name_header(sample_record,264))
        print(file_name_payload(sample_record,264,24))
        print(data_block(sample_record,392))
        print("Running with administrative privileges.")
        input("\nPress Enter to exit..")   
    else:
        print("Requesting admin privileges...")
        launch_as_admin()