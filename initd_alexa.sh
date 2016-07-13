#!/bin/bash

get_alexa_pid () {
    export ALEXA_PID=$(ps aux | egrep '^pi.*AlexaPi/main.py' | grep -v grep | awk '{print $2}')
}

case "$1" in

start)
    echo "$(date +%Y%m%d_%H%M%S) Starting Alexa" >> /var/log/alexa
    # Using stdbuf to unbuffer output
    sudo -i -u pi stdbuf -o0 python /home/pi/AlexaPi/main.py >> /var/log/alexa 2>&1 &
;;

status)
    get_alexa_pid
    if [ -z "${ALEXA_PID}" ]; then
        echo "Alexa Stopped"
    else
        echo "Alexa Running with PID: ${ALEXA_PID}"
    fi
;;

stop)
    get_alexa_pid
    echo "$(date +%Y%m%d_%H%M%S) Stopping Alexa PID: ${ALEXA_PID}" >> /var/log/alexa
    kill -SIGINT ${ALEXA_PID}
;;

restart|force-reload)
        echo "Restarting Alexa.."
        $0 stop
        sleep 2
        $0 start
        echo "Restarted."
;;
*)
        echo "Usage: $0 {start|stop|restart}"
        exit 1
esac
