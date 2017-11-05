#include "MidiException.h"
#include "MidiInWin.h"
#include "MidiOutWin.h"


// The following ifdef block is the standard way of creating macros which make exporting 
// from a DLL simpler. All files within this DLL are compiled with the OPENMIDI_EXPORTS
// symbol defined on the command line. this symbol should not be defined on any project
// that uses this DLL. This way any other project whose source files include this file see 
// OPENMIDI_API functions as being imported from a DLL, wheras this DLL sees symbols
// defined with this macro as being exported.
#ifdef OPENMIDI_EXPORTS
#define OPENMIDI_API __declspec(dllexport)
#else
#define OPENMIDI_API __declspec(dllimport)
#endif

#define MIDI_ERROR_SIZE 512

// This is an example of an exported variable
//extern OPENMIDI_API int nOpenmidi;

// Exported functions
OPENMIDI_API int GetNumberOfMidiInDevs(void);
OPENMIDI_API int GetNumberOfMidiOutDevs(void);
OPENMIDI_API int GetMidiInDevName(int index, char* lpszDeviceName, int iLen);
OPENMIDI_API int GetMidiOutDevName(int index, char* lpszDeviceName, int iLen);

// This class is exported from the openmidi.dll
class OPENMIDI_API MidiOut {
protected:
	MidiOutWin* out;
	int iOutIndex;
	int iBlockSize;
	char szLastError[MIDI_ERROR_SIZE];
public:
	MidiOut(int idx, int blocksize, int delay);
	virtual ~MidiOut(void);

	int GetLastError(char* lpszBuffer, int iLen);
	int SendShort(char cStatus, char cByte1, char cByte2);
	int SendLong(const char* lpcSendBuffer, int iSendLen);
};

class OPENMIDI_API MidiInOut : MidiOut {
private:
	MidiInWin* in;
	int iInIndex;
	int iTimeout;
public:
	MidiInOut(int iInIndex, int iOutIndex, int blocksize, int delay, int timeout);
	virtual ~MidiInOut(void);

	int Request(char* lpcRcvBuffer, int iRcvLen, 
		const char* lpcSendBuffer, int iSendLen, int iNumRepliesToExpect = 1);
};

extern "C" OPENMIDI_API void initmidi();