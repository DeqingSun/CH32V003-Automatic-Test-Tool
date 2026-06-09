#include "util.h"

uint8_t hexToUchar(char s) {
  if (s >= '0' && s <= '9') {
    return (s - '0');
  }
  if (s >= 'A' && s <= 'F')  {
    return (s - 'A' + 10);
  }
  if (s >= 'a' && s <= 'f') {
    return (s - 'a' + 10);
  }
  return 0xff;
}

uint8_t hexToUchar2(char *s) {
  return (hexToUchar(*s) << 4) + hexToUchar(*(s + 1));
}

uint16_t hexToUint16(char *s) {
  return (hexToUchar2(s) << 8) + hexToUchar2(s + 2);
}

uint32_t hexToUint32(char *s) {
  uint32_t value = 0;
  for (uint8_t i = 0; i < 8; i++) {
    uint8_t nibble = hexToUchar(s[i]);
    if (nibble == 0xff) {
      return 0;
    }
    value = (value << 4) | nibble;
  }
  return value;
}