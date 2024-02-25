#!/usr/bin/env python3
# Nov 1, 2020
# This script is intended to download data from Garmin and then insert it into an InfluxDB


from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
    GarminConnectAuthenticationError,
)

from datetime import date, timedelta
import time
import lxml

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
# from influxdb import InfluxDBClient

import logging

import gpxpy
import gpxpy.gpx
from math import radians, cos, sin, asin, sqrt


logging.basicConfig(level=logging.DEBUG)
start_date = date(2023,9,1)
end_date = date(2023,9,17)

today = date.today()
# The speed multiplier was found by taking the "averageSpeed" float from an activity and comparing
# to the speed reporting in the app. For example a speed of 1.61199998 * multiplyer = 5.77804 km/hr
speed_multiplier = 3.584392177
garmin_username = 'croquelois.adrien@gmail.com'
garmin_password = ''

garmin_date_format = "%Y-%m-%d"
influx_server = "192.168.1.62:8086"
influx_port = 8086
influx_username = "acroquelois"
influx_org = "home"
influx_bucket = "sport-monitoring"
influx_token = ""
influx_db = "sport-monitoring"
influxdb_time_format = "%Y-%m-%dT%H:%M:%SZ"
gather_hrv_data = False

def connect_to_garmin(username, password):
    """
    initialize the connection to garmin servers
    The library will try to relogin when session expires

    :param username: garmin username
    :param password: garmin connect password
    :return: client object
    """

    print("Garmin(email, password)")
    print("----------------------------------------------------------------------------------------")
    try:
        client = Garmin(username, password)
    except (
            GarminConnectConnectionError,
            GarminConnectAuthenticationError,
            GarminConnectTooManyRequestsError,
    ) as err:
        print(f"Error occurred during Garmin Connect Client get initial client: {err}")
        quit()
    except Exception:
        print("Unknown error occurred during Garmin Connect Client get initial client")
        quit()
    print("client.login()")
    print("----------------------------------------------------------------------------------------")
    login_command = "client.login()"
    get_data_from_garmin("login", login_command, client=client)
    return client

def create_json_body(measurement, measurement_value, datestamp, tags=None):
    return [
        {
            "measurement": measurement,
#             "tags": tags,
            "time": datestamp,
            "fields": {
                "value": measurement_value
            }
        }
    ]

# with influxdb_client.InfluxDBClient(url=influx_server, token=influx_token, org=influx_org) as influx:
#                     write_api = influx.write_api(write_options=SYNCHRONOUS)
#                     print("Adding: %s\nValue: %s" % (inner_heading, value))
#                     loaded = create_json_body(inner_heading, value, heading)
#                     print("loaded %s" % (loaded))
#                     write_api.write(bucket=influx_bucket, record=loaded)
def calc_distance(lat1, lat2, lon1, lon2):
    lon1 = radians(lon1)
    lon2 = radians(lon2)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return(c * r)

gpx_file = open('test.gpx', 'r')

gpx = gpxpy.parse(gpx_file)

lat1 = None
lat2 = None
lon1 = None
lon2 = None

time1 = None
time2 = None

total_distance = 0
total_time = timedelta(0)

for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            ## Caclulate distance
            lat1 = lat2
            lon1 = lon2
            lat2 = point.latitude
            lon2 = point.longitude
            distance = 0
            if(lat1 or lon1):
                distance = calc_distance(lat1, lat2, lon1, lon2)

            ## Caclulate elapsed time
            time1 = time2
            time2 = point.time
            elapsed_time = timedelta(0)
            if(time1):
                elapsed_time = time2 - time1

            speed = 0
            pace = 0
            if(elapsed_time):
                speed = distance / (elapsed_time.total_seconds() / 3600)
                pace = 60 / speed
            base_data = {
                    'timestamp': point.time,
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'elevation': point.elevation,
                    'distance': distance,
                    'elapsed_time': elapsed_time,
                    'total_time': total_time.total_seconds() / 60,
                    'speed': speed,
                    'pace': pace
            }
            total_distance += base_data['distance']
            total_time += base_data['elapsed_time']
            for k, v in point.extensions:
                base_data['heart_rate'] = k.text
                base_data['cadence'] = v.text
            print(base_data)

print('distance: {0} | time: {1}'.format(total_distance, total_time))
for waypoint in gpx.waypoints:
    print('waypoint {0} -> ({1},{2})'.format(waypoint.name, waypoint.latitude, waypoint.longitude))

for route in gpx.routes:
    print('Route:')

# client = connect_to_garmin(username=garmin_username,password=garmin_password)
# # step = client.get_activity_split_summaries("14069614150")
# gpx_data = client.download_activity("14069614150", dl_fmt=client.ActivityDownloadFormat.GPX)
# output_file = f"./test.gpx"
# with open(output_file, "wb") as fb:
#     fb.write(gpx_data)
# step = client.get_last_activity()
# print("sum :::%s" % (step))
# unless you want to graph the hourly heart rate times heart_rate is useless as you can get this info
# from the daily stats
# heart_rate = get_data_from_garmin("heart_rate", "client.get_heart_rates(today.isoformat())", client=client)

