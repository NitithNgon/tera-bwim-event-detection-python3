from os.path import split, join, basename, exists
import shlex
import subprocess

from dotenv import dotenv_values

def subprocess_call_bwim_truck_as_main(path_event_folder, license_plate):
    path_event_folder = path_event_folder.replace("\\", "/")
    env_vars = dotenv_values(".env")
    current_working_dir = env_vars.get("CURRENT_WORKING_DIR")

    _arg_plate = repr(license_plate)
    arg_plate = _arg_plate.replace(" ", "").replace("'", "")


    path_python = env_vars.get("PATH_PYTHON")
    sh_command = '"cd \\"{cwd}\\" && PATH=$PATH:\\"{path_to_python}\\" && py -3 -u -m pipenv run python -m deployment.truck \\"{path}\\" {lpr} > .bwim_truck_output "'.format(
        path=path_event_folder,
        lpr=arg_plate,
        cwd=current_working_dir,
        path_to_python=path_python,
    )
    command_line = " ".join([
        'start',
        '""',
        '"%ProgramFiles%\\Git\\git-bash.exe"',
        '--hide',
        '-c',
        sh_command
    ])
    lexer = shlex.shlex(command_line, posix=True)
    lexer.escape = ""
    lexer.whitespace_split = True
    # lexer.quotes = '"'
    # print(command_line)
    r = subprocess.Popen(
        command_line,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    __waiting_for, __process_closed = r.communicate()
    std_out_location = basename(current_working_dir)
    path_bwim_output = join("..", "tera-bwim-control-analysis-system", ".bwim_truck_output")
    if exists(path_bwim_output):
        # with open(join(std_out_location, ".bwim_truck_output"), "r") as f:
        with open(path_bwim_output, "r") as f:
        # with open(join(current_working_dir, ".bwim_truck_output"), "r") as f:
            process_output = f.readline()
    else:
        print(" [FATAL] no Output in '.bwim_truck_output', crash during bwim algorithm")
        return 0, 0
    dirname, correct_basename = split(path_event_folder)
    str_output = str(process_output).lstrip("b'").rstrip("'")
    output_split = str_output.split(", ")
    if len(output_split) != 3:
        print(" [FATAL] no Output in '.bwim_truck_output', crash during bwim algorithm")
        return 0, 0
    check_basename, str_return_code, str_lane = output_split
    lane = int(str_lane)
    if check_basename == correct_basename:
        return_code = int(str_return_code)
    else:
        print(" [ERROR] Output basename in '.bwim_truck_output' does not match")
        return_code = 0
    return return_code, lane
