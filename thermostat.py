# apt-get install openssh-server screen vim autossh python3.5 mysql-server apache2 php phpmyadmin librrd-dev
# pip3 install mysql-connector-pythonrf rrdtool
# GRANT ALL PRIVILEGES ON *.* TO 'phpmyadmin'@'localhost';

import os
import glob
import time
import socket
import sys 
from Crypto.Cipher import AES
import struct
import base64
from Crypto import Random
import hashlib
import subprocess
from subprocess import call
from threading import Thread
import threading
import datetime
from socketserver import ThreadingMixIn

BLOCK_SIZE = 16
pad= lambda s: s + (BLOCK_SIZE -len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE -len(s) % BLOCK_SIZE)
unpad = lambda s : s[0:-s[-1]]

# Load and configure WiringPi in the modes that require use of the relay
if (sys.argv[1] == "server"):
    import wiringpi
    wiringpi.wiringPiSetup()
    wiringpi.pinMode(0, 1) # Sets WP pin 0 to output

# Configure the digital thermometer (DS18B20) in the modes that require it
if sys.argv[2] == "send_temperature":
    os.system('modprobe w1-gpio')
    os.system('modprobe w1-therm')
    base_dir = '/sys/bus/w1/devices/'
    device_folder = glob.glob(base_dir + '28*')[0]
    device_file = device_folder + '/w1_slave'

# Configure TCP client for communication with TCP server located on boiler
TCP_IP = '192.168.2.85' # IP address of Raspberry Pi connected to boiler
TCP_PORT = 5005 # Port that server will be listening on
BUFFER_SIZE = 1024
MESSAGE = ""
ENCRYPTION_PASSPHRASE = "place-your-own-passphrase-here"

# Global variables
current_temperature_dictionary = {}
target_temperature_dictionary = {}
last_call_for_heating_on_or_off = ""
mydb = "null"
conn = ""

# Encrypt data before sending over network socket
def do_encrypt(message):
    cipher = AES.new(ENCRYPTION_PASSPHRASE)
    ciphertext = cipher.encrypt(pad(message))
    return ciphertext

# Decrypt data after sending over network socket
def do_decrypt(ciphertext):
    cipher = AES.new(ENCRYPTION_PASSPHRASE)
    test = cipher.decrypt(ciphertext)
    data = test[:-test[-1]]
    return data

# Get raw digital thermometer data from device
def read_temperature_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines

# Format the raw digital thermometer data into temperature in degrees C or F
def read_temperature():
    lines = read_temperature_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temperature_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        #return temp_c, temp_f
        return temp_c

# Function to see if target room temperature has been reached and turn heating system on and off accordingly
def check_target_temperature_reached():
    global current_temperature_dictionary
    global target_temperature_dictionary
    
    while True:
        if last_call_for_heating_on_or_off == "on":
            print("Current in lounge:", current_temperature_dictionary.get("lounge"))
            print("Target in lounge:", target_temperature_dictionary.get("lounge"))
            if current_temperature_dictionary.get("lounge") != None:
                if target_temperature_dictionary.get("lounge") != None:
                    if current_temperature_dictionary.get("lounge") < target_temperature_dictionary.get("lounge"):
                        print("Keep heating on as required temperature not yet reached.")
                        call(["/usr/bin/python3.5", "/home/pi/heating-control/thermostat.py", "client", "on", "auto-on"])
                    else:
                        print("Turn heating off as required temperature now reached.")
                        call(["/usr/bin/python3.5", "/home/pi/heating-control/thermostat.py", "client", "off", "auto-off"])
        time.sleep(30)

