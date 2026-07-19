"""
High-Dimensional Data Explorer (v2)
-------------------------------------
A small desktop app for beginners/intermediate learners.

What it does:
    1. Load a CSV file.
    2. Keep only the numeric columns and drop rows with missing values.
    3. Reduce the numeric data to 2 dimensions using PCA.
    4. Plot the 2D result with Matplotlib, right inside the window.
    5. If the file has a "target"/"label"/"class" column, use it to color
       the points. Otherwise, all points get one default color.

Libraries used: tkinter, pandas, matplotlib, scikit-learn (PCA only).
No classes, no extra windows, no themes/animations -- just plain
functions and a single Tk window, to keep things easy to follow.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import pandas as pd
import matplotlib
matplotlib.use("TkAgg")  # make sure matplotlib draws into a Tk widget
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from sklearn.decomposition import PCA


# ---------------------------------------------------------------------
# Simple shared state
# ---------------------------------------------------------------------
# Instead of a class, we just keep the "current data" in a few plain
# variables. This is fine for a small single-screen app like this one.
raw_df = None          # the CSV as loaded by pandas
numeric_df = None      # only numeric columns, missing rows dropped
pca_result = None      # 2D numpy array after PCA
color_labels = None    # values from target/label/class column, or None
color_column_name = None

CANDIDATE_LABEL_COLUMNS = ["target", "label", "class"]


# ---------------------------------------------------------------------
# Step 1: Load CSV
# ---------------------------------------------------------------------
def load_csv():
    """Open a file dialog, read the CSV, and reset the app state."""
    global raw_df, numeric_df, pca_result, color_labels, color_column_name

    file_path = filedialog.askopenfilename(
        title="Select a CSV file",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if not file_path:  # user cancelled the dialog
        return

    try:
        raw_df = pd.read_csv(file_path)
    except Exception as error:
        messagebox.showerror("Error Loading File", f"Could not read this CSV file.\n\n{error}")
        return

    if raw_df.empty:
        messagebox.showerror("Empty File", "The selected CSV file has no data.")
        raw_df = None
        return

    # Reset anything left over from a previous file
    numeric_df = None
    pca_result = None
    color_labels = None
    color_column_name = None
    clear_plot()

    # Show just the file name (not the whole path) to keep the UI tidy
    file_name = file_path.split("/")[-1].split("\\")[-1]
    file_name_var.set(f"File: {file_name}")

    update_info_text(
        f"Loaded '{file_name}'\n"
        f"Rows: {raw_df.shape[0]}\n"
        f"Columns: {raw_df.shape[1]}\n\n"
        f"Next: click 'Perform PCA'."
    )
    set_status("CSV loaded successfully.")


# ---------------------------------------------------------------------
# Step 2 & 3: Keep numeric columns, perform PCA
# ---------------------------------------------------------------------
def perform_pca():
    """Clean the loaded data down to numeric columns and run 2D PCA."""
    global numeric_df, pca_result, color_labels, color_column_name

    if raw_df is None:
        messagebox.showwarning("No Data", "Please load a CSV file first.")
        return

    # Look for an optional label/target column to use for coloring later.
    # We check this BEFORE dropping non-numeric columns, since label
    # columns are often text (e.g. "setosa", "versicolor").
    color_column_name = None
    for column in raw_df.columns:
        if column.strip().lower() in CANDIDATE_LABEL_COLUMNS:
            color_column_name = column
            break

    if color_column_name is not None:
        color_labels = raw_df[color_column_name]
    else:
        color_labels = None

    # Keep only numeric columns for PCA itself
    working_df = raw_df.select_dtypes(include="number").copy()

    # If the label column happened to be numeric (e.g. 0/1/2 classes),
    # it would end up in working_df too -- remove it so it isn't
    # treated as a "feature" during PCA.
    if color_column_name is not None and color_column_name in working_df.columns:
        working_df = working_df.drop(columns=[color_column_name])

    if working_df.shape[1] < 2:
        messagebox.showerror(
            "Not Enough Numeric Columns",
            "PCA needs at least 2 numeric columns (other than the label column) to work."
        )
        return

    # Handle missing values simply: drop any row containing NaN.
    # Also drop the matching rows from color_labels so the lengths stay equal.
    if color_labels is not None:
        combined = working_df.copy()
        combined["_label_"] = color_labels.values
        combined = combined.dropna()
        working_df = combined.drop(columns=["_label_"])
        color_labels = combined["_label_"]
    else:
        working_df = working_df.dropna()

    if working_df.shape[0] < 2:
        messagebox.showerror(
            "Not Enough Data",
            "Not enough complete numeric rows remain after removing missing values."
        )
        return

    numeric_df = working_df

    # Run PCA down to 2 components
    try:
        pca = PCA(n_components=2)
        pca_result = pca.fit_transform(numeric_df)
    except Exception as error:
        messagebox.showerror("PCA Error", f"Something went wrong while running PCA.\n\n{error}")
        pca_result = None
        return

    explained = pca.explained_variance_ratio_
    label_note = f"Coloring by column: '{color_column_name}'" if color_column_name else "No label column found (single color will be used)."

    update_info_text(
        f"PCA completed successfully.\n"
        f"Rows used: {numeric_df.shape[0]}\n"
        f"Numeric columns used: {numeric_df.shape[1]}\n"
        f"Explained variance (PC1, PC2): "
        f"{explained[0]*100:.1f}%, {explained[1]*100:.1f}%\n\n"
        f"{label_note}\n\n"
        f"Next: click 'Visualize'."
    )
    set_status("PCA completed. Ready to visualize.")


# ---------------------------------------------------------------------
# Step 4 & 5/6/7: Visualize the 2D PCA result
# ---------------------------------------------------------------------
def visualize():
    """Draw the 2D PCA scatter plot inside the window."""
    if pca_result is None:
        messagebox.showwarning("No PCA Result", "Please perform PCA before visualizing.")
        return

    figure.clear()
    plot = figure.add_subplot(111)

    x_values = pca_result[:, 0]
    y_values = pca_result[:, 1]

    if color_labels is not None:
        # Color points by their label/target/class value.
        # factorize() turns text or numeric labels into plain integers
        # so matplotlib can assign a color per group.
        codes, unique_labels = pd.factorize(color_labels)
        scatter = plot.scatter(x_values, y_values, c=codes, cmap="viridis", s=25)

        # Build a simple legend showing which color is which label
        handles, _ = scatter.legend_elements()
        if len(handles) == len(unique_labels):
            plot.legend(handles, list(unique_labels), title=color_column_name, loc="best", fontsize=8)
    else:
        # No label column found -- use one default color for every point
        plot.scatter(x_values, y_values, color="#3b82f6", s=25)

    plot.set_title("PCA - 2D Projection")
    plot.set_xlabel("Principal Component 1")
    plot.set_ylabel("Principal Component 2")
    figure.tight_layout()

    canvas.draw()
    set_status("Visualization ready.")


def clear_plot():
    """Erase whatever is currently drawn on the plot area."""
    figure.clear()
    canvas.draw()


# ---------------------------------------------------------------------
# Clear / Exit
# ---------------------------------------------------------------------
def clear_all():
    """Reset the app back to its starting state."""
    global raw_df, numeric_df, pca_result, color_labels, color_column_name

    raw_df = None
    numeric_df = None
    pca_result = None
    color_labels = None
    color_column_name = None

    file_name_var.set("File: (none selected)")
    update_info_text("No data loaded yet.\n\nClick 'Load CSV' to begin.")
    clear_plot()
    set_status("Cleared. Ready for a new file.")


def exit_app():
    root.destroy()


# ---------------------------------------------------------------------
# Small helper functions for the GUI text areas
# ---------------------------------------------------------------------
def set_status(message):
    status_var.set(message)


def update_info_text(message):
    info_text.config(state="normal")
    info_text.delete("1.0", tk.END)
    info_text.insert(tk.END, message)
    info_text.config(state="disabled")


# ---------------------------------------------------------------------
# GUI layout
# ---------------------------------------------------------------------
root = tk.Tk()
root.title("High-Dimensional Data Explorer (v2)")
root.geometry("900x600")
root.resizable(False, False)  # fixed-size window, as requested
root.configure(bg="#f5f6fa")

# --- Simple modern-ish styling for ttk widgets ---
style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", padding=6, font=("Segoe UI", 10))
style.configure("TLabel", background="#f5f6fa", font=("Segoe UI", 10))
style.configure("Title.TLabel", background="#f5f6fa", font=("Segoe UI", 14, "bold"))

# --- Title ---
title_label = ttk.Label(root, text="High-Dimensional Data Explorer (v2)", style="Title.TLabel")
title_label.pack(pady=(12, 4))

# --- Top bar: buttons ---
button_bar = ttk.Frame(root)
button_bar.pack(pady=6)

ttk.Button(button_bar, text="Load CSV", command=load_csv).grid(row=0, column=0, padx=5)
ttk.Button(button_bar, text="Perform PCA", command=perform_pca).grid(row=0, column=1, padx=5)
ttk.Button(button_bar, text="Visualize", command=visualize).grid(row=0, column=2, padx=5)
ttk.Button(button_bar, text="Clear", command=clear_all).grid(row=0, column=3, padx=5)
ttk.Button(button_bar, text="Exit", command=exit_app).grid(row=0, column=4, padx=5)

# --- File name display ---
file_name_var = tk.StringVar(value="File: (none selected)")
ttk.Label(root, textvariable=file_name_var).pack(pady=(4, 8))

# --- Main content area: info text (left) + plot (right) ---
content_frame = ttk.Frame(root)
content_frame.pack(fill="both", expand=True, padx=12)

# Left side: small text area with dataset / PCA info
info_frame = ttk.Frame(content_frame, width=260)
info_frame.pack(side="left", fill="y", padx=(0, 10))
info_frame.pack_propagate(False)

ttk.Label(info_frame, text="Dataset Info").pack(anchor="w", pady=(0, 4))

info_text = tk.Text(
    info_frame, height=18, width=32, wrap="word",
    bg="white", relief="solid", borderwidth=1,
    font=("Consolas", 9)
)
info_text.pack(fill="both", expand=True)
update_info_text("No data loaded yet.\n\nClick 'Load CSV' to begin.")
info_text.config(state="disabled")

# Right side: Matplotlib plot embedded in the window
plot_frame = ttk.Frame(content_frame)
plot_frame.pack(side="left", fill="both", expand=True)

figure = Figure(figsize=(5.5, 4.2), dpi=100)
canvas = FigureCanvasTkAgg(figure, master=plot_frame)
canvas.get_tk_widget().pack(fill="both", expand=True)

# --- Bottom status bar ---
status_var = tk.StringVar(value="Ready.")
status_label = ttk.Label(root, textvariable=status_var, relief="sunken", anchor="w")
status_label.pack(side="bottom", fill="x")


# ---------------------------------------------------------------------
# Run the app
# ---------------------------------------------------------------------
if __name__ == "__main__":
    root.mainloop()
