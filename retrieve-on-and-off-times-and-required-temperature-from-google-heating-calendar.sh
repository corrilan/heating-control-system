#!/bin/bash

GCALCLI_PATH="/usr/bin/gcalcli"
CODE_PATH="/home/pi/heating-control-system"

# Write out current crontab
crontab -l > $CODE_PATH/original-cron

# Find out how many lines are in crontab, static line count is 6
CRONTAB_LINES=`/usr/bin/crontab -l | wc --lines`
echo "Lines in crontab $CRONTAB_LINES"

# Work out lines to delete in crontab
let "CRONTAB_LINES_TO_DELETE = CRONTAB_LINES - 6"
echo $CRONTAB_LINES_TO_DELETE

# Delete yesterdays on and off times
head -n -$CRONTAB_LINES_TO_DELETE $CODE_PATH/original-cron > $CODE_PATH/new-cron

RAW=`$GCALCLI_PATH --tsv --detail_length --nocache --calendar 'Heating' agenda 12am 11.59pm`

echo "Trying to retrieve heating schedule..."
echo $RAW

# If no on time is defined on Google Calendar, or if Google was unobtainable, then set a dummy schedule so heating remains off and under manual control, then quit the script
if [[ -z $RAW ]] || [[ $RAW == *"No Events Found..."* ]]
then
	RAW="dummy"
	echo "Setting default"

	# Echo new cron items into crontab file
	echo '0 1 * * * /bin/echo DUMMY' >> $CODE_PATH/new-cron
		
	# Install new crontab file
	crontab $CODE_PATH/new-cron

	# Clean up temporary crontab files
	rm $CODE_PATH/original-cron $CODE_PATH/new-cron
	
	exit
fi

echo "$RAW"

while read -r line; do
	# Get the required temperature
	REQUIRED_TEMPERATURE=`echo $line | awk -F ' ' '{print $5}'`
	echo Required temperature $REQUIRED_TEMPERATURE 
	# Convert the retrieved on time and duration to crontab compatible times
	ON_TIME_RAW=`echo $line | awk -F ' ' '{print $2}'`
	echo On time raw $ON_TIME_RAW
	OFF_TIME_RAW=`echo $line | awk -F ' ' '{print $4}'`
	echo Off time raw $OFF_TIME_RAW
	ON_TIME_24HR_H=`/bin/date -d "$ON_TIME_RAW" +'%H'`
	echo On time 24 H $ON_TIME_24HR_H
	ON_TIME_24HR_M=`/bin/date -d "$ON_TIME_RAW" +'%M'`
	echo On time 24 M $ON_TIME_24HR_M
	OFF_TIME_24HR_H=`/bin/date -d "$OFF_TIME_RAW" +'%H'`
	echo On time 24 H $OFF_TIME_24HR_H
	OFF_TIME_24HR_M=`/bin/date -d "$OFF_TIME_RAW" +'%M'`
	echo On time 24 M $OFF_TIME_24HR_M

	# Echo new cron items into crontab file
	echo "$ON_TIME_24HR_M $ON_TIME_24HR_H * * * /usr/bin/python3.5 /home/pi/heating-control-system/thermostat.py client set_target_temperature lounge $REQUIRED_TEMPERATURE" >> $CODE_PATH/new-cron
	echo "$ON_TIME_24HR_M $ON_TIME_24HR_H * * * /usr/bin/python3.5 /home/pi/heating-control-system/thermostat.py client on calendar-via-cron" >> $CODE_PATH/new-cron
	echo "$OFF_TIME_24HR_M $OFF_TIME_24HR_H * * * /usr/bin/python3.5 /home/pi/heating-control-system/thermostat.py client off calendar-via-cron" >> $CODE_PATH/new-cron
done <<< "$RAW"

# Install new crontab file
crontab $CODE_PATH/new-cron

# Clean up temporary crontab files
rm $CODE_PATH/original-cron $CODE_PATH/new-cron
