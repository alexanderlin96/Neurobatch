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
 
mydict={}
mutex = Lock()
total = 0
progress = 0
progress_x = 0
collecting_info = True

def is_valid_file(parser, arg):
  if not os.path.exists(arg):
    parser.error("The file %s does not exist!" % arg)
  return arg

def directory_exists(parser, arg):
	if os.path.exists(arg):
		parser.error("The output file name is already taken: %s" % arg)
	return arg
 
def f(x):
	x_coor_raw = str(mydict[x][0])
	y_coor_raw = str(mydict[x][1])
	z_coor_raw = str(mydict[x][2])

	# this path returns us a json which includes the download link
	path = "http://neurosynth.org/locations/"+ x_coor_raw + "_" + y_coor_raw + "_" + z_coor_raw + "/images"
	success = False
	testfile = urllib.request.URLopener()
	fc = ""
	mc = ""
	while(not success):
		try: r1 = urllib.request.urlopen(path)
		except urllib.error.URLError as e:
			print(e.reason) 
			continue;
		parsed_json = json.loads(r1.read().decode());
		for y in parsed_json['data']:
			if(y['name'] == 'Functional connectivity'):
				fc = 'http://neurosynth.org'+y['download']+'/?.ni.gz'
				# print(fc)
			if(y['name'] == 'Meta-analytic coactivation'):
				mc = 'http://neurosynth.org'+y['download']+'/?.ni.gz'
		success = True
	fields=[x_coor_raw,y_coor_raw,z_coor_raw,fc,mc]
	mutex.acquire()
	try:
		global progress
		progress += 1
	finally:
		mutex.release()
	return fields

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
			global progress_x
			percentage = '{percent:.2%}'.format(percent=progress/total)
			x = int((progress/total) * 40)
			# sys.stdout.write(chr(8)*(41 + len(percentage)))
			print('Progress' + ": [" + "#" * x + "-" * (40 - x) + "]" + percentage + chr(8)*(41+9+2+len(percentage)), end="", flush=True)
		finally:
			mutex.release()
 
def main():
	#parses command line arguments
	parser = argparse.ArgumentParser(description="Batch Donwloader for http://neurosynth.org Functional Connectivity images")
	parser.add_argument("-i", dest="inputcsv", required=True, help="csv file path", metavar="FILE", type=lambda x: is_valid_file(parser, x))
	parser.add_argument("-o", dest="outputfolder", help="output folder path", metavar="FILE", type=lambda x: directory_exists(parser, x))
	parser.add_argument("-w", dest="bounds", nargs=2, metavar="SEC", required=True, type=int, help="random wait time lower and upper bounds inclusive");
	args = parser.parse_args()

	global total
	global progress
	global collecting_info

	lowerbound = args.bounds[0]
	upperbound = args.bounds[1]

	f1 = open(args.inputcsv,'r')
	f2 = open('tmp_'+args.inputcsv, 'a');

	csv_reader = csv.reader(f1)
	for count, elem in enumerate(csv_reader):
		total += 1
		mydict[count] = elem
	f1.close();	
	print('dictdone')

	csv_writer = csv.writer(f2);

	progress_bar()

	with ThreadPoolExecutor(max_workers=10) as executor:
		futures = [executor.submit(f, key) for key in mydict.keys()]
		for future in as_completed(futures):
			if(future.exception() is not None):
				print(future.exception());
			else:
				write_to_csv(csv_writer,future.result())

	sys.stdout.write('Progress' + ": [" + "#" * 40 + "] 100.00%"  +'\n')
	sys.stdout.flush()

	f1.close();
	f2.close();

	collecting_info = False;
	print('Done collecting download links')
	print()
	
	# delete the old csv file and replace it with the new one with links
	os.remove(args.inputcsv)
	os.rename('tmp_'+args.inputcsv,args.inputcsv)

	if(args.outputfolder == None):
		quit()
	elif(args.outputfolder != '' and args.outputfolder != None):
		# makes the folder the files are going to be in
		os.makedirs(args.outputfolder)

	print('Initial File Downloads...')
	print()

	f3 = open(args.inputcsv,'r')
	csv_download = csv.reader(f3)

	for row in csv_download:

		x_coor_raw = str(row[0])
		y_coor_raw = str(row[1])
		z_coor_raw = str(row[2])
		download_link = str(row[3])
		success_inner = False
		while(not success_inner):

			wait_time = random.randint(lowerbound,upperbound);
			print('Waiting for: '+str(wait_time)+' seconds', end="", flush=False)
			for i in range(wait_time):
				print('.', end="",flush=False)
				time.sleep(1)
			print();
			print('X: '+x_coor_raw.zfill(2)+' Y: '+y_coor_raw.zfill(2)+' Z: '+z_coor_raw.zfill(2))
			print('Downloading: '+download_link)

			folder = ''
			if(args.outputfolder != ''):
				folder = args.outputfolder;

			filename = folder+x_coor_raw.zfill(2)+'_'+y_coor_raw.zfill(2)+'_'+z_coor_raw.zfill(2)+'.nii.gz'
			print("Saving to file: "+filename)
			testfile = urllib.request.URLopener()
			try: testfile.retrieve(download_link, filename)
			except urllib.error.URLError as e:
				print(e.reason)
				continue; 
			end = time.time();
			success_inner = True;
			print()
 
####################
 
if __name__ == "__main__":
    main()