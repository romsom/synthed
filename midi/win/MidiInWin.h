// MidiInWin.h: interface for the MidiWinService class.
//
// Copyright (c) 2001, 2002 by John Bair
// ALL RIGHTS RESERVED
//
//////////////////////////////////////////////////////////////////////

#if !defined(AFX_MIDIINWIN_H__E4AAD4A4_5D95_461F_BD70_C8DA98656DDF__INCLUDED_)
#define AFX_MIDIINWIN_H__E4AAD4A4_5D95_461F_BD70_C8DA98656DDF__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

#include "wtypes.h"
#include "Mmsystem.h"

#include "SysexMessage.h"

#ifndef MIDI_NUM_RETRIES
#define MIDI_NUM_RETRIES 5
#endif

#ifndef MIDI_BUFFER_LEN
#define MIDI_BUFFER_LEN 1024
#endif

// static global Callback funtion
void CALLBACK ProcessMidiMessage(HMIDIIN hmi, UINT wMsg, DWORD dwInstance, DWORD param1, DWORD param2);

class MidiInWin
{
friend class MidiInOut;

private:
	HMIDIIN hMidiIn;
	SysexMessage* messageBuffer;
	int iNumBuffers;
	HANDLE hEvent;
	int index;
	bool bIsOpen;
	bool bIsStarted;
	int iMsgBits;
	int iNumMessagesExpected;
	int iNumMessagesReceived;

protected:
	int iDelay;
	int iRetries;

public:
	MidiInWin(int index);
	MidiInWin(int index, int iBufferSize);
	virtual ~MidiInWin(void);
	void Resize(int iBufferSize);
	int OpenDevice(void);
	HANDLE Start(int iBufferLen, int iNumMessagesToExpect);
	int GetNumMessagesReceived();
	void Unprepare();
	int Reset();
	int Stop();
	int GetStatus();
	int GetHeaderStatus();
	HANDLE GetEvent();
	void RaiseEvent(DWORD midiInputMsg, LPMIDIHDR lpHmi);
	int GetSysexMessage(char* pcRcvBuffer, int iMaxLen, int iMsgIndex = 0);
	int CloseDevice();
};

#endif // !defined(AFX_MIDIINWIN_H__E4AAD4A4_5D95_461F_BD70_C8DA98656DDF__INCLUDED_)
