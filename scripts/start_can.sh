#!/bin/bash

sudo ip link set can0 down
sudo ip link set can0 type can bitrate 1000000 loopback on
sudo ifconfig can0 txqueuelen 65536
sudo ip link set can0 up
