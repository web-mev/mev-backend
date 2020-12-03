import os
import sys
import uuid
import subprocess
import argparse

from google.cloud import storage

WORKING_DIR = '/workspace'
GOOGLE_BUCKET_PREFIX = 'gs://'

def send_to_bucket(local_filepath, args):
	'''
	Uploads the local file to the bucket
	'''
	destination_bucketname = args.destination_bucketname
	file_uuid = str(uuid.uuid4())
	bucket_root = args.bucket_root
	# places the file in a unique "folder" to prevent collisions from the same filename
	object_name = '{b}/{u}/{n}'.format(b=bucket_root,u = file_uuid, n = args.filename)
	full_destination = '{prefix}{bucket}/{obj}'.format(
		prefix = GOOGLE_BUCKET_PREFIX,
		bucket = destination_bucketname, 
		obj = object_name
	)

	storage_client = storage.Client()
	# trying to get an existing bucket.  If raises exception, means bucket did not exist (or similar)
	try:
		destination_bucket = storage_client.get_bucket(destination_bucketname)
	except (google.api_core.exceptions.NotFound, google.api_core.exceptions.BadRequest) as ex:
		raise Exception('Could not locate bucket: {b}'.format(b=destination_bucketname))

	try:
		destination_blob = destination_bucket.blob(object_name)
		destination_blob.upload_from_filename(local_filepath)
	except Exception as ex:
		raise Exception('Could not create or upload the blob with name %s' % object_name)

	return full_destination


def download_to_disk(args):
	'''
	local_filepath is the path on the VM/container of the file that
	will be downloaded.
	'''
	source_link = args.resource_link
	local_path = os.path.join(WORKING_DIR, 'download')
	cmd = 'wget -q -O %s "%s"' % (local_path, source_link)
	p = subprocess.Popen(cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
	stdout, stderr = p.communicate()
	if p.returncode != 0:
		raise Exception('Download from Dropbox has failed.  Is it possible that this file is restricted?')
	else:
		return local_path


def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-s',"--source", 
		help="The source of the file that is being downloaded", 
		dest='resource_link', 
		required=True)
	parser.add_argument('-n',"--name", 
		help="The name of the file", 
		dest='filename', 
		required=True)
	parser.add_argument('-d',"--destination", 
		help="The name of the bucket where the upload will be stored.  DO NOT include the gs:// prefix.", 
		dest='destination_bucketname', 
		required=True)
	parser.add_argument('-r',"--root", 
		help="The root folder, relative to the bucket, where the file will be stored.", 
		dest='bucket_root',
		default='dropbox-uploads',
		required=False)
	args = parser.parse_args()
	return args


if __name__ == '__main__':
	try:
		args = parse_args()
		os.mkdir(WORKING_DIR)
		local_filepath = download_to_disk(args)
		path_in_bucket = send_to_bucket(local_filepath, args)
		sys.stdout.write(path_in_bucket)
	except Exception as ex:
		sys.stderr.write('Experienced an unexpected error. Error was: {ex}'.format(ex=ex))
		sys.exit(1)


