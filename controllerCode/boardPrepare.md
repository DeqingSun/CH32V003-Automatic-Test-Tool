# CH32V305CCT6

We want to use config "FLASH-128K + RAM-192K" to maximize RAM for data capture. And the link file is prepared for that. But a new chip does not come with this config. CH32V305CCT6 does not support USB flash so we can connect WCH-LinkE, and use WCH-LinkUtility on windows to set "FLASH-128K + RAM-192K". Otherwise we get hardfault on RAM write failure.

# CH32V305FBP6

refer to WCH-LinkUserManual.PDF for SWD flash. TODO:

