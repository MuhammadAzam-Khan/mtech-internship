# High-Dimensional Data Explorer (v2)

A small desktop app that loads a CSV file, reduces it to 2 dimensions
using PCA, and shows the result as a scatter plot -- all inside one
simple Tkinter window.


## Folder contents

```
HDDE_Project/
├── main.py              <- the program itself (run this)
├── requirements.txt     <- the 3 packages it needs (pandas, matplotlib, scikit-learn)
├── run_windows.bat       <- double-click to run on Windows
├── run_mac_linux.sh      <- run this to launch on Mac or Linux
├── sample_data/
│   └── sample_iris_dataset.csv   <- a ready-made file to try the app with
└── README.md             <- this file
```


## Requirements

- **Python 3.8 or newer**, downloaded from https://www.python.org/downloads/
  - Tkinter comes built into Python already on Windows and Mac.
    On some Linux distributions it needs to be installed separately --
    see the "Linux: if tkinter is missing" section below.
- The following packages, installed automatically by the launcher scripts
  (or manually, see below): `pandas`, `matplotlib`, `scikit-learn`


## How to run it

### Option A -- Windows

Double-click **`run_windows.bat`**.

It will:
1. Look for Python on your computer.
2. Install the required packages if they aren't already installed.
3. Launch the program.

A console window will stay open so you can read any messages -- press
any key to close it once you're done.

### Option B -- Mac or Linux

Open a terminal in this folder and run:

```bash
./run_mac_linux.sh
```

If you get a "permission denied" message the first time, run this once:

```bash
chmod +x run_mac_linux.sh
```

then try `./run_mac_linux.sh` again.

### Option C -- Run it manually (any operating system)

If you'd rather do it by hand, or the scripts above don't work on your
machine, just run these two commands from inside this folder:

```bash
pip install -r requirements.txt
python main.py
```

(On some systems you may need `pip3` and `python3` instead of `pip`
and `python`.)


## Using the app

1. Click **Load CSV** and choose a file. You can start with the sample
   file in `sample_data/sample_iris_dataset.csv` to see how it works.
2. Click **Perform PCA**. The app automatically keeps only numeric
   columns and drops any rows with missing values before running PCA.
3. Click **Visualize** to see the 2D scatter plot.
   - If your CSV has a `target`, `label`, or `class` column, the
     points will be colored by that column with a legend.
   - If not, all points are shown in one default color.
4. Click **Clear** to reset and load a different file, or **Exit** to close.


## Troubleshooting

**"Python was not found"**
Install Python from https://www.python.org/downloads/. On Windows,
make sure to tick "Add Python to PATH" during setup.

**Linux: if tkinter is missing**
Some Linux distributions ship Python without Tkinter. If you see an
error mentioning `tkinter` when the program starts, install it with:

```bash
sudo apt install python3-tk        # Debian/Ubuntu
sudo dnf install python3-tkinter   # Fedora
```

**"externally-managed-environment" pip error**
This shows up on some newer Linux systems and just means your system
protects its main Python install. The launcher scripts already handle
this automatically by retrying with `--user`. If you're installing
manually, use:

```bash
pip install -r requirements.txt --user
```

**The window looks too small / cut off**
The window has a fixed size of 900x600 by design (per the project
requirements) so it displays consistently. If your screen's display
scaling is set very high, you can lower it in your OS display settings,
or edit the `root.geometry("900x600")` line near the bottom of
`main.py` to a size that suits your screen.
