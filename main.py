#!/usr/bin/env pytho
import sys
import os
				# pip install requests
from datetime import datetime, timedelta
import time
import threading
import ftd2xx as d2xx			# pip install ftd2xx
import numpy as np				# pip install numpy
# import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt	# pip install matplotlib
from struct import *
#from distutils.dir_util import copy_tree
import cv2
import subprocess
import paho.mqtt.client as mqtt # pip install paho-mqtt
import json
import LPRobj
from time import sleep
import pytz
# import websocket
from py3_bwim_truck import subprocess_call_bwim_truck_as_main
import psutil

import shutil  # built-in, no pip install needed
import zipfile  # built-in, no pip install needed
import ftplib  # built-in, no pip install needed

# IP CAMERA Parameters
CAM_NUMBER_MAX = 4

RTSP_LINK = ["rtsp://admin:Alphax123@192.168.15.52/Streaming/channels/101",
            "rtsp://admin:Alphax123@192.168.15.52/Streaming/channels/101",
            "rtsp://admin:Alphax123@192.168.15.51/Streaming/channels/101",
            "rtsp://admin:Alphax123@192.168.15.51/Streaming/channels/101"]

CAM_USER = 'admin'
CAM_PWD = 'Alphax123'

# basic parameters about strain data
BRIDGE_NAME = "BANGPHLAT"
STRAIN_NUMBER = 24	# 8, 16 , 24, 32
QUARTER_BRIDGE_STRAIN = 0
DATA_BUFFER_LENGTH = 8 + (STRAIN_NUMBER*4) + 8 # preamble[4] / sequence[4] / strain[4xSTRAIN_NUMBER] / axle[4x2]
STR_IDX = STRAIN_NUMBER + 2 # number of strain channel to read
QTR_IDX = QUARTER_BRIDGE_STRAIN + 2 # number of quarter bridge strain channel to read ( need to inverse data )
AXLE_NUMBER = 4
STRAIN_SAMPLING_RATE = 1024

# Micro strain conversion factor
VOFFSET = 8388608	# 0x800000 : 24bit data mid range
VRANGE = 838.8607	# 0xFFFFFF / 20,000 uV : 24 bit full range divide full scale voltag
GAUGE_FACTOR = 211	# quater bridge gaugae factor

# strain event detection parameter [ event_channel_1 , event_channel_2 , ... , event_channel_n ]
EVENT_NUMBER_MAX = 4	# channel of event number ( one event by strain threshold per channel) / represent event number for road lane in wight calculation
STRAIN_THRESHOLD_CHANNEL = [1,9,10,18]        # channel of strain use for event threshold detection
# STRAIN_THRESHOLD_MICROVOLT = [400,400,400,400]  # first stage for event threshold detection //35 on calibrate use 25 rail is 150
# EVENT_THRESHOLD_MICROVOLT = [550,550,550,550]   # second stage for event threshold detection //40 on calibrate use 30 rail is 200
STRAIN_THRESHOLD_MICROVOLT = [400,400,400,400]  # first stage for event threshold detection //35 on calibrate use 25 rail is 150
EVENT_THRESHOLD_MICROVOLT = [500,500,500,500]   # second stage for event threshold detection //40 on calibrate use 30 rail is 200
EVENT_PRE_POST_MICROVOLT_DIFF =  [5]*EVENT_NUMBER_MAX    # the different of strain value on Bwim_data pre-first block and last block, decision for end of event file detection
                                           # when set '0' is disable this function , end of event file upon EVENT_POST_BLOCK_MAX only
# strain event block recording parameter
EVENT_BLOCK_TIME = 	1	# recording and detect every xx second
EVENT_PRE_BLOCK = 	[1]*EVENT_NUMBER_MAX # number of previous event block in event file calculation
EVENT_POST_BLOCK_MAX =	[2]*EVENT_NUMBER_MAX	# maximum number of post event block in event file when pre_post threshold ara fail or disable
EVENT_BLOCK_BUFFER_MAX = 20	# circular block buffer for recording data

# event cam image recording : CAM-1 = lane 1 ( To Klongton ) / CAM-2 = lane 2 ( To Pratunam )
EVENT_CAM_START =  [2,2,2,2]		# cam start time when event occurred for each road lane [0,1]
EVENT_CAM_FINISH = [-1,-1,-1,-1]	# cam stop time when event occurred for each road lane [-3,-2]

EVENT_UNCLASSIFIED_SYNOLOGY_DRIVE = "C:\SynologyDrive\BWIM_BMA_002\EVENT_UNCLASSIFIED" # folder which store unclassified event
EVENT_BWIM_SYNOLOGY_DRIVE = "C:\SynologyDrive\BWIM_BMA_002\EVENT_BWIM"
EVENT_VIDEO_SYNOLOGY_DRIVE = "C:\SynologyDrive\www\BMA002_EVENT"   # folder which store event video
EVENT_FTP_PATH = '/home/www/BMA002_EVENT'

VIDEO_LINK = ["rtsp://admin:Alphax123@192.168.15.52:554/Streaming/tracks/203",
            "rtsp://admin:Alphax123@192.168.15.52:554/Streaming/tracks/203",
              "rtsp://admin:Alphax123@192.168.15.51:554/Streaming/tracks/203",
              "rtsp://admin:Alphax123@192.168.15.51:554/Streaming/tracks/203"]

# event cam image recording : CAM-1 = lane 1 ( To Klongton ) / CAM-2 = lane 2 ( To Pratunam )
VIDEO_CAM_START =  [5,5,5,5]		# cam start time when event occurred for each road lane ( 10 sec recoding )
VIDEO_CAM_STOP = [5,5,5,5]		# cam stop time when event occurred for each road lane ( 10 sec recording )

STRAIN_PLOT_CH_LIST = [1, 19, 2, 20, 9, 3, 10, 4, 17, 11, 18, 12]   # List of All-CH-Number
STRAIN_CH_NUM_TO_SENSOR_NAME = {
    1: "G1_WS01-1",
    2: "G2_WS02-2",
    3: "G3_WS09-3",
    4: "G4_WS10-4",
    5: "G5_SG17-5",
    6: "G6_SG18-6",
    7: "-",
    8: "-",
    9: "G3_WS03-9",
    10: "G4_WS04-10",
    11: "G5_WS11-11",
    12: "G6_WS12-12",
    13: "G1_SG13-13",
    14: "G2_SG14-14",
    15: "-",
    16: "-",
    17: "G5_WS05-17",
    18: "G6_WS06-18",
    19: "G1_WS07-19",
    20: "G2_WS08-20",
    21: "G3_SG15-21",
    22: "G4_SG16-22",
    23: "-",
    24: "-",
}

STRAIN_PLOT_LANE_CH_MAP = {
    1: [1, 19, 2, 20, 9, 3],
    2: [3, 9, 20, 2, 19, 1],
    3: [10, 4, 17, 11, 18, 12],
    4: [12, 18, 11, 17, 4, 10],
}

