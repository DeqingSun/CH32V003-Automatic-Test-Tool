#ifndef LOGIC_ANALYZER_H
#define LOGIC_ANALYZER_H

#include <Arduino.h>

#define LA_BUFFER_SIZE (128 * 1024)
#define LA_MAGIC 0x31414C4Cu /* "LLA1" little-endian on wire */

enum LogicAnalyzerResult {
  LA_OK = 0,
  LA_ERR_BUSY,
  LA_ERR_BAD_RATE,
  LA_ERR_BAD_COUNT,
};

enum LogicAnalyzerPollState {
  LA_POLL_IDLE = 0,
  LA_POLL_RUNNING,
  LA_POLL_DONE,
};

bool logicAnalyzerIsBusy();
LogicAnalyzerResult logicAnalyzerStart(uint32_t rateHz, uint32_t sampleCount,
                                       uint32_t *actualRateHz);
LogicAnalyzerPollState logicAnalyzerPoll(Stream &out);
const uint8_t *logicAnalyzerBuffer();
void logicAnalyzerUpload(Stream &out, uint32_t sampleCount, uint32_t rateHz);

#endif
