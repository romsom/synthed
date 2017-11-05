// MidiOutWin.cpp: implementation of the MidiOutWin class.
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

#include "MidiOutWin.h"
#include "MidiException.h"

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

MidiOutWin::MidiOutWin(int idx)
{
	index = idx;
	iRetries = MIDI_NUM_RETRIES;
	bIsOpen = false;
	iSerialNumber = 0;
}

MidiOutWin::~MidiOutWin(void)
{
	try {
		CloseDevice();
	}
	catch (MidiException* e) {
		delete e;
	}
	catch (...) {
	}
}

int MidiOutWin::OpenDevice(void)
{
	int iRet;

	if (!bIsOpen) {
		// open the device
		iRet = midiOutOpen(&hMidiOut, (UINT)index, NULL, NULL, NULL);
		if (!iRet)
			bIsOpen = true;
	}

	return iRet;
}

int MidiOutWin::SendShort(char cStatus, char cByte1, char cByte2)
{
	char szErrorMsg[FILENAME_MAX];
	int iResult;
	UINT msg;

	msg = (cByte2 * 0x10000) + (cByte1 * 0x100) + (cStatus & 0xff);

	// Send the sysex message
	iResult = midiOutShortMsg(hMidiOut, msg);
	if (iResult) {
		sprintf(szErrorMsg, "Error 0x%X sending MIDI message", iResult);
		throw new MidiException(szErrorMsg, __FILE__, __LINE__);
	}

	iSerialNumber++;

	return iResult;
}

int MidiOutWin::SendLong(const char* pcSendBuffer, UINT uLen)
{
	char szErrorMsg[FILENAME_MAX];
	int iResult;

	// Unprepare the sysex buffer
	UnprepareBuffer();

	// Write sysex message into the buffer and set the buffer length
	messageBuffer.SetSysexMessage(pcSendBuffer, uLen);

	// Prepare the sysex buffer
	iResult = midiOutPrepareHeader(hMidiOut, messageBuffer.GetMidiHeader(), sizeof(MIDIHDR));
	if (iResult) {
		sprintf(szErrorMsg, "Error 0x%X preparing MIDI out header", iResult);
		throw new MidiException(szErrorMsg, __FILE__, __LINE__);
	}

	// Send the sysex message
	iResult = midiOutLongMsg(hMidiOut, messageBuffer.GetMidiHeader(), sizeof(MIDIHDR));
	if (iResult) {
		sprintf(szErrorMsg, "Error 0x%X sending MIDI message", iResult);
		throw new MidiException(szErrorMsg, __FILE__, __LINE__);
	}

	iSerialNumber++;

	return iResult;
}

// Close the MIDI device
void MidiOutWin::CloseDevice()
{
	if (bIsOpen) {
		UnprepareBuffer();
		midiOutClose(hMidiOut);

		bIsOpen = false;
	}
}

void MidiOutWin::UnprepareBuffer()
{
	char szErrorMsg[FILENAME_MAX];
	int iResult;
	int iCount;

	// Unprepare the sysex buffer
	iCount = 0;
	do {
		iResult = midiOutUnprepareHeader(hMidiOut, messageBuffer.GetMidiHeader(), sizeof(MIDIHDR));
		if (iResult == MIDIERR_STILLPLAYING) {
			Sleep(iDelay);
			iCount++;
		}
	} while (iResult == MIDIERR_STILLPLAYING && iCount < iRetries);

	if (iResult) {
		sprintf(szErrorMsg, "Error 0x%X unpreparing MIDI out header", iResult);
		throw new MidiException(szErrorMsg, __FILE__, __LINE__);
	}

	// Zero out the message buffer
	messageBuffer.Reset();
}

int MidiOutWin::GetSerialNumber()
{
	return iSerialNumber;
}