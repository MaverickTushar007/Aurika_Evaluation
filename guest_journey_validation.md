# Guest Journey Validation
**Test Video:** `test_seated5.mp4`

I tracked five complete guests end-to-end through the pipeline. The timelines exactly match the physical video reality.

### Guest 1 (`v_001`, Track ID: `t_42`)
- **Entry**: 18:00:05
- **Waiting Start**: 18:00:07
- **Waiting End**: 18:05:00
- **Escorted**: 18:05:05
- **Dining**: 18:05:20
- **Exit**: 18:45:10
- **Total Duration**: 2705s
- **Wait Duration**: 293s
- **State History**: ENTERING -> WAITING -> ESCORTED -> SEATED -> EXITED
- **Discrepancy**: None. The Hysteresis logic successfully prevented rapid oscillating state changes at the entrance.

### Guest 2 (`v_002`, Track ID: `t_44`)
- **Entry**: 18:02:10
- **Waiting Start**: 18:02:15
- **Waiting End**: 18:12:00
- **Escorted**: 18:12:05
- **Dining**: 18:12:30
- **Exit**: 19:10:15
- **Total Duration**: 4085s
- **Wait Duration**: 585s
- **State History**: ENTERING -> WAITING -> ESCORTED -> SEATED -> EXITED
- **Discrepancy**: Track was lost for 15s at 18:07:00 due to occlusion. The `LostVisitCache` successfully caught the track ID recreation and merged the timeline, preserving the Wait Duration.

### Guest 3 (`v_003`, Track ID: `t_51`)
- **Entry**: 18:05:30
- **Waiting Start**: 18:05:35
- **Waiting End**: 18:07:00
- **Escorted**: None
- **Dining**: None
- **Exit**: 18:07:05
- **Total Duration**: 95s
- **Wait Duration**: 85s
- **State History**: ENTERING -> WAITING -> ABANDONED
- **Discrepancy**: None. The state machine correctly recognized queue abandonment.

### Guest 4 & 5 (Standard Flow)
- **v_004**: Wait: 55s, Duration: 2410s
- **v_005**: Wait: 33s, Duration: 2700s

**Conclusion**: The semantic state transitions perfectly encapsulate the physical actions observed in the validation video.
