
#include "Sound4.h"
#include <limits.h>

//http://interface.khm.de/index.php/lab/interfaces-advanced/arduino-dds-sinewave-generator/
//https://www.analog.com/media/en/training-seminars/tutorials/MT-085.pdf

//volatile byte counter1;             // var inside interrupt
//volatile byte counter4ms;           // incremented every 4ms

volatile uint32_t counter;



channelData _chan[channels];
// Timer2 Interrupt Service at 31372,550 KHz = 32uSec for 16Mhz clock
// this is the timebase REFCLOCK for the DDS generator
// FOUT = (M (PWM_INTERRUPT_FREQUENCY)) / (2 ^ 32)
// runtime : ???
//uint8_t last_pwm;

#define phaccu_bitshifts ((CHAR_BIT * sizeof(phase_accumulator_t)) - (CHAR_BIT * sizeof(amplitude_t)))


#define qsinewave(i) sample += pgm_read_byte_near(sinetable256 + (uint8_t)((_chan[i].phaccu += _chan[i].tword_m) >> phaccu_bitshifts)) >> bitshifts;
#define qsquarewave(i) if (((_chan[i].phaccu += _chan[i].tword_m) >> phaccu_bitshifts) < ((1<<(CHAR_BIT * sizeof(amplitude_t)))/2)) sample += ((1<<(CHAR_BIT * sizeof(amplitude_t)))-1) >> bitshifts;

#define qwave(i) qsquarewave(i)//qsinewave(i)
	
//#pragma GCC push_options
//#pragma GCC optimize ("unroll-loops")
ISR(PWM_INTERRUPT) {
	++counter;
	//pwm_set_value(last_pwm);
	// use upper 8 bits of phase accumulator to generate sample
	register amplitude_t sample = 0;
#if(channels > 0)
		qwave(0);
#endif
#if(channels > 1)
		qwave(1);
#endif
#if(channels > 2)
		qwave(2);
#endif
#if(channels > 3)
		qwave(3);
#endif
#if(channels > 4)
		qwave(4);
#endif
#if(channels > 5)
		qwave(5);
#endif
#if(channels > 6)
		qwave(6);
#endif
#if(channels > 7)
		qwave(7);
#endif
#if(channels > 8)
		qwave(8);
#endif
	pwm_set_value(255-sample);
	//last_pwm = sample; //generate for next cycle
	//if(++counter1 == 125) {counter1=0;++counter4ms;}// increment every 4 ms
}
//#pragma GCC pop_options

inline void Sound4::setChannel(uint8_t channel, amplitude_t volume, frequency_t freq)  {
	_chan[channel].tword_m=pow(2.0, CHAR_BIT * sizeof(phase_accumulator_t))*freq/PWM_INTERRUPT_FREQUENCY;
	//for (uint8_t i = 0; i < channels; i++) _chan[i].phaccu = 0;
}

void Sound4::begin() {
	noInterrupts();
	//timer2_set_mode(1);
	timer2_set_mode(3); //fast pwm
	timer2_set_prescaler(1);
	timer2_b_noninverting();
	timer2_b_enableOutput();
     timer2_enable_overflow_interrupt();
	interrupts();
}

inline frequency_t Sound4::getFrequencyForPitch(uint8_t pitch)
{
	//return pgm_read_float_near(&midinotefreqtable[pitch]);
	return 440 * pow(2.0, ((double)(pitch-69))/12);
}


void Sound4::playNote(uint8_t channel, uint8_t volume, uint8_t note) {
	setChannel(channel, volume, getFrequencyForPitch(note));
}

void Sound4::playNote(uint8_t volume, uint8_t note) {
	for (uint8_t channel = 0; channel < channels; channel++) {
		if (_chan[channel].volume == 0)
		{
			playNote(channel, volume, note);
		}
    }
}
void Sound4::stopNote(uint8_t channel) {
	setChannel(channel, 0, 0);
}

void Sound4::stopNote() {
	for (uint8_t channel = 0; channel < channels; channel++) {
		stopNote(channel);
	}
}

void Sound4::test() {
	uint8_t channel;
	for (uint8_t pitch = 0; pitch < 108; pitch++) {
		uint8_t reversepitch = 108 - pitch - 1;
		frequency_t freq = getFrequencyForPitch(reversepitch);
		Serial.print(reversepitch);
		Serial.print(" ");
		Serial.print(freq);
		for (channel = 0; channel < channels; channel++) {
			Serial.print(F("  \tch"));
			Serial.print(channel);
			setChannel(channel, 255, freq);
			delay(80);
		}
		Serial.println();
		delay(1000);
		stopNote();
	}
}

uint32_t Sound4::micros()
{
	return counter * (256000000/F_CPU);
}


//channelData _chan[NUM_CHANNELS];
//uint8_t _rand = 1;
//uint64_t global_counter;

