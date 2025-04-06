import os
import shutil  # built-in, no pip install needed
import zipfile  # built-in, no pip install needed
from event_detection.bwim_obj import Bwim_flag

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


def backup_event_file(day,month,year,Flag: Bwim_flag):
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