cd /home/onionperf

touch /home/onionperf/measure.log
touch /home/onionperf/analyze.log

#crontab -l | { cat; echo "55 2 * * * pkill -INT onionperf 2>&1"; } | crontab -
#crontab -l | { cat; echo "56 2 * * * mkdir -p /home/onionperf/results/\$(date +\%Y-\%m-\%d) && /home/onionperf/venv/bin/onionperf analyze --tgen /root/onionperf-data/tgen-client/onionperf.tgen.log --torctl /root/onionperf-data/tor-client/onionperf.torctl.log -p /home/onionperf/results/\$(date +\%Y-\%m-\%d) >> /home/onionperf/analyze.log 2>&1"; } | crontab -
#crontab -l | { cat; echo "0 3 * * * /home/onionperf/venv/bin/onionperf measure --tgen /home/onionperf/tgen/build/src/tgen --tor /home/onionperf/ator-protocol/src/app/anon --tgen-listen-port 9510 --tgen-connect-port 9520 >> /home/onionperf/measure.log 2>&1"; } | crontab -

onionperf measure --tgen /home/onionperf/tgen/build/src/tgen --tor /home/onionperf/ator-protocol/src/app/anon --tgen-listen-port 9510 --tgen-connect-port 9520

#service cron start
#tail -f /home/onionperf/measure.log