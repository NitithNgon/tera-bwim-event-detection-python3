#-*- coding: utf-8 -*-
import paho.mqtt.client as mqtt
import json
import threading
import shutil
import os
import glob
import datetime
import cv2
import requests
import subprocess
import csv
import math
import socket
import pytesseract
import ftplib
from pytesseract import Output
from time import sleep
import re
import itertools

LPR_CAM_MAX = 2
LPR_FTP_Dir = 'C:\LPR'  # Parent FTP folder
LPR_FTP_Dir_1 = 'C:\LPR\LPR_2'  # FTP folder which store LPR picture from Hikvsion IP CAM
LPR_FTP_Dir_2 = 'C:\LPR\LPR_2'  # FTP folder which store LPR picture from Hikvsion IP CAM
LPR_FTP_Dir_3 = 'C:\LPR\LPR_1'  # FTP folder which store LPR picture from Hikvsion IP CAM
LPR_FTP_Dir_4 = 'C:\LPR\LPR_1'  # FTP folder which store LPR picture from Hikvsion IP CAM
# LPR jpg format name is 20201231010203999_unknown_BACKGROUND.jpg
LPR_TIME_STR =  len(LPR_FTP_Dir_1) + 1    # parse LPR time from image file name
LPR_NAME_STR =  len(LPR_FTP_Dir_1) + 19   # parse LPR name from image file name

LPR_BWIM_DRIVE = "C:\LPR_BWIM"  # folder which store Trucks LPR
OVERWEIGHT_SYNOLOGY_DRIVE = "C:\SynologyDrive\BWIM_BMA_002\OVERWEIGHT" # folder which store OVerWeight Trucks
EVENT_SUMMARY_SYNOLOGY_DRIVE = "C:\SynologyDrive\www\BMA002_EVENT"   # folder which store event summary picuter
FTP_PATH_WWW = "/home/www/BMA002_EVENT"

HMI_TCP_IP = '192.168.1.179'  # '127.0.0.1'
HMI_TCP_PORT = 8005
HMI_TCP_BUFFER_SIZE = 1024

LINE_TOKEN_LIST_DEV = ["xxxxxxxxxxxxxxxxxxxxxxxxx",  # Group "BWIM: BMA-002 (BPT)" (P'pu's token)
                       "xxxxxxxxxxxxxxxxxxxxxxxxx",  # Group "BWIM: BMA-002 (BPT)" (Best's token)
                       "xxxxxxxxxxxxxxxxxxxxxxxxx",  # Group "BWIM: BMA-002 (BPT)" (Best's token)
                       "xxxxxxxxxxxxxxxxxxxxxxxxx",  # Group "BWIM: BMA-002 (BPT)" (Best's token)
                       ]
LINE_TOKEN_LIST_BMA = ["xxxxxxxxxxxxxxxxxxxxxxxxx",]  # Group "BWIM-BMA" (P'pu's token)
line_token_dev_group_cycle = itertools.cycle(LINE_TOKEN_LIST_DEV)
line_token_bma_group_cycle = itertools.cycle(LINE_TOKEN_LIST_BMA)

URL_LINE = "https://notify-api.line.me/api/notify"

POWER_SHELL_REMOVE_ITEM_1 = "powershell.exe Remove-Item C:\LPR\LPR_1\*"     # power shell command for remove all items in FTP LPR
POWER_SHELL_REMOVE_ITEM_2 = "powershell.exe Remove-Item C:\LPR\LPR_2\*"     # power shell command for remove all items in FTP LPR
POWER_SHELL_REMOVE_ITEM_3 = "powershell.exe Remove-Item C:\LPR\LPR_3\*"
POWER_SHELL_REMOVE_ITEM_4 = "powershell.exe Remove-Item C:\LPR\LPR_4\*"


LPR_DELAY_TIME =[2.5, 2.5, 2.5 ,3.0]   # delay time waiting for LPR trigger musb be positive value ( lane-0 laos->thai have continuty span effect, should some delay before event LPR trigger )
# LPR_DELAY_TIME = [2.0, 1.0, 1.5 ,2.5]    # delay time waiting for LPR triiger ( lane-0 laos->thai have continuty span effect, should some delay before event LPR trigger )
TIME_LPR_EVENT_DIFF_OUT = [-2.5, -2.5, -2.5, -3.0]  # different of LPR time & event trigger time to determine all right truck

TIME_LPR_EVENT_DIFF_IN = [2.25, 2.25, 2.25, 3.0]

