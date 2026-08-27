#include "Arduino.h"

#define bitAt(position, input) ((input & (1UL<<position))>>position)
#define setto(register, target, bits) (register = target ? register | (bits) : register & ~(bits))
#define _set(register, bits) (register |= (bits))  
#define _clr(register, bits) (register &= ~(bits))

#if defined(ARDUINO_AVR_UNO)

#define TIMER1_A_CTRL TCCR1A   //TCCR1A COM1A1 COM1A0 COM1B1 COM1B0 -     -      WGM11  WGM10 
#define TIMER1_B_CTRL TCCR1B   //TCCR1B ICNC1  ICES1  -      WGM13  WGM12 CS12   CS11   CS10 
#define TIMER1_INT_MASK TIMSK1 //TIMSK1 -      -      ICIE1  -      -     OCIE1B OCIE1A TOIE1
#define TIMER1_A_INT_ENABLE _BV(OCIE1A)
#define TIMER1_MODE_0 _BV(WGM10)
#define TIMER1_MODE_1 _BV(WGM11)
#define TIMER1_MODE_2 _BV(WGM12)
#define TIMER1_MODE_3 _BV(WGM13)
#define TIMER1_CLOCK_0 _BV(CS10)
#define TIMER1_CLOCK_1 _BV(CS11)
#define TIMER1_CLOCK_2 _BV(CS12)
#define TIMER1_A_TYPE_0 _BV(COM1A0)
#define TIMER1_A_TYPE_1 _BV(COM1A1)

#define TIMER2_A_CTRL TCCR2A //TCCR2A   COM2A1 COM2A0 COM2B1 COM2B0 -     -     WGM21 WGM20 
#define TIMER2_B_CTRL TCCR2B //TCCR2B   FOC2A  FOC2B  -      -      WGM22 CS22  CS21  CS20 
#define TIMER2_MODE_0 _BV(WGM20)
#define TIMER2_MODE_1 _BV(WGM21)
#define TIMER2_MODE_2 _BV(WGM22)
#define TIMER2_CLOCK_0 _BV(CS20)
#define TIMER2_CLOCK_1 _BV(CS21)
#define TIMER2_CLOCK_2 _BV(CS22)
#define TIMER2_A_TYPE_0 _BV(COM2A0)
#define TIMER2_A_TYPE_1 _BV(COM2A1)
#define TIMER2_B_TYPE_0 _BV(COM2B0)
#define TIMER2_B_TYPE_1 _BV(COM2B1)

#define TIMER2_INT_MASK TIMSK2 //TIMSK2  – – – – – OCIE2B OCIE2A TOIE2
#define TIMER2_OVF_INT_ENABLE _BV(TOIE2)

#define PWM_INTERRUPT TIMER2_OVF_vect

__attribute__((always_inline)) inline void timer2_b_noninverting()
{
  _clr(TIMER2_A_CTRL, TIMER2_B_TYPE_0);
  _set(TIMER2_A_CTRL, TIMER2_B_TYPE_1);
}
__attribute__((always_inline)) inline void timer2_set_mode(uint8_t mode)
{
  setto(TIMER2_A_CTRL, bitAt(0, mode), TIMER2_MODE_0);
  setto(TIMER2_A_CTRL, bitAt(1, mode), TIMER2_MODE_1);
  setto(TIMER2_B_CTRL, bitAt(2, mode), TIMER2_MODE_2);
}

__attribute__((always_inline)) inline void timer2_set_prescaler(uint8_t prescaler)
{
  setto(TIMER2_B_CTRL, bitAt(0, prescaler), TIMER2_CLOCK_0);
  setto(TIMER2_B_CTRL, bitAt(1, prescaler), TIMER2_CLOCK_1);
  setto(TIMER2_B_CTRL, bitAt(2, prescaler), TIMER2_CLOCK_2);
}

__attribute__((always_inline)) inline void timer2_a_enableOutput()
{
  _set(DDRB, _BV(DDB3));
}

__attribute__((always_inline)) inline void timer2_a_disableOutput()
{
  _clr(DDRB, _BV(DDB3));
}

__attribute__((always_inline)) inline void timer2_b_enableOutput()
{
  _set(DDRD, _BV(DDD3));
}

__attribute__((always_inline)) inline void timer2_b_disableOutput()
{
  _clr(DDRD, _BV(DDD3));
}

