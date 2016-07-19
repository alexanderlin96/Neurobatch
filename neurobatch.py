#!/usr/bin/env python
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import time
import threading
from threading import Thread, current_thread, Lock
import urllib.request
import json
import sys
import argparse
import os
import logging

# dictionary to store all coordinates and their download links 
mydict={}

# mutex lock to protect progress resource
mutex = Lock()
total = 0
progress = 0
collecting_info = True

# checks if supplied file exists
def is_valid_csv_file(parser, arg):
  if not os.path.exists(arg):
    parser.error("The file %s does not exist!" % arg)
  elif not arg.endswith('.csv'):
  	parser.error("Not a csv file!")
  return arg

def directory_exists(parser, arg):
	if os.path.exists(arg):
		parser.error("The output file name is already taken: %s" % arg)
	return arg

# extracts the download links for the coordinates in the csv file
def f(x):
	global mydict
	x_coor_raw = str(mydict[x][0])
	y_coor_raw = str(mydict[x][1])
	z_coor_raw = str(mydict[x][2])

	# this path returns us a json which includes the download link
	path = "http://neurosynth.org/locations/"+ x_coor_raw + "_" + y_coor_raw + "_" + z_coor_raw + "/images"

	# download links are defaulted to empty strings
	fc = ""
	mc = ""

	# download file until success
	success = False
	while(not success):
		try: r1 = urllib.request.urlopen(path)
		except urllib.error.URLError as e:
			logging.exception(e.reason)
			continue;
		# parse response json
		parsed_json = json.loads(r1.read().decode());

		# extract the download link
		for y in parsed_json['data']:
			if(y['name'] == 'Functional connectivity'):
				fc = 'http://neurosynth.org'+y['download']+'/?.nii.gz'
				# print(fc)
			if(y['name'] == 'Meta-analytic coactivation'):
				mc = 'http://neurosynth.org'+y['download']+'/?.nii.gz'
		success = True

	fields=[x_coor_raw,y_coor_raw,z_coor_raw,fc,mc]

	# acquire editing permission to dictionary and update progress
	mutex.acquire()
	try:
		global progress
		mydict[x] = fields
		progress += 1
	finally:
		mutex.release()
	return fields

def y(x, args):
	x_coor_raw = str(mydict[x][0])
	y_coor_raw = str(mydict[x][1])
	z_coor_raw = str(mydict[x][2])
	fc_download_link = str(mydict[x][3])

	# download file until success
	success_inner = False
	while(not success_inner):

		# wait a random period of time between the bounds before downloading (perhaps to avoid IP ban)
		wait_time = random.randint(args.bounds[0],args.bounds[1]);
		for i in range(wait_time):
			time.sleep(1)

		# sets up correct download directory
		folder = ''
		if(args.outputfolder != ''):
			folder = args.outputfolder;

		# full path of download file
		filename = folder+x_coor_raw.zfill(2)+'_'+y_coor_raw.zfill(2)+'_'+z_coor_raw.zfill(2)+'.nii.gz'
		
		# attempt to download the functional connectivity file
		try: urllib.request.URLopener().retrieve(fc_download_link, filename)
		except urllib.error.URLError as e:
			logging.exception(e.reason)
			continue; 

		success_inner = True;

		# update progress
		mutex.acquire()
		try:
			global progress
			progress += 1
		finally:
			mutex.release()
		


def write_to_csv(writer,fields):
	writer.writerow(fields);

def progress_bar():
	global collecting_info
	if(collecting_info):
		t = threading.Timer(0.5, progress_bar)
		t.daemon = True
		t.start()
		mutex.acquire()
		try:
			global progress
			global total
			percentage = '{percent:.2%}'.format(percent=progress/total)
			x = int((progress/total) * 40)
			# sys.stdout.write(chr(8)*(41 + len(percentage)))
			print('Progress' + ": [" + "#" * x + "-" * (40 - x) + "]" + percentage + chr(8)*(41+9+2+len(percentage)), end="", flush=True)
		finally:
			mutex.release()
 