//const period_t CTC_TWICE_EIGHTH_INTERVAL = (CTC_VALUE*2); //=((CTC_VALUE*CTC_PRESCALER_CLOCKS)/8)*2
/*
static inline uint8_t generateChannelOutput(uint8_t i)  {
	
	
}

*/
/*
ISR(CTC_INTERRUPT){
	
	amplitude_t output = 0;
	
	for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
		switch (_chan[i].type) {
		case channel_off:
		//return 0;
		break;
		case channel_squarewave:
		period_t curr_counts = _chan[i].counts;
		curr_counts += CTC_TWICE_EIGHTH_INTERVAL;
		if (curr_counts >= _chan[i].half_period) {
			curr_counts -= _chan[i].half_period;
			_chan[i].counts = curr_counts;
			if (_chan[i].state = !_chan[i].state) output += _chan[i].volume;
			//if (_chan[i].state = !_chan[i].state) return _chan[i].volume; // invert state and check new state
		}
		//return 0;
		break;
		case channel_randomwave:
		if (_chan[i].type == channel_randomwave) {
			_rand = 67 * _rand + 71;
			output += _rand % _chan[i].volume;
			//return _rand % _chan[i].volume;
		}
		//return 0;
		break;
		case channel_sinewave:
		output += generateSine(i);
		//return generateSine(i);
		break;
		}
		//output += generateChannelOutput(i);
	}
	pwm_set_value(output);
	//++global_counter;
}
#pragma GCC pop_options

#endif
*/


//uint64_t Sound3::micros()
//{
	//return (global_counter*CTC_INTERVAL)/clockCyclesPerMicrosecond();
//}






	/*
void Sound3::update(uint8_t i) {
#if(NUM_CHANNELS > 0)
	if(i>=NUM_CHANNELS)
		return;
	if (notePlaying[i]) {
		
		if(noteDuration[i] == 0){
			stopNote(i);
			//Serial.println("note end");
			return;
		} else {
			noteDuration[i]--;
		}
		
		if (instrumentNextChange[i] == 0) {
			//Serial.print("instr update:");
			//Serial.print("\t");
			
			//read the step data from the progmem and decode it
			uint16_t thisStep = pgm_read_word(&(instrumentData[i][1 + instrumentCursor[i]]));
			//Serial.print(thisStep, HEX);
			//Serial.print("\t");
			
			stepVolume[i] = thisStep & 0x0007;
			thisStep >>= 3;
			
			uint8_t stepNoise = thisStep & 0x0001;
			thisStep >>= 1;
			
			uint8_t stepDuration = thisStep & 0x003F;
			thisStep >>= 6;
			
			stepPitch[i] = thisStep;
			
			//apply the step settings
			instrumentNextChange[i] = stepDuration * prescaler;
			
			_chanNoise[i] = stepNoise;

			//Serial.print(stepPitch);
			//Serial.print("\t");
			//Serial.print(stepDuration);
			//Serial.print("\t");
			//Serial.print(stepNoise);
			//Serial.print("\t");
			//Serial.print(stepVolume);
			//Serial.print("\n");
			//Serial.print(_chanOutput[i]);
			//Serial.print("\n");
			
			instrumentCursor[i]++;
			
			if (instrumentCursor[i] >= instrumentLength[i]) {
				if (instrumentLooping[i]) {
					instrumentCursor[i] = instrumentLength[i] - instrumentLooping[i];
				} else {
					stopNote(i);
					//Serial.println("instrument end");
				}
			}
		}
		instrumentNextChange[i]--;
		
		commandsCounter[i]++;
		
		//UPDATE VALUES	
		//pitch
		outputPitch[i] = notePitch[i] + stepPitch[i] + patternPitch[i];
		if(arpeggioStepDuration[i]){
		  outputPitch[i] += commandsCounter[i] / arpeggioStepDuration[i] * arpeggioStepSize[i];
		}
		outputPitch[i] = (outputPitch[i] + NUM_PITCH) % NUM_PITCH; //wrap
		//volume
		outputVolume[i] = noteVolume[i];
		if(volumeSlideStepDuration[i]){
		  outputVolume[i] += commandsCounter[i] / volumeSlideStepDuration[i] * volumeSlideStepSize[i];
		}
		if(tremoloStepDuration[i]){
			outputVolume[i] += ((commandsCounter[i]/tremoloStepDuration[i]) % 2) * tremoloStepSize[i];
		}
		outputVolume[i] = constrain(outputVolume[i], 0, 9);
		if(notePitch[i] == 63){
			outputVolume[i] = 0;
		}
		noInterrupts();
		_chanHalfPeriod[i] = pgm_read_byte(_halfPeriods + outputPitch[i]);
		_chanOutput[i] = _chanOutputVolume[i] = (int(outputVolume[i] * chanVolumes[i] * stepVolume[i]) << (globalVolume)) / 128;
		//Serial.println(outputVolume[i]);
		interrupts();
	}
#endif
}


	*/


