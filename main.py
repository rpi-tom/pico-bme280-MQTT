#https://www.tomshardware.com/how-to/send-and-receive-data-raspberry-pi-pico-w-mqtt?fbclid=IwAR3PeGw4SO-NKryiuL2cjz5a-sms_9t2gl9KaXwJPBXFDXPYb-O2TcpdnW8
#https://community.hivemq.com/t/getting-started-raspberry-pi-pico-w/1316/12
#HIVE MQ SSL Params: https://community.hivemq.com/t/getting-started-raspberry-pi-pico-w/1316/20

import os
import network
import time
import ntptime
import bme280
import secrets

from simple import MQTTClient
from machine import Pin, I2C
from machine import WDT

###watchdogtimer to cause reset - NOT USED IN THIS CODE###
#wdt = WDT(timeout=8000)

#---TURN ON LOG FOR DEBUGGING---#
#logfile = open('log.txt', 'a') 
#os.dupterm(logfile)  # duplicate stdout and stderr to the log file

print("START / RESTART COMPLETED")

time.sleep(1)
i2c=I2C(0,sda=Pin(20), scl=Pin(21), freq=400000)

led = Pin("LED", Pin.OUT)
led.off() #led.on()

#WLAN CONNECT:
wlan = network.WLAN(network.STA_IF)
wlan.disconnect()
#sleep(1)
wlan.active(True)
wlan.connect(secrets.SSID,secrets.PASSWORD)

# Wait for connect or fail - LED will blink 1s ON / 1s OFF during this time
wait = 15
while wait > 0:
    #print(wlan.status())
    if wlan.status() == 3: #< 0 or wlan.status() >= 3:
        break
    wait = wait-1
    print('waiting for connection...')
    led.on()
    time.sleep(1)
    led.off()
    time.sleep(1)

# Handle connection error
if wlan.status() != 3:
    i = 1
    while i<30:  ##FAST BLINK FOR 6 SECONDS = WIFI CONNECTION FAILED##
        i=i+1
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)
    print("wifi connection failed")
    machine.reset()
    #raise RuntimeError('wifi connection failed')

else:
    print('connected')
    ip=wlan.ifconfig()[0]
    print('IP: ', ip)

time.sleep(2)

try:
    ntptime.settime()
    print(ntptime.time())
    variable1 = str(ntptime.time())[7]  #4 - resets every 27.7 hrs (digit 3 would be 11 days)
    print(variable1)
except OSError as e:
    print("ntptime.time initialisation failing - machine reset")
    time.sleep(2)
    machine.reset()
    
mqtt_server = secrets.MQTT_SERVER #'broker.hivemq.com'
client_id = secrets.CLIENT_ID
client_password = secrets.CLIENT_PASSWORD
topic_pub= b""+secrets.TOPIC_PUB
mqtt_ssl_params = {'server_hostname': str(secrets.MQTT_SSL_PARAMS)}

def mqtt_connect():
    client = MQTTClient(client_id,mqtt_server,user="rpimqtt",password="2pA8XCJn%glF",keepalive=3600,ssl=True,ssl_params=mqtt_ssl_params)
    client.connect()
    print('Connected to %s MQTT Broker'%(mqtt_server))
    return client

def reconnect():
    print('Failed to connect to the MQTT Broker. Resetting machine and reconnecting...')
    time.sleep(5)
    machine.reset()

#sensor_value = 0

try:
    client = mqtt_connect()
except OSError as e:
    print(e)
    reconnect()

fail_count = 1
count = 1
while True:
    while fail_count < 50:
        try:
            led.on()
            time.sleep(6)
            bme = bme280.BME280(i2c=i2c)
            time.sleep(6)
            time_now = ntptime.time()
            variable2 = str(time_now)[7]
            topic_msg = b"" + secrets.MEASUREMENT + " temperature=" + str(bme.values[3]) + ",Pressure=" + str(bme.values[4]) + ",Humidity=" + str(bme.values[5]) + " " + str(time_now)+"000000000"
            print(topic_msg)
            led.on()
            client.publish(topic_pub, topic_msg, retain=False, qos=1)
            time.sleep(106)
            led.off()
            count = count + 1
            print(count)
            time.sleep(2)
            if count > 10:
                ntptime.settime()
                count = 0
            
        except OSError as e:
            print(e)
            #time.sleep(5)
            print("sleeping 5 / +1 to fail count")
            fail_count = fail_count + 1
            print("failcount: " + str(fail_count))
            j = 1
            while j<30:  ## V FAST BLINK = re==READING/UPLOAD FAILED
                j=j+1
                led.on()
                time.sleep(0.05)
                led.off()
                time.sleep(0.05)
            time.sleep(5)
    else:
        print("failure count to 50 invokes reset")
        machine.reset()