class LPR_CAM:

    def line_daily_summary(self,bwim_json,event_dir):
        msg = str(bwim_json['bridge_name']) + ' OverWeight\r\nDaily Summary Report'

    def truck_class_wheels(self,truck_class):
        wheels = {1: '4',2: '6',3: '10',4: '12',5: '14',6: '18',7: '18',8: '20',9: '22',10: '24',11: '14',12: '18',13: '20',14: '22',15: '24'}
        return wheels.get(truck_class)

    def truck_class_weight_limit(self,truck_class):
        wheels = {1: '10.0',2: '15.0',3: '25.0',4: '30.0',5: '35.0',6: '40.5',7: '45.0',8: '50.0',9: '50.5',10: '50.5',11: '37.0',12: '47.0',13: '50.5',14: '50.5',15: '50.5'}
        return wheels.get(truck_class)

    def thai_month_string(self,month):
        thai_string = {1: 'มกราคม',2: 'กุมภาพันธ์',3: 'มีนาคม',4: 'เมษายน',5: 'พฤษภาคม',6: 'มิถุนายน',7: 'กรกฏาคม',8: 'สิงหาคม',9: 'กันยายน',10: 'ตุลาคม',11: 'พฤศจิกายน',12: 'ธันวาคม'}
        return thai_string.get(month)

    def hmi_event_display(self,msg):
        s = socket.socket(socket.AF_INET)
        try:
            s.settimeout(1)
            s.connect((HMI_TCP_IP,HMI_TCP_PORT))
            s.sendall(msg)
        except ( socket.timeout , socket.error ) as error:
            print("HMI Socket Error:")
            print(error)
        finally:
            s.close()

    def vehicle_type_ocr(self,lpr_image_cv2):
        try:
            pytesseract.pytesseract.tesseract_cmd = "C:/Program Files/Tesseract-OCR/tesseract.exe"
            # image_corp = lpr_image_cv2[1120:1200, 500:900]  # lane 1 corp  y=h, x=w 1072x1600, capture show all parameter
            image_corp = lpr_image_cv2[1072:1136, 410:900]  # lane 1 corp  y=h, x=w 1920x1136, capture show only vehicle type
            #adding custom options
            # custom_config = r' --oem 3 --psm6'
            result = pytesseract.image_to_string(image_corp,lang='eng')
            # have to show onlu the alphabes
            # result = re.sub('[^a-zA-Z\s]', '', result)

            return result
        except OSError as error:
            print(error)
            print("Tesseract Error")
            return "ERROR"

    def vehicle_lpr_ocr(self,lpr_image_cv2): # still not working
        pytesseract.pytesseract.tesseract_cmd = "C:/Program Files/Tesseract-OCR/tesseract.exe"
        # image_corp = lpr_image_cv2[1120:1200, 500:900]  # lane 1 corp  y=h, x=w 1072x1600
        #adding custom options
        # custom_config = r' --oem 3 --psm6'
        result = pytesseract.image_to_string(lpr_image_cv2,lang='tha+eng')
        return result

    def line_notify(self, bwim_json,event_create_time, event_lane, event_lpr_file, lpr_number,event_dir):

        current_date_time = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")


        # msg = str(bwim_json['bridge_name']) + '\r\n'  # Title Message
        msg = '\r\n'  # Title Message
        if (bwim_json['gross_vehicle_weight'] == 0):
            msg += 'Time = ' + current_date_time + '\r\n'  # for invalid classification
        else:
            msg += 'Time = ' + str(bwim_json['date_time']) + '\r\n'  # Event time message

        if (lpr_number != "UNKNOWN") and (lpr_number != "NONE") and (lpr_number != "ERROR"):
            msg += 'License Plate = ' + lpr_number + '\r\n'  # LPR message
        msg += 'Truck Class = ' + self.truck_class_wheels(bwim_json['vehicle_type']) + ' Wheels\r\n'  # Class message
        msg += 'Speed = ' + str(round(bwim_json['velocity'], 1)) + ' km/h\r\n'  # velocity message
        if (event_lane == 0):
            msg += 'Direction-1 = to Sirindhorn (L)\r\n'  # Road Lane message
        elif (event_lane == 1):
            msg += 'Direction-2 = to Sirindhorn (R)\r\n'  # Road Lane message
        elif (event_lane == 2):
            msg += 'Direction-3 = to KrungThon (R)\r\n'  # Road Lane message
        elif (event_lane == 3):
            msg += 'Direction-4 = to KrungThon (L)\r\n'  # Road Lane message


        msg += 'Weight = ' + str(bwim_json['gross_vehicle_weight']) + ' tons\r\n'  # weight message
        msg += 'Weight Limit =' + self.truck_class_weight_limit(bwim_json['vehicle_type']) + ' tons'
        if bwim_json['overweight_amount'] >= float(self.truck_class_weight_limit(bwim_json['vehicle_type']))*0.1:
            msg += '\r\nOverWeight Amount = *' + str(bwim_json['overweight_amount']) + '* tons'  # overweight amount message

        if (bwim_json['confident'] != True):
            msg += '\r\n _Unconfident Classification._ '

        if (bwim_json['gross_vehicle_weight'] == 0):
            msg += '\r\n _Un-Classification._ '

        # Corp LPR image using openCV
        image = cv2.imread(event_lpr_file)
        h = image.shape[0]  # image height
        w = image.shape[1]  # image width


        # if (h == 1200): # check image high to corp or resize
        if (h == 1136):  # check image high to corp or resize
            # corp the LPR image
            # crop image to 1072x1200
            if (event_lane == 0):
                image_corp = image[0:1072, 700:1900]   # lane 1 corp [0:1072, 820:w]
            elif (event_lane == 1):
                image_corp = image[0:1072, 100:1300]  # lane 2 corp [0:1072, 400:1500]
            elif (event_lane == 2):
                image_corp = image[0:1072, 100:1300]  # lane 3 corp [0:1072, 600:1700]
            elif (event_lane == 3):
                image_corp = image[0:1072, 500:1700]  # lane 4 corp [0:1072, 820:w]
        else:
            # resize the grab image
            dim = (1920,1072)
            image_corp = cv2.resize(image[0:h, 0:w],dim,interpolation=cv2.INTER_AREA)
            print(("[LANE-" + str(event_lane + 1) + "]: Not found LPR image using grab image instead"))

        # description image is 540x1072
        desc_image = cv2.imread('DESCRIPTION.jpg')

        if (bwim_json['gross_vehicle_weight'] == 0):
            date_str, time_str = current_date_time.split(' ')  # for invalid classification
        else:
            date_str, time_str = str(bwim_json['date_time']).split(' ')
        # put date String on Picture
        cv2.putText(
            desc_image,  # numpy array on which text is written
            date_str,  # weight String
            (45, 105),  # width, high
            cv2.FONT_HERSHEY_SIMPLEX,  # font family
            2,  # font size
            (255, 255, 255),  # font color B G R
            6)  # thickness
        # put time String on Picture
        cv2.putText(
            desc_image,  # numpy array on which text is written
            time_str,  # weight String
            (45, 180),  # width, high
            cv2.FONT_HERSHEY_SIMPLEX,  # font family
            2,  # font size
            (255, 255, 255),  # font color B G R
            6)  # font stroke
        if (lpr_number != "UNKNOWN") and (lpr_number != "NONE") and (lpr_number != "ERROR"):
            # put LPR String on Picture
            cv2.putText(
                desc_image,  # numpy array on which text is written
                lpr_number,  # weight String
                (50, 350),  # width, high
                cv2.FONT_HERSHEY_SIMPLEX,  # font family
                3,  # font size
                (255, 255, 255),  # font color B G R
                7)  # font thickness
        axle_count_str = 'AXLE - ' + str(bwim_json['axle_count'])
        # put truck class String on Picture
        cv2.putText(
            desc_image,  # numpy array on which text is written
            axle_count_str,  # weight String
            (225, 445),  # width, high
            cv2.FONT_HERSHEY_SIMPLEX,  # font family
            2,  # font size
            (255, 255, 255),  # font color B G R
            7)  # font thickness
        truck_class_str = self.truck_class_wheels(bwim_json['vehicle_type']) + ' Wheels'  # truck class
        # put truck class String on Picture
        cv2.putText(
            desc_image,  # numpy array on which text is written
            truck_class_str,  # weight String
            (50, 545),  # width, high
            cv2.FONT_HERSHEY_SIMPLEX,  # font family
            3,  # font size
            (255, 255, 255),  # font color B G R
            7)  # font thickness
        # lane_str = 'LANE - ' + str(bwim_json['lane']) event_lane
        lane_str = 'LANE - ' + str(event_lane+1)
        # put truck class String on Picture
        cv2.putText(
            desc_image,  # numpy array on which text is written
            lane_str,  # weight String
            (225, 630),  # width, high
            cv2.FONT_HERSHEY_SIMPLEX,  # font family
            2,  # font size
            (255, 255, 255),  # font color B G R
            7)  # font thickness
        truck_speed_str = str(math.trunc(bwim_json['velocity'])) + ' km/h'  # truck class
        # put truck speed String on Picture
        cv2.putText(
            desc_image,  # numpy array on which text is written
            truck_speed_str,  # weight String
            (50, 725),  # width, high
            cv2.FONT_HERSHEY_SIMPLEX,  # font family
            3,  # font size
            (255, 255, 255),  # font color B G R
            7)  # font thickness
        # set weight string text
        weight_str = "%.1f" % (bwim_json['gross_vehicle_weight']) + ' T'
        # put weight String on Picture
        cv2.putText(
            desc_image,  # numpy array on which text is written
            weight_str,  # weight String
            (80, 925),  # width, high
            cv2.FONT_HERSHEY_SIMPLEX,  # font family
            4,  # font size
            (255, 255, 255),  # font color B G R
            7)  # font thickness
        # set overweight string text
        if bwim_json['overweight_amount'] >= float(self.truck_class_weight_limit(bwim_json['vehicle_type']))*0.1:
            over_weight_str = '(' + "%.1f"%(bwim_json['overweight_amount']) + ' T)'
            # put weight String on Picture
            cv2.putText(
                desc_image,  # numpy array on which text is written
                over_weight_str,  # weight String
                (80, 1040),  # width, high
                cv2.FONT_HERSHEY_SIMPLEX,  # font family
                3,  # font size
                (0, 128, 255),  # font color B G R
                7)  # font thickness

        # concatenate image with same horizontal 1x2
        image_lpr = cv2.hconcat([image_corp, desc_image])
        # image_lpr = desc_image
        # write Picture which corp image and LPR number insetting
        cv2.imwrite(event_lpr_file, image_lpr)
        # sleep(1)
        # image of LPR to shown
        file_img_1 = {'imageFile': open(event_lpr_file, 'rb')}
        line_msg = ({'message': msg})

        # if (bwim_json['gross_vehicle_weight'] > 20) :
        if ((bwim_json['gross_vehicle_weight'] > 20) and (bwim_json['overweight_amount'] >= float(self.truck_class_weight_limit(bwim_json['vehicle_type'])) * 0.1)):# or (bwim_json['vehicle_type'] > 3):
            LINE_TOKEN = next(line_token_bma_group_cycle)  # for BMA
        else:
            LINE_TOKEN = next(line_token_dev_group_cycle)  # for dev team only

        LINE_HEADERS = {"Authorization": "Bearer " + LINE_TOKEN}

        sleep(1) # waiting for everything completed

        session = requests.Session()
        session_post = session.post(URL_LINE, headers=LINE_HEADERS, files=file_img_1, data=line_msg)
        with open("line_notify_log.txt", 'a') as line_notify_log_file:
            line_notify_log_file.write(str(event_create_time).encode('utf-8')\
                                       + "-" + str(session_post.text).encode('utf-8')\
                                       + " - Remaining" + str(session_post.headers.get("X-RateLimit-Remaining"))\
                                       + " - ImageRemaining" + str(session_post.headers.get("X-RateLimit-ImageRemaining"))\
                                       + "\n")
        if (session_post.status_code != 200):
            print(("[LANE-" + str(event_lane + 1) + "]: Line notify Fail / status code = " + str(session_post.text)))
        session.close()

        if (1):  # for dev team only see the BWIM Signal
            session = requests.Session()
            msg = ({'message': 'Signal'})
            file_img_3 = {'imageFile': open(os.path.join(event_dir, 'plot.png'), 'rb')}
            session_post = session.post(URL_LINE, headers=LINE_HEADERS, files=file_img_3, data=msg)
            session.close()

        # copy line image to summary folder
        EVENT_DATE = datetime.datetime.today().strftime("%Y-%m-%d")
        EVENT_YEAR = datetime.datetime.today().strftime("%Y")
        summary_event_dir = os.path.join(EVENT_SUMMARY_SYNOLOGY_DRIVE, EVENT_YEAR, EVENT_DATE)
        # create summary_event_dir
        if not os.path.exists(summary_event_dir):
            os.makedirs(summary_event_dir)
        shutil.copyfile(event_lpr_file, os.path.join(summary_event_dir, event_create_time + '.jpg'))

        # upload  image to ftp server
        session = ftplib.FTP()  # create a new FTP() instance
        session.connect('neowave.ddns.net', 2122)  # connect to NAS FTP site
        session.login('bwim', 'bwim-nas')  # log into the FTP site
        file = open(event_lpr_file, 'rb')  # file to send
        session.cwd(FTP_PATH_WWW)  # change remote directory to www folder

        if EVENT_YEAR in session.nlst():  # check if EVENT_YEAR folder exiest inside directory
            session.cwd(EVENT_YEAR)  # change into EVENT_YEAR directory
        else:
            session.mkd(EVENT_YEAR)  # create a new EVENT_YEAR Directory on server
            session.cwd(EVENT_YEAR)  # change into EVENT_YEAR directory

        if EVENT_DATE in session.nlst():  # check if EVENT_YEAR folder exiest inside directory
            session.cwd(EVENT_DATE)  # change into EVENT_YEAR directory
        else:
            session.mkd(EVENT_DATE)  # create a new EVENT_YEAR Directory on server
            session.cwd(EVENT_DATE)  # change into EVENT_YEAR directory

        session.storbinary('STOR ' + event_create_time + '.jpg', file)  # upload the file
        file.close()  # close file and jm,.FTP
        session.quit()

        # Truck over weight which LPR detected copy to Overweight_TRUCKS folder
        if (bwim_json['overweight_amount'] >= float(self.truck_class_weight_limit(bwim_json['vehicle_type']))*0.1):
            year_str = datetime.datetime.today().strftime('%Y')
            year_month_str = datetime.datetime.today().strftime('%Y-%m')
            overweight_trucks_dir = os.path.join(OVERWEIGHT_SYNOLOGY_DRIVE, year_str, year_month_str, lpr_number)
            if not os.path.exists(overweight_trucks_dir):
                os.makedirs(overweight_trucks_dir)
            time_stmp_str = str(date_str).replace("-", "") + str(time_str).replace(":", "") + '_'
            class_str = str(bwim_json['vehicle_type']) + '_'
            speed_str = str(math.trunc(bwim_json['velocity'])) + '_'
            weight_str = str(bwim_json['gross_vehicle_weight']) + '_' + str(bwim_json['overweight_amount'])
            shutil.copyfile(event_lpr_file, os.path.join(overweight_trucks_dir,time_stmp_str + class_str + speed_str + weight_str + '.jpg'))
            print(("[LANE-" + str(event_lane + 1) + "]: Overweight Truck Detected"))

        # send tcp socket to HMI event display
        # hmi_msg = str(date_str) +"     "
        # hmi_msg = hmi_msg[:10] + str(time_str) + str(bwim_json['lane']) + "     "
        # if (lpr_number != "UNKNOWN") and (lpr_number != "NONE") and (lpr_number != "ERROR"):
        #     hmi_msg = hmi_msg[:20] + lpr_number + str(bwim_json['vehicle_type']) + "     "
        # else:
        #     hmi_msg = hmi_msg[:20] + "       " + str(bwim_json['vehicle_type']) + "     "
        # hmi_msg = hmi_msg[:30] + truck_class_str + "      "
        # hmi_msg = hmi_msg[:40] + truck_speed_str + "      "
        # hmi_msg = hmi_msg[:50] + str(bwim_json['gross_vehicle_weight']) + " T     "
        # hmi_msg = hmi_msg[:60] + self.truck_class_weight_limit(bwim_json['vehicle_type']) + " T      "
        # if bwim_json['overweight_amount'] >= 1:
        #     hmi_msg = hmi_msg[:70] + str(bwim_json['overweight_amount'])+" T "
        # else:
        #     hmi_msg = hmi_msg[:70] + "           "
        #
        # self.hmi_event_display(hmi_msg)

    def LPR_fixed_OCR_number(self, plate):
        # fix OCR missing LPR ( Trucks LPR contain number only, not have character )
        plate = plate.replace('D', '0')
        plate = plate.replace('O', '0')
        plate = plate.replace('T', '1')
        plate = plate.replace('I', '1')
        plate = plate.replace('J', '1')
        plate = plate.replace('L', '1')
        plate = plate.replace('F', '1')
        plate = plate.replace('A', '4')
        plate = plate.replace('S', '5')
        plate = plate.replace('B', '8')
        plate = plate.replace('Z', '2')
        return plate


    def lpr_process(self,event_time,Bwim_event,event_cam): # specific lane


        LPR_DATE = datetime.datetime.today().strftime("%Y-%m-%d")
        if (event_cam == 0 ):
            event_lane = 1
            LPR_FTP_Dir = LPR_FTP_Dir_1
            lpr_picture_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_1', LPR_DATE, )
            lpr_plate_dir = os.path.join(lpr_picture_dir,'PLATE')
            lpr_invalid_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_1', 'INVALID', LPR_DATE)
        elif (event_cam == 1):
            event_lane = 2
            LPR_FTP_Dir = LPR_FTP_Dir_2
            lpr_picture_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_2', LPR_DATE)
            lpr_plate_dir = os.path.join(lpr_picture_dir,'PLATE')
            lpr_invalid_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_2', 'INVALID', LPR_DATE)
        elif (event_cam == 2):
            event_lane = 3
            LPR_FTP_Dir = LPR_FTP_Dir_3
            lpr_picture_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_3', LPR_DATE)
            lpr_plate_dir = os.path.join(lpr_picture_dir,'PLATE')
            lpr_invalid_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_3', 'INVALID', LPR_DATE)
        elif (event_cam == 3):
            event_lane = 4
            LPR_FTP_Dir = LPR_FTP_Dir_4
            lpr_picture_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_4', LPR_DATE)
            lpr_plate_dir = os.path.join(lpr_picture_dir,'PLATE')
            lpr_invalid_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_4', 'INVALID', LPR_DATE)

        try:
            # check LPR FTP is empty ?
            sleep(LPR_DELAY_TIME[event_cam]) # wait x seconds for LPR Process

            if not os.listdir(LPR_FTP_Dir):
                sleep(0.2) # wait 1 seconds when FTP empty
                if not os.listdir(LPR_FTP_Dir):
                    print("[LANE-" +str(event_lane) +"]: LPR FTP Directory is empty")
                    Bwim_event.lpr[event_cam] = "ERROR"
                    Bwim_event.lpr_bg[event_cam] = "ERROR"
                    Bwim_event.lpr_p[event_cam] = "ERROR"
                    Bwim_event.lpr_done[event_cam] =1
                    return

            # get absolute path jpg of latest image on LPR FTP Dir
            # list_of_files = glob.iglob(LPR_FTP_Dir + '\*_BACKGROUND.jpg')
            list_of_files = sorted(glob.iglob(LPR_FTP_Dir + '\*_BACKGROUND.jpg'), key=os.path.getctime, reverse=True)
            # lpr_ftp_cam = max(list_of_files,key=os.path.getctime)
            lpr_ftp_cam = list_of_files[0]
            lpr_ftp_cam_2 = list_of_files[1]
            lpr_ftp_cam_3 = list_of_files[2]
            # parse for LPR image file name
            lpr_file_background = lpr_ftp_cam[LPR_TIME_STR:]
            lpr_file_plate = lpr_file_background.replace("_BACKGROUND", "_PLATE")
            # print ("Lpr file name = " + lpr_file_background)
            # print ("Lpr file plate = " + lpr_file_plate)
            # parse for LPR capture time
            lpr_time = lpr_ftp_cam[LPR_TIME_STR:(LPR_TIME_STR+17)]
            lpr_time_obj = datetime.datetime.strptime(lpr_time,"%Y%m%d%H%M%S%f")
            # parse for LPR number
            lpr_plate, lpr_jpg=  lpr_ftp_cam[LPR_NAME_STR:].split('_BACKGROUND')
            event_time_obj = datetime.datetime.strptime(event_time,"%Y-%m-%d %H:%M:%S-%f")
            # print ("EVENT TIME:",event_time_obj)

            # find delta time between LPR capture time and Event time
            time_diff_1 = lpr_time_obj - event_time_obj

            # get vehicle_type on caption background image by Tesseract OCR
            img = cv2.imread(lpr_ftp_cam)
            vehicle_type = self.vehicle_type_ocr(img)

            print(("[LANE-" + str(event_lane) + "]: License Plate = " + lpr_plate + " / Time: " + str(lpr_time_obj) + " / diff: " + str(time_diff_1.total_seconds())) + ' / Type: ' + vehicle_type)
            # check time_diff is lower than TIME_LPR_EVENT_DIFF_OUT ?
            if (float(time_diff_1.total_seconds()) < float(TIME_LPR_EVENT_DIFF_OUT[event_cam])): #-2.5
                print(("[LANE-" + str(event_lane) + "]: LPR time diff error"))
                Bwim_event.lpr[event_cam] = "ERROR"
                Bwim_event.lpr_bg[event_cam] = "ERROR"
                Bwim_event.lpr_p[event_cam] = "ERROR"
                Bwim_event.lpr_done[event_cam] = 1
                return

            elif (len(lpr_plate) >= 6) and (str(lpr_plate).isdigit()) and (int(lpr_plate[0]) >= 5) and (vehicle_type != 'Sedan') and (vehicle_type != 'SUU“APU'):
                print(("[LANE-" + str(event_lane) + "]: LPR PLATE OK"))

            # # check time_diff is greater than TIME_LPR_EVENT_DIFF_IN ? ( and Truck LPR must be numeric )
            # elif (float(time_diff_1.total_seconds()) > float(TIME_LPR_EVENT_DIFF_IN[event_lane])) or ((lpr_plate.isdigit() == False) and (lpr_plate != 'unknown')):
            elif (float(time_diff_1.total_seconds()) > float(TIME_LPR_EVENT_DIFF_IN[event_cam])) or ((vehicle_type.strip() != 'Truck'.strip()) and (vehicle_type.strip() != 'Light Truck'.strip()) and (vehicle_type.strip() != 'Bus'.strip()) and (vehicle_type.strip() != 'BUS'.strip())) :#and (vehicle_type.strip() != 'Pickup Truck'.strip())):
            # elif (float(time_diff_1.total_seconds()) > 2.5) or :
            # elif (vehicle_type != 'Truck') and (vehicle_type != 'Light Truck') and (vehicle_type != 'Bus') and (vehicle_type != 'Pickup Truck'):


                print(("[LANE-" + str(event_lane) + "]: Invalid Type, Get new LPR"))
                # get the absolute path lpr image for latest second on LPR FTP Dir
                # list_of_files = sorted(glob.iglob(LPR_FTP_Dir + '\*_BACKGROUND.jpg'), key=os.path.getctime, reverse=True)
                # list_of_files_2 =  sorted(list_of_files,key=os.path.getctime, reverse=True)
                # lpr_ftp_cam = list_of_files_2[1]


                lpr_ftp_cam = lpr_ftp_cam_2
                lpr_file_background = lpr_ftp_cam[LPR_TIME_STR:]
                lpr_file_plate = lpr_file_background.replace("_BACKGROUND", "_PLATE")
                lpr_time = lpr_ftp_cam[LPR_TIME_STR:(LPR_TIME_STR + 17)]
                lpr_time_obj = datetime.datetime.strptime(lpr_time, "%Y%m%d%H%M%S%f")
                lpr_plate, lpr_jpg = lpr_ftp_cam[LPR_NAME_STR:].split('_BACKGROUND')
                # event_time_obj = datetime.datetime.strptime(event_time, "%Y-%m-%d %H:%M:%S-%f")
                time_diff_2 = lpr_time_obj - event_time_obj
                # check time_diff is lower than TIME_LPR_EVENT_DIFF_OUT ?
                # get vehicle_type on caption background image by Tesseract OCR
                img = cv2.imread(lpr_ftp_cam)
                vehicle_type = self.vehicle_type_ocr(img)
                print(("[LANE-" + str(event_lane) + "]: New License Plate = " + lpr_plate + " / Time: " + str(lpr_time_obj) + " / diff: " + str(time_diff_2.total_seconds())) + ' / Type: ' + vehicle_type)

                if (float(time_diff_2.total_seconds()) < float(TIME_LPR_EVENT_DIFF_OUT[event_cam])):  # -2.5
                    print(("[LANE-" + str(event_lane) + "]: LPR time diff error"))
                    Bwim_event.lpr[event_cam] = "ERROR"
                    Bwim_event.lpr_bg[event_cam] = "ERROR"
                    Bwim_event.lpr_p[event_cam] = "ERROR"
                    Bwim_event.lpr_done[event_cam] = 1
                    return

                elif (len(lpr_plate) >= 6) and (str(lpr_plate).isdigit()) and (int(lpr_plate[0]) >= 5) and (vehicle_type != 'Sedan') and (vehicle_type != 'SUU“APU'):
                    print(("[LANE-" + str(event_lane) + "]: LPR PLATE OK"))

                else:
                     # if (str(lpr_plate).isdigit() == False):
                    if (vehicle_type.strip() != 'Truck'.strip()) and (vehicle_type.strip() != 'Light Truck'.strip()) and (vehicle_type.strip() != 'Bus'.strip()) and (vehicle_type.strip() != 'BUS'.strip()): # and (vehicle_type.strip() != 'Pickup Truck'.strip()):
                        print(("[LANE-" + str(event_lane) + "]: Still Invalid Type, Get again"))
                        lpr_ftp_cam = lpr_ftp_cam_3
                        lpr_file_background = lpr_ftp_cam[LPR_TIME_STR:]
                        lpr_file_plate = lpr_file_background.replace("_BACKGROUND", "_PLATE")
                        lpr_time = lpr_ftp_cam[LPR_TIME_STR:(LPR_TIME_STR + 17)]
                        lpr_time_obj = datetime.datetime.strptime(lpr_time, "%Y%m%d%H%M%S%f")
                        lpr_plate, lpr_jpg = lpr_ftp_cam[LPR_NAME_STR:].split('_BACKGROUND')
                        # event_time_obj = datetime.datetime.strptime(event_time, "%Y-%m-%d %H:%M:%S-%f")
                        time_diff_3 = lpr_time_obj - event_time_obj
                        # check time_diff is lower than TIME_LPR_EVENT_DIFF_OUT ?
                        # get vehicle_type on caption background image by Tesseract OCR

                        img = cv2.imread(lpr_ftp_cam)
                        # get vehicle_type on caption background image by Tesseract OCR
                        vehicle_type = self.vehicle_type_ocr(img)
                        print(("[LANE-" + str(event_lane) + "]: New License Plate = " + lpr_plate + " / Time: " + str(lpr_time_obj) + " / diff: " + str(time_diff_3.total_seconds())) + ' / Type: ' + vehicle_type)

                        if float(time_diff_3.total_seconds()) < float(TIME_LPR_EVENT_DIFF_OUT[event_cam]):  # -2.5
                            print(("[LANE-" + str(event_lane) + "]: LPR time diff error"))
                            Bwim_event.lpr[event_cam] = "ERROR"
                            Bwim_event.lpr_bg[event_cam] = "ERROR"
                            Bwim_event.lpr_p[event_cam] = "ERROR"
                            Bwim_event.lpr_done[event_cam] = 1
                            return

                        elif (len(lpr_plate) >= 6) and (str(lpr_plate).isdigit()) and (int(lpr_plate[0]) >= 5) and (vehicle_type != 'Sedan') and (vehicle_type != 'SUU“APU'):
                            print(("[LANE-" + str(event_lane) + "]: LPR PLATE OK"))

                        else:
                            if (vehicle_type.strip() != 'Truck'.strip()) and (vehicle_type.strip() != 'Light Truck'.strip()) and (vehicle_type.strip() != 'Bus'.strip()) and (vehicle_type.strip() != 'BUS'.strip()):  # and (vehicle_type.strip() != 'Pickup Truck'.strip()):
                                Bwim_event.lpr[event_cam] = "ERROR"
                                Bwim_event.lpr_bg[event_cam] = "ERROR"
                                Bwim_event.lpr_p[event_cam] = "ERROR"
                                Bwim_event.lpr_done[event_cam] = 1
                                return
                            else:   # get LPR Result on 3rd trial
                                print(("[LANE-" + str(event_lane) + "]: LPR OK"))
                    else:   # get LPR Result on 2nd trial
                        print(("[LANE-" + str(event_lane) + "]: LPR OK"))
            else:  # get LPR Result on 1st trial
                print(("[LANE-" + str(event_lane) + "]: LPR OK"))

            if (lpr_plate != 'unknown'):
                # OCR number correction
                lpr_plate = self.LPR_fixed_OCR_number(lpr_plate)
            # create LPR on One Drive storage directory
            if not os.path.exists(lpr_picture_dir):
                os.makedirs(lpr_picture_dir)
            # create LPR on One Drive storage directory
            if not os.path.exists(lpr_plate_dir):
                os.makedirs(lpr_plate_dir)
                # update lpr background on Bwim_event
            # create LPR on One Drive storage directory
            if not os.path.exists(lpr_invalid_dir):
                os.makedirs(lpr_invalid_dir)

            # check Invalid Truck LPR ( numeric plate and first digit >= 5 )
            if (str(lpr_plate).isdigit() == False) and (lpr_plate != 'unknown'):
                print("[LANE-" + str(event_lane) + "]: is not numeric LPR")
                Bwim_event.lpr[event_cam] = "UNKNOWN"
                # Bwim_event.lpr_bg[event_cam] = "ERROR"
                # Bwim_event.lpr_p[event_cam] = "ERROR"
                lpr_invalid_file = os.path.join(lpr_invalid_dir, lpr_plate + '.jpg')
                shutil.copyfile(lpr_ftp_cam, lpr_invalid_file)
            elif (lpr_plate != 'unknown'):
                # Truck LPR must be 50xxxx -99xxxx
                if (int(lpr_plate[0]) < 5):
                    print("[LANE-" + str(event_lane) + "]: is not Truck LPR")
    #                Bwim_event.lpr[event_cam] = "UNKNOWN"
    #                # Bwim_event.lpr_bg[event_cam] = "ERROR"
    #                # Bwim_event.lpr_p[event_cam] = "ERROR"
    #                lpr_invalid_file = os.path.join(lpr_invalid_dir, lpr_plate + '.jpg')
    #                shutil.copyfile(lpr_ftp_cam, lpr_invalid_file)


            # check invalid length LPR
            if ((len(lpr_plate) > 7) or (len(lpr_plate) < 6)) and (lpr_plate != 'unknown'):
                print("[LANE-" + str(event_lane) + "]: LPR length invalid")
                Bwim_event.lpr[event_cam] = "UNKNOWN"
                 # move LPR invlid length to LENGTH_INVALID folder
                # lpr_invalid_file = os.path.join(lpr_invalid_dir,lpr_plate + '.jpg')
                # shutil.copyfile(lpr_ftp_cam, lpr_invalid_file)
                # return

            # Corp LPR image using openCV
            img = cv2.imread(lpr_ftp_cam)
            # corp image to square for shown on main event picture BWIM app
            h = img.shape[0]  # image height
            w = img.shape[1]  # image width
            # image_corp = img[0:h, (w-h)-130:w-130]  # y=h, x=w
            image_corp = img[0:h, 0:w ] # y=h, x=w

            # Check LPR Result and insert lpr_plate caption
            if ( lpr_plate != 'unknown' ) and (len(lpr_plate) == 6) and (lpr_plate.isdigit() == True):
                # AA-BBBB format insert '-' between front & back plate format
                lpr_plate = lpr_plate[:2] + '-' + lpr_plate[2:] # set plate format "AA-BBBB:
                Bwim_event.lpr[event_cam] = lpr_plate
            elif ( lpr_plate != 'unknown' ) and (len(lpr_plate) == 7) and (lpr_plate.isdigit() == True):
                # AAA-BBBB format insert '-' between front & back plate format
                lpr_plate = lpr_plate[:3] + '-' + lpr_plate[3:] # set plate format "AAA-BBBB:
                Bwim_event.lpr[event_cam] = lpr_plate
            else:
                Bwim_event.lpr[event_cam] = "UNKNOWN"

            # update path of bg/plate on Bwim_event

            Bwim_event.lpr_bg[event_cam] = os.path.join(lpr_picture_dir, lpr_file_background)
            Bwim_event.lpr_p[event_cam] = os.path.join(lpr_plate_dir, lpr_file_plate)
            # copy LPR file plate to lpr folder
            cv2.imwrite(Bwim_event.lpr_bg[event_cam], image_corp)
            # copy LPR file plate to plate folder
            if (  lpr_plate == 'unknown'):
                lpr_ftp_cam_plate = lpr_ftp_cam.replace("_BACKGROUND", "_VEHICLE")
            else:
                lpr_ftp_cam_plate = lpr_ftp_cam.replace("_BACKGROUND", "_PLATE")

            shutil.copyfile(lpr_ftp_cam_plate, Bwim_event.lpr_p[event_cam])
            Bwim_event.lpr_done[event_cam] = 1

            # # remove all LPR picture on LPR_FTP_Dir
            # if (event_lane == 0):
            #     subprocess.call(POWER_SHELL_REMOVE_ITEM_1, shell=True)
            # elif (event_lane == 1):
            #     subprocess.call(POWER_SHELL_REMOVE_ITEM_2, shell=True)

        except WindowsError as e:
            print(("[LANE-" +str(event_lane)+"] LPR Directory Error:"))
            print(e)
            POWER_SHELL_REMOVE_LPR = 'powershell.exe Remove-Item -Path "' + LPR_FTP_Dir +'\*" -Recurse -Force'
            print(POWER_SHELL_REMOVE_LPR)
            subprocess.call(POWER_SHELL_REMOVE_LPR, shell=True)
            Bwim_event.lpr_done[event_cam] = 1


    def concat_tile(self,im_list_2D):
        return cv2.vconcat([cv2.hconcat(im_list_h) for im_list_h in im_list_2D])

    def lpr_thread(self,event_time, Bwim_event, event_lane):
        t = threading.Thread(target=self.lpr_process, args=(event_time, Bwim_event,event_lane))
        t.start()

    def lpr_thred_summary(self):
        t = threading.Thread(target=self.lpr_summary)
        t.start()

    def lpr_summary(self):
        # get the absolute path jpg of latest image on LPR FTP Dir
        # get last day
        date = datetime.date.today() - datetime.timedelta(1)
        LPR_DATE = date.strftime("%Y-%m-%d")
        lpr_count_data = [date.strftime("%d/%m/%Y"),date.strftime("%a")]

        for event_lane in range(LPR_CAM_MAX):
            # initial LPR counter daily
            count_day = 0
            count_night = 0
            count_day_fail = 0
            count_night_fail = 0

            if (event_lane == 0):
                lpr_plate_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_1', LPR_DATE, 'PLATE')
            elif (event_lane == 1):
                lpr_plate_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_2', LPR_DATE, 'PLATE')
            elif (event_lane == 2):
                lpr_plate_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_3', LPR_DATE, 'PLATE')
            elif (event_lane == 3):
                lpr_plate_dir = os.path.join(LPR_BWIM_DRIVE, 'LPR_4', LPR_DATE, 'PLATE')

            LPR_PLATE_TIME_STR = len(lpr_plate_dir) + 1 # parse LPR time from image file name
            LPR_PLATE_NAME_STR = len(lpr_plate_dir) + 19  # parse LPR name from image file name

            print ("---- LPR SUMMARY RECORD ----")

            for lpr_bwim_plate in glob.iglob(lpr_plate_dir + '\*_PLATE.jpg'):
                # parse for LPR image file name
                lpr_file_plate = lpr_bwim_plate[LPR_PLATE_TIME_STR:]
                # print ("Lpr file plate = " + lpr_file_plate)
                # parse for LPR capture time
                lpr_time = lpr_bwim_plate[LPR_PLATE_TIME_STR:(LPR_PLATE_TIME_STR + 17)]
                lpr_time_obj = datetime.datetime.strptime(lpr_time, "%Y%m%d%H%M%S%f")
                # parse for LPR number
                lpr_plate, lpr_jpg = lpr_bwim_plate[LPR_PLATE_NAME_STR:].split('_PLATE')
                # print ("License Plate = " + lpr_plate + " / TIME : " + str(lpr_time_obj))
                if (lpr_time_obj.hour >= 6) and (lpr_time_obj.hour < 19):  # day time
                    count_day += 1
                    if (lpr_plate == "unknown"):
                        count_day_fail += 1
                else:  # night tine
                    count_night += 1
                    if (lpr_plate == "unknown"):
                        count_night_fail += 1

            # summary total lpr and unknown
            print(("--- LPR-"+ str(event_lane+1) + " Day = " + str(count_day) + ", Unknown LPR " + str(count_day_fail) + " ---"))
            print(("--- LPR-"+ str(event_lane+1) + " Night = " + str(count_night) + ", Unknown LPR " + str(count_night_fail) + " ---"))
            count_all = count_day + count_night
            count_all_fail = count_day_fail + count_night_fail
            print(("--- LPR-"+ str(event_lane+1) + " ALL = " + str(count_all) + ", Unknown LPR " + str(count_all_fail) + " ---"))
            unknown_percent_day = (count_day_fail * 100) / count_day
            unknown_percent_night = (count_night_fail * 100) / count_night
            unknown_percent_all = (count_all_fail * 100) / count_all
            # save summary result into csv file
            lpr_count_data.extend([str(count_all), str(count_all_fail), str(unknown_percent_all),
                                   str(count_day), str(count_day_fail), str(unknown_percent_day),
                                   str(count_night), str(count_night_fail), str(unknown_percent_night)])

        f = open(os.path.join(LPR_BWIM_DRIVE, "LPR.csv"), 'a')  # open csv file in append mode
        writer = csv.writer(f)
        writer.writerow(lpr_count_data)
        f.close()

    def __init__(self, mqttobj):
        self.mqttobj = mqttobj