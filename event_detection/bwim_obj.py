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


class Bwim_data:
    id = 0                  # block index number
    start_time = ""         # blcok start time recording
    end_time = ""           # blcok end time recording
    create_time = ""        # create_time for event file name
    strain = []             # list of strain data
    axle = []               # list of axle data
    strain_array = np.arange(strain_number)     # numpy array of strain data
    axle_array = np.arange(axle_number)         # numpy array of axle data
    min_strain = [0]*event_number_max           # minimum strain value each event number ( road lane )
    max_strain = [0]*event_number_max           # minimum strain value each event number ( road lane )
    diff_max_min_strain = [0]*event_number_max  # delta max min strain value each event number ( road lane )
    min_index = [0]*event_number_max            # np index for min strain each event number ( road lane )
    max_index = [0]*event_number_max            # np index for max strain each event number ( road lane )
    cam_image = ['']                            # CCTV image data grab retrieve


class Bwim_event:
    block_id = 0    # index of Bwim_data block when event activated
    number = 0      # number of all Bwim_data block to recording in event
    min_strain = 0  # min strain value of all Bwim_data block in event
    max_strain = 0  # max strain value of all Bwim_data block in event
    lpr = ["" for x in range(cam_number_max)]   # lpr plate string , NONE is initial or already removed image , ERROR is invalid lpr image in lpr_process
    lpr_bg = ["" for x in range(cam_number_max)]# lpr background crop image path , NONE is initial or already removed image , ERROR is invalid lpr image in lpr_process
    lpr_p = ["" for x in range(cam_number_max)] # lpr plate image path , NONE is initial or already removed image , ERROR is invalid lpr image in lpr_process
    lpr_done = [0 for x in range(cam_number_max)]# lpr processing are finish


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

    