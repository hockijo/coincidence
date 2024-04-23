'''
A bokeh-based interface for Eric Ayars coincidence counter
First-draft attempt at controls, graphs and values.
'''

import numpy as np

import numpy.random as random
import time
from bokeh.io import curdoc
from bokeh.layouts import row, widgetbox, column
from bokeh.models import ColumnDataSource, Range1d
from bokeh.models.widgets import Slider, TextInput, Paragraph, Div
from bokeh.plotting import figure
from bokeh.models.widgets import Button


import serial
import serial.tools.list_ports

useSerial = False
# To debug away from the device. True connects for real, False uses fake data
# If the counter is not connected, you can set this to False in order to try it
# out, or edit the calculations etc.

if useSerial:
    # Use serial tools to find the port for the coincidence counter
    # this is based on the information for my device, I hope it's true in general
    # there is a small chance this will find something else on your usb bus too
    # but only if you have another device using the same UID/VID.
    EJAdevices = list(serial.tools.list_ports.grep("04b4:f232"))
    portstring = EJAdevices[0][0]
    print(portstring)
    s = serial.Serial(portstring,250000,timeout=2)

# Set up data variables and names
channels = ["A","B","B'","C"]
coinc = ["AB","AB'","NA","ABB'"]
counts = [0,0,0,0]
# create bokeh data sources for the two graphs
source = ColumnDataSource(data=dict(x=channels, y=counts))
source2 = ColumnDataSource(data=dict(x=coinc, y=counts))

# these lists will be filled with the raw data
a = []
b = []
ab = []
abp = []
abbp = []
bbp = []

# Set up plot
plot = figure(plot_height=360, plot_width=800, title="Single counts",
              tools="crosshair,pan,reset,save,wheel_zoom",
              x_range=channels, y_range=[0, 400000])

# colors are dark for use in the dark optics labs
plot.background_fill_color = "black"
plot.border_fill_color = "black"

plot.vbar(x='x', top='y', width=0.5, source=source, color="red")

plot2 = figure(plot_height=360, plot_width=800, title="Coincidence counts",
              tools="crosshair,pan,reset,save,wheel_zoom",
              x_range=coinc, y_range=[0, 40000])

plot2.background_fill_color = "black"
plot2.border_fill_color = "black"

plot2.vbar(x='x', top='y', width=0.5, source=source2, color="yellow")


# Set up widgets to control scale of plots
# TODO change these to actual range sliders
command = TextInput(title="Command Entry:", value='raw counts')
scalemin = Slider(title="A/B Scale min", value=0.0, start=0.0, end=1000.0, step=100)
scalemax = Slider(title="A/B Scale max", value=400000.0, start=1000.0, end=500000.0, step=100)
scalemin2 = Slider(title="AB Scale min", value=0.0, start=0.0, end=1000.0, step=100)
scalemax2 = Slider(title="AB Scale max", value=30000.0, start=1000.0, end=50000.0, step=100)

# other widgets (not all are used yet)
phase = Slider(title="phase", value=0.0, start=0.0, end=5.0, step=0.1)
points = Slider(title="data points", value=20, start=10, end=300, step=10, width=200)
statsA = Div(text="100", width=250, height=40, style={'font-size': '150%'})
statsB = Div(text="100", width=250, height=40, style={'font-size': '150%'})
statsAB = Div(text="100", width=250, height=40, style={'font-size': '150%'})
statsABP = Div(text="100", width=250, height=40, style={'font-size': '150%'})
statsABBP = Div(text="100", width=250, height=40, style={'font-size': '150%'})
g2 = Paragraph(text="100", width=200, height=80, style={'font-size': '150%'})
g2_2d = Paragraph(text="100", width=250, height=40, style={'font-size': '150%'})

# Additional widgets for logging data
filename_input = TextInput(title="Log Filename:", value="data_log.txt")
logging_duration = Slider(title="Logging Duration (seconds):", value=5, start=1, end=30, step=1)
start_logging_button = Button(label="Start Logging", button_type="success")
stop_logging_button = Button(label="Stop Logging", button_type="danger")
log_status = Div(text="Logging Status: Ready", width=200, height=30)

# Global variables for logging
logging_active = False
start_time = None

def start_logging():
    global logging_active, start_time
    logging_active = True
    start_time = time.time()
    log_status.text = "Logging Status: Logging..."

def stop_logging():
    global logging_active
    if logging_active:
        logging_active = False
        log_status.text = "Logging Status: Stopped"
        update_data()  # Ensure one final data write if still within time limit

def log_data(data):
    if logging_active:
        current_time = time.time()
        elapsed_time = current_time - start_time
        if elapsed_time < logging_duration.value:
            with open(filename_input.value, 'a') as file:
                file.write(f"{data}\n")
        else:
            stop_logging()

def send_command(command:str):
    """
    Send a command to the device.

    Args:
        command (str): The command to be sent.

    Returns:
        None
    """
    if useSerial:
        plot.title.text = command.value
        s.write(bytes(command, 'utf-8'))
        #response = read_response()

def read_response(query_delay=0.3):
    """
    Reads the response from the device and returns it. 

    Returns:
        str: The response from the device.
    
    """
    time.sleep(query_delay)
    response = s.readline().decode('utf-8').strip('\n')
    return response

#command.on_change('value', send_command)

last_time = time.time()

# start out keeping 20 data points
datapoints = 20

