#!/usr/bin/env python3
import os
from sys import argv
import csv
from geopy.distance import geodesic
import geopy.distance
import math, numpy as np

SF_MIN =  (37.675,-122.48)
SF_MAX =  (37.825,-122.35)
CARLA_MIN = (-0.0018703476525843143, -0.0013416497968137264)
CARLA_MAX = (0.0018795838113874197, 0.002198888687416911)

def transform_lat(lat):
    slope = (CARLA_MAX[0] - CARLA_MIN[0])/(SF_MAX[0] - SF_MIN[0])
    intersection = (SF_MAX[0] *CARLA_MIN[0] - CARLA_MAX[0] * SF_MIN[0]) / (SF_MAX[0] - SF_MIN[0])
    return lat * slope + intersection

def transform_lng(lng):
    slope = (CARLA_MAX[1] - CARLA_MIN[1])/(SF_MAX[1] - SF_MIN[1])
    intersection = (SF_MAX[1] *CARLA_MIN[1] - CARLA_MAX[1] * SF_MIN[1]) / (SF_MAX[1] - SF_MIN[1])
    return lng * slope + intersection

def get_bearing(lat1,lon1,lat2,lon2):
    dLon = lon2 - lon1;
    y = math.sin(dLon) * math.cos(lat2);
    x = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dLon);
    brng = np.rad2deg(math.atan2(y, x));
    if brng < 0: brng+= 360
    return brng

def check_operation(operation):
    if operation == "limits" or operation == "generate":
        return True
    return False 

def main(directory,operation, min_time=None ,max_time=None,time_delta=None):
    assert(check_operation(operation))
    data = dict()
    for filename in os.listdir(directory):
        if filename.endswith(".txt") and filename.startswith("new"): 
            with open(os.path.join(directory,filename), 'r') as csv_file:
                print("processing {}".format(filename))
                reader = csv.reader(csv_file, delimiter=' ')
                name = filename[4:-4]
                input_vals = []
                for row in reader:
                    lat = float(row[0])
                    lng = float(row[1])
                    unixtimestamp = int(row[3])*1000
                    input_vals.append([lat,lng,unixtimestamp])
                input_vals.sort(key=lambda x: x[2])
                prev = None
              
                last_good_loc = None
                for row in input_vals:
                    lat = row[0]
                    lng = row[1]
                    unixtimestamp = row[2]
                    if min_time and unixtimestamp < min_time:
                        continue
                    elif max_time and unixtimestamp > max_time:
                        continue

                    if lat < SF_MIN[0] or lat > SF_MAX[0] or lng < SF_MIN[1] or lng > SF_MAX[1]:
                      if last_good_loc == None:
                        continue
                      else:
                        (lat, lng) = last_good_loc
                    last_good_loc = (lat, lng)

                    if name not in data:
                        data[name]=[]
                    if prev and time_delta:
                        distance = geodesic((prev[0],prev[1]),(lat,lng))
                        bearing = get_bearing(prev[0],prev[1],lat,lng)
                        difftime = unixtimestamp - prev[2]
                        num= int(difftime / time_delta)
                        if num < 0:
                            num = 0
                        if num > 0:
                            num-=1
                        if num > 0:
                            each_distance = distance/num
                        for i in range(num):
                            nextpoint = each_distance.destination((prev[0],prev[1]), bearing=bearing)
                            nextval = (nextpoint.latitude, nextpoint.longitude, prev[2]+time_delta)
                            data[name].append((transform_lat(nextval[0]),transform_lng(nextval[1]),float(nextval[2])/1000.0))
                            prev = nextval 

                    trans_lat = transform_lat(lat)
                    trans_lng = transform_lng(lng)
                    data[name].append((trans_lat,trans_lng,float(unixtimestamp)/1000.0))
                    prev = (lat,lng,unixtimestamp)
    if operation == "limits":
        min_time = []
        max_time = []
        min_lat = []
        max_lat = []
        min_lng = []
        max_lng = []
        for (name, rows) in data.items():
            min_lat.append(min(rows,key=lambda x: x[0])[0])
            max_lat.append(max(rows,key=lambda x: x[0])[0])
            min_lng.append(min(rows,key=lambda x: x[1])[1])
            max_lng.append(max(rows,key=lambda x: x[1])[1])
            min_time.append(min(rows,key=lambda x: x[2])[2])
            max_time.append(max(rows,key=lambda x: x[2])[2])
        print("Total traces: {}\nLimits ->\n\tlat: [{},{}]\n\t lng: [{},{}]\n\t time: [{},{}]".format(len(data),min(min_lat),max(max_lat),min(min_lng),max(max_lng),min(min_time),max(max_time)))
    elif operation == "generate":
        index=0
        dirname = "/tmp/crawdad_processed"
        minTime = None 
        for (name, rows) in data.items():
            for row in rows:
                if not minTime or minTime > row[2]:
                    minTime = row[2]
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        for (name, rows) in data.items():
            with open(os.path.join(dirname,'{}.txt'.format(index)), 'w') as f:
                write = csv.writer(f,delimiter=' ')
                for row in rows:
                    write.writerow(["{:.5f}".format(row[0]),"{:.5f}".format(row[1]),row[2]-minTime])
                #write.writerows(rows)
            index+=1
        print("Data generated in {}".format(dirname))


if __name__ == "__main__":
    if len(argv) == 3:
        main(argv[1],argv[2])
    elif len(argv) == 5:
        main(argv[1],argv[2], 1000*int(argv[3]), 1000*int(argv[4]))
    elif len(argv) == 6:
        main(argv[1],argv[2], 1000*int(argv[3]),1000*int(argv[4]), int(argv[5]))
    else:
        print("Usage python3 ./{} <directory> <limits,generate> [min_time_unix] [max_time_unix] [time_delta_milliseconds]".format(argv[0]))
        print("To generate the dataset for the first hour use:\n python3 parse_crawdad_taxi.py <dataset> generate 1211018404 1211022004 1000.\n This will have 328 cars")
        exit(1)
