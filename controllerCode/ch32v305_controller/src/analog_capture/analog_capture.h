#ifndef ANALOG_CAPTURE_H
#define ANALOG_CAPTURE_H

#include <Arduino.h>

enum AnalogCaptureResult {
  AC_OK = 0,
  AC_ERR_BUSY,
  AC_ERR_BAD_RATE,
  AC_ERR_BAD_COUNT,
  AC_ERR_BAD_CHANNELS,
};

bool analogCaptureIsBusy();
AnalogCaptureResult analogCapture(uint32_t rateHz, uint32_t timeSamples,
                                  uint8_t channelMask, uint32_t *actualRateHz);
void analogCaptureUpload(Stream &out, uint32_t timeSamples, uint8_t channelMask,
                         uint8_t numChannels);

#endif
