#!/bin/bash
set -e

PI_IP="192.168.1.8"
PI_USER="mohamed-ayman"
PI_PASS="mohamed2004"

echo "=== Deploying CODESYS SoftPLC to Raspberry Pi 4B ($PI_IP) ==="

# 1. Create runtime directory on Pi
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_IP" "mkdir -p /home/$PI_USER/codesys_runtime"

# 2. Copy files to Pi
sshpass -p "$PI_PASS" scp -o StrictHostKeyChecking=no codesys_pi/codesys_softplc.py "$PI_USER@$PI_IP:/home/$PI_USER/codesys_runtime/"
sshpass -p "$PI_PASS" scp -o StrictHostKeyChecking=no codesys_pi/codesys-plc.service "$PI_USER@$PI_IP:/home/$PI_USER/codesys_runtime/"

# 3. Install systemd service
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_IP" "echo $PI_PASS | sudo -S cp /home/$PI_USER/codesys_runtime/codesys-plc.service /etc/systemd/system/ && echo $PI_PASS | sudo -S systemctl daemon-reload && echo $PI_PASS | sudo -S systemctl enable --now codesys-plc"

# 4. Check status
echo "=== CODESYS SoftPLC Service Status ==="
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no "$PI_USER@$PI_IP" "echo $PI_PASS | sudo -S systemctl status codesys-plc --no-pager"

echo "=== Deployment to Raspberry Pi Complete! ==="
