export NICKNAME=${NOMAD_IP_http_port:-"Unnamed"}
echo "Starting OnionPerf with nickname: ${NICKNAME}"
onionperf measure -n ${NICKNAME} --tgen /home/onionperf/tgen/build/src/tgen --tor /usr/sbin/anon --tgen-listen-port 9510 --tgen-connect-port 9520