# activities = get_data_from_garmin("activities", "client.get_activities(0, 10)", client=client)  # 0=start, 1=limit
# activity_list = ['distance', 'duration', 'averageSpeed', 'maxSpeed', 'averageHR', 'maxHR',
#                 'averageRunningCadenceInStepsPerMinute', 'steps', 'avgStrideLength']
# # there is very little data in the step_data so it's not worth re-skinning
# time_delta = end_date - start_date
# influxdb_client_init = influxdb_client.InfluxDBClient(url=influx_server, token=influx_token, org=influx_org)
# # create_influxdb_multi_measurement(activities, activity_list, 'startTimeLocal', '%Y-%m-%d %H:%M:%S',
# #                                  timestamp_offset=True)
# for x in range(time_delta.days +1):
#     day = str(start_date + timedelta(days=x))
#     client_get_data = f'client.get_steps_data("{day}")'
#     client_get_sleep = f'client.get_sleep_data("{day}")'
#     client_get_stats = f'client.get_stats("{day}")'
#
#     step_data = get_data_from_garmin("step_data", client_get_data, client=client)
#
#     stats = get_data_from_garmin("stats", client_get_stats, client=client)
#     sleep_data = get_data_from_garmin("sleep_data", client_get_sleep, client=client)
#     sleep_data_date = time.mktime(time.strptime(sleep_data['dailySleepDTO']['calendarDate'], garmin_date_format))
#     # Adding 20000 seconds to the date to account for the GMT offset. Without this, activities were showing up
#     # on previous day in InfluxDB
#     daily_stats_date = time.mktime(time.strptime(stats['calendarDate'], garmin_date_format)) + 20000
#     floor_data = {
#         'floors_ascended': stats['floorsAscended'],
#         'floors_descended':  stats['floorsDescended'],
#         "current_date": time.strftime(influxdb_time_format, time.localtime(daily_stats_date))
#     }
#     useful_daily_sleep_data = {
#         'awake_minutes': sleep_data['dailySleepDTO']['awakeSleepSeconds'],
#         'light_sleep_minutes': sleep_data['dailySleepDTO']['lightSleepSeconds'],
#         'deep_sleep_minutes': sleep_data['dailySleepDTO']['deepSleepSeconds'],
#         'total_sleep_minutes': sleep_data['dailySleepDTO']['sleepTimeSeconds'],
#         'current_date': time.strftime(influxdb_time_format, time.localtime(sleep_data_date))
#                               }
#     heart_rate = {
#         "lowest_heart_rate": stats['minHeartRate'],
#         "highest_heart_rate": stats['maxHeartRate'],
#         "resting_heart_rate": stats['restingHeartRate'],
#         "current_date": time.strftime(influxdb_time_format, time.localtime(daily_stats_date))
#     }
#
#     daily_stats = {
#         "total_burned_calories": stats['totalKilocalories'],
#         "current_date": time.strftime(influxdb_time_format, time.localtime(daily_stats_date)),
#         "total_steps": stats['totalSteps'],
#         "daily_step_goal": stats['dailyStepGoal'],
#         "highly_active_minutes": stats['highlyActiveSeconds'],
#         "moderately_active_minutes": stats['activeSeconds'],
#         "sedentary_minutes": stats['sedentarySeconds']
#     }
#
#     if gather_hrv_data:
#         # Only gather this data if the user has set this to true
#         # This data isn't available on all devices so it will error if set to True by default
#         client_get_hrv = f'client.get_hrv_data("{day}")'
#         hrv_data = get_data_from_garmin("hrv_data", client_get_hrv, client=client)
#         hrv_daily_summary = {
#             "hrv_last_night_avg": hrv_data['hrvSummary']['lastNightAvg'],
#             "hrv_weekly_avg": hrv_data['hrvSummary']['weeklyAvg'],
#             "hrv_status": hrv_data['hrvSummary']['status'],
#             "current_date": time.strftime(influxdb_time_format, time.localtime(daily_stats_date))
#         }
#         create_influxdb_daily_measurement(hrv_daily_summary, influxdb_client_init)
#
#     create_influxdb_daily_measurement(daily_stats, influxdb_client_init)
#     create_influxdb_daily_measurement(useful_daily_sleep_data, influxdb_client_init)
#     create_influxdb_daily_measurement(heart_rate, influxdb_client_init)
#     create_influxdb_daily_measurement(floor_data, influxdb_client_init)
#
#     step_list = ['steps']
#
#     create_influxdb_multi_measurement(step_data, step_list, 'startGMT', "%Y-%m-%dT%H:%M:%S.%f",
#                                       )
#     print(day)
#     time.sleep(2.5)
#
# print("")