inline __attribute__((always_inline))
void timer2_enable_overflow_interrupt()
{
	_set(TIMER2_INT_MASK, TIMER2_OVF_INT_ENABLE);
}

#define PWM_PIN 3 //OCR2B
inline __attribute__((always_inline))
void pwm_set_value(uint8_t value)
{
	OCR2B = value;
}


/*

inline __attribute__((always_inline))
void timer1_set_mode(uint8_t mode)
{
  setto(TIMER1_A_CTRL, bitAt(0, mode), TIMER1_MODE_0);
  setto(TIMER1_A_CTRL, bitAt(1, mode), TIMER1_MODE_1);
  setto(TIMER1_B_CTRL, bitAt(2, mode), TIMER1_MODE_2);
  setto(TIMER1_B_CTRL, bitAt(3, mode), TIMER1_MODE_3);
}

inline __attribute__((always_inline))
void timer1_set_prescaler(uint8_t prescaler)
{
  setto(TIMER1_B_CTRL, bitAt(0, prescaler), TIMER1_CLOCK_0);
  setto(TIMER1_B_CTRL, bitAt(1, prescaler), TIMER1_CLOCK_1);
  setto(TIMER1_B_CTRL, bitAt(2, prescaler), TIMER1_CLOCK_2);
}

inline __attribute__((always_inline))
void timer1_a_set_type(uint8_t type)
{
  setto(TIMER1_A_CTRL, bitAt(0, type), TIMER1_A_TYPE_0);
  setto(TIMER1_A_CTRL, bitAt(1, type), TIMER1_A_TYPE_1);
}

inline __attribute__((always_inline))
void ctc_timer_set_interval(uint16_t interval)
{
	OCR1A = interval;
}

inline __attribute__((always_inline))
void ctc_timer_init(uint8_t prescaler)
{
	//timer1_a_set_type(0);
	timer1_set_mode(4);
	timer1_set_prescaler(prescaler);
}

inline __attribute__((always_inline))
void ctc_timer_enable_interrupt()
{
	_set(TIMER1_INT_MASK, TIMER1_A_INT_ENABLE);
}

inline __attribute__((always_inline))
void ctc_timer_disable_interrupt()
{
	_clr(TIMER1_INT_MASK, TIMER1_A_INT_ENABLE);
}
#define CTC_INTERRUPT TIMER1_COMPA_vect
*/
#endif


#if defined(ARDUINO_AVR_DIGISPARK)
#define TIMER0_A_CTRL TCCR0A   //TCCR0A COM0A1 COM0A0 COM0B1 COM0B0 –     –    WGM01 WGM00
#define TIMER0_B_CTRL TCCR0B   //TCCR0B FOC0A  FOC0B  –      –      WGM02 CS02 CS01  CS00
#define TIMER0_A_TYPE_0 _BV(COM0A0)
#define TIMER0_A_TYPE_1 _BV(COM0A1)
#define TIMER0_B_TYPE_0 _BV(COM0B0)
#define TIMER0_B_TYPE_1 _BV(COM0B1)
#define TIMER0_MODE_0 _BV(WGM00)
#define TIMER0_MODE_1 _BV(WGM01)
#define TIMER0_MODE_2 _BV(WGM02)
#define TIMER0_CLOCK_0 _BV(CS00)
#define TIMER0_CLOCK_1 _BV(CS01)
#define TIMER0_CLOCK_2 _BV(CS02)

#define TIMER_INT_MASK TIMSK //TIMSK   –  OCIE1A OCIE1B OCIE0A OCIE0B TOIE1 TOIE0 –
#define TIMER0_A_INT_ENABLE _BV(OCIE0A)

#define TIMER1_G_CTRL GTCCR //GTCCR TSM PWM1B COM1B1 COM1B0 FOC1B FOC1A PSR1 PSR0
#define TIMER1_CTRL TCCR1 //TCCR1 CTC1 PWM1A COM1A1 COM1A0 CS13 CS12 CS11 CS10
#define TIMER1_A_TYPE_0 _BV(COM1A0)
#define TIMER1_A_TYPE_1 _BV(COM1A1)
#define TIMER1_B_TYPE_0 _BV(COM1B0)
#define TIMER1_B_TYPE_1 _BV(COM1B1)
#define TIMER1_A_PWM_ENABLE _BV(PWM1A)
#define TIMER1_B_PWM_ENABLE _BV(PWM1B)
#define TIMER1_CLOCK_0 _BV(CS10)
#define TIMER1_CLOCK_1 _BV(CS11)
#define TIMER1_CLOCK_2 _BV(CS12)
#define TIMER1_CLOCK_3 _BV(CS12)

