// openmidi.cpp : Defines the entry point for the DLL application.
//

#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif

#include "stdafx.h"
#include "stdio.h"
#include "wtypes.h"
#include "Mmsystem.h"

#include "Python.h"
#include "openmidi.h"

BOOL APIENTRY DllMain( HANDLE hModule, 
                       DWORD  ul_reason_for_call, 
                       LPVOID lpReserved
					 )
{
    switch (ul_reason_for_call)
	{
		case DLL_PROCESS_ATTACH:
		case DLL_THREAD_ATTACH:
		case DLL_THREAD_DETACH:
		case DLL_PROCESS_DETACH:
			break;
    }
    return TRUE;
}


// This is an example of an exported variable
//OPENMIDI_API int nOpenmidi=0;

OPENMIDI_API int GetNumberOfMidiInDevs(void)
{
	return (int)(midiInGetNumDevs());
}

OPENMIDI_API int GetMidiInDevName(int index, char* lpszDeviceName, int iLen)
{
	MIDIINCAPS capabilities;
	int iRetLen = 0;

	if (lpszDeviceName) {

		*lpszDeviceName = 0;

		if (index < GetNumberOfMidiInDevs()) {
			// Get the device info
			midiInGetDevCaps(index, &capabilities, sizeof(capabilities));

			// Copy the device name
			strncpy(lpszDeviceName, capabilities.szPname, iLen);
			lpszDeviceName[iLen - 1] = 0;

			// Get the length
			iRetLen = strlen(lpszDeviceName);
		}
	}

	// return length of device name
	return iRetLen;
}

OPENMIDI_API int GetNumberOfMidiOutDevs(void)
{
	return (int)(midiOutGetNumDevs());
}

OPENMIDI_API int GetMidiOutDevName(int index, char* lpszDeviceName, int iLen)
{
	MIDIOUTCAPS capabilities;
	int iRetLen = 0;

	if (lpszDeviceName) {

		*lpszDeviceName = 0;

		if (index < GetNumberOfMidiOutDevs()) {
			// Get the device info
			midiOutGetDevCaps(index, &capabilities, sizeof(capabilities));

			// Copy the device name
			strncpy(lpszDeviceName, capabilities.szPname, iLen);
			lpszDeviceName[iLen - 1] = 0;

			// Get the length
			iRetLen = strlen(lpszDeviceName);
		}
	}

	// return length of device name
	return iRetLen;
}

// This is the constructor of a class that has been exported.
// see openmidi.h for the class definition
MidiOut::MidiOut(int index, int blocksize, int delay)
{ 
	iBlockSize = blocksize;
	szLastError[0] = '\0';

	out = new MidiOutWin(index);
	out->index = index;
	out->iDelay = delay;
}

MidiOut::~MidiOut(void)
{
	if (out)
		delete out;
}

int MidiOut::GetLastError(char* lpszBuffer, int iLen) 
{
	int iRetLen = 0;

	if (lpszBuffer) {
		if (iLen > MIDI_ERROR_SIZE)
			iLen = MIDI_ERROR_SIZE;

		strncpy(lpszBuffer, szLastError, iLen);
		lpszBuffer[iLen - 1] = '\0';

		iRetLen = strlen(lpszBuffer);
	}

	return iRetLen;
}

int MidiOut::SendShort(char cStatus, char cByte1, char cByte2)
{
	int iRet = -1;

	// Clear the last error message
	szLastError[0] = '\0';

	try {
		// Open the MIDI device
		out->OpenDevice();

		// Delay
		Sleep(out->iDelay);

		// Send MIDI message
		iRet = out->SendShort(cStatus, cByte1, cByte2);

		// Close the MIDI device
		out->CloseDevice();
	}
	catch (MidiException* e) {
		// Save the error message
		sprintf(szLastError, "%s:%d %s", e->sFileName, e->iLineNumber, e->sErrMsg);

		// Close MIDI out
		out->CloseDevice();

		// Delete the exception
		delete e;
	}

	return iRet;
}

