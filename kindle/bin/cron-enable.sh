 ./cron-disable.sh
 2 
 3 mntroot rw
 4 rm -f cron.bak
 5 cp /etc/crontab/root ./cron.bak
 6 echo "*/5 * * * * /mnt/us/extensions/kindle-weather/bin/display-weather.sh" >>/etc/crontab/root
