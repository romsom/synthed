// MidiOutWin.h: interface for the MidiOutWin class.
//
// Copyright (c) 2001, 2002 by John Bair
// ALL RIGHTS RESERVED
//
//////////////////////////////////////////////////////////////////////

#if !defined(AFX_MIDIOUTWIN_H__7C519DD3_EC72_4626_87C8_E6D6DAF3F261__INCLUDED_)
#define AFX_MIDIOUTWIN_H__7C519DD3_EC72_4626_87C8_E6D6DAF3F261__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

#include "wtypes.h"
#include "Mmsystem.h"

#include "SysexMessage.h"

#ifndef MIDI_NUM_RETRIES
#define MIDI_NUM_RETRIES 5
#endif

class MidiOutWin  
{
friend class MidiOut;
friend class MidiInOut;

private:
	int index;
	int iSerialNumber;
	HMIDIOUT hMidiOut;
	SysexMessage messageBuffer;
	bool bIsOpen;
	void UnprepareBuffer();

protected:
	int iDelay;
	int iRetries;

public:
	MidiOutWin(int index);
	virtual ~MidiOutWin(void);
	int OpenDevice(void);
	int SendShort(char cStatus, char cByte1, char cByte2);
	int SendLong(const char* pcSendBuffer, UINT uLen);
	int GetSerialNumber();
	void CloseDevice();

};

#endif // !defined(AFX_MIDIOUTWIN_H__7C519DD3_EC72_4626_87C8_E6D6DAF3F261__INCLUDED_)