// Send a sysex message
int MidiOut::SendLong(const char* lpcSendBuffer, int iSendLen)
{
	int iOffset = 0;
	int iLen = iBlockSize;
	int iRet;

	// Clear the last error message
	szLastError[0] = '\0';

	try {
		// Open the MIDI device
		out->OpenDevice();

		// Send the sysex message one block at a time
		while (iOffset < iSendLen) {

			// length is min(iSendLen, iBlockSize)
			if (iSendLen - iOffset < iBlockSize)
				iLen = iSendLen - iOffset;

			// Delay
			Sleep(out->iDelay);

			// Send sysex message
			iRet = out->SendLong(lpcSendBuffer + iOffset, iLen);
			if (iRet)
				break;

			// Advance offset to start of next block
			iOffset += iLen;
		}

		// Close the MIDI device
		out->CloseDevice();
	}
	catch (MidiException* e) {
		// Save the error message
		sprintf(szLastError, "%s:%d %s", e->sFileName, e->iLineNumber, e->sErrMsg);

		// Close MIDI out
		out->CloseDevice();

		// Delete the exception
		delete e;
	}

	// return number of bytes sent
	return iOffset;
}


MidiInOut::MidiInOut(int iInIndex, int iOutIndex, int blocksize, int delay, int timeout) :
	MidiOut(iOutIndex, blocksize, delay)
{ 
	iTimeout = timeout;

	in = new MidiInWin(iInIndex);
	in->iDelay = delay;
}

MidiInOut::~MidiInOut(void)
{
	if (in)
		delete in;
}

// Send a sysex message and receive replies
int MidiInOut::Request(char* lpcRcvBuffer, int iRcvLen, 
						const char* lpcSendBuffer, int iSendLen, int iNumRepliesToExpect /* = 1 */)
{
	int i;
	int iLen;						// Length of received sysex message(s) in pcInBuffer
	char* lp;						// Buffer pointers
	HANDLE hEvent;					// Event handle for interrupt-driven receiving
	int iRet;						// 0 == success, -1 == failed to parse sysex message

	// Clear the last error message
	szLastError[0] = '\0';

	// Zero out the receive buffer
	memset(lpcRcvBuffer, 0, iRcvLen);

	iLen = 0;

	try {
		// Open MIDI out
		out->OpenDevice();

		// Open MIDI in
		in->OpenDevice();

		// Start listening to MIDI in
		hEvent = in->Start(iRcvLen, iNumRepliesToExpect);

		// Insert the delay
		Sleep(in->iDelay);

		// Send sysex message
		out->SendLong(lpcSendBuffer, iSendLen);

		// Close MIDI out
		out->CloseDevice();

		// Wait for reply or time out
		iRet = WaitForSingleObject(hEvent, iTimeout);

		if (iRet == WAIT_OBJECT_0) {
			// Stop listening to MIDI in
			in->Stop();

			// Get any received sysex message(s)
			for (i = 0, lp = lpcRcvBuffer; iLen < iRcvLen && i < iNumRepliesToExpect; i++) {
				iLen += in->GetSysexMessage(lp, iRcvLen, i);
				lp = lpcRcvBuffer + iLen;
			}
		}

		// Close MIDI in
		in->CloseDevice();

	}
	catch (MidiException* e) {
		// Save the error message
		sprintf(szLastError, "%s:%d %s", e->sFileName, e->iLineNumber, e->sErrMsg);

		// Close MIDI devices
		in->CloseDevice();
		out->CloseDevice();

		// Delete the exception
		delete e;
	}

	// Return the number of bytes received
	return iLen;
}

static PyObject* PyGetNumberOfMidiInDevs(PyObject* pSelf, PyObject* pArgs)
{
	if (!PyArg_ParseTuple(pArgs,""))
		return NULL;

	int n = GetNumberOfMidiInDevs();

	return Py_BuildValue("i", n);
}

static PyObject* PyGetMidiInDevName(PyObject* pSelf, PyObject* pArgs, PyObject* pKeywds)
{
	static char *kwlist[] = {"index", NULL};
	int i;

	if (!PyArg_ParseTupleAndKeywords(pArgs, pKeywds, "i", kwlist, &i))
		return NULL;

	char buf[1024] = "";

	int n = GetNumberOfMidiInDevs();
	if (i >= 0 && i < n)
	{
		GetMidiInDevName(i, buf, 1024);
		return Py_BuildValue("z", buf);
	} else
		return Py_BuildValue("z", NULL);
}

static PyObject* PyGetNumberOfMidiOutDevs(PyObject* pSelf, PyObject* pArgs)
{
	if (!PyArg_ParseTuple(pArgs,""))
		return NULL;

	int n = GetNumberOfMidiOutDevs();

	return Py_BuildValue("i", n);
}

static PyObject* PyGetMidiOutDevName(PyObject* pSelf, PyObject* pArgs, PyObject* pKeywds)
{
	static char *kwlist[] = {"index", NULL};
	int i;

	if (!PyArg_ParseTupleAndKeywords(pArgs, pKeywds, "i", kwlist, &i))
		return NULL;

	char buf[1024] = "";

	int n = GetNumberOfMidiOutDevs();
	if (i >= 0 && i < n)
	{
		GetMidiOutDevName(i, buf, 1024);
		return Py_BuildValue("z", buf);
	} else
		return Py_BuildValue("z", NULL);
}

static PyObject* PyMidiRequest(PyObject* pSelf, PyObject* pArgs, PyObject* pKeywds)
{
	static char *kwlist[] = {"outdev", "buffer", "indev", "expect", NULL};
	
	int outDev, inDev, outLen, expect;
	char* outBuf = NULL;

	if (!PyArg_ParseTupleAndKeywords(pArgs, pKeywds, "it#ii", kwlist, 
                                     &outDev, &outBuf, &outLen, &inDev, &expect))
        return NULL; 

	char inBuf[32767] = "";
	int inLen = 0;

	MidiInOut m(inDev, outDev, 1024, 50, 5000);

	inLen = m.Request(inBuf, 32767, outBuf, outLen, expect);

	return Py_BuildValue("z#", inBuf, inLen);
}

static PyObject* PyMidiSend(PyObject* pSelf, PyObject* pArgs, PyObject* pKeywds)
{
	static char *kwlist[] = {"outdev", "buffer", NULL};
	
	int outDev, outLen;
	char* outBuf = NULL;

	if (!PyArg_ParseTupleAndKeywords(pArgs, pKeywds, "it#", kwlist, 
                                     &outDev, &outBuf, &outLen))
        return NULL; 

	MidiOut m(outDev, 50, 5000);

	int sent = m.SendLong(outBuf, outLen);

	return Py_BuildValue("i", sent);
}

static PyMethodDef midi_methods[] =
{
	{"GetNumInDevs", PyGetNumberOfMidiInDevs, METH_VARARGS, NULL},
	{"GetInDevName", (PyCFunction)PyGetMidiInDevName, METH_VARARGS|METH_KEYWORDS, NULL},
	{"GetNumOutDevs", PyGetNumberOfMidiOutDevs, METH_VARARGS, NULL},
	{"GetOutDevName", (PyCFunction)PyGetMidiOutDevName, METH_VARARGS|METH_KEYWORDS, NULL},
	{"Request", (PyCFunction)PyMidiRequest, METH_VARARGS|METH_KEYWORDS, NULL},
	{"Send", (PyCFunction)PyMidiSend, METH_VARARGS|METH_KEYWORDS, NULL},
	{NULL, NULL, 0, NULL}
};

OPENMIDI_API void initmidi()
{
	Py_InitModule("midi", midi_methods);
}


