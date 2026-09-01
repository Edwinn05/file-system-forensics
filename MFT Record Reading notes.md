# MFT Record Reading notes

*Document Type: DOCX*

The MFT works as a structural database where every file and folder on the hard drive get at least one 1024-byte record in this database. The NTFS (New Technology File System) manages the MFT. The MFT is the structural backbone of the NTFS architecture. When an action is performed on a computer, the NTFS driver(ntfs.sys) automatically handles creation, modification and deletion of MFT records in the background. The NTFS performs several automated tasks to keep the MFT functioning such as:

Reserving space to prevent the MFT from becoming fragmented
Dynamically allocates records
Recycles deleted records – when a file is deleted, the NTFS changes a flag in the record header from in use (0x01 or 0x03 for folders) to deleted (0x00 or 0x02) which will be overwritten later when a new file is created
Self-tracking via metafiles – The MFT is so central to the file system that the MFT tracks itself.
The Volume Boot Record is the very first sector of an NTFS partition which contains the BIOS Parameter Block (BPB) and an extended BPB. Within the extended BPB there is a field that stores the starting cluster number of the $MFT. So basically, the VBR contains a pointer which tells the operating system where the MFT starts on the drive.

An MFT record contains time/date stamps, file size, file status and memory addresses for file content. An MFT record is 1024 bytes and in the first 512 bytes is where the record header, standard information attribute, file name attribute, data storage and pointers and the update fixup number can be found.

The first 42 to 56 bytes define the structural properties of the record itself.

Magic number or signature is a 4-byte ASCII string (FILE or BAAD if a sector corruption or error is detected)
Update sequence array points to the location of the fixup array used to verify sector data integrity
Log sequence number (LSN) is a 64-bit value pointing to the entry in the transaction log ($LogFile -hidden system metadata file used by the windows NTFS to maintain transactional integrity and prevent data corruption) that last modified the record
Sequence number is a counter incremented every time the record is deleted and reused
Hard link count tracks how many directory names link to this specific file
First attribute offset explicitly tells the file system where the first metadata attribute block begins
Record flag is a 2-byte flag denoting the file status (0x00 deleted file, 0x01 allocated fille,0x02 deleted directory,0x03 allocated directory)
MFT record ID is the logical index of the specific record in the MFT array
The Standard Information Attribute always follows the header and contains universal file operating system metadata.

MACB timestamps are 4 distinct 64-bit Win32 file times tracking Modified, Accessed, Changed (metadata update) and Birth (Creation) dates.
DOS file permissions which are Read-only- prevents the file from being modified or deleted, archive- used to backup files. It is automatically turned on when a file is created or modified, system-identifies critical operating system files and protects them from accidental deletion and hides them from the basic file listings, hidden-prevents a file from appearing in standard directory listings unless a specific flag is passed (RASH)
Max versions & security ID is metadata linking the file to security descriptors.
File name attribute maps the human readable identifier to the record

Parent directory record reference is the file reference address of the folder containing this file
Secondary MACB timestamps is a duplicate set of timestamps managed by the kernel used to catch “timestomping”
File name length & name is the actual name string stored in 16-bit Unicode characters
Data storage and content pointers dictate how the data is handled depending on the size of the file.

Resident data - if the file is small enough to fit inside the remaining space of the 1024-byte record, the actual file contents are written directly inside the MFT
Non-resident data – if the file content cannot fit inside the record, the first 512-bytes store **Data runs** (the dynamic pointers that specify the starting LCN and cluster lengths where the data actually resides on the disk platters)
The update sequence number is the final two bytes of the first 512-byte sector which during reads, the operating system verifies these bytes against the fixup array in the header to confirm that the sector was fully written and wasn’t partial or corrupted due to sudden power loss.

The second 512 bytes only contain data if the size of a records corresponding file is less than 512 bytes.

In order to get the other records from record 0 of the MFT one must:

Read Record 0 first.
Parse its **$DATA** attribute to build a complete list of all data runs.
Walk through those data runs to find which run actually contains the offset for Record N.