class Bwim_data:
    id = 0                  # block index number
    start_time = ""         # blcok start time recording
    end_time = ""           # blcok end time recording
    create_time = ""        # create_time for event file name
    strain = []             # list of strain data
    axle = []               # list of axle data
    strain_array = np.arange(STRAIN_NUMBER)     # numpy array of strain data
    axle_array = np.arange(AXLE_NUMBER)         # numpy array of axle data
    min_strain = [0]*EVENT_NUMBER_MAX           # minimum strain value each event number ( road lane )
    max_strain = [0]*EVENT_NUMBER_MAX           # minimum strain value each event number ( road lane )
    diff_max_min_strain = [0]*EVENT_NUMBER_MAX  # delta max min strain value each event number ( road lane )
    min_index = [0]*EVENT_NUMBER_MAX            # np index for min strain each event number ( road lane )
    max_index = [0]*EVENT_NUMBER_MAX            # np index for max strain each event number ( road lane )
    cam_image = ['']                            # CCTV image data grab retrieve


class Bwim_event:
    block_id = 0    # index of Bwim_data block when event activated
    number = 0      # number of all Bwim_data block to recording in event
    min_strain = 0  # min strain value of all Bwim_data block in event
    max_strain = 0  # max strain value of all Bwim_data block in event
    lpr = ["" for x in range(CAM_NUMBER_MAX)]   # lpr plate string , NONE is initial or already removed image , ERROR is invalid lpr image in lpr_process
    lpr_bg = ["" for x in range(CAM_NUMBER_MAX)]# lpr background crop image path , NONE is initial or already removed image , ERROR is invalid lpr image in lpr_process
    lpr_p = ["" for x in range(CAM_NUMBER_MAX)] # lpr plate image path , NONE is initial or already removed image , ERROR is invalid lpr image in lpr_process
    lpr_done = [0 for x in range(CAM_NUMBER_MAX)]# lpr processing are finish

class Bwim_flag:
    system_shutdown = 0  # System Shutdown Flag
    event_1_triggered = 0
    event_2_triggered = 0
    event_3_triggered = 0
    event_4_triggered = 0
    lpr_summary = 0
    event_backup = 0

class Currently_bwim_process_status:
    expacted_buffering_data_time = timedelta(seconds= int(EVENT_BLOCK_BUFFER_MAX * EVENT_BLOCK_TIME * 1.2) )
    actual_buffering_data_time = None
    strain_sampling_rate_status = "NONE"
    last_record_time = None
    last_event_time = None
    Flag_data = Bwim_flag

# create Data_Bwim_Block
Data_Bwim = [Bwim_data() for i in range(EVENT_BLOCK_BUFFER_MAX)]
# initial Data_Bwim_Block
for i in range(EVENT_BLOCK_BUFFER_MAX):	# 0 to BWIM_BLOCK_NUMBER-1
    Data_Bwim[i].id = i
    Data_Bwim[i].strain = []
    Data_Bwim[i].axle = []
    Data_Bwim[i].cam_image = ['']*CAM_NUMBER_MAX
    Data_Bwim[i].min_strain = [0]*EVENT_NUMBER_MAX
    Data_Bwim[i].max_strain = [0]*EVENT_NUMBER_MAX
    Data_Bwim[i].min_index = [0]*EVENT_NUMBER_MAX
    Data_Bwim[i].max_index = [0]*EVENT_NUMBER_MAX

# initial BWIM detection event flag
Event_Bwim = [Bwim_event() for i in range(EVENT_NUMBER_MAX)]
for n in range(EVENT_NUMBER_MAX):
    Event_Bwim[n].number = 0
    Event_Bwim[n].min_strain = 0
    Event_Bwim[n].max_strain = 0
    for m in range(CAM_NUMBER_MAX):
        Event_Bwim[n].lpr[m] = "NONE"
        Event_Bwim[n].lpr_bg[m] = "NONE"
        Event_Bwim[n].lpr_p[m] = "NONE"

Flag = Bwim_flag()
Flag.system_shutdown = 0
Flag.lpr_summary = 0
Flag.event_backup = 0

# initial Bwim_process_status
Bwim_process_status = Currently_bwim_process_status()
Bwim_process_status.Flag_data = Flag

#initial openCV RTSP video capture
camera = ['']*CAM_NUMBER_MAX
image_cam = ['']*CAM_NUMBER_MAX

# # thread cam
# for n in range(CAM_NUMBER_MAX):
#     # time.sleep(10)
#     camera[n] = cv2.VideoCapture(RTSP_LINK[n])
#     image_cam[n] = ['']
#     try:
#         # Check if camera opened successfully
#         # if ( camera[n].isOpened() == True):
#         if (camera[n] is None):
#             print("[CAM-"+str(n+1)+"] NO STREAM")
#             # try again...
#         # Else is important to display error message on the screen if can.isOpened returns false
#         else:
#             read_Fail = True
#             while read_Fail:
#                 time.sleep(1)
#                 ret, frame = camera[n].read()
#                 frame_size = sys.getsizeof(frame)
#                 # print(ret)
#                 # print(frame_size)
#                 if ( frame_size > 10000 ) and (ret == True): # frame image have to more than 1KB
#                     print("[CAM-" + str(n+1) + "] STREAM OK ")
#                     read_Fail = False
#                 else:
#                     print("[CAM-" + str(n+1) + "] STREAM FAIL!!")
#                     camera[n].released()
#                     time.sleep(10)
#                     camera[n] = cv2.VideoCapture(RTSP_LINK[n])
#     except:
#         print("[CAM-" + str(n+1) + "] Unavailable")
#         # try again...
#         camera[n] = cv2.VideoCapture(RTSP_LINK[n])
#         pass
# 
# # sleep(2)
# # intial BWIM MAQTT connection
# MQTT_Bwim = mqtt.Client()
# # intial LPR Object
# LPR = LPRobj.LPR_CAM(MQTT_Bwim)

