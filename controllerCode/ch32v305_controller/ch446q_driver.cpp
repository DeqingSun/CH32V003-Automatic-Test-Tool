#include "ch446q_driver.h"

CH446Q::CH446Q(uint8_t rstPin, uint8_t datPin, uint8_t clkPin, uint8_t stbPin)
  : rstPin_(rstPin), datPin_(datPin), clkPin_(clkPin), stbPin_(stbPin) {
  for (uint8_t i = 0; i < 16; i++) {
    currentMatrixStatus_[i] = 0;
    savedMatrixStatus_[i] = 0;
  }
}

void CH446Q::init() {
  digitalWrite(rstPin_, LOW);
  pinMode(rstPin_, OUTPUT);

  digitalWrite(datPin_, LOW);
  pinMode(datPin_, OUTPUT);

  digitalWrite(clkPin_, LOW);
  pinMode(clkPin_, OUTPUT);

  digitalWrite(stbPin_, LOW);
  pinMode(stbPin_, OUTPUT);
}

void CH446Q::reset() {
  digitalWrite(rstPin_, HIGH);
  delayMicroseconds(10);
  digitalWrite(rstPin_, LOW);

  for (uint8_t i = 0; i < 16; i++) {
    currentMatrixStatus_[i] = 0;
  }
}

void CH446Q::switchChannel(uint8_t x, uint8_t y, bool enabled) {
  // Output Y address.
  for (int8_t i = 2; i >= 0; i--) {
    digitalWrite(clkPin_, LOW);
    digitalWrite(datPin_, (y >> i) & 0x01);
    delayMicroseconds(1);
    digitalWrite(clkPin_, HIGH);
    delayMicroseconds(1);
  }

  // Output X address.
  for (int8_t i = 3; i >= 0; i--) {
    digitalWrite(clkPin_, LOW);
    digitalWrite(datPin_, (x >> i) & 0x01);
    delayMicroseconds(1);
    digitalWrite(clkPin_, HIGH);
    delayMicroseconds(1);
  }

  // Output ON command.
  digitalWrite(datPin_, HIGH);
  delayMicroseconds(1);
  if (enabled) {
    digitalWrite(stbPin_, HIGH);
    delayMicroseconds(1);
    digitalWrite(stbPin_, LOW);
    currentMatrixStatus_[x] |= 1 << y;
  }
  delayMicroseconds(1);

  // Output OFF command.
  digitalWrite(datPin_, LOW);
  delayMicroseconds(1);
  if (!enabled) {
    digitalWrite(stbPin_, HIGH);
    delayMicroseconds(1);
    digitalWrite(stbPin_, LOW);
    currentMatrixStatus_[x] &= ~(1 << y);
  }
  delayMicroseconds(1);

  digitalWrite(clkPin_, LOW);
  digitalWrite(datPin_, HIGH);
}

void CH446Q::saveMatrix() {
  for (uint8_t i = 0; i < 16; i++) {
    savedMatrixStatus_[i] = currentMatrixStatus_[i];
  }
}

void CH446Q::restoreMatrix() {
  for (uint8_t i = 0; i < 16; i++) {
    if (savedMatrixStatus_[i] == currentMatrixStatus_[i]) {
      continue;
    }
    for (uint8_t j = 0; j < 8; j++) {
      if ((savedMatrixStatus_[i] & (1 << j)) != (currentMatrixStatus_[i] & (1 << j))) {
        if (savedMatrixStatus_[i] & (1 << j)) {
          switchChannel(i, j, true);
        } else {
          switchChannel(i, j, false);
        }
      }
    }
  }
}
