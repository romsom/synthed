// InsException.h: interface for the MrException class.
//
// Copyright (c) 2001, 2002 by John Bair
// ALL RIGHTS RESERVED
//
//////////////////////////////////////////////////////////////////////

#if !defined(AFX_MIDIEXCEPTION_H__05FAE472_6E6D_45F4_8923_7DA75C40052F__INCLUDED_)
#define AFX_MIDIEXCEPTION_H__05FAE472_6E6D_45F4_8923_7DA75C40052F__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

class MidiException  
{
public:
	MidiException();
	virtual ~MidiException();

	MidiException(const char* lpErr, const char* lpFile, int iLineNo);
	char sErrMsg[80];
	char sFileName[80];
	int iLineNumber;

};

#endif // !defined(AFX_MIDIEXCEPTION_H__05FAE472_6E6D_45F4_8923_7DA75C40052F__INCLUDED_)