# collect images from all data_block and write to jpg files
def event_image(event_block_id, cam_number, image_dir,block_id_finish):
    # initial event cam block index
    idx_cam_start = event_block_id - EVENT_CAM_START[cam_number]
    idx_cam_finish = event_block_id - EVENT_CAM_FINISH[cam_number]

    # append relate block data to event data
    for i in range(idx_cam_start, idx_cam_finish + 1):  # EVENT_CAM_START to EVENT_CAM_FINISH
        # check circular list index
        if (i >= EVENT_BLOCK_BUFFER_MAX):
            # in case circular list index out of range ( EVENT_BLOCK_BUFFER_MAX )
            j = i - EVENT_BLOCK_BUFFER_MAX
        else:
            j = i

        # event snapshot name is CAM_NUMBER(event_number+1)_CAM_INDEX
        snapshot_name = "./" +str(cam_number+1) +"_" + str(i - idx_cam_start + 1) + ".jpg"
        image_save = Data_Bwim[j].cam_image[cam_number]
        # create event image ...
        # if ((cam_number+1 == 1) and (i - idx_cam_start + 1 == 2)and (event_number+1 == 1)) or ((cam_number+1 == 2) and (i - idx_cam_start + 1 == 3) and (event_number+1 == 2)) :
        #     # corp image to 1/2 square when using in main event picture on BWIM app
        #     h = image_save.shape[0] # image height
        #     w = image_save.shape[1] # image width
        #     image_corp = image_save[0:h, (w-h)-130:w-130]  # y=h, x=w #LPR CAM
        #     # image_corp = image_save[0:w/2,w/2:w] # y=h, x=w
        #
        #     cv2.imwrite(os.path.join(image_dir, snapshot_name), image_corp)
        # elif  ((cam_number+1 == 1) and (i - idx_cam_start + 1 == 2)and (event_number+1 == 2)):
        #     # corp image to 1/2 square when using in main event picture on BWIM app
        #     h = image_save.shape[0]  # image height
        #     w = image_save.shape[1]  # image width
        #     image_corp = image_save[0:w/2, 2*w/6: 5*w/6] # y=h, x=w
        #     cv2.imwrite(os.path.join(image_dir, snapshot_name), image_corp)
        # else:
        #     cv2.imwrite(os.path.join(image_dir,snapshot_name),image_save)
        # sleep(1)
        cv2.imwrite(os.path.join(image_dir,snapshot_name),image_save)

# stream CCTV cam and grab image into data_block buffer
def camera_grab_retrieve(cam_number, data_block):
    #r, image = camera[cam_number].retrieve()
    data_block.cam_image[cam_number] = image_cam[cam_number]
    # camera[cam_number].release()

def start_capture_image(data_block):
    threads = []
    for i in range(CAM_NUMBER_MAX):
        # start capture image thread form  IP CAM
        t = threading.Thread(target=camera_grab_retrieve, args=(i, data_block,))
        t.daemon = True
        threads.append(t)
        t.start()

def bwin_initial_zero_adjustment(h):
    # check first packet correction
    i = 0
    while i < 10:
        # get praamble
        data = h.read(4)
        preamble = unpack('<I', data)
        i = i + 1
        if preamble[0] == 2863311530:	# preamble = 0xAAAAAAAA
            # get data without preamble
            data = h.read(DATA_BUFFER_LENGTH - 4)
            break
    data = h.read(DATA_BUFFER_LENGTH)
    if (STRAIN_NUMBER == 32):
        buffer_data = unpack("<I I 32I 4H", data)  # data[n*144:((n+1)*144)]
    if (STRAIN_NUMBER == 24):
        buffer_data = unpack("<I I 24I 4H", data)  # data[n*144:((n+1)*144)]
    if (STRAIN_NUMBER == 16):
        buffer_data = unpack("<I I 16I 4H", data)  # data[n*144:((n+1)*144)]
    if (STRAIN_NUMBER == 8):
        buffer_data = unpack("<I I 8I 4H", data)  # data[n*144:((n+1)*144)]
    axle_data = (buffer_data[STR_IDX:(STR_IDX+4)])
    # zero_adjust_voltage = [(i - VOFFSET) / VRANGE for i in buffer_data[2:STR_IDX]]
    zero_adjust_voltage = [(VOFFSET-i) / VRANGE for i in buffer_data[2:STR_IDX]] # negative strain value
    # strain_data = [(VOFFSET - i) / VRANGE for i in strain_data[1:STR_IDX]]
    print (zero_adjust_voltage)

# strain & axle recording and checking event occurred
def record_data(h, time_sec, data_block):
    # empty data list and initial output string data
    del data_block.strain[:]
    del data_block.axle[:]
    # initial data_block start time
    data_block.start_time = datetime.today().strftime("%Y-%m-%d %H:%M:%S-%f")
    data_block.create_time = datetime.today().strftime('%Y%m%d_%H%M%S')

    # initial all list for recording
    number_of_sample = time_sec*STRAIN_SAMPLING_RATE

    sys.stdout.write('.') 	#print "." without \r\n

    # start recording
    n = 0
    while n < number_of_sample:
        # read data from controller
        data = h.read(DATA_BUFFER_LENGTH)
        if (STRAIN_NUMBER == 16):
            buffer_data = unpack(f"<I I {STRAIN_NUMBER}I 4H", data)  # data[n*144:((n+1)*144)]
        if (STRAIN_NUMBER == 8):
            buffer_data = unpack("<I I 8I 4H", data)  # data[n*144:((n+1)*144)]
        if (STRAIN_NUMBER == 24):
            buffer_data = unpack("<I I 24I 4H", data)  # data[n*144:((n+1)*144)]

        axle_data = (buffer_data[STR_IDX:(STR_IDX+4)])
        # strain_data = [(i - VOFFSET)/VRANGE for i in buffer_data[2:STR_IDX]]
        strain_data = [(VOFFSET - i) / VRANGE for i in buffer_data[2:STR_IDX]] # Negative Strain value

        #strain_data = [(VOFFSET - i) / VRANGE for i in strain_data[1:STR_IDX]]	# for quater brige

        # round strain data as two decimal digit
        strain_data = [round(i,2) for i in strain_data]

        # append all strain & axle list , prepare plot when finish
        data_block.strain.append(strain_data)
        data_block.axle.append(axle_data)

        n = n+1

    # set end time recording
    data_block.end_time = datetime.today().strftime("%Y-%m-%d %H:%M:%S-%f")

    # convert data block list to numpy array
    data_block.strain_array = np.asarray(data_block.strain)
    data_block.axle_array = np.asarray(data_block.axle)

    # check event block by compare max/min value with STRAIN_THRESHOLD_MICROVOLT
    for n in range(EVENT_NUMBER_MAX):
        # operate when event not occurred
        data_block.min_strain[n] = np.amin(data_block.strain_array, axis=0)[STRAIN_THRESHOLD_CHANNEL[n] - 1]  # get minimum value within strain data block
        data_block.max_strain[n] = np.amax(data_block.strain_array, axis=0)[STRAIN_THRESHOLD_CHANNEL[n] - 1]  # get maximum value within strain data block
        data_block.min_index[n] = np.argmin(data_block.strain_array, axis=0)[STRAIN_THRESHOLD_CHANNEL[n] - 1]
        data_block.max_index[n] = np.argmax(data_block.strain_array, axis=0)[STRAIN_THRESHOLD_CHANNEL[n] - 1]
        data_block.diff_max_min_strain[n] = data_block.max_strain[n] - data_block.min_strain[n]

    # for n in range(EVENT_NUMBER_MAX):
    for n in [0,1,3,2]:
        if (Event_Bwim[n].number  == 0):
            # check max/min with threshold micro volt
            if ((data_block.diff_max_min_strain[n]) > STRAIN_THRESHOLD_MICROVOLT[n]) and (data_block.max_index[n] > data_block.min_index[n] ):

                if ( n == 0) and ( data_block.diff_max_min_strain[1] > data_block.diff_max_min_strain[0] ) and (Event_Bwim[1].number == 0):
                    # event lane 1 are dominant
                    print ("[LANE-1] less dominant")
                    n = 1

                if ( n == 3) and ( data_block.diff_max_min_strain[2] > data_block.diff_max_min_strain[3] ) and (Event_Bwim[2].number == 0):
                    # event lane 2 are dominant
                    print ("[LANE-4] less dominant")
                    n = 2

                if (n == 0) and (Flag.event_1_triggered == 1):
                    return  # exit when event-1 not yet finish, prevent dupicate event-1
                elif (n == 1) and ((Flag.event_1_triggered == 1) or (Flag.event_2_triggered == 1)):
                    return  # exit event-2 trigger when event-1 or event-2 not yet finish ( event-1 have more priority )
                elif (n == 0):
                    Flag.event_1_triggered = 1  # set event-1 trigger flag
                    Flag.event_2_triggered = 0  # clear event-2 trigger flag
                    Event_Bwim[1].number = 0  # clear event-2
                elif (n == 1):
                    Flag.event_2_triggered = 1  # set event-2 trigger flag

                if (n == 3) and (Flag.event_4_triggered == 1):
                    return  # exit when event-4 not yet finish, prevent dupicate on event-4
                elif (n == 2) and ((Flag.event_3_triggered == 1) or (Flag.event_4_triggered == 1)):
                    return  # exit event-3 trigger when event-3 or event-4 not yet finish ( event-4 have more priority )
                elif (n == 3):
                    Flag.event_4_triggered = 1  # set event-4 trigger flag
                    Flag.event_3_triggered = 0  # clear event-3 trigger flag
                    Event_Bwim[2].number = 0  # clear event-2
                elif (n == 2):
                    Flag.event_3_triggered = 1  # set event-2 trigger flag

                print ("[LANE-" +str(n+1) +"]: Strain Threshold / max=" + str(data_block.max_strain[n]) + ", min=" + str(data_block.min_strain[n]))
                Event_Bwim[n].number = 1
                Event_Bwim[n].min_strain = data_block.min_strain[n]
                Event_Bwim[n].max_strain = data_block.max_strain[n]
                Event_Bwim[n].block_id = data_block.id

                Event_Bwim[n].lpr[n] = 'NONE'
                Event_Bwim[n].lpr_bg[n] = 'NONE'
                Event_Bwim[n].lpr_p[n] = 'NONE'
                Event_Bwim[n].lpr_done[n] = 0

                # # thread cam
                # LPR.lpr_thread( data_block.start_time, Event_Bwim[n], n)

        elif (Event_Bwim[n].number == EVENT_BLOCK_BUFFER_MAX):
            # Get LPR picture after strain threshold occured 1 seconds ( next block )
            # print "event_number=1"
            Event_Bwim[n].lpr = "NONE"
            Event_Bwim[n].lpr_bg = "NONE"
            Event_Bwim[n].lpr_p = "NONE"

