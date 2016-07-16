# Neurobatch
This Python3 script is specific for [neurosynth](http://http://neurosynth.org/) and allows:

1. Batch extract download links "Functional Connectivity"
2. Batch extract download links "Meta-analytic Coactivation"
3. Batch download "Functional Connectivity"
````
usage: neurobatch.py [-h] -i FILE [-o FILE] [-s] [-a WORKERS] [-w SEC SEC]

Batch Donwloader for http://neurosynth.org Functional Connectivity images

optional arguments:
  -h, --help  show this help message and exit
  -i FILE     csv file path
  -o FILE     output folder path
  -s          set flag to skip link collection
  -a WORKERS  multithread mode, if not set default: 1
  -w SEC SEC  random wait time lower and upper bounds inclusive
````
the usage of the flags are explained in the Example Usage Section
##Expected Input:
sample.csv

 -56 |14  | 10|
--- | --- | ---
10 | -2 | 4
24 | -2 | 56
-6 | 16 | 42

**NOTE** that there should not be any headers

##Example Usage:
###Basic:
````
neurobatch.py -i sample.csv -o output/ -w 2 6
````
This is the most basic usage one thread will collect all download links and save them in the input csv (`sample.csv` in this case) and will attempt to download all "Functional Connectivity" files. The `-w` flag must be set when the `-o` flag is set to denote delay time between downloads. Set `-w 0 0` if no delay time is necessary.
````
neurobatch.py -i sample.csv
````
This usage only extracts download links and saves them in the input csv file. The `-w` tag will be ignored.
###Advance:
````
neurobatch.py -a 10 -i sample.csv -o output/ -w 2 6
````
Setting the `-a` flag unleashes the power of multithreading for the batch download process. Downloads will now be handled with the set number of threads. The number of threads signifies how many files will be downloaded asynchronously. Note that each thread will have its own individual wait time. The `-w` does not guarantee non-overlapping download requests.
````
neurobatch.py -a 10 -s -i sample.csv -o output/ -w 2 6
````
Setting the `-s` flag will skip download link extraction and will assume the input csv file will supply the download link in the third column. This command can be ideally used after the second basic command `neurobatch.py -i sample.csv`, which will be the same as the full command `neurobatch.py -a 10 -i sample.csv -o output/ -w 2 6`
