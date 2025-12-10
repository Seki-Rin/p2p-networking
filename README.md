# p2p-networking
## Description
lightweight, fully decentralized async P2P framework for local networks.  
Provides peer discovery, direct TCP connectivity and reliable message delivery with no central server.

## Features
- UDP broadcast-based peer discovery with timeout & cleanup  
- Direct bidirectional TCP connections (active/passive) with keep-alive and auto-reconnect  
- EventBus publishing `NodeDiscoveredEvent`, `NodeLostEvent`, `MessageReceivedEvent`  
- Persistent UUID node identifier (config.ini)  
- Length-prefixed message framing (4-byte big-endian)  
- Pure asyncio implementation  
- Minimal reference GUI (FastAPI + WebSocket) for demo purposes  
- Dependencies: `fastapi`, `uvicorn[standard]`, `netifaces`, `pydantic`, `websockets`

## How To Install

Linux/Mac:

1. Clone the repo:
```bash
git clone https://github.com/Seki-Rin/p2p-networking.git
```
2. Navigate to the project folder:
```bash
cd p2p-networking
```
3. Create the virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate
```
4. Install dependencies:
```bash
pip install .
```


Windows:

1. Clone the repo:
```bash
git clone https://github.com/Seki-Rin/p2p-networking.git
```
2. Navigate to the project folder:
```bash
cd p2p-networking
```
3. Create the virtual environment (recommended):
```bash
python3 -m venv venv
venv\Scripts\activate
```
4. Install dependencies:
4.1 Install with C++ Build Tools:
Install "Microsoft C++ Build tools v14.0" for compile `netifaces` framework.
Then, install all dependencies:
```bash
pip install .
```
4.2 Use appropriate ".whl" for your system and python. You can download the pre-compiled wheel file for `netifaces` at: https://www.cgohlke.com
```bash
pip install path/to/your/version/netifaces.whl
pip install .
```

# How to run
1. Activate the virtual environment (if it's not activated):
Linux/Mac:
```bash
source venv/bin/activate
```
Windows:
```bash
venv\Scripts\activate
```
2. Run the code:
```bash
cd src
python3 -m p2p_networking.main
```
Then, you can navigate to http://127.0.0.1:8000 in your browser to view the minimal GUI and monitor peer activity.