def update_data():
    # TODO: store data in a stream for charting vs time
    # this function is called every 100 ms (set below if you want to change it)

    # keep track of time interval for accurate counting calculations
    global last_time
    T = time.time() - last_time
    last_time = time.time()
    #print(T)

    # get data via serial (or fake):
    if useSerial:
        s.write("c\n".encode())
        serialData = s.readline()
        # AMCD divide by T to report in counts per second
        data = [int(x)/T for x in serialData.decode('ascii').rstrip().split(' ')]
        #print(data)
    else:
        mockdata = [57000,27000,27000,100,3000,3000,10,60,0]
        data = [(1 + 0.1*random.rand())*x for x in mockdata]

    raw = data[0:4]
    coinc = data[4:8]
    err = data[8]

    # populate the lists
    a.append(raw[0])
    b.append(raw[1])
    ab.append(coinc[0])
    abp.append(coinc[1])
    abbp.append(coinc[3])
    bbp.append(coinc[2]) # TODO fix the settings on coinc unit

    # resize this lists to keep only datapoints
    while len(a) > datapoints: a.pop(0)
    while len(b) > datapoints: b.pop(0)
    while len(ab) > datapoints: ab.pop(0)
    while len(abp) > datapoints: abp.pop(0)
    while len(abbp) > datapoints: abbp.pop(0)
    while len(bbp) > datapoints: bbp.pop(0)
    #print(a)

    # set the A and B count displays
    statsA.text = "A: %d +/- %d" % (np.mean(a), np.std(a))
    statsB.text = "B: %d +/- %d" % (np.mean(b), np.std(b))
    statsAB.text = "AB: %d +/- %d" % (np.mean(ab), np.std(ab))
    statsABP.text = "AB': %d +/- %d" % (np.mean(abp), np.std(abp))
    statsABBP.text = "ABB': %d +/- %d" % (np.mean(abbp), np.std(abbp))
    # calculate g(2):
    try:
        g2value = (np.sum(a)*np.sum(abbp)) / (np.sum(ab) * np.sum(abp))
        g2dev = g2value * np.sqrt((np.std(a) / np.mean(a))**2 +
                            (np.std(abbp) / np.mean(abbp))**2 +
                            (np.std(ab) / np.mean(ab))**2 +
                            (np.std(abp) / np.mean(abp))**2)
    except ValueError:
        print("value error calculating g2")
        g2value = 0
    try:
        g2.text = "g(2) = %3.2f +/- %4.3f" % ( g2value, g2dev )
    except ValueError:
        print("value error printing g2")
        g2.text = "g(2) = NaN"

    # calculate the 2-detector version (i.e. non-gated, classical light)
    try:
        g2_2d_value = (np.sum(bbp)*np.sum(abbp)) / (np.sum(ab) * np.sum(abp))
        g2_2d_dev = g2value * np.sqrt((np.std(a) / np.mean(a))**2 +
                            (np.std(abbp) / np.mean(abbp))**2 +
                            (np.std(ab) / np.mean(ab))**2 +
                            (np.std(abp) / np.mean(abp))**2)
    except ValueError:
        print("value error calculating g2")
        g2value = 0
    try:
        g2.text = "g(2) = %3.2f +/- %4.3f (%2.2f st.devs)" % ( g2value, g2dev, (1-g2value)/g2dev )
    except ValueError:
        print("value error printing g2")
        g2.text = "g(2) = NaN"

    # If logging is active, log the data
    if logging_active:
        data_to_log = [raw[0], raw[1], coinc[0], coinc[1], coinc[2], coinc[3], err]
        if g2value and g2dev:
            data_to_log.append(g2value)
            data_to_log.append(g2dev)
        if g2_2d_value and g2_2d_dev:
            data_to_log.append(g2_2d_value)
            data_to_log.append(g2_2d_dev)
        log_data(data)  # Pass the raw or processed data for logging

    #print(raw)

    plot.title.text = "A:%d B:%d" % (raw[0], raw[1])

    # Generate the new plots
    channels = ["A","B","B'","C"]
    chan2 = ["AB","AB'","NA","ABB'"]

    source.data = dict(x=channels, y=raw)
    source2.data = dict(x=chan2, y=coinc)

def update_scales(attrname, old, new):
    global datapoints

    # Get the current slider values
    smin = scalemin.value
    smax = scalemax.value
    s2max = scalemax2.value
    s2min = scalemin2.value
    w = phase.value
    datapoints = points.value

    plot.y_range.start = smin
    plot.y_range.end = smax
    plot2.y_range.start = s2min
    plot2.y_range.end = s2max

# Add on_change listener to each widget that we're using:
for w in [scalemin, scalemax, scalemin2, scalemax2, points]:
    w.on_change('value', update_scales)


# Set up layouts and add to document
countControls = column(command, scalemin, scalemax, width=150)
coincControls = column(scalemin2,scalemax2, width=150)

# build the app document, this is just layout control and arranging the interface
curdoc().add_root(row(countControls, plot, column(statsA, statsB, statsAB, statsABP, statsABBP, g2, points), width=1200))
curdoc().add_root(row(coincControls, plot2, width=1200))
curdoc().title = "Coincidence"

start_logging_button.on_click(start_logging)
stop_logging_button.on_click(stop_logging)

# Adjust layout to include logging controls
logging_controls = column(filename_input, logging_duration, start_logging_button, stop_logging_button, log_status)

curdoc().add_root(row(logging_controls, width=400))
# Add this row wherever you want the logging controls to appear in your layout

# set the callback to pull the data every 100 ms:
curdoc().add_periodic_callback(update_data, 100)
