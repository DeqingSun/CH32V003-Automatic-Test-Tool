#ifndef __UTIL_H
#define __UTIL_H

#include <Arduino.h>

uint8_t hexToUchar(char s);
uint8_t hexToUchar2(char *s);
uint16_t hexToUint16(char *s);
uint32_t hexToUint32(char *s);

#endif
