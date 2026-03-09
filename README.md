# Terminal 1: start network emulator
```bash
python3 network_emulator.py 9991 localhost 9994 9993 localhost 9992 0.05 10 1
```

# Terminal 2: start receiver
```bash
python3 receiver.py localhost 9993 9994 output.txt
```

# Terminal 3: start sender
```bash
python3 sender.py localhost 9991 9992 input.txt
```


## Assumptions
- For simplicity and more insightful logs, a "new packet" counts retransmissions as an event that updates timestamp.
- technically assignment didn't specify what to do on inflight packets when when window shrinks due to ECN feedback. 
    - I made it drop inflight packets outside the new window
