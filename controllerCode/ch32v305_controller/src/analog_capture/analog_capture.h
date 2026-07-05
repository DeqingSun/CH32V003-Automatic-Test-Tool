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

enum AnalogCapturePollState {
  AC_POLL_IDLE = 0,
  AC_POLL_RUNNING,
  AC_POLL_DONE,
};

bool analogCaptureIsBusy();
AnalogCaptureResult analogCaptureStart(uint32_t rateHz, uint32_t timeSamples,
                                       uint8_t channelMask, uint32_t *actualRateHz);
AnalogCapturePollState analogCapturePoll(Stream &out);
void analogCaptureUpload(Stream &out, uint32_t timeSamples, uint8_t channelMask,
                         uint8_t numChannels);

#endif