def bwim_create_event_file( Bwim_event_data , event_number):
    # initial all event list
    event_max_strain = []
    event_min_strain = []
    lpr_bg = ["" for x in range(CAM_NUMBER_MAX)]
    lpr_p = ["" for x in range(CAM_NUMBER_MAX)]
    lpr_number = ["" for x in range(CAM_NUMBER_MAX)]

    event_block_id = Bwim_event_data.block_id
    number_block = Bwim_event_data.number

    # print(Bwim_event_data.lpr_done[event_number])
    t_end = time.time() + 10
    while (time.time() < t_end):
        # check lpr done for xx seconds time
        # if (Bwim_event_data.lpr_done[0] == 1) & (Bwim_event_data.lpr_done[1] == 1)&(Bwim_event_data.lpr_done[2] == 1) & (Bwim_event_data.lpr_done[3] == 1):
        if (Bwim_event_data.lpr_done[event_number] == 1):
            print(Bwim_event_data.lpr_done[event_number])
            break

    for m in range(CAM_NUMBER_MAX):
        lpr_bg[m] = Bwim_event_data.lpr_bg[m]
        lpr_p[m] = Bwim_event_data.lpr_p[m]
        lpr_number[m] = Bwim_event_data.lpr[m]
        # print(lpr_bg[m])

    if (event_number == 0):
        Flag.event_1_triggered = 0 # clear event-1 trigger flag
    if (event_number == 1):
        Flag.event_2_triggered = 0  # clear event-2 trigger flag
    if (event_number == 2):
        Flag.event_3_triggered = 0  # clear event-3 trigger flag
    if (event_number == 3):
        Flag.event_4_triggered = 0  # clear event-4 trigger flag

    # initial event block index
    idx_block_start = event_block_id - EVENT_PRE_BLOCK[event_number]
    idx_block_finish = event_block_id + number_block -1
    # set event time stamp
    event_create_time = Data_Bwim[idx_block_start].create_time + "_" + str(event_number+1) # data_time_channel[1,2,3...]
    event_start_time = Data_Bwim[idx_block_start].start_time
    event_date = event_start_time[0:10]	# for create parent folder event
    if (idx_block_finish >= EVENT_BLOCK_BUFFER_MAX):
        # in case circular list index out of range ( EVENT_BLOCK_BUFFER_MAX )
        event_end_time = Data_Bwim[idx_block_finish-EVENT_BLOCK_BUFFER_MAX].end_time
    else:
        event_end_time = Data_Bwim[idx_block_finish].end_time

    # append relate block data to event data
    for i in range(idx_block_start, idx_block_finish + 1):  # EVENT_PRE_BLOCK to EVENT_POST_BLOCK
        # check circular list index
        if (i >= EVENT_BLOCK_BUFFER_MAX):
            # in case circular list index out of range ( EVENT_BLOCK_BUFFER_MAX )
            j = i - EVENT_BLOCK_BUFFER_MAX
        else:
            j = i
        # append numpy array block
        if ( j == idx_block_start):
            # get first block array
            event_strain_array = Data_Bwim[j].strain_array
            event_axle_array = Data_Bwim[j].axle_array
        else:
            # append other block array
            event_strain_array = np.append(event_strain_array, Data_Bwim[j].strain_array,axis = 0)
            event_axle_array = np.append(event_axle_array, Data_Bwim[j].axle_array, axis = 0)

        # collect max / min data
        event_min_strain.append(Data_Bwim[j].min_strain[event_number])
        event_max_strain.append(Data_Bwim[j].max_strain[event_number])

    # check event block's max / min strain data with EVENT_THRESHOLD_MICROVOLT
    if (max(event_max_strain) - min(event_min_strain)) < EVENT_THRESHOLD_MICROVOLT[event_number]:
        print ("[LANE-" + str(event_number+1) + "]: No Event : less than threshold.")
        # # remove the LPR image
        # # print "LPR="+lpr_image
        # for m in range(CAM_NUMBER_MAX):
        #     if (lpr_bg[m] != "ERROR") and (lpr_bg[m] != "NONE") :
        #         sleep(1)  # wait 800 lpr_image
        #         #print "remove LPR "+lpr_image
        #         os.remove(lpr_bg[m])
        #     # exit for create event file
        return
        # create event directory ./EVENT/event_date/event_create_time
        # event_dir = os.path.join(os.getcwd(), 'EVENT', event_date, event_create_time)
        # create event directory SYNOLOGY/EVENT_BWIM/YEAR/YEAR-MONTH/event_date/event_create_time

    month = time.localtime().tm_mon
    year = time.localtime().tm_year
    # event_dir = os.path.join(EVENT_BWIM_SYNOLOGY_DRIVE, year, year+'-'+'%02d'%(int(month)), event_date, event_create_time)
    event_dir = os.path.join(EVENT_BWIM_SYNOLOGY_DRIVE, str(year), str(year) + '-' + '%02d' % (month), event_date,
                             event_create_time)  #

    if not os.path.exists(event_dir):
        os.makedirs(event_dir)
    # create event strain and axle text file
    f = open(os.path.join(event_dir, 'event.txt'), 'wb')
    f.write("Event data number - ")  # header : Event data channel
    f.write(str(event_number + 1) + "\r\n")  # event channel
    f.write("Start time = ")  # header : Start time
    f.write(event_start_time + "\r\n")  # header : date & time created
    # concatenate strain and axle array
    event_bwim_array = np.concatenate((event_strain_array, event_axle_array), axis=1)
    # write bwim array into txt file
    np.savetxt(f, event_bwim_array, delimiter='\t', fmt='%1.2f')
    f.write("End time = ")  # footer : end time
    f.write(event_end_time + "\r\n")  # footer : date & time created
    f.close()


    # zero adjustment voltage for event_strain_array
    zero_voltage_array = event_strain_array[0]
    event_strain_array = event_strain_array - zero_voltage_array

    # Create plot
    fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={'height_ratios': [3, 1]})


    # plot strain data
    strain_plot_list_by_lane = STRAIN_PLOT_LANE_CH_MAP.get(event_number + 1, STRAIN_PLOT_CH_LIST)
    for ch_num in strain_plot_list_by_lane:
        ch_name = STRAIN_CH_NUM_TO_SENSOR_NAME.get(ch_num, ch_num)
        ch_index = ch_num - 1
        axs[0].plot(event_strain_array[:, ch_index], label='%s' % (ch_name))
    axs[0].set_title('%s : Event Lane-%s' % (BRIDGE_NAME, event_number + 1), fontweight='bold')
    axs[0].set_ylabel("WS (uV)")
    axs[0].grid()
    axs[0].legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize='small')

    # plot axle data
    if (event_number <= 1):
        axs[1].plot(event_axle_array[:, 0], label='%s' % ("AX-01"))
        axs[1].plot(event_axle_array[:, 1], label='%s' % ("AX-02"))
    else:
        axs[1].plot(event_axle_array[:, 2], label='%s' % ("AX-03"))
        axs[1].plot(event_axle_array[:, 3], label='%s' % ("AX-04"))
    axs[1].set_ylabel("AXLE (cm)")
    axs[1].set_ylim(0, 760)
    axs[1].set_yticks(np.arange(0, 760, 250))
    axs[1].grid()
    axs[1].legend(loc='center left', bbox_to_anchor=(1, 0.5))
    plt.tight_layout()

    # figure = plt.figure()
    # figure.set_size_inches(10, 8)
    fig.savefig(os.path.join(event_dir, 'plot.png'), dpi=150)
    # plt.show()
    # clear matplot memory
    plt.cla()
    plt.clf()
    fig.clear()
    plt.close(fig)

    # create event image files only same direction ( lane1/2 or lane3/4 )
    # if (event_number <= 1): # lane-1/2
    #     event_image(event_block_id, 0 ,event_dir,idx_block_finish)    # CAM number-0
    #
    # if (event_number > 1): # lane-3/4
    #     event_image(event_block_id, 1 ,event_dir,idx_block_finish)     # CAM number-1
    #
    # print ("[LANE-" + str(event_number + 1) + " [Capture image")
    event_image(event_block_id, event_number, event_dir, idx_block_finish)

    print ("[LANE-" + str(event_number + 1) +"]: Event "+event_create_time +" detected !!")

    return_code, lane = subprocess_call_bwim_truck_as_main(event_dir, lpr_number)
    BWIMret = return_code
    # lane = 0
    print("[AVC]: ret = %d, lane = %d" % (BWIMret, lane))

    # BWIMret
    # 0 = Unclassified
    # 1 = AVC lane 1 success ( to Sirindhorn (L))
    # 2 = AVC lane 2 success ( to Sirindhorn (R) )
    # 3 = AVC lane 3 success ( to Krungthon (R) )
    # 4 = AVC lane 4 success ( to Krungthon (L))

    # create LPR image files for truck event only
    # BWIMret = 100
    if (BWIMret >= 0):
        event_lpr_background = ["" for x in range(CAM_NUMBER_MAX)]
        event_lpr_plate = ["" for x in range(CAM_NUMBER_MAX)]

        # for m in range(CAM_NUMBER_MAX):

        # copy LPR image to event folder
        if (BWIMret == 0):
            m = event_number
        else:
            m = BWIMret - 1 # update lane direction from AVC Calculation
            if ( m !=  event_number):
                print ("[LANE-" + str(event_number + 1) + "]: Update direction to LANE-" + str(m+1) + " by AVC")
                event_number = m # update the event_number

        if (lpr_bg[m] != "ERROR") and (lpr_bg[m] != "NONE"):
        # if (lpr_bg[m] != "ERROR") :
            event_lpr_background[m] = os.path.join(event_dir, str(m+1) + '_background.jpg')
            event_lpr_plate[m] = os.path.join(event_dir, str(m+1) +'_plate.jpg')
            shutil.copyfile(lpr_bg[m], event_lpr_background[m])
            shutil.copyfile(lpr_p[m], event_lpr_plate[m])

    mqtt_json_file = event_dir + "\json_BANGPHLAT_" + event_create_time + ".json"

    if not os.path.exists(mqtt_json_file):
        mqtt_json_file = "test.json.txt"    # for invalid unclassification
        print ("[LANE-" + str(event_number + 1) + "]: BWIM Unclassified!!!")

    time.sleep(2.0) # waiting seconds for LPR image existing in event directory

    if os.path.exists(mqtt_json_file):
        with open(mqtt_json_file) as f:
            json_data = json.load(f)

        # update event_lpr_background incase of lane-1 detection false
        # if (json_data["lane"] == 1): #lane-1 :
        #     print(event_lpr_background[0])
        if (event_number == 0):
            event_lane_cam = 0
            # print(event_lpr_background[0])
            if os.path.exists(event_lpr_background[0]):
                line_notify_image = event_lpr_background[0]
            # in case of LPR image not existing, use grab image instead
            elif (time.localtime().tm_hour > 6) and (time.localtime().tm_hour < 18):
                # day time
                line_notify_image = os.path.join(event_dir, '1_3.jpg')
            else:
                # night time
                line_notify_image = os.path.join(event_dir, '1_3.jpg')
        # elif (json_data['lane'] == 2):   #lane-2
        elif (event_number == 1):
            event_lane_cam = 1
            # print(event_lpr_background[1])
            if os.path.exists(event_lpr_background[1]):
                line_notify_image = event_lpr_background[1]
            # in case of LPR image not existing, use grab image instead
            elif (time.localtime().tm_hour > 6) and (time.localtime().tm_hour < 18):
                # day time
                line_notify_image = os.path.join(event_dir, '2_3.jpg')
            else:
                # night time
                line_notify_image = os.path.join(event_dir, '2_3.jpg')
        # elif (json_data['lane'] == 3):  # lane-3
        elif (event_number == 2):
            event_lane_cam = 2
            # print(event_lpr_background[2])
            if os.path.exists(event_lpr_background[2]):
                line_notify_image = event_lpr_background[2]
            # in case of LPR image not existing, use grab image instead
            elif (time.localtime().tm_hour > 6) and (time.localtime().tm_hour < 18):
                # day time
                line_notify_image = os.path.join(event_dir, '3_3.jpg')
            else:
                # night time
                line_notify_image = os.path.join(event_dir, '3_3.jpg')
        # elif (json_data['lane'] == 4):  # lane-4
        elif (event_number == 3):
            event_lane_cam = 3
            # print(event_lpr_background[3])
            if os.path.exists(event_lpr_background[3]):
                line_notify_image = event_lpr_background[3]
            # in case of LPR image not existing, use grab image instead
            elif (time.localtime().tm_hour > 6) and (time.localtime().tm_hour < 18):
                # day time
                line_notify_image = os.path.join(event_dir, '4_3.jpg')
            else:
                # night time
                line_notify_image = os.path.join(event_dir, '4_3.jpg')

        # check confident for weight calculation
        if (json_data['confident'] == True):
            print ("[LANE-" + str(event_number + 1) +"]: BWIM Successful")
            # LPR.line_notify(json_data, event_create_time, event_number, line_notify_image, lpr_number[event_lane_cam], event_dir)
        else:
            print ("[LANE-" + str(event_number + 1) +"]: BWIM Unconfident!!!")
        
        # # thread cam
        # LPR.line_notify(json_data, event_create_time, event_number, line_notify_image, lpr_number[event_lane_cam],
        #                 event_dir)

        download_video_process(event_start_time, event_number, event_dir)

    # Zip the directory
    zip_directory(event_dir, event_dir+".zip")
    # Remove the directory
    sleep(10)
    remove_directory(event_dir)

    # if ( BWIMret == 0):
    #     # move event to unclassified folder
    #     shutil.move(event_dir,os.path.join(EVENT_UNCLASSIFIED_SYNOLOGY_DRIVE, event_date, event_create_time))
    #     return


