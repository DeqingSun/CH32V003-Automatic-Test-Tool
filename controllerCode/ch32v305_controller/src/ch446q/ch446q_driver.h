#ifndef CH446Q_DRIVER_H
#define CH446Q_DRIVER_H

#include <Arduino.h>


class CH446Q {
public:
  CH446Q(uint8_t rstPin, uint8_t datPin, uint8_t clkPin, uint8_t stbPin);

  void init();
  void reset();
  void switchChannel(uint8_t x, uint8_t y, bool enabled);
  void saveMatrix();
  void restoreMatrix();

private:
  uint8_t rstPin_;
  uint8_t datPin_;
  uint8_t clkPin_;
  uint8_t stbPin_;
  uint8_t currentMatrixStatus_[16];
  uint8_t savedMatrixStatus_[16];
};

#endif