def main():
	#parses command line arguments
	parser = argparse.ArgumentParser(description="Batch Downloader and Link Extractor for http://neurosynth.org\nGitHub: https://github.com/alexanderlin96/Neurobatch\n", formatter_class=argparse.RawTextHelpFormatter)
	parser.add_argument("-i", dest="inputcsv", required=True, help="csv file path", metavar="FILE", type=lambda x: is_valid_csv_file(parser, x))
	parser.add_argument("-o", dest="outputfolder", help="output folder path", metavar="FILE", type=lambda x: directory_exists(parser, x))
	parser.add_argument("-s", action="store_true", help="set flag to skip link collection")
	parser.add_argument("-a", dest="workers", required=False, help="multithread mode, if not set default: 1", type=int);
	parser.add_argument("-w", dest="bounds", nargs=2, metavar="SEC", type=int, help="random wait time lower and upper bounds inclusive");
	args = parser.parse_args()

	global total
	global progress
	global collecting_info

	logging.basicConfig(filename='neurobatch.log',level=logging.DEBUG)

	# checks for correct flag sets
	if(args.outputfolder is not None):
		if(not args.outputfolder.endswith('/')):
			parser.error("incorrect outputfolder format")
		if(args.bounds[0] is None):
			parser.error("-w needs to be set")

	if(args.s):
		if(args.outputfolder is None):
			parser.error("-o needs to be set")
		elif(args.bounds is None):
			parser.error("-w needs to be set")
		if(not args.outputfolder.endswith('/')):
			parser.error("incorrect outputfolder format")

	# sets number of threads
	workers = 1
	if(args.workers is not 0 and args.workers is not None):
		workers = args.workers

	# open input csv 
	f1 = open(args.inputcsv,'r')
	csv_reader = csv.reader(f1)

	# checking for correctness and puts coordinates into a dictionary
	for count, elem in enumerate(csv_reader):
		try:
		    is_x = int(elem[0])
		    is_y = int(elem[1])
		    is_z = int(elem[2])
		except (IndexError, ValueError) as e:
			parser.error("This csv file doesn't seem to be valid..")

		total += 1
		mydict[count] = elem
	f1.close();

	# error checking
	if(total == 0):
		parser.error("This csv file doesn't seem to be valid...")

	print()	
	print('Loaded coordinates into Memory')
	print()

	if(not args.s):
		print('Collecting '+str(total)+' Download Links')
		# open temporary file to save download links
		f2 = open('tmp_'+args.inputcsv, 'a')
		csv_writer = csv.writer(f2);

		# start the progress bar
		progress_bar()

		# download primary json files
		with ThreadPoolExecutor(max_workers=workers) as executor:
			futures = [executor.submit(f, key) for key in mydict.keys()]
			for future in as_completed(futures):
				if(future.exception() is not None):
					logging.exception(future.exception());
				else:
					write_to_csv(csv_writer,future.result())

		sys.stdout.write('Progress' + ": [" + "#" * 40 + "] 100.00%"  +'\n')
		sys.stdout.flush()

		# close the temp csv file
		f2.close();

		# delete the old csv file and replace it with the temp one with links
		os.remove(args.inputcsv)
		os.rename('tmp_'+args.inputcsv,args.inputcsv)

		collecting_info = False;
		print()
		print('Done collecting download links')
		print()

	# if no output folder we just exit
	if(args.outputfolder == None):
		quit()
	elif(args.outputfolder != '' and args.outputfolder != None):
		# makes the folder the files are going to be in
		os.makedirs(args.outputfolder)

	# reset settings and initiate file downloads
	print('Initiating '+ str(total) +' File Downloads with '+str(workers)+' worker(s)')
	collecting_info = True
	progress = 0
	progress_bar()

	# assign download task to each worker
	with ThreadPoolExecutor(max_workers=workers) as executor:
		futures = [executor.submit(y, key, args) for key in mydict.keys()]
		for future in as_completed(futures):
			if(future.exception() is not None):
				logging.exception(future.exception());

	collecting_info = False			
	sys.stdout.write('Progress' + ": [" + "#" * 40 + "] 100.00%"  +'\n')
	sys.stdout.flush()
	print()
	print('All files downloaded successfully')
 
if __name__ == "__main__":
	main()