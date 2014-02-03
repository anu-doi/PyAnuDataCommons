ANU Data Uploader

Requirements:
	Python 3.3

Usage:

To display command line help:
	
	dcuploader.py -h
	
To display version information:

	dcuploader.py -v
	
To create a new collection:

	dcuploader.py -c METADATAFILE
	
	where METADATAFILE is the collection parameter information file. Refer to metadata.txt for sample.
	
	The metadata file contains the following sections. Each section contains data in key=value pairs:
		[metadata]
			Contains the actual metadata of a collection to be created.
		
		[files]
			Contains files to be uploaded in the filename=local_filepath format. E.g.
				some file.txt=C:\Data\Really Important Stuff.txt
				
			will upload the file "C:\Data\Really Important Stuff.txt" to the collection and store it as some file.txt
			
			
			This section also allows the user to specify the directories to be uploaded. All files in the specified
			directory and its subdirectories will be uploaded maintaining the directory structure on the local drive.
			
				/ = ~/dir1
			
			The line above will create a directory dir1 in the collection and upload the files in the local directory
			dir1 and all its subdirectories.  
			
				/RenamedDir2 = ~/dir2/
				
			The line above will create a directory RenamedDir2 in the collection and upload the files in the local
			directory dir2 and all its subdirectories to RenamedDir2. Note the trailing slash after 'dir2'. This
			prevents the creation of a directory named dir2 within RenamedDir2 in the collection. 
				
			
		[relations]
			Contains information about relations to other collections.
			
		[pid]
			Once a collection is created the metadata file is updated and this section to the file with the Identifier (PID)
			of the created collection. Subsequent calls to the data uploader script using this metadata file will not create
			a new collection.

			
To add files to an existing collection:
	
	dcuploader.py -p PID -f file1.txt -f "c:\long folder name\long file name.txt"
	
	where PID is the Identifier of the collection to which the files are to be uploaded. This will be of the form 'anudc:123'

	
To add directories to an existing collection:

	dcuploader.py -p PID -f ~/dir1 -f ~/dir2/
	
	where PID is the Identifier of the collection to which the files are to be uploaded. This will be of the form anudc:123
	or test:123 . When specifying directories for upload, all files within that directory and all its subdirectories will be
	uploaded. Note the trailing slash for dir2. This will result in uploading the files within dir2 on the local drive to be
	uploaded to the collection's root directory. Because there's no trailing slash for dir1, a directory 'dir1' will be created
	in the collection and all files will be uploaded relative to that directory.
	 
	
To add files to a collection previously created using a collection parameter file.

	dcuploader.py -c METADATAFILE -f "c:\long folder name\long file name.txt" -f "c:\long folder name\long file name2.txt"
		
	where METADATAFILE is a collection parameter file containing the section 'PID' that would have been created once a
	collection was created. Alternatively, creating a collection parameter file with only the following data can also be
	created for the same functionality:
	
		[pid]
		pid = anudc:123
		
