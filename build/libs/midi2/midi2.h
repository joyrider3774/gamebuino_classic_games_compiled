
#ifndef MIDI2_H
#define MIDI2_H
enum midiStatusType
{
  //status types below 0x8 are running status events
  midiNoteOff = 0x8,
  midiNoteOn = 0x9, //if velocity 0, it is a midiNoteOff at velocity 40
  midiPolyphonicPressure = 0xA,
  midiController = 0xB,
  midiProgramChange = 0xC,
  midiChannelPressure = 0xD,
  midiPitchBend = 0xE,
  midiSystem = 0xF, // calling application must read or discard the data bytes before continuing
};

struct midiEvent
{
	uint32_t delta;
	uint8_t event_status;
     uint32_t length;
	uint8_t data[2];
};

struct MIDIWrapperState
{
	uint8_t previous_event_status;
};

template<class I, class S>
class MIDIWrapper
{
	public:
int readVarLen(uint32_t & output, S & state, I & input)
{
  register uint32_t value;
  register uint8_t b;
  register uint8_t c;
  value = 0;
  for (b = 1; b <= 4; ++b)
  {
    if (input.read(&c, 1, state) < 1) return -1;
    value = (value << 7) | (c & 0x7f);
    //Serial.println(c);
    if (c < 0x80) {output = value; return b;}
  } 
  return -2;
  return true;
}

int readMidiEvent(midiEvent & e, MIDIWrapperState & state, S & inputstate, I & input)
{
	register uint8_t bytesRead;
	register uint8_t bytesReadTotal;
	
	register uint8_t byte1; // determines running status
	register uint8_t event_status;
	
	bytesReadTotal = 0;
	
	if ((bytesRead = readVarLen(e.delta, inputstate, input)) < 0) return -bytesReadTotal;//{Serial.println(bytesRead);return -bytesReadTotal;}
	bytesReadTotal += bytesRead;
	if ((bytesRead = input.read(&byte1, 1, inputstate)) < 1) return -bytesReadTotal;
	bytesReadTotal += bytesRead;
	
	//Serial.println(e.delta);
	//Serial.println(byte1);
	
	if (byte1 & 0x80)
	{
		event_status = byte1;
	} else {
		//Serial.print(byte1);
		//http://somascape.org/midi/tech/mfile.html
		// "If the first (status) byte is less than 128 (hex 80),
		// this implies that running status is in effect,
		// and that this byte is actually the first data byte
		// (the status carrying over from the previous MIDI event)"
		
		uint8_t previous_event_status = state.previous_event_status;
		if (!((previous_event_status > 0xF0) && (previous_event_status < 0xF7)))
		{
			Serial.print(F("running status event, using previous "));
			Serial.println(previous_event_status);
			event_status = previous_event_status;
		} else {
			//previous_event_type was system exclusive message or system common message
			return -bytesReadTotal;
		}
	}
	state.previous_event_status = event_status;
	e.event_status = event_status;
	
	//HI_NIBBLE = (event_status >> 4) & 0xF;
	//LO_NIBBLE = (event_status) & 0xF;
	
	Serial.print(F("event_status:"));
	Serial.println(event_status, HEX);
	
	switch ((event_status >> 4) & 0xF)
	{
		case (midiNoteOn)://note on(key,velocity[default 40 or 0,alternate note off])
		case (midiNoteOff)://note off(key,velocity)
		case (midiPolyphonicPressure)://polyphonic key pressure(key,pressure)
		case (midiController):
		//controller change, controller no (0x0-0x77), controller value
		//channel mode message, message (0x78-0x7F), [message dependent value]
		case (midiPitchBend)://pitch bend, 2 bytes following, lsb, msb
		
		e.length = 2;
		
		if (byte1 & 0x80) {
			if ((bytesRead = input.read(e.data, 2, inputstate)) < 2) return -bytesReadTotal;
			bytesReadTotal += bytesRead;
		} else {
			e.data[0] = byte1;
			if ((bytesRead = input.read(&e.data[1], 1, inputstate)) < 1) return -bytesReadTotal;
			bytesReadTotal += bytesRead;
		}
	
		break;
		case (midiProgramChange)://program change 1 byte following, program no
		case (midiChannelPressure)://channel key pressure (aftertouch) 1 byte following, pressure value
		e.length = 1;
		
		if (byte1 & 0x80) {
			if ((bytesRead = input.read(&e.data[0], 1, inputstate)) < 1) return -bytesReadTotal;
			bytesReadTotal += bytesRead;
		} else {
			e.data[0] = byte1;
		}
		e.data[1] = 0;
		break;
		case (midiSystem):
		//make sure to cancel running status if system exclusive message or system common message(all 0xF0 to 0xF7)
		//if (LO_NIBBLE < 0x7) inputstate->flags &= ~midiRunningStatusFlag;
		if (event_status & 0xF == 0xF)
		{
			//meta event
			Serial.println(F("metaEvent"));
			if (byte1 & 0x80) {
				if ((bytesRead = input.read(&e.data[0], 1, inputstate)) < 1) return -bytesReadTotal;
				bytesReadTotal += bytesRead;
			} else {
				e.data[0] = byte1;
			}
			Serial.print(F("type"));
			Serial.print(e.data[0], HEX);
			
			if ((bytesRead = readVarLen(e.length, inputstate, input)) < 0) return -bytesReadTotal;
			bytesReadTotal += bytesRead;
			
			Serial.print(F(" length"));
			Serial.println(e.length);
			//if (input.read(NULL, output.length, inputstate) < output.length) return false;
		}
		break;
		
		default:
		// code should not reach this point
		// Serial.print(F("error"));
		return -bytesReadTotal;
		break;
	}
	return bytesReadTotal;
}
};

#endif //MIDI2_H