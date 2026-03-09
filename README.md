## Run a local end-to-end test

Use 3 terminals from this project root.

### Terminal 1: start network emulator
```bash
python3 network_emulator.py 9991 localhost 9994 9993 localhost 9992 0.05 10 1
```

### Terminal 2: start receiver
```bash
python3 receiver.py localhost 9993 9994 output.txt
```

### Terminal 3: start sender
```bash
python3 sender.py localhost 9991 9992 input.txt
```