__attribute__((always_inline)) inline void timer1_a_enableOutput()
{
  _set(DDRB, _BV(DDB1));
}

__attribute__((always_inline)) inline void timer1_a_disableOutput()
{
  _clr(DDRB, _BV(DDB1));
}

__attribute__((always_inline)) inline void timer1_a_invert_enableOutput()
{
  _set(DDRB, _BV(DDB0));
}

__attribute__((always_inline)) inline void timer1_a_invert_disableOutput()
{
  _clr(DDRB, _BV(DDB0));
}

inline __attribute__((always_inline))
void timer1_a_enable_pwm()
{
	_set(TIMER1_CTRL, TIMER1_A_PWM_ENABLE);
}

inline __attribute__((always_inline))
void timer1_a_disable_pwm()
{
	_set(TIMER1_CTRL, TIMER1_A_PWM_ENABLE);
}

inline __attribute__((always_inline))
void timer1_a_set_type(uint8_t type)
{
  setto(TIMER1_CTRL, bitAt(0, type), TIMER1_A_TYPE_0);
  setto(TIMER1_CTRL, bitAt(1, type), TIMER1_A_TYPE_1);
}

inline __attribute__((always_inline))
void timer1_b_set_type(uint8_t type)
{
  setto(TIMER1_G_CTRL, bitAt(0, type), TIMER1_B_TYPE_0);
  setto(TIMER1_G_CTRL, bitAt(1, type), TIMER1_B_TYPE_1);
}

inline __attribute__((always_inline))
void timer1_set_prescaler(uint8_t prescaler)
{
  setto(TIMER1_CTRL, bitAt(0, prescaler), TIMER1_CLOCK_0);
  setto(TIMER1_CTRL, bitAt(1, prescaler), TIMER1_CLOCK_1);
  setto(TIMER1_CTRL, bitAt(2, prescaler), TIMER1_CLOCK_2);
}

#define PWM_PIN 1
inline __attribute__((always_inline))
void pwm_set_value(uint8_t value)
{
	OCR1A = value;
}

inline __attribute__((always_inline))
void pwm_timer_init(uint8_t prescaler)
{
	OCR1C = 255;
	//analogWrite(1, 255);
	timer1_a_enable_pwm();
	timer1_a_set_type(1);
	timer1_set_prescaler(prescaler);
	timer1_a_enableOutput();
}

inline __attribute__((always_inline))
void timer0_set_mode(uint8_t mode)
{
  setto(TIMER0_A_CTRL, bitAt(0, mode), TIMER0_MODE_0);
  setto(TIMER0_A_CTRL, bitAt(1, mode), TIMER0_MODE_1);
  setto(TIMER0_B_CTRL, bitAt(2, mode), TIMER0_MODE_2);
}

inline __attribute__((always_inline))
void timer0_set_prescaler(uint8_t prescaler)
{
  setto(TIMER0_B_CTRL, bitAt(0, prescaler), TIMER0_CLOCK_0);
  setto(TIMER0_B_CTRL, bitAt(1, prescaler), TIMER0_CLOCK_1);
  setto(TIMER0_B_CTRL, bitAt(2, prescaler), TIMER0_CLOCK_2);
}

inline __attribute__((always_inline))
void ctc_timer_set_interval(uint8_t interval)
{
	OCR0A = interval;
}

inline __attribute__((always_inline))
void ctc_timer_init(uint8_t prescaler)
{
	timer0_set_mode(2);
	timer0_set_prescaler(prescaler);
}

inline __attribute__((always_inline))
void ctc_timer_enable_interrupt()
{
	_set(TIMER_INT_MASK, TIMER0_A_INT_ENABLE);
}

inline __attribute__((always_inline))
void ctc_timer_disable_interrupt()
{
	_clr(TIMER_INT_MASK, TIMER0_A_INT_ENABLE);
}

#define CTC_INTERRUPT TIMER0_COMPA_vect
#endif