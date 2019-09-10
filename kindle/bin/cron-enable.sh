./cron-disable.sh
 
mntroot rw
rm -f cron.bak
cp /etc/crontab/root ./cron.bak
echo "45 * * * * /mnt/us/extensions/kindle-weather/bin/display-weather.sh" >>/etc/crontab/root
restart cron