# def event_process(block_id, number_block, event_number, lpr_bg,lpr_p,lpr_number):
def event_process(Bwim_event_data,event_number):
    # bwim_create_event_file(block_id)
    t = threading.Thread(target=bwim_create_event_file, args=(Bwim_event_data,event_number))
    t.daemon = True
    t.start()
    #t.join()

def download_video_process(event_start_time, event_number, event_dir):
    # bwim_create_event_file(block_id)
    t = threading.Thread(target=camera_download_video, args=(event_start_time, event_number, event_dir))
    t.daemon = True
    t.start()

def camera_grab_images(cam_number):
    while True:
        # camera[cam_number].grab()
        r,  image = camera[cam_number].read()
        if r == False:
            print("[CAM-"+str(cam_number+1)+"]: Can't read, Grab again")
            camera[cam_number].release()
            sleep(0.5)
            camera[cam_number] = cv2.VideoCapture(RTSP_LINK[cam_number])
        else:
            image_cam[cam_number] = image

def camera_download_video(event_start_time, event_number, event_dir):
    sleep(120) # delay time for RTSP ready to stream recoding
    # Define the input timezone (UTC+7)
    input_timezone = pytz.FixedOffset(420)  # 7 hours * 60 minutes
    # Parse the input time string into a naive datetime object
    naive_datetime = datetime.strptime(event_start_time, '%Y-%m-%d %H:%M:%S-%f')
    # Localize the naive datetime object to the input timezone
    localized_datetime = input_timezone.localize(naive_datetime)
    # Convert the localized datetime to UTC
    utc_datetime = localized_datetime.astimezone(pytz.utc)

    start_time = utc_datetime - timedelta(seconds=VIDEO_CAM_START[event_number])
    end_time = utc_datetime + timedelta(seconds=VIDEO_CAM_STOP[event_number])

    # Format the UTC datetime into the desired output format
    start_time_str = start_time.strftime('%Y%m%dT%H%M%SZ')
    end_time_str =  end_time.strftime('%Y%m%dT%H%M%SZ')

    rtsp_url = VIDEO_LINK[event_number] + "?starttime=" + start_time_str + "&endtime=" +end_time_str

    # time_name = datetime.today().strftime('%Y%m%d_%H%M%S')
    # output_file =  time_name + ".mp4"
    # output_file = event_dir + "//video.mp4"
    event_name = event_dir.split("EVENT_BWIM")[-1]
    output_file = EVENT_VIDEO_SYNOLOGY_DRIVE + event_name[:5] + event_name[13:] + ".mp4"
    # print(output_file)

    # FFmpeg command to download the video stream
    command = [
        "ffmpeg",
        '-rtsp_transport', 'tcp',
        '-i', rtsp_url,  # Input file (RTSP stream)
        '-c','copy',
        '-t', '00:00:10',  # Duration (optional, here it's set to 5 minutes)
        output_file  # Output file
    ]
    # Suppress output by redirecting stdout and stderr to os.devnull
    # with open(os.devnull, 'w') as fnull:
        # Run the FFmpeg command
    # try:
    #     ret = subprocess.call(command)
    #     # subprocess.call(command)
    #     if (ret == 0):
    #         print("[LANE-" + str(event_number + 1) +"]: Video downloaded successfully")
    #     else:
    #         print("[LANE-" + str(event_number + 1) + "]: Video downloaded fail")
    #
    # except subprocess.CalledProcessError as e:
    #     print("[LANE-" + str(event_number + 1) + "]: ffmpeg error occurred: " + e)

    # Number of retries
    max_retries = 1
    retry_delay = 10  # seconds between retries

    # Suppress output by redirecting stdout and stderr to os.devnull
    with open(os.devnull, 'w') as fnull:
        for attempt in range(max_retries):
            try:
                kill_ffmpeg_process()
                return_code = subprocess.call(command, stdout=fnull, stderr=fnull)
                if return_code == 0:
                    print("[LANE-" + str(event_number + 1) + "]: Video downloaded successfully")
                    # upload create video file to FTP NAS
                    sleep(10)
                    ftp_upload(output_file)
                    break
                else:
                    print("[LANE-" + str(event_number + 1) + "]: Video downloaded fail")
                    # print("FFmpeg failed with return code {}. Attempt {}/{}.".format(return_code, attempt + 1,
                    #                                                                  max_retries))
                    if attempt < max_retries - 1:
                        print("Retrying in {} seconds...".format(retry_delay))
                        time.sleep(retry_delay)
            except Exception as e:
                print("An error occurred: {}. Attempt {}/{}.".format(e, attempt + 1, max_retries))
                if attempt < max_retries - 1:
                    print("Retrying in {} seconds...".format(retry_delay))
                    time.sleep(retry_delay)
            else:
                if attempt == max_retries - 1:
                    print("Max retries reached. Exiting.")
                    # kill_ffmpeg_process()

