// SysexMessage.cpp: implementation of the SysexMessage class.
//
// Copyright (c) 2001, 2002 by John Bair
// ALL RIGHTS RESERVED
//
// A wrapper for the Windows MIDIHDR structure. It's used to
// insert and retrieve sysex messages from Windows MIDI buffers
//////////////////////////////////////////////////////////////////////

#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif

#include "stdafx.h"

#include <stdlib.h>
#include <malloc.h>
#include <string.h>

#include "SysexMessage.h"

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

SysexMessage::SysexMessage()
{
	pcBuffer = NULL;
	iBufferLen = 0;
	Resize(SYSEX_BUFFER_LEN);
	Reset();
}

SysexMessage::SysexMessage(int iSize)
{
	pcBuffer = NULL;
	iBufferLen = 0;
	Resize(iSize);
	Reset();
}

SysexMessage::~SysexMessage()
{
	if (pcBuffer) {
		free(pcBuffer);
		pcBuffer = NULL;
	}
}

int SysexMessage::Resize(int iLen)
{
	if (iLen > iBufferLen) {
		if (pcBuffer)
			free(pcBuffer);
		pcBuffer = (char*)malloc(iLen);
		iBufferLen = iLen;
		Reset();
	}

	return iBufferLen;
}

void SysexMessage::Reset()
{
	memset(pcBuffer, 0, iBufferLen);
	memset(&header, 0, sizeof(header));

	header.dwBufferLength = iBufferLen;
	header.lpData = pcBuffer;
}

LPMIDIHDR SysexMessage::GetMidiHeader()
{
	return &header;
}

int SysexMessage::SetSysexMessage(const char* lpSendMsg, int iLen)
{
	if (iLen > iBufferLen)
		return -1;

	// Clear out the buffer
	memset(pcBuffer, 0, iBufferLen);

	// Copy the data into the buffer and set the mesage length
	memcpy(pcBuffer, lpSendMsg, iLen);
	header.dwBufferLength = iLen;

	return 0;
}

int SysexMessage::GetSysexMessage(char* lpcRcvBuffer, int iMaxLen)
{
	UINT uCount = 0;
	int iLen = 0;

	// Copy the data
	if (header.dwFlags & MHDR_DONE) {
		iLen = header.dwBytesRecorded;
		if (iLen > iMaxLen)
			iLen = iMaxLen;
		memcpy(lpcRcvBuffer, pcBuffer, iLen);
	}

	// Return the number of bytes received
	return iLen;
}
