import os
import sys
import json
import uuid
import subprocess
import argparse

PARTIAL_SUCCESS_EXIT_CODE = 3

WORKDIR = os.environ['WORKDIR']

def download_to_disk(source_link, filename, destination_dir):
	'''
	local_filepath is the path on the VM/container of the file that
	will be downloaded.
	'''
	full_name = '{u}.{n}'.format(
		u = uuid.uuid4(),
		n = filename
	)
	local_path = os.path.join(destination_dir, full_name)
	cmd = 'wget -q -O %s "%s"' % (local_path, source_link)
	p = subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
	stdout, stderr = p.communicate()
	if p.returncode != 0:
		raise Exception('Download from Dropbox has failed.  Is it possible that this file is restricted?')
	else:
		return local_path

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-l',"--links", 
		help="A comma-delimited list of links provided by Dropbox", 
		dest='links', 
		required=True)
	parser.add_argument('-n',"--names", 
		help="A comma-delimited list of the names of the files", 
		dest='filenames', 
		required=True)
	args = parser.parse_args()
	return args


if __name__ == '__main__':
	try:
		args = parse_args()
		link_list = [x.strip() for x in args.links.split(',')]
		name_list = [x.strip() for x in args.filenames.split(',')]
		n = len(link_list)
		if len(name_list) != n:
			sys.stderr.write('The number of links and names must be the same.')
			sys.exit(1)
		if not os.path.exists(WORKDIR):
			sys.stderr.write('The directory {d} must already exist.'.format(d=WORKDIR))
			sys.exit(1)
		
		final_paths = []
		errors = []
		for link, name in zip(link_list, name_list):
			try:
				local_filepath = download_to_disk(link, name, WORKDIR)
				final_paths.append(local_filepath)
			except Exception as ex:
				# catch any errors from the upload itself. A single failure
				# shouldn't kill the whole process
				errors.append(name)

	except Exception as ex:
		sys.stderr.write('Experienced an unexpected error. Error was: {ex}'.format(ex=ex))
		sys.exit(1)

	if len(errors) > 0:
		sys.stderr.write('Failed to upload: {x}'.format(x=', '.join(errors)))

		# if all the files failed, exit with 1, which indicates a total failure
		if len(errors) == n:
			# no outputs, so just exit.
			sys.exit(1)
		else:
			# if only a subset failed, we want to indicate a partial success.
			# We will do this by exiting with a special code.
			exit_code = PARTIAL_SUCCESS_EXIT_CODE
	else:
		exit_code = 0
    outputs = {
        'uploaded_paths': final_paths
    }
    json.dump(outputs, open(os.path.join(WORKDIR, 'outputs.json'), 'w'))
	sys.exit(exit_code)