# Function to kill ffmpeg process
def kill_ffmpeg_process():
    for proc in psutil.process_iter():
        try:
            # Check if the process name is ffmpeg
            if 'ffmpeg' in proc.name():
                print("Killing ffmpeg process (PID: {})".format(proc.pid))
                proc.kill()
        except psutil.NoSuchProcess:
            pass

def ftp_upload(event_file):
    # Connect to the server using the custom port
    ftp = ftplib.FTP()
    ftp.connect('neowave.ddns.net', 2122)
    # Login to the FTP server
    ftp.login(user='bwim', passwd='bwim-nas')
    file = open(event_file, 'rb')  # file to send
    # Change to the directory where you want to upload
    file_path_parts = event_file.split('\\')
    # Get the "year" and "date" parts
    year = file_path_parts[-3]
    date = file_path_parts[-2]
    ftp_dir = EVENT_FTP_PATH + "/" + year + "/" + date
    # print(ftp_dir)
    ftp.cwd(ftp_dir)
    ftp.storbinary('STOR ' + file_path_parts[-1], file)

    # # Open the local file in binary mode
    # with open(event_file, 'rb') as ftp_file:
    #     try:
    #         ftp.cwd(ftp_dir)
    #     except ftplib.error_perm:
    #         # Create directory recursively
    #         dirs = ftp_dir.split("/")
    #         for d in dirs:
    #             if d != "":
    #                 try:
    #                     ftp.cwd(d)
    #                 except ftplib.error_perm:
    #                     ftp.mkd(d)
    #                     ftp.cwd(d)
    #                     # Upload the file
    #     ftp.storbinary('STOR ' + file_path_parts[-1], ftp_file)
    # Close the connection
    ftp.quit()

def zip_directory(directory_path, zip_file_name):
    # Create a zip file
    with zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all the directories and files in the given directory
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                # Create the complete file path
                file_path = os.path.join(root, file)
                # Write the file to the zip archive
                zipf.write(file_path, os.path.relpath(file_path, directory_path))

def remove_directory(directory_path):
    # Remove the directory after zipping
    shutil.rmtree(directory_path)

def backup_event_file(day,month,year):
    # backup event folder on same month
    if (day == 20):
        # src_event_dir =./EVENT/year-month-day/
        src_event_dir_base = os.path.join(os.getcwd(), 'EVENT', str(year)+'-%02d'%(month)+'-')
        # event directory backup = D//EVENT_BWIM/year/year-month
        event_backup_dir = os.path.join('c:'+os.sep, 'EVENT_BWIM', str(year), str(year)+'-'+'%02d'%(month))
        if not os.path.exists(event_backup_dir):
            os.makedirs(event_backup_dir)
        for i in range(1, 11):
            src_event = src_event_dir_base+'%02d'%i
            # check src event path already exists
            if os.path.exists(src_event):
                print ('backup ' + (src_event) + ' to ' +(event_backup_dir))
                shutil.move(src_event, event_backup_dir)

    # backup event folder on previous month with same year
    if ((day == 1)or(day == 10)) and (month != 1):
        # src_event_dir =./EVENT/year-month-day/
        src_event_dir_base = os.path.join(os.getcwd(), 'EVENT', str(year)+'-%02d'%(month-1)+'-')
        # create event directory D;///EVENT_BWIM/year/year-month
        event_backup_dir = os.path.join('c:'+os.sep, 'EVENT_BWIM', str(year), str(year)+'-'+'%02d'%(month-1))
        if not os.path.exists(event_backup_dir):
            os.makedirs(event_backup_dir)
        for i in range(day+10, day+20+2):
            src_event = src_event_dir_base + '%02d' % i
            # check src event path already exists
            if os.path.exists(src_event):
                print ('backup ' + (src_event) + ' to ' + (event_backup_dir))
                shutil.move(src_event, event_backup_dir)

    # backup event folder on previous month and previous year
    if ((day == 1)or(day == 10))  and (month == 1):
        # src_event_dir =./EVENT/year-month-day/
        src_event_dir_base = os.path.join(os.getcwd(), 'EVENT', str(year - 1) + '-12-')
        # create event directory D;///EVENT_BWIM/year/year-month
        event_backup_dir = os.path.join('c:' + os.sep, 'EVENT_BWIM', str(year - 1), str(year - 1) + '-12')
        if not os.path.exists(event_backup_dir):
            os.makedirs(event_backup_dir)
        for i in range(day+10, day+20+2):
            src_event = src_event_dir_base + '%02d' % i
            # check src event path already exists
            if os.path.exists(src_event):
                print ('backup ' + (src_event) + ' to ' + (event_backup_dir))
                shutil.move(src_event, event_backup_dir)
    # cleat event back up flag
    Flag.event_backup = 0


