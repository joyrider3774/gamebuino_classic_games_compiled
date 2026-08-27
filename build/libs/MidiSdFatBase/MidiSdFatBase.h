/*
 * MidiSdFatBase.h -- RECONSTRUCTION, not the original file.
 *
 * angyongen's makerbuino-midi ("Makerbuino MIDI file player") opens with
 *
 *     #include <MidiSdFatBase.h>
 *     #include <midi2.h>
 *     ...
 *     MIDIFileTrack file;
 *     midiFileSdFat midi_file;
 *
 * and its README lists the dependencies as SPI, greiman/SdFat, "my sound
 * library" (angyongen/Sound4), "my modified gamebuino library" and "my midi
 * library" (angyongen/Midi2).  Sound4 and Midi2 were both published on
 * 2020-05-18, the same day the sketch's sources were uploaded, and are used
 * here as-is.  The glue between Midi2 and SdFat -- this header -- never was:
 * it is in none of his repositories, in no branch or deleted commit of them,
 * in the gamebuino_classic_source_codes archive, or in the sibling
 * gamebuino_classic_vircon32 tree.  What follows is therefore written from
 * scratch against the two things that do survive: the API the sketch calls,
 * and the input contract of Midi2's MIDIWrapper.
 *
 * Reconstructed API, all of it exercised by makerbuino-midi.ino and
 * mainplayer.ino:
 *
 *   MIDIFileTrack           an SdFat FatFile (the sketch calls openNext,
 *                           getSFN, getName and close on it directly) that
 *                           also carries the running-status and
 *                           bytes-left-in-chunk state of the track being read.
 *   midiFileSdFat::loadFile(track)        parse MThd, find the first MTrk
 *   midiFileSdFat::format()               MThd format word
 *   midiFileSdFat::time_division()        MThd division word (the sketch
 *                                         treats it as PPQ)
 *   midiFileSdFat::tracks()               MThd track count
 *   midiFileSdFat::readable_tracks()      MTrk chunks actually found
 *   midiFileSdFat::findNextNoteEvent(track, event)
 *                           advance through the track until a note-on or
 *                           note-off, filling `event` (delta, event_status,
 *                           data[0..1]); false at end of track.
 *
 * MIDIWrapper<I,S>::readMidiEvent does the event decoding; it asks for bytes
 * through `input.read(buf, count, state)`, which is what MidiSdFatReader and
 * MIDIFileTrack provide here.  Two things it does not do are handled below:
 * it never consumes a meta event's payload (the call that would is commented
 * out in midi2.h), and its system-message test `event_status & 0xF == 0xF`
 * parses as `event_status & 1`, so it does not read a length for 0xF0/0xF7
 * sysex at all.  Both are skipped here so the byte stream stays aligned.
 *
 * Tempo (FF 51) is deliberately not acted on: mainplayer.ino keeps its own
 * `uspb = 500000` and never asks for a tempo change, so honouring it here
 * would alter how the sketch plays.
 */
#ifndef MIDISDFATBASE_H
#define MIDISDFATBASE_H

#include <Arduino.h>
#include <SdFat.h>
#include <midi2.h>

class MIDIFileTrack : public FatFile {
  public:
    MIDIWrapperState state;  //running status carried between events
    uint32_t remaining;      //bytes left in the current MTrk chunk

    MIDIFileTrack() : remaining(0) {
      state.previous_event_status = 0;
    }

    void beginTrack(uint32_t length) {
      state.previous_event_status = 0;
      remaining = length;
    }

    //read at most `count` bytes, never past the end of the chunk
    int readTrack(void* buf, uint16_t count) {
      if (remaining == 0) return -1;
      if (count > remaining) count = (uint16_t)remaining;
      int n = FatFile::read(buf, count);
      if (n > 0) remaining -= (uint32_t)n;
      return n;
    }

    //step over a payload this reader does not care about
    bool skipTrack(uint32_t count) {
      if (count > remaining) count = remaining;
      if (count == 0) return true;
      if (!seekCur((int32_t)count)) {
        remaining = 0;
        return false;
      }
      remaining -= count;
      return true;
    }
};

//the byte source MIDIWrapper reads through
class MidiSdFatReader {
  public:
    int read(void* buf, uint16_t count, MIDIFileTrack & track) {
      return track.readTrack(buf, count);
    }
};

class midiFileSdFat {
  public:
    midiFileSdFat() : _format(0), _tracks(0), _division(0), _readable(0) {}

    uint16_t format() {
      return _format;
    }
    uint16_t time_division() {
      return _division;
    }
    uint16_t tracks() {
      return _tracks;
    }
    uint16_t readable_tracks() {
      return _readable;
    }

    /* Read the MThd header of an already-open file, count its MTrk chunks and
       leave `f` positioned on the first one. */
    bool loadFile(MIDIFileTrack & f) {
      _format = _tracks = _division = _readable = 0;
      f.remaining = 0;
      if (!f.isOpen()) return false;
      if (!f.seekSet(0)) return false;

      uint8_t chunk[8];
      if (f.FatFile::read(chunk, 8) != 8) return false;
      if (memcmp_P(chunk, PSTR("MThd"), 4) != 0) return false;
      uint32_t headerLength = be32(chunk + 4);
      if (headerLength < 6) return false;

      uint8_t header[6];
      if (f.FatFile::read(header, 6) != 6) return false;
      _format = be16(header);
      _tracks = be16(header + 2);
      _division = be16(header + 4);
      if (headerLength > 6 && !f.seekCur((int32_t)(headerLength - 6))) return false;

      uint32_t firstTrack = 0;
      uint32_t firstLength = 0;
      while (f.FatFile::read(chunk, 8) == 8) {
        uint32_t chunkLength = be32(chunk + 4);
        if (memcmp_P(chunk, PSTR("MTrk"), 4) == 0) {
          if (_readable == 0) {
            firstTrack = f.curPosition();
            firstLength = chunkLength;
          }
          ++_readable;
        }
        if (!f.seekCur((int32_t)chunkLength)) break;
      }
      if (_readable == 0) return false;

      if (!f.seekSet(firstTrack)) return false;
      f.beginTrack(firstLength);
      return true;
    }

    /* Advance through the loaded track until the next note-on or note-off.
       Everything else is stepped over.  false once the track is exhausted or
       its end-of-track meta event is reached. */
    bool findNextNoteEvent(MIDIFileTrack & f, midiEvent & e) {
      while (f.remaining) {
        e.length = 0;
        if (_midi.readMidiEvent(e, f.state, f, _reader) <= 0) break;

        uint8_t type = (e.event_status >> 4) & 0xF;
        if (type == midiSystem) {
          if (e.event_status == 0xF0 || e.event_status == 0xF7) {
            //readMidiEvent's meta branch does not fire for these, so their
            //length is still in the stream
            uint32_t length = 0;
            if (_midi.readVarLen(length, f, _reader) < 0) break;
            if (!f.skipTrack(length)) break;
          } else {
            if (e.event_status == 0xFF && e.data[0] == 0x2F) break; //end of track
            if (!f.skipTrack(e.length)) break;
          }
          continue;
        }
        if (type == midiNoteOn || type == midiNoteOff) return true;
      }
      f.remaining = 0;
      return false;
    }

  private:
    static uint16_t be16(const uint8_t* p) {
      return ((uint16_t)p[0] << 8) | p[1];
    }
    static uint32_t be32(const uint8_t* p) {
      return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
             ((uint32_t)p[2] << 8) | p[3];
    }

    MIDIWrapper<MidiSdFatReader, MIDIFileTrack> _midi;
    MidiSdFatReader _reader;
    uint16_t _format;
    uint16_t _tracks;
    uint16_t _division;
    uint16_t _readable;
};

#endif /* MIDISDFATBASE_H */
