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

### Check transfer correctness
```bash
cmp -s input.txt output.txt && echo "PASS: files match" || echo "FAIL: files differ"
```

## Run without emulator (direct, zero added delay)

Use 2 terminals and skip `network_emulator.py`.

### Terminal 1: start receiver
```bash
python3 receiver.py localhost 9992 9994 output.txt
```

### Terminal 2: start sender
```bash
python3 sender.py localhost 9994 9992 input.txt
```

## Assumptions
- For simplicity and more insightful logs, a "new packet" count may include retransmissions.
- technically assignment didn't specify what to on inflight packets when when window shrinks due to ECN feedback. 
    - I made it drop inflight packets outside the new window
