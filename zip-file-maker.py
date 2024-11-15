import os
import zipfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import zlib
import bz2
import lzma
import struct
from collections import Counter
import heapq
import io
import binascii

class AdvancedCompression:
    def __init__(self):
        self.chunk_size = 1024 * 1024  # 1MB chunks for large files
        
    def analyze_data(self, data):
        """Analyze data to determine best compression method."""
        # Calculate entropy to determine data complexity
        entropy = self._calculate_entropy(data[:4096])  # Sample first 4KB
        
        # Check if data is already compressed
        if self._is_compressed(data[:4096]):
            return 'store'  # Don't compress already compressed files
            
        # Choose compression method based on entropy and size
        if len(data) < 1024:  # Small files
            return 'zlib'
        elif entropy > 7.5:  # High entropy (complex data)
            return 'lzma'
        elif entropy > 6.5:  # Medium entropy
            return 'bzip2'
        else:  # Low entropy
            return 'zlib'
    
    def _calculate_entropy(self, data):
        """Calculate Shannon entropy of data."""
        if not data:
            return 0
        
        counts = Counter(data)
        total = len(data)
        entropy = 0
        
        for count in counts.values():
            probability = count / total
            entropy -= probability * (probability.bit_length())
        
        return entropy
    
    def _is_compressed(self, data):
        """Check if data is already compressed."""
        # Check for common compression signatures
        compression_signatures = [
            b'PK\x03\x04',  # ZIP
            b'\x1f\x8b',    # GZIP
            b'BZh',         # BZIP2
            b'\xFD7zXZ',    # XZ
            b'\x89PNG',     # PNG
            b'\xFF\xD8\xFF', # JPEG
        ]
        
        return any(data.startswith(sig) for sig in compression_signatures)
    
    def preprocess_text(self, data):
        """Preprocess text data for better compression."""
        try:
            # Try to decode as text
            text = data.decode('utf-8')
            
            # Remove redundant whitespace
            text = ' '.join(text.split())
            
            # Convert to lowercase for better compression if it's all text
            if text.isalnum():
                text = text.lower()
            
            return text.encode('utf-8')
        except UnicodeDecodeError:
            return data  # Return original if not valid text
    
    def compress_data(self, data, method='auto'):
        """Compress data using the most effective method."""
        if method == 'auto':
            method = self.analyze_data(data)
        
        # Preprocess data if it's text
        if method != 'store' and not self._is_compressed(data[:4096]):
            data = self.preprocess_text(data)
        
        compressed = None
        compression_method = ''
        
        try:
            if method == 'store':
                return data, 'store'
            
            elif method == 'zlib':
                # Try different compression levels
                best_compressed = data
                best_level = 6
                
                for level in [1, 6, 9]:
                    try_compressed = zlib.compress(data, level)
                    if len(try_compressed) < len(best_compressed):
                        best_compressed = try_compressed
                        best_level = level
                
                compressed = best_compressed
                compression_method = f'zlib-{best_level}'
            
            elif method == 'bzip2':
                compressed = bz2.compress(data, compresslevel=9)
                compression_method = 'bzip2'
            
            elif method == 'lzma':
                filters = [
                    {'id': lzma.FILTER_LZMA2, 'preset': 9}
                ]
                compressed = lzma.compress(data, format=lzma.FORMAT_RAW, filters=filters)
                compression_method = 'lzma'
            
            # Return original data if compression didn't help
            if compressed and len(compressed) < len(data):
                return compressed, compression_method
            return data, 'store'
            
        except Exception as e:
            print(f"Compression error: {str(e)}")
            return data, 'store'

class ZipMakerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Zip Maker")
        self.root.geometry("800x600")
        self.root.configure(padx=20, pady=20)
        
        # Initialize compression engine
        self.compression_engine = AdvancedCompression()
        
        # Initialize variables
        self.files_to_zip = []
        self.compression_method = tk.StringVar(value='auto')
        self.is_processing = False
        
        self.create_widgets()
    
    def create_widgets(self):
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True)
        
        # File selection frame
        file_frame = ttk.LabelFrame(main_container, text="File Selection", padding=10)
        file_frame.pack(fill='x', pady=(0, 10))
        
        # Buttons frame
        buttons_frame = ttk.Frame(file_frame)
        buttons_frame.pack(fill='x', pady=5)
        
        # Add file button
        self.add_button = ttk.Button(buttons_frame, text="Add Files", command=self.add_files)
        self.add_button.pack(side='left', padx=5)
        
        # Clear files button
        self.clear_button = ttk.Button(buttons_frame, text="Clear Files", command=self.clear_files)
        self.clear_button.pack(side='left', padx=5)
        
        # Compression method selection
        compression_frame = ttk.LabelFrame(main_container, text="Compression Settings", padding=10)
        compression_frame.pack(fill='x', pady=(0, 10))
        
        methods = [
            ('Automatic', 'auto'),
            ('ZLIB', 'zlib'),
            ('BZIP2', 'bzip2'),
            ('LZMA', 'lzma'),
            ('Store Only', 'store')
        ]
        
        for text, value in methods:
            ttk.Radiobutton(
                compression_frame,
                text=text,
                value=value,
                variable=self.compression_method
            ).pack(side='left', padx=10)
        
        # Files listbox frame with size info
        list_frame = ttk.LabelFrame(main_container, text="Selected Files", padding=10)
        list_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Create tree view for files
        self.tree = ttk.Treeview(
            list_frame,
            columns=('size', 'path'),
            show='headings',
            selectmode='extended'
        )
        
        # Configure columns
        self.tree.heading('size', text='Size')
        self.tree.heading('path', text='File Path')
        self.tree.column('size', width=100)
        self.tree.column('path', width=500)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_container, text="Progress", padding=10)
        progress_frame.pack(fill='x', pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill='x')
        
        # Status label
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.pack(fill='x', pady=(5, 0))
        
        # Create zip button
        self.create_button = ttk.Button(
            main_container,
            text="Create Zip File",
            command=self.create_zip_threaded
        )
        self.create_button.pack(fill='x')
    
    def format_size(self, size):
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def add_files(self):
        """Open file dialog and add selected files to the list."""
        files = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=[("All Files", "*.*")]
        )
        
        for file in files:
            if file not in self.files_to_zip:
                self.files_to_zip.append(file)
                size = os.path.getsize(file)
                self.tree.insert('', 'end', values=(
                    self.format_size(size),
                    file
                ))
    
    def clear_files(self):
        """Clear all files from the list."""
        self.files_to_zip.clear()
        self.tree.delete(*self.tree.get_children())
    
    def create_zip_threaded(self):
        """Start zip creation in a separate thread."""
        if not self.files_to_zip:
            messagebox.showwarning("Warning", "No files selected!")
            return
        
        if self.is_processing:
            messagebox.showwarning("Warning", "Already processing!")
            return
        
        output_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("Zip files", "*.zip")],
            title="Save Zip File As"
        )
        
        if output_path:
            self.is_processing = True
            self.update_buttons_state()
            threading.Thread(
                target=self.create_zip,
                args=(output_path,),
                daemon=True
            ).start()
    
    def create_zip(self, output_path):
        """Create a zip file containing all added files."""
        try:
            total_files = len(self.files_to_zip)
            original_size = 0
            compressed_size = 0
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for index, file_path in enumerate(self.files_to_zip, 1):
                    self.update_status(f"Processing: {os.path.basename(file_path)}")
                    
                    with open(file_path, 'rb') as f:
                        data = f.read()
                    
                    original_size += len(data)
                    method = self.compression_method.get()
                    
                    if method != 'store':
                        compressed_data, used_method = self.compression_engine.compress_data(
                            data,
                            method=method
                        )
                        
                        arc_name = os.path.basename(file_path)
                        if used_method != 'store':
                            arc_name = f"{arc_name}.{used_method}"
                        
                        zipf.writestr(arc_name, compressed_data)
                        compressed_size += len(compressed_data)
                    else:
                        zipf.write(file_path, os.path.basename(file_path))
                        compressed_size += os.path.getsize(file_path)
                    
                    progress = (index / total_files) * 100
                    self.update_progress(progress)
            
            # Calculate and show compression ratio
            ratio = (1 - (compressed_size / original_size)) * 100
            message = (f"Zip file created successfully!\n"
                      f"Original size: {self.format_size(original_size)}\n"
                      f"Compressed size: {self.format_size(compressed_size)}\n"
                      f"Compression ratio: {ratio:.1f}%")
            
            self.update_status(message)
            messagebox.showinfo("Success", message)
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Error creating zip file: {str(e)}")
        
        finally:
            self.is_processing = False
            self.update_buttons_state()
            self.update_progress(0)
    
    def update_progress(self, value):
        """Update progress bar value."""
        self.progress_var.set(value)
        self.root.update_idletasks()
    
    def update_status(self, message):
        """Update status label text."""
        self.status_label.config(text=message)
        self.root.update_idletasks()
    
    def update_buttons_state(self):
        """Update buttons state based on processing status."""
        state = 'disabled' if self.is_processing else 'normal'
        self.add_button.config(state=state)
        self.clear_button.config(state=state)
        self.create_button.config(state=state)

def main():
    root = tk.Tk()
    app = ZipMakerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()