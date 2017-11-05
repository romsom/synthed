// InsException.cpp: implementation of the InsException class.
//
// Copyright (c) 2001, 2002 by John Bair
// ALL RIGHTS RESERVED
//
// This is nothing more than a simple structure to hold exception info
//////////////////////////////////////////////////////////////////////

#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif

#include "stdafx.h"
#include "string.h"

#include "MidiException.h"

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

MidiException::MidiException()
{

}

MidiException::MidiException(const char* lpErr, const char* lpFile, int iLineNo)
{
	strncpy(sErrMsg, lpErr, sizeof(sErrMsg) - 1);
	sErrMsg[sizeof(sErrMsg) - 1] = 0;
	strncpy(sFileName, lpFile, sizeof(sFileName) - 1);
	sFileName[sizeof(sFileName) - 1] = 0;
	iLineNumber = iLineNo;
}

MidiException::~MidiException()
{

}
