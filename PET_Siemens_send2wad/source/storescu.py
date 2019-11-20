#!/usr/bin/python

from __future__ import print_function
import sys
from pynetdicom import AE, VerificationPresentationContexts
from pynetdicom.sop_class import SecondaryCaptureImageStorage
from pydicom.uid import ExplicitVRLittleEndian, ImplicitVRLittleEndian, ExplicitVRBigEndian


# Set Transfer Syntax options 
ts = [
		ExplicitVRLittleEndian, 
		ImplicitVRLittleEndian, 
		ExplicitVRBigEndian
	 ]


def OnAssociateResponse(association):
	print("Association response received")


def StoreSCU(remotehost,remoteport,dicomobject,aec,aet='PYNETDICOM',verbose=False):

	MyAE = AE(ae_title=aet)
	
	# only require Secondary Capture Image Storage beside Verification
	MyAE.requested_contexts = VerificationPresentationContexts
	MyAE.add_requested_context(SecondaryCaptureImageStorage,transfer_syntax=ts) 

	# Try and associate with the peer AE
	#   Returns the Association thread
	if verbose:
		print("Requesting Association with peer {0}@{1}:{2}".format(aec,remotehost,remoteport))
	assoc = MyAE.associate(addr=remotehost,ae_title=aec,port=remoteport)

	if verbose:
		if assoc.is_established:
			print('Association accepted by peer')
		else:
			print("Could not establish association")
			sys.exit(1)

	# perform a DICOM ECHO, just to make sure remote AE is listening
	if verbose:
		print("DICOM C-ECHO... ",end='')
	status = assoc.send_c_echo()
	if status and verbose:
		print('Response: 0x{0:04x}'.format(status.Status))

	# Send a DIMSE C-STORE request to the peer
	if verbose:
		print("DICOM C-STORE... ",end='')
	try:
		status = assoc.send_c_store(dicomobject)
		if verbose:
			print('Response: 0x{0:04x}'.format(status.Status))
	except:
		if verbose:
			print("problem {}".format(dicomobject.SOPClassUID))
		return False

	if verbose:
		print("Release association")
	assoc.release()

	return True

