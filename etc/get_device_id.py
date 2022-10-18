import json
import sys
import subprocess as sp
import shlex
import argparse

NVME_CMD = 'nvme list -o json'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i',
        '--volume-id',
        required=True,
        dest='volume_id'
    )
    return parser.parse_args()


def get_device_json():
    split_cmd = shlex.split(NVME_CMD)
    p = sp.Popen(split_cmd, stdout=sp.PIPE, stderr=sp.STDOUT)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        sys.stderr.write(f'Failed to execute {NVME_CMD}')
        sys.exit(1)
    else:
        try:
            return json.loads(stdout)
        except json.decoder.JSONDecodeError as ex:
            sys.stderr.write(f'Exception when parsing nvme JSON: {ex}')
            sys.exit(1)


def find_device(volume_id, j):
    device_list = j['Devices']
    for device in device_list:
        if device['SerialNumber'] == volume_id:
            return device['DevicePath'] 


if __name__ == '__main__':
    args = parse_args()

    # the volume id parsed from the nvme cli tool does
    # NOT have a dash, while the one provided to this script
    # DOES have the dash. 
    volume_id = args.volume_id.replace('-', '')

    j = get_device_json()
    device_path = find_device(volume_id, j)
    if device_path is not None:
        sys.stdout.write(device_path)
    else:
        sys.stderr.write(f'Could not locate device with volume ID {volume_id}')
        sys.exit(1)