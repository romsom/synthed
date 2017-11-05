// MidiInWin.cpp: implementation of the MidiInWin class.
//
// Copyright (c) 2001, 2002 by John Bair
// ALL RIGHTS RESERVED
//
//////////////////////////////////////////////////////////////////////

#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif

#include "stdafx.h"
#include "stdio.h"

#include "MidiException.h"
#include "MidiInWin.h"

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

MidiInWin::MidiInWin(int idx)
{
	index = idx;
	iRetries = MIDI_NUM_RETRIES;
	messageBuffer = NULL;
	Resize(MIDI_BUFFER_LEN);

	// Create a synchronization event that will be used to determine
	// when MIDI sysex messages have been received
	hEvent = CreateEvent(NULL, true, false, NULL);

	bIsOpen = false;
	bIsStarted = false;
}

MidiInWin::MidiInWin(int idx, int iBufferSize)
{
	char szName[FILENAME_MAX];

	index = idx;
	iRetries = MIDI_NUM_RETRIES;
	messageBuffer = NULL;
	Resize(iBufferSize);

	// Create a synchronization event that will be used to determine
	// when MIDI sysex messages have been received
	sprintf(szName, "/MidiInWin/%x", this);
	hEvent = CreateEvent(NULL, true, false, szName);

	bIsOpen = false;
	bIsStarted = false;
}

MidiInWin::~MidiInWin()
{
	try {
		CloseDevice();
		CloseHandle(hEvent);
	}
	catch (MidiException* e) {
		delete e;
	}
	catch (...) {
	}

	if (messageBuffer) {
		delete[] messageBuffer;
		messageBuffer = NULL;
	}
}

void MidiInWin::Resize(int iBufferSize)
{
	if (messageBuffer) {
		delete[] messageBuffer;
		messageBuffer = NULL;
	}

	iNumBuffers = (iBufferSize / SYSEX_BUFFER_LEN) + 1;

	messageBuffer = new SysexMessage[iNumBuffers];
	if (!messageBuffer)
		throw new MidiException("Out of memory", __FILE__, __LINE__);
}

// Open the MIDI device for input
int MidiInWin::OpenDevice(void)
{
	if (!bIsOpen) {
		// open the device
		if (midiInOpen(&hMidiIn, (UINT)index, (DWORD)ProcessMidiMessage, (DWORD)this, CALLBACK_FUNCTION))
			throw new MidiException("Cannot open MIDI device for input", __FILE__, __LINE__);

		bIsOpen = true;
	}

	return 0;
}

// Unprepare the MIDI buffer
void MidiInWin::Unprepare()
{
	int iRet;
	int iCount;
	char szErrorMsg[FILENAME_MAX];

	for (int i = 0; i < iNumBuffers; i++) {
		// Unprepare the sysex buffer
		iCount = 0;
		do {
			iRet = midiInUnprepareHeader(hMidiIn, messageBuffer[i].GetMidiHeader(), sizeof(MIDIHDR));
			if (iRet == MIDIERR_STILLPLAYING) {
				Sleep(iDelay);
				iCount++;
			}
		} while (iRet == MIDIERR_STILLPLAYING && iCount < iRetries);

		if (iRet) {
			sprintf(szErrorMsg, "Error 0x%X unpreparing MIDI input buffer", iRet);
			throw new MidiException(szErrorMsg, __FILE__, __LINE__);
		}

		// Zero out and reset the message buffer
		messageBuffer[i].Reset();
	}

}

// Start receiving
HANDLE MidiInWin::Start(int iBufferLen, int iNumMessagesToExpect)
{
	int iRet;
	char szErrorMsg[FILENAME_MAX];

	// Clear debugging bitfield
	iMsgBits = 0;

	// Stop if already started
	if (bIsStarted)
		Stop();

	// Get any unused buffers back
	Reset();

	// Make sure there are enough buffers
	Resize(iBufferLen);

	iNumMessagesReceived = 0;
	iNumMessagesExpected = iNumMessagesToExpect;

	// Reset the synchronization event
	iRet = ResetEvent(hEvent);
	if (!iRet) { // Non-zero is success
		sprintf(szErrorMsg, "Error 0x%X resetting synchronization event", iRet);
		throw new MidiException(szErrorMsg, __FILE__, __LINE__);
	}

	for (int i = 0; i < iNumBuffers; i++) {
		// Prepare the sysex buffer
		iRet = midiInPrepareHeader(hMidiIn, messageBuffer[i].GetMidiHeader(), sizeof(MIDIHDR));
		if (iRet) {
			sprintf(szErrorMsg, "Error 0x%X preparing MIDI input buffer", iRet);
			throw new MidiException(szErrorMsg, __FILE__, __LINE__);
		}

		// Attach the sysex buffer
		iRet = midiInAddBuffer(hMidiIn, messageBuffer[i].GetMidiHeader(), sizeof(MIDIHDR));
		if (iRet) {
			sprintf(szErrorMsg, "Error 0x%X adding MIDI input buffer", iRet);
			throw new MidiException(szErrorMsg, __FILE__, __LINE__);
		}
	}

	// Start receiving
	iRet = midiInStart(hMidiIn);
	if (iRet) {
		sprintf(szErrorMsg, "Error 0x%X starting MIDI input device", iRet);
		throw new MidiException(szErrorMsg, __FILE__, __LINE__);
	}

	bIsStarted = true;

	// return a handle to the synchronization event
	return hEvent;
}