# Multithreaded Python server : TCP Server Socket Thread Pool
class ClientThread(Thread):
 
    def __init__(self,ip,port):
        Thread.__init__(self)
        self.ip = ip
        self.port = port
        print("[+] New server socket thread started for " + ip + ":" + str(port))
 
    def run(self):
        global current_temperature_dictionary
        global target_temperature_dictionary
        global last_call_for_heating_on_or_off
        global conn
        while True:
            data = conn.recv(BUFFER_SIZE)
            print("Target temperature in lounge is:", str(target_temperature_dictionary.get("lounge")))
            if not data: break
            # Why is this send required?  Does not work without it!
            received_data = do_decrypt(data)
            received_data = received_data.decode()
            received_data = convert_string_to_list(received_data)
            if received_data[0] == "INPUT":
                if received_data[1] == "CURRENT_TEMPERATURE":
                    current_temperature_dictionary[received_data[2]] = float(received_data[3])
                    print("Current lounge temperature:", current_temperature_dictionary.get(received_data[2]))
                    #print("Going to return data as:", data)
                    conn.send(data)
                    #make_input_log_entry(received_data[0], received_data[1], received_data[2], received_data[3])
                if received_data[1] == "TURN_ON_HEATING":
                    wiringpi.digitalWrite(0, 1) # Sets port 0 to 1 (3.3V, on)
                    print("Heating on.")
                    if received_data[2] != "auto-on":
                        pop_up_message_on_linux_pcs('phone', "Heating is turning on", "Current temperature in lounge is:\n" + str(current_temperature_dictionary.get('lounge')) + "  degrees.")
                        last_call_for_heating_on_or_off = "on"
                    conn.send(data)
                    #make_input_log_entry(received_data[0], received_data[1], received_data[2], received_data[3])
                if received_data[1] == "TURN_OFF_HEATING":
                    conn.send(data)
                    #make_input_log_entry(received_data[0], received_data[1], received_data[2], received_data[3])
                    wiringpi.digitalWrite(0, 0) # Sets port 0 to 0 (3.3V, off)
                    print("Heating off.")
                    if received_data[2] != "auto-off":
                        pop_up_message_on_linux_pcs('phone', "Heating is turning off", "Current temperature in lounge is:\n" + str(current_temperature_dictionary.get('lounge')) + " degrees.")
                        last_call_for_heating_on_or_off = "off"
                if received_data[1] == "SET_TARGET_TEMPERATURE":
                    target_temperature_dictionary[received_data[2]] = float(received_data[3])
                    print("Setting target temperature in lounge to:", target_temperature_dictionary.get(received_data[2]))
                    conn.send(data)
                    #make_input_log_entry(received_data[0], received_data[1], received_data[2], received_data[3])
            if received_data[0] == "OUTPUT":
                if received_data[1] == "CURRENT_TEMPERATURE":
                    print("Going to now send:", str(current_temperature_dictionary.get(received_data[2])))
                    conn.send(do_encrypt(str(current_temperature_dictionary.get(received_data[2]))))
                    make_output_log_entry(received_data[0], received_data[1], received_data[2], received_data[3], current_temperature_dictionary.get(received_data[2]))
                if received_data[1] == "CURRENT_HEATING_ON_OFF_STATUS":
                    state = subprocess.Popen("/usr/bin/gpio read 0", stdout=subprocess.PIPE, shell=True)
                    (output, err) = state.communicate()
                    state_status = state.wait()
                    print("Current heating on/off state is:", output.rstrip().decode())
                    conn.send(do_encrypt(output.rstrip().decode()))
                    #make_output2_log_entry(received_data[0], received_data[1], received_data[2])
 
# Start as server and listen for temperature from other Raspberry Pi with temperature sensor, and requests for temperature statuses from Asterisk etc.  These all communicate with the server via the client function.
def server():
    global current_temperature_dictionary
    global target_temperature_dictionary
    global last_call_for_heating_on_or_off
    global conn
    print("Target temperature in lounge is:", str(target_temperature_dictionary.get("lounge")))
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((TCP_IP, TCP_PORT))
    threads = []
    
    while True:
        s.listen(4)
        print("Waiting for connections...")
        (conn, (ip,port)) = s.accept()
        newthread = ClientThread(ip,port)
        newthread.start()
        threads.append(newthread)

    for t in threads:
        t.join()

def make_input_log_entry(input_output, request_type, location, temperature):
    now = datetime.datetime.now()
    sql = "INSERT INTO log (input_output, request_type, location, temperature, time, date) VALUES (%s, %s, %s, %s, %s, %s)"
    val = (input_output, request_type, location, temperature, now.strftime("%H:%M:%S"), now.strftime("%Y-%m-%d"))
    mycursor.execute(sql, val)
    mydb.commit()

