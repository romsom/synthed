// SysexMessage.h: interface for the SysexMessage class.
//
// Copyright (c) 2001, 2002 by John Bair
// ALL RIGHTS RESERVED
//
//////////////////////////////////////////////////////////////////////

#if !defined(AFX_SYSEXMESSAGE_H__8C141E5F_F829_435F_8308_69B2BBF21DA2__INCLUDED_)
#define AFX_SYSEXMESSAGE_H__8C141E5F_F829_435F_8308_69B2BBF21DA2__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

#include "wtypes.h"
#include "Mmsystem.h"

#define SYSEX_BUFFER_LEN 256

class SysexMessage  
{
private:
	MIDIHDR header;
	char* pcBuffer;
	int iBufferLen;
public:
	SysexMessage();
	SysexMessage(int iBufferSize);
	virtual ~SysexMessage();
	int Resize(int iLen);
	void Reset();
	LPMIDIHDR GetMidiHeader();
	int SetSysexMessage(const char* lpSendMsg, int iLen);
	int GetSysexMessage(char* lpcSendBuffer, int iMaxLen);
};

#endif // !defined(AFX_SYSEXMESSAGE_H__8C141E5F_F829_435F_8308_69B2BBF21DA2__INCLUDED_)