def bwim_process():
    # initial MQTT set up
    time.sleep(5)
    # Check by serial number
    print ("Serial = ",d2xx.listDevices())
    # open the device, can directly open using zero location,
    # as the FT245 devices are enumerated starting from zero
    logger = d2xx.open(0)
    # Firstly, system reset for Hardware strain auto tare
    logger.write("SENSOR_RESET\r\n")
    print ("System reset..")
    logger.close()
    # waiting system ready
    time.sleep(5)
    logger = d2xx.open(0)
    # Start sensor acquisition command with 1 ms sampling period
    # SENSOR_START:ABCD
    # A = sampling rate >> 0:1000Hz,1:1024Hz,2:512Hz,3:200Hz
    # B = AC excied enable >> 0:disable,1:enable
    # C = Fast Step Fileter >> 0:disable,1:enable
    # D = autotare >> 0:start with zero tare,1:start with auto tare,2:start with load latest auto tare value
    print ("Start Reading\r\n")
    logger.write("SENSOR_START:1112\r\n")
    # initial the zero offset adjustment
    bwin_initial_zero_adjustment(logger)

    # camera grab image treading
    # camera_rtsp_testing()

    # # thread cam
    # threads = []
    # for i in range(CAM_NUMBER_MAX):
    #     # start camera grab image thread form 2 IP CAM
    #     t = threading.Thread(target=camera_grab_images, args=(i,))
    #     # t.daemon=True
    #     threads.append(t)
    #     t.start()

    # dailysummary = BWIMobj.DailySummary(MQTT_Bwim)
    # dailysummary.periodic_run()

    # LPR.line_notify()
    # LPR.get_lpr()
    # event_lpr_update = LPR.get_lpr_picture()
    # print event_lpr_update

    # main loop for data recording
    while 1:
        start_buffering_time = datetime.now()
        for i in range(EVENT_BLOCK_BUFFER_MAX):# 0 to BWIM_BLOCK_NUMBER-1
            # run capture image thread into Data_Bwim Block
            
            # # thread cam
            # start_capture_image(Data_Bwim[i])
            
            # strain and axle data recording into Data_Bwim Block
            record_data(logger, EVENT_BLOCK_TIME, Data_Bwim[i])
            for n in range(EVENT_NUMBER_MAX):
                # checking event occur
                if( Event_Bwim[n].number > 0):
                    # continue recording till event finish condition
                    if (EVENT_PRE_POST_MICROVOLT_DIFF[n] != 0):
                        #get different between first block and last block to determine ending event
                        Diff_Strain_End = (Data_Bwim[i].min_strain[n] - Data_Bwim[Event_Bwim[n].block_id - EVENT_PRE_BLOCK[n]].min_strain[n])
                    else:
                        Diff_Strain_End = EVENT_PRE_POST_MICROVOLT_DIFF[n] + 1  # disable this function by set Diff_Strain_End to threshold

                    # determine the ending event by checking Diff_Strain_End or EVENT_POST_BLOCK_MAX
                    if ((Event_Bwim[n].number >= 2) and ((Diff_Strain_End < EVENT_PRE_POST_MICROVOLT_DIFF[n])or(Event_Bwim[n].number > EVENT_POST_BLOCK_MAX[n]))):
                        Bwim_process_status.last_event_time = datetime.now()
                        # running event process
                        # event_process(Event_Bwim[n].block_id,Event_Bwim[n].number ,n, Event_Bwim[n].lpr_bg[0], Event_Bwim[n].lpr_p[0],Event_Bwim[n].lpr[0])
                        event_process(Event_Bwim[n],n)
                        # clear image lpr string on Event structure
                        # for m in range(CAM_NUMBER_MAX):
                        #     Event_Bwim[n].lpr[m] = 'NONE'
                        #     Event_Bwim[n].lpr_bg[m] = 'NONE'
                        #     Event_Bwim[n].lpr[m] = 'NONE'
                        Event_Bwim[n].number = 0

                    else:
                        # waiting for event occured finish
                        Event_Bwim[n].number += 1
        Bwim_process_status.last_record_time = datetime.now()
        Bwim_process_status.actual_buffering_data_time = Bwim_process_status.last_record_time - start_buffering_time
        if Bwim_process_status.actual_buffering_data_time <= Bwim_process_status.expacted_buffering_data_time:
            Bwim_process_status.strain_sampling_rate_status = "OK"      # reserve runtime 20%
        else: Bwim_process_status.strain_sampling_rate_status = "SLOW"  # runtime > 120%
       

        # scheduler system daily for summary LPR unknown on 0:05
        if (time.localtime().tm_hour == 0) and (time.localtime().tm_min == 5) and (Flag.lpr_summary == 0) :
            # LPR.lpr_thred_summary()
            Flag.lpr_summary = 1
        elif (time.localtime().tm_hour == 0) and (time.localtime().tm_min == 10) and (Flag.lpr_summary == 1):
            Flag.lpr_summary = 0


        # scheduler system remove All LPR Directory daily 1:00
        if (time.localtime().tm_hour == 0) and (time.localtime().tm_min == 59):
            # # power shell command for remove all items in FTP LPR
            # print ("Remove All LPR Items\r\n")
            # subprocess.call("powershell.exe Remove-Item C:\LPR\LPR_1\*", shell=True)
            # subprocess.call("powershell.exe Remove-Item C:\LPR\LPR_2\*", shell=True)
            # subprocess.call("powershell.exe Remove-Item C:\LPR\LPR_3\*", shell=True)
            # subprocess.call("powershell.exe Remove-Item C:\LPR\LPR_4\*", shell=True)
            logger.write("SENSOR_STOP\r\n")
            logger.close()
            print ("Stop Reading and system restart !!!\r\n")
            time.sleep(30)
            os.system("shutdown /r /t 1");  # restart system


        # scheduler for move event directory from onedrive to local backup directory on date 1,10,20 1:01AM
        # if (time.localtime().tm_hour == 31) and (time.localtime().tm_min == 1) and (Flag.event_backup == 0):
        #     if ( time.localtime().tm_mday == 1) or ( time.localtime().tm_mday == 10) or ( time.localtime().tm_mday == 20):
        #         t = threading.Thread(target=backup_event_file, args=(time.localtime().tm_mday,time.localtime().tm_mon,time.localtime().tm_year,))
        #         t.start()
        #         Flag.event_backup = 1

        # system shutdown process when Battery low alert
        if (Flag.system_shutdown == 1):
            logger.write("SENSOR_STOP\r\n")
            logger.close()
            os.system("shutdown /s /t 1");  # shutdown system

        # debug
        #event_process(Data_Bwim_2.id)
        #break

# -------- Start BWIM Process ---------#
bwim_process()

# camera_download_video("2024-08-11 18:49:27-320000", 0, "C:")
# -------- Module testing ---------#
# LPR.lpr_thred_summary()

# json_file = 'json_20220325_174102_2.json'
# bwim_dir ='C:/Users/BWIM/OneDrive/BWIM THAILAOS/PROGRAM/EVENT/2022-03-25/20220325_174102_2'
# with open(json_file) as f:
#     json_data = json.load(f)
# # line notify process
# LPR.line_notify(json_data, bwim_dir, 0, '1_background.jpg', '70-6477')

# image_file_1 = "D:/SynologyDrive/PHOTHARAM/LPR_BWIM/LPR_1/2021-07-16/20210716024045475_707073_BACKGROUND.jpg" # truck
# image_file_2 = "D:/SynologyDrive/PHOTHARAM/LPR_BWIM/LPR_1/2021-07-16/20210716022743559_709678_BACKGROUND.jpg" # light trick
# LPR.vehicle_type_ocr(image_file_2)
# #
# event_time = '20220426_143033_1'
# event_time = '20220426_173607_1'

# dir = 'C:/Users/BWIM/SynologyDrive/THAILAOS/EVENT_RAILS/2022/2022-04/'
# # dir = 'C:/Users/BWIM/SynologyDrive/THAILAOS/EVENT_RAILS/2022/2022-04/'
# # dir = 'C:/Users/BWIM/SynologyDrive/THAILAOS/EVENT_RAILS/2022/2022-03/'
#
# json_file = 'json_' + event_time +'.json'
# with open(os.path.join(dir,event_time,json_file)) as f:
#     json_data = json.load(f)
# # # line notify process
# LPR.line_notify_rail(json_data, event_time , dir + event_time)
