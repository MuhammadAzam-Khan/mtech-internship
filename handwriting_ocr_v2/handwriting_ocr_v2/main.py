"""
main.py
--------
Handwriting OCR (v2) - A simple beginner-friendly desktop app.

This app lets the user:
1. Upload an image (JPG / PNG / JPEG) containing handwritten text.
2. Preview the image inside the app.
3. Extract the text from the image using OCR (via ocr_helper.py).
4. View the extracted text in a text box.
5. Save the extracted text as a .txt file.
6. Clear everything and start over.

GUI Library : Tkinter
Image Handling : Pillow (PIL) + OpenCV (inside ocr_helper.py)
OCR Engine : EasyOCR (inside ocr_helper.py)
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# Import our own helper function for text extraction
from ocr_helper import extract_text_from_image


class HandwritingOCRApp:
    """
    This class represents the entire Handwriting OCR application.
    Keeping everything inside one class keeps the code organized.
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Handwriting OCR (v2)")
        self.root.geometry("900x600")
        self.root.resizable(False, False)
        self.root.configure(bg="#f4f6f8")

        # This will store the path of the currently uploaded image
        self.image_path = None

        # This will keep a reference to the preview image
        # (Tkinter requires us to keep a reference, otherwise it disappears)
        self.preview_image = None

        # Build all the GUI elements
        self.create_widgets()

    def create_widgets(self):
        """
        Creates and arranges all the buttons, labels, and text areas
        for the application window.
        """

        # ---------- Title Label ----------
        title_label = tk.Label(
            self.root,
            text="Handwriting OCR",
            font=("Segoe UI", 18, "bold"),
            bg="#f4f6f8",
            fg="#2c3e50"
        )
        title_label.pack(pady=10)

        # ---------- Top Frame (Buttons) ----------
        button_frame = tk.Frame(self.root, bg="#f4f6f8")
        button_frame.pack(pady=5)

        button_style = {
            "font": ("Segoe UI", 10),
            "width": 14,
            "bg": "#2c8bd6",
            "fg": "white",
            "activebackground": "#2372b5",
            "activeforeground": "white",
            "relief": "flat",
            "cursor": "hand2"
        }

        self.upload_btn = tk.Button(
            button_frame, text="Upload Image",
            command=self.upload_image, **button_style
        )
        self.upload_btn.grid(row=0, column=0, padx=5)

        self.extract_btn = tk.Button(
            button_frame, text="Extract Text",
            command=self.extract_text, **button_style
        )
        self.extract_btn.grid(row=0, column=1, padx=5)

        self.clear_btn = tk.Button(
            button_frame, text="Clear",
            command=self.clear_all, **button_style
        )
        self.clear_btn.grid(row=0, column=2, padx=5)

        self.save_btn = tk.Button(
            button_frame, text="Save Text",
            command=self.save_text, **button_style
        )
        self.save_btn.grid(row=0, column=3, padx=5)

        self.exit_btn = tk.Button(
            button_frame, text="Exit",
            command=self.root.quit,
            font=("Segoe UI", 10),
            width=14,
            bg="#e74c3c",
            fg="white",
            activebackground="#c0392b",
            activeforeground="white",
            relief="flat",
            cursor="hand2"
        )
        self.exit_btn.grid(row=0, column=4, padx=5)

        # ---------- Middle Frame (Image Preview + Text Box) ----------
        middle_frame = tk.Frame(self.root, bg="#f4f6f8")
        middle_frame.pack(pady=10, fill="both", expand=True)

        # Left side: Image preview area
        preview_container = tk.LabelFrame(
            middle_frame, text="Image Preview",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff", fg="#2c3e50",
            width=400, height=420
        )
        preview_container.pack(side="left", padx=15)
        preview_container.pack_propagate(False)  # keep fixed size

        self.image_label = tk.Label(preview_container, bg="#ffffff")
        self.image_label.pack(expand=True)

        # Right side: Extracted text box
        text_container = tk.LabelFrame(
            middle_frame, text="Extracted Text",
            font=("Segoe UI", 10, "bold"),
            bg="#ffffff", fg="#2c3e50",
            width=420, height=420
        )
        text_container.pack(side="left", padx=15)
        text_container.pack_propagate(False)

        # Scrollbar for the text box
        scrollbar = tk.Scrollbar(text_container)
        scrollbar.pack(side="right", fill="y")

        self.text_box = tk.Text(
            text_container,
            wrap="word",
            font=("Segoe UI", 11),
            yscrollcommand=scrollbar.set
        )
        self.text_box.pack(fill="both", expand=True, padx=5, pady=5)
        scrollbar.config(command=self.text_box.yview)

        # ---------- Bottom Status Label ----------
        self.status_label = tk.Label(
            self.root,
            text="Status: Waiting for image upload...",
            font=("Segoe UI", 10),
            bg="#dfe6e9",
            fg="#2d3436",
            anchor="w",
            padx=10
        )
        self.status_label.pack(side="bottom", fill="x")

    # ------------------------------------------------------------------
    # BUTTON FUNCTIONS
    # ------------------------------------------------------------------

    def upload_image(self):
        """
        Opens a file dialog for the user to choose an image.
        Then displays that image inside the preview area.
        """
        file_path = filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png")]
        )

        # If the user cancels the dialog, file_path will be empty
        if not file_path:
            return

        self.image_path = file_path

        try:
            # Open the image using Pillow
            img = Image.open(file_path)

            # Resize the image so it fits nicely inside the preview box
            img.thumbnail((380, 380))

            # Convert the image so Tkinter can display it
            self.preview_image = ImageTk.PhotoImage(img)

            # Show the image inside the label
            self.image_label.config(image=self.preview_image)

            self.update_status("Image uploaded successfully. Ready to extract text.")

        except Exception as error:
            messagebox.showerror("Error", f"Could not open image.\n{error}")
            self.update_status("Error: Failed to load image.")

    def extract_text(self):
        """
        Runs OCR on the uploaded image and displays the extracted text.
        """

        # Make sure an image has been uploaded first
        if not self.image_path:
            messagebox.showwarning("No Image", "Please upload an image first.")
            return

        self.update_status("Extracting text... please wait.")
        self.root.update()  # refresh the GUI so the status message shows immediately

        try:
            # Call our helper function from ocr_helper.py
            extracted_text = extract_text_from_image(self.image_path)

            # Clear the text box before adding new text
            self.text_box.delete("1.0", tk.END)

            if extracted_text.strip() == "":
                self.text_box.insert(tk.END, "No text detected in this image.")
                self.update_status("No text found.")
            else:
                self.text_box.insert(tk.END, extracted_text)
                self.update_status("Text extracted successfully.")

            messagebox.showinfo("Success", "Text extraction completed.")

        except Exception as error:
            messagebox.showerror("Error", f"OCR failed.\n{error}")
            self.update_status("Error: Text extraction failed.")

    def clear_all(self):
        """
        Clears the image preview, the text box, and resets the app state.
        """
        self.image_path = None
        self.preview_image = None
        self.image_label.config(image="")
        self.text_box.delete("1.0", tk.END)
        self.update_status("Cleared. Waiting for image upload...")

    def save_text(self):
        """
        Saves the extracted text (from the text box) into a .txt file
        chosen by the user.
        """
        text_content = self.text_box.get("1.0", tk.END).strip()

        if text_content == "":
            messagebox.showwarning("Nothing to Save", "There is no text to save yet.")
            return

        # Ask the user where to save the file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt")],
            title="Save Extracted Text"
        )

        if not file_path:
            return  # user cancelled

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(text_content)

            messagebox.showinfo("Saved", f"Text saved successfully to:\n{os.path.basename(file_path)}")
            self.update_status("Text saved successfully.")

        except Exception as error:
            messagebox.showerror("Error", f"Could not save file.\n{error}")
            self.update_status("Error: Failed to save text.")

    def update_status(self, message):
        """
        Small helper function to update the status label at the bottom.
        """
        self.status_label.config(text=f"Status: {message}")


# ------------------------------------------------------------------
# PROGRAM ENTRY POINT
# ------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = HandwritingOCRApp(root)
    root.mainloop()
