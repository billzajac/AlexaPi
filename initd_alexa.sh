#! /bin/bash

exec >> /var/log/alexa.log 2>&1 
case "$1" in

start)
    echo "Starting Alexa..."
    stdbuf -o0 python /home/chip/AlexaPi/main.py &

;;

stop)
    echo "Stopping Alexa.."
    kill -SIGINT $(ps aux | egrep 'AlexaPi/main.py' | grep -v grep | awk '{print $2}')
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
