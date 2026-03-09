# EweGo Web Interface

This application allows for raspberry pi devices connected to the same mdns server to have their system health displayed locally within an 
interative web dashboard hosted via Python FLASK

![Dashboard](templates/EweGoUIWithData(1).png)

## Features

- ✅ Allows for recording/syncing files while in runtime
- ✅ Status of recording and file synching
- ✅ Disk Usage
- ✅ Memory Usage
- ✅ Latency 
- ✅ GPS attributes (Latittude, Longitude, Altitude)
- ✅ Current Battery level


## Quick Start (On the Raspberry Pi)

### Step 1: Set env for project on raspberry pi

```bash
python source venv/bin/activate
```

### Step 2: Run pi_app.py

```bash
python3 pi_app.py
```

### Step 3: Curl api/health to esnure connection is stable (in second terminal)

```bash
curl https://localhost:5000/api/health
```

### Step 4: Start mdns script

```bash
python3 mdns_setup.py
```

### Step 5: Test raspberry pi self-ping

```bash
ping <raspberry pi name>.local
```

## Quick Start (On the local computer)

### Step 1: Test raspberry pi ping from terminal (ensures both devices are reachable)

```bash
ping <raspberry pi name>.local
```

### Step 2: Run dashboard_app.py

```bash
python3 dashboard_app.py
```

## License

Free to use and modify as needed.
