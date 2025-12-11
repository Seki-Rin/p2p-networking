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
```
4. Activate virtual environment:

Linux:
```bash
source venv/bin/activate
```

Windows:
```bash
venv\Scripts\activate
```
4. Install dependencies:

For Python 3.9 (or older), you can install all dependencies directly — no C++ build tools are required:
```bash
pip install .
```
For Python 3.10+ netifaces not have precompiled wheels for your Python version.
In this case, you need to install C/C++ build tools first:
Windows: Microsoft C++ Build Tools v14+
Linux: `build-essential` and `python3-dev`
macOS: Xcode Command Line Tools



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