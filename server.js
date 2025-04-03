const express = require('express');
const bodyParser = require('body-parser');
const { DateTime } = require('luxon');
// npm install express body-parser luxon

const app = express();
app.use(bodyParser.json());

const intervalSeconds = 10
let deviceStatus = {}; // Store last heartbeat timestamps

// Add Root Route to Return 200 OK
app.get('/', (req, res) => {
    res.status(200).json({ message: "Server is running" });
});

// Route to receive heartbeat
app.post('/heartbeat', (req, res) => {
    const {
        device_id,
        device_status,
    } = req.body;
    if (device_id) {
        deviceStatus[device_id] = {
            last_time: DateTime.now(),
            ...device_status
        }; // Store last seen time
        return res.status(200).json({ status: 'ok' });
    } else {
        return res.status(400).json({ error: 'No device_id provided' });
    }
});

// Function to check inactive devices
function checkInactiveDevices() {
    const now = DateTime.now();
    const timeout = (intervalSeconds*1.2)/60; // Timeout threshold in a minutes

    const {inactiveDevices, activeDevice} = Object.entries(deviceStatus).reduce(
        (result, [device_id, status]) => {   // (callback, initialValue (key, value) )
            if (now.diff(status.last_time, 'minutes').minutes > timeout) {
                result.inactiveDevices[device_id] = status; // Group inactiveDevices
            } else {
                result.activeDevice[device_id] = status; // Group B: activeDevice
            }
            return result;
        },
        { inactiveDevices: {}, activeDevice: {} }
    );
    
    if (Object.entries(activeDevice).length > 0) {
        console.log(`active devices: ${JSON.stringify(activeDevice, null, 2)}`); // Log activeDevice
    }
    if (Object.entries(inactiveDevices).length > 0) {
        console.log(`!Inactive devices: ${JSON.stringify(inactiveDevices, null, 2)}`); // Log alerts
    }
}

// Background function to monitor inactive devices every 30 seconds
function monitorInactiveDevices() {
    setInterval(() => {
        checkInactiveDevices(); // Check and handle inactive devices
    }, intervalSeconds*1000); // Every 30 seconds
}

// Start the background task for checking inactive devices
monitorInactiveDevices();

// Start the server
const PORT = 5000;
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
