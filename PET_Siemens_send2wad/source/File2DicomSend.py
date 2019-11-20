# -*- coding: utf-8 -*-
import os
import configparser
from argparse import ArgumentParser

import pydicom as dicom
    
import re
from datetime import datetime

import create_dicom
import storescu


def main():
    my_path = os.path.dirname(os.path.realpath(__file__))

    #Parse command line arguments
    #can be used to overrule several parameters from config.ini
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", dest="INIFILE", default=os.path.join(my_path, 'config.ini'),
                         help="read configuration from FILE", metavar="FILE")
    parser.add_argument("-src", "--source", dest="SRCDIR", help="read files from SRCDIR")
    parser.add_argument("-p", "--processed", dest="PROCESSEDDIR", default=my_path,
                         help="store processed item status files in DIR", metavar="DIR")
    parser.add_argument("-s", "--stationname", dest="STATIONNAME",
                         help="use station name NAME", metavar="NAME")
    parser.add_argument("-e", "--extension", dest="EXTENSION", default='xml',
                         help="use file extension EXT", metavar="EXT")
    parser.add_argument("-i", "--patientid", dest="PATIENTID",
                         help="use PatientID ID", metavar="ID")
    parser.add_argument("-n", "--patientname", dest="PATIENTNAME",
                         help="use PatientName NAME", metavar="NAME")
    parser.add_argument("-q", "--quiet", action="store_false", dest="verbose", default=True,
                         help="don't print status messages to stdout")
 
    args = parser.parse_args()

    configFile = args.INIFILE

    #Read config
    config = configparser.ConfigParser(comment_prefixes=('#',';'),inline_comment_prefixes=(';',))
    config.read(configFile)

    # only load some values from config if not specified on command line
    sourcedir = args.SRCDIR or config.get("FILECONFIG","SRCDIR")
    fileext = args.EXTENSION or config.get("FILECONFIG","EXT")
    processedDir = args.PROCESSEDDIR
    stationName = args.STATIONNAME or config.get("DCMCONFIG","STATIONNAME")
    patientName = args.PATIENTNAME or config.get("DCMCONFIG","PATNAME")
    patientID = args.PATIENTID or config.get("DCMCONFIG","PATID")

    if args.verbose:
        print("Reading configuration from  : {}".format(configFile));
        print("Storing processed status in : {}".format(processedDir));
        print("Reading QA files from       : {}".format(sourcedir));

    #create new file if it doesn't exist
    PROCESSED_FILEPATH = os.path.join(processedDir, "processed_files.txt")
    open(PROCESSED_FILEPATH, 'a').close()
    if args.verbose:
        print("Lookup file for processed files: {0}".format(PROCESSED_FILEPATH))
    with open(PROCESSED_FILEPATH, 'r') as f:
        processed = [f.strip() for f in f.readlines()]
       
    #Convert comma-separated values into list
    contains = [s.strip() for s in config.get("FILECONFIG","CONTAINS").split(',')]
    not_contains = [s.strip() for s in config.get("FILECONFIG","NOT_CONTAINS").split(',')]

    if args.verbose:
        print("Using QA file extension     : {}".format(fileext));
        print("Including QA files with     : {}".format(contains));
        print("Excluding QA files with     : {}".format(not_contains));
        print("Using station name          : {}".format(stationName));
        print("Using patient name          : {}".format(patientName));
        print("Using patient ID            : {}".format(patientID));

    dcmconfig = {
        'patid': patientID,
        'patname': patientName,
        'studydes': config.get("DCMCONFIG","STUDYDES"),
        'seriesdes': config.get("DCMCONFIG","SERIESDES"),
        'stationname': stationName
    }
    tag = dicom.tag.Tag(config.get("DCMCONFIG","TAG").split(','))

    my_aet =  config.get("SERVERCONFIG","MY_AET")
    remote_aet =  config.get("SERVERCONFIG","REMOTE_AET")
    destip = config.get("SERVERCONFIG","IP")
    port = int(config.get("SERVERCONFIG","PORT"))
    
    #Find all files in `sourcedir` with extension `fileext`
    allfiles = [fn for fn in os.listdir(sourcedir) if fn.endswith(fileext)]

    #Filter allfiles
    filepathlist = []
    for filename in allfiles:
        #Include filenames which contain any substrings in `contains`
        if not any([substr in filename for substr in contains]):
            print("{} contains".format(filename))
            continue
        #Exclude filenames which contain any substring in `not_contains`
        if any([substr in filename for substr in not_contains]):
            print("{} not contains".format(filename))
            continue
        print("{} filtered out".format(filename))
        
        #Include file if it fits the matching/exclusion criteria
        #and hasn't been processed before
        path = os.path.join(sourcedir, filename)
        if path not in processed:
            filepathlist.append(os.path.join(sourcedir, filename))

    for path in filepathlist:
        #dicom encapsulate scan and send to wad server
        print("preparing wadqc dicom object for: {0}".format(os.path.basename(path)))
        
        #Get file content
        with open(path) as f:
            payload =  bytes(''.join(f.readlines()), 'utf-8')

        #Get date and time from filepath
        match = re.findall(r'\d+', path)
        studydate = match[-2]
        studytime = match[-1]
        dcmconfig['studydate'] = datetime.strptime(studydate, '%d%m%Y')
        dcmconfig['studytime'] = datetime.strptime(studytime, '%H%M%S')
        dcmconfig['seriestime'] = datetime.strptime(studytime, '%H%M%S')
        filename_noext = os.path.splitext(os.path.basename(path))[0]
        dcmconfig['seriesdes'] = filename_noext

        dcmconfig['studyuid']=dicom.uid.generate_uid(entropy_srcs=[filename_noext,studydate,studytime,'study'])
        dcmconfig['seriesuid']=dicom.uid.generate_uid(entropy_srcs=[filename_noext,studydate,studytime,'series'])
        dcmconfig['instanceuid']=dicom.uid.generate_uid(entropy_srcs=[filename_noext,studydate,studytime,'instance'])

        #Create DCM
        tmpdicom = create_dicom.create_dicom(tag, payload, path, dcmconfig, verbose=args.verbose)

        #Send to PACS
        print("sending to wadqc dicom node: {0}@{1}:{2}".format(remote_aet,destip,port))
        status=storescu.StoreSCU(remotehost=destip, remoteport=port, dicomobject=tmpdicom, aec=remote_aet, aet=my_aet, verbose=args.verbose)

        if status:
            #Add path to processed_files.txt
            with open(PROCESSED_FILEPATH, 'a') as f:
                f.write(path+"\n")


if __name__ == "__main__":
    main()
