import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import ExplicitVRLittleEndian

def create_dicom(private_tag, payload, filename, dcmconfig, verbose=False):
    """ Function creates minimal dicom file from scratch with required tags
        and stores payload (string) in the specified private tag.
    """
    
    PatientID = dcmconfig['patid']
    PatientName = dcmconfig['patname']
    StudyDescription = dcmconfig['studydes']
    SeriesDescription = dcmconfig['seriesdes']
    StationName = dcmconfig['stationname']

    StudyDate = dcmconfig['studydate'].strftime('%Y%m%d')
    StudyTime = dcmconfig['studytime'].strftime('%H%M%S')

    # create empty dicomfile
    if verbose:
        print('Creating dicom dateset') 
    file_meta = Dataset()

    # Raw Data Storage
    file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.66'
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian; 

    # unieke uid's
    file_meta.MediaStorageSOPInstanceUID = dcmconfig.get('instanceuid',None) or pydicom.uid.generate_uid()
    file_meta.ImplementationClassUID = pydicom.uid.generate_uid()

    if verbose:
        print("Creating dicom file for: {}".format(filename)) 
    ds = FileDataset(filename, {}, file_meta = file_meta, preamble="\0"*128)

    # Set the transfer syntax
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    
    ds.SOPClassUID = '1.2.840.10008.5.1.4.1.1.7' # secondary capture SOP UID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = dcmconfig.get('studyuid',None) or pydicom.uid.generate_uid()
    if verbose:
        print("Using StudyInstanceUID: {}".format(ds.StudyInstanceUID)) 
    ds.SeriesInstanceUID = dcmconfig.get('seriesuid',None) or pydicom.uid.generate_uid()

    ds.PatientID = PatientID
    ds.PatientName = PatientName
    ds.StudyDescription = StudyDescription
    ds.SeriesDescription = SeriesDescription
    ds.StationName = StationName
    ds.Modality = 'OT'

    ds.StudyDate =  StudyDate
    ds.SeriesDate =  ds.StudyDate

    ds.ContentDate = ds.StudyDate
    ds.StudyTime = ds.SeriesTime = ds.ContentTime = StudyTime

    # add QA payload as private tag
    if verbose:
        print("Adding QA as payload with private tag {}".format(private_tag)) 
    
    # space padding until string length is even (required for private tag content)
    if len(payload)%2 != 0:
        if verbose:
            print('padding payload with a space to get even value length')
        payload = payload.ljust(len(payload) +1) 
    
    ds.add_new(private_tag,'OB', payload)

    return ds