def make_output_log_entry(input_output, request_type, location, source, temperature):
    now = datetime.datetime.now()
    sql = "INSERT INTO log (input_output, request_type, location, source, temperature, time, date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    val = (input_output, request_type, location, source, temperature, now.strftime("%H:%M:%S"), now.strftime("%Y-%m-%d"))
    mycursor.execute(sql, val)
    mydb.commit()

def make_output2_log_entry(input_output, request_type, source):
    now = datetime.datetime.now()
    sql = "INSERT INTO log (input_output, request_type, source, time, date) VALUES (%s, %s, %s, %s, %s)"
    val = (input_output, request_type, source, now.strftime("%H:%M:%S"), now.strftime("%Y-%m-%d"))
    mycursor.execute(sql, val)
    mydb.commit()

def make_system_log_entry(input_output, request_type):
    now = datetime.datetime.now()
    sql = "INSERT INTO log (input_output, request_type, time, date) VALUES (%s, %s, %s, %s)"
    val = (input_output, request_type, now.strftime("%H:%M:%S"), now.strftime("%Y-%m-%d"))
    mycursor.execute(sql, val)
    mydb.commit()

def convert_string_to_list(string):
    li = list(string.split(","))
    return li

# Get current on/off status of the heating
def client():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((TCP_IP, TCP_PORT))

    def encode_encrypt_and_send_to_server(data):
        #data = str(data).encode()
        s.send(do_encrypt(data))
        returned_data = s.recv(BUFFER_SIZE)
        returned_data = do_decrypt(returned_data)
        returned_data = returned_data.decode() 
        print(returned_data)
        s.close()
 
    # Read the sensor to obtain current temperature and send to server
    if sys.argv[2] == "send_temperature":
        while True:
            string_temperature = str(read_temperature())
            data = "INPUT,CURRENT_TEMPERATURE," + sys.argv[3] + "," + string_temperature
            print(string_temperature)
            encode_encrypt_and_send_to_server(data)
            time.sleep(30)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((TCP_IP, TCP_PORT))

    if sys.argv[2] == "get_heating_on_off_status":
        data = "OUTPUT,CURRENT_HEATING_ON_OFF_STATUS," + sys.argv[3]
        encode_encrypt_and_send_to_server(data)
    
    if sys.argv[2] == "get_current_temperature_status":
        data = "OUTPUT,CURRENT_TEMPERATURE," + sys.argv[3] + "," + sys.argv[4]
        encode_encrypt_and_send_to_server(data)
 
    if sys.argv[2] == "set_target_temperature":
        data = "INPUT,SET_TARGET_TEMPERATURE," + sys.argv[3] + "," + str(sys.argv[4])
        encode_encrypt_and_send_to_server(data)
   
    if sys.argv[2] == "on":
        data = "INPUT,TURN_ON_HEATING," + sys.argv[3]
        encode_encrypt_and_send_to_server(data)
    
    if sys.argv[2] == "off":
        data = "INPUT,TURN_OFF_HEATING," + sys.argv[3]
        encode_encrypt_and_send_to_server(data)

def database_connection():
    global mydb
    mydb = mysql.connector.connect(
            host = "localhost",
            user = "phpmyadmin",
            password = "your-database-password-here",
            database = "heating"
            )

def pop_up_message_on_linux_pcs(icon, title, message):
    # Need to retrieve a list of PCs to show pop up message on and iterate through them
    call(["/usr/bin/ssh", "your-username@192.168.2.58", "export", "DISPLAY=:0", "&&", "notify-send", "-i", "%(ICON)s" % {'ICON': icon}, "'%(TITLE)s'" % {'TITLE': title}, "'%(MESSAGE)s'" % {'MESSAGE': message}])

# Define what happens when program started with parameters
if sys.argv[1] == "server":
    # Start server in thread to respond to querys for data input and output
    import rrdtool
    import mysql.connector
    database_connection()
    mycursor = mydb.cursor()
    server_thread = Thread(target = server)
    server_thread.start()
    check_target_temperature_reached_thread = Thread(target = check_target_temperature_reached)
    check_target_temperature_reached_thread.start()
    make_system_log_entry("INPUT", "SERVER_STARTUP")

if sys.argv[1] == "client":
    client()
