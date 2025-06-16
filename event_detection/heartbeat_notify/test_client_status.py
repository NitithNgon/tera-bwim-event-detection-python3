import numpy as np
from datetime import timedelta
from event_detection.__main__ import(
    strain_number,
    axle_number,
    event_number_max,
    cam_number_max,
    event_block_buffer_max,
    event_block_time,
)

class Bwim_flag:
    system_shutdown = 0  # System Shutdown Flag
    event_1_triggered = 0
    event_2_triggered = 0
    event_3_triggered = 0
    event_4_triggered = 0
    lpr_summary = 0
    event_backup = 0


class Currently_bwim_process_status:
    expacted_buffering_data_time = timedelta(seconds= int(event_block_buffer_max * event_block_time * 1.2) )
    actual_buffering_data_time = None
    strain_sampling_rate_status = "NONE"
    last_record_time = None
    last_event_time = None
    Flag_data = Bwim_flag

Flag = Bwim_flag()
Flag.system_shutdown = 0
Flag.lpr_summary = 0
Flag.event_backup = 0

# initial Bwim_process_status
Bwim_process_status = Currently_bwim_process_status()
Bwim_process_status.Flag_data = Flag