// Stop receiving
int MidiInWin::Stop()
{
	int iRet = 0;
	char szErrorMsg[FILENAME_MAX];

	if (bIsStarted) {
		// Reset the synchronization event
		iRet = ResetEvent(hEvent);
		if (!iRet) { // Non-zero is success
			sprintf(szErrorMsg, "Error 0x%X resetting synchronization event", iRet);
			throw new MidiException(szErrorMsg, __FILE__, __LINE__);
		}

		// Stop
		iRet = midiInStop(hMidiIn);
		if (iRet) {
			sprintf(szErrorMsg, "Error 0x%X stopping MIDI input device", iRet);
			throw new MidiException(szErrorMsg, __FILE__, __LINE__);
		}
		bIsStarted = false;
	}

	return iRet;
}

int MidiInWin::Reset()
{
	int iRet = 0;

	if (bIsOpen) {
		iRet = midiInReset(hMidiIn);
		Unprepare();
	}

	return iRet;
}

// Signal that a MIDI sysex message has been received
void MidiInWin::RaiseEvent(DWORD midiInputMsg, LPMIDIHDR lpHmi)
{
	UINT uLen;
	char c;

	// Signal that a sysex message has been received
	// process MIM (Midi Input Message)
	switch (midiInputMsg) {
	case MIM_OPEN:
		iMsgBits |= 1;
		break;
	case MIM_CLOSE:
		iMsgBits |= 2;
		break;
	case MIM_DATA:
		iMsgBits |= 4;
		break;
	case MIM_LONGDATA:
		iMsgBits |= 8;

		uLen = lpHmi->dwBytesRecorded;
		if (uLen < lpHmi->dwBufferLength) {
			if (++iNumMessagesReceived >= iNumMessagesExpected)
				SetEvent(hEvent);
		}
		else {
			c = lpHmi->lpData[uLen - 1];
			if (c == '\xf7') {
				if (++iNumMessagesReceived >= iNumMessagesExpected)
					SetEvent(hEvent);
			}
		}
		break;
	case MIM_ERROR:
		iMsgBits |= 16;
		break;
	case MIM_LONGERROR:
		iMsgBits |= 32;
		break;
	case MIM_MOREDATA:
		iMsgBits |= 64;
		break;
	}
}

int MidiInWin::GetStatus()
{
	return iMsgBits;
}

// Copy the received sysex message into the passed buffer
int MidiInWin::GetSysexMessage(char* pcRcvBuffer, int iMaxLen, int iMsgIndex /* = 0 */)
{
	char c;
	char pcBuffer[SYSEX_BUFFER_LEN];
	int i;
	int iIndex;
	int iLen = 0;
	char* pc;

	// Zero out the destination buffer
	memset(pcRcvBuffer, 0, iMaxLen);

	iIndex = 0;

	// Skip to the requested message index
	for (i = 0; i < iNumBuffers && iIndex < iMsgIndex; i++) {
		iLen = messageBuffer[i].GetSysexMessage(pcBuffer, sizeof(pcBuffer));
		c = pcBuffer[iLen - 1];
		if (c == '\xf7')
			iIndex++;
	}

	pc = pcRcvBuffer;
	iLen = 0;
	while (i < iNumBuffers) {
		iLen += messageBuffer[i].GetSysexMessage(pc, iMaxLen - iLen);
		if (iLen) {
			c = pcRcvBuffer[iLen - 1];
			if (c == '\xf7')
				break;
		}
		pc = pcRcvBuffer + iLen;
		i++;
	}

	return iLen;
}

// Close the MIDI device
int MidiInWin::CloseDevice()
{
	int iRet = 0;
	char szErrorMsg[FILENAME_MAX];

	Stop();
	Reset();

	if (bIsOpen) {
		iRet = midiInClose(hMidiIn);
		if (iRet) {
			sprintf(szErrorMsg, "Error 0x%X closing MIDI input device", iRet);
			throw new MidiException(szErrorMsg, __FILE__, __LINE__);
		}
		bIsOpen = false;
	}

	return iRet;
}

// This is defined outside the MidiInWin class but is included here because it is a way to get 
// Windows to notify a thread that a sysex message has been received
void CALLBACK ProcessMidiMessage(HMIDIIN hmi, UINT wMsg, DWORD dwInstance, DWORD param1, DWORD param2)
{
	LPMIDIHDR lpMidiHdr;

	if (dwInstance) {
		lpMidiHdr = (LPMIDIHDR)param1;
		((MidiInWin*)dwInstance)->RaiseEvent(wMsg, lpMidiHdr);
	}
}

// return a handle to the synchronization event
HANDLE MidiInWin::GetEvent()
{
	return hEvent;
}

// return the number of sysex messages that have been received
int MidiInWin::GetNumMessagesReceived()
{
	return iNumMessagesReceived;
}