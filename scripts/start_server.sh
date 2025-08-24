#!/bin/bash

APP_DIR="/home/pi/Desktop/RPI_Desktop/CAN_web"

VENV_DIR="/home/pi/Desktop/RPI_Desktop/env"

cd $APP_DIR

source $VENV_DIR/bin/activate

$VENV_DIR/bin/python3 CanServer.py
