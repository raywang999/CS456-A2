# Running and Testing
## Terminal 1: start network emulator
- on `ubuntu2404-002.student.cs.uwaterloo.ca` run
```bash
python3 network_emulator.py 6101 ubuntu2404-004.student.cs.uwaterloo.ca 6104 6103 ubuntu2404-006.student.cs.uwaterloo.ca 6102 0.05 10 1
```

## Terminal 2: start receiver 
- on `ubuntu2404-004.student.cs.uwaterloo.ca` run 
```bash
python3 receiver.py ubuntu2404-002.student.cs.uwaterloo.ca 6103 6104 output.txt
```

## Terminal 3: start sender
- on `ubuntu2404-006.student.cs.uwaterloo.ca` run 
```bash
python3 sender.py ubuntu2404-002.student.cs.uwaterloo.ca 6101 6102 input.txt
```


# Assumptions
- For simplicity and more insightful logs, a "new packet" counts retransmissions as an event that updates timestamp.
- technically assignment didn't specify what to do on inflight packets when when window shrinks due to ECN feedback. 
    - I made it drop inflight packets outside the new window


# References 
- Looked at the Timer and Lock sections of the python threading library: https://docs.python.org/3/library/threading.html#using-locks-conditions-and-semaphores-in-the-with-statement
- copied some of the argparse code from